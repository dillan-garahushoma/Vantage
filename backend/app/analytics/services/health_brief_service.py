"""The estate health brief service (BATCH AI-4).

Turns the latest **stored** Living Score snapshot into a short plain-English
brief. The AI layer explains; it never calculates, never sees resident text and
never decides anything. With AI off, or with any failure, this service answers
with the same shape built deterministically from the snapshot.

The rules, all enforced here:

* **Authorization first.** A read needs membership; a generate needs the global
  ``hoa_admin`` role *and* a membership of that estate; feedback needs
  membership. The estate always arrives as an ``estate_id`` argument that was
  authorized, never as a body field.
* **Stored snapshots only.** Every number is projected from a snapshot row and the
  two comparison snapshots. Nothing re-runs the score engine, so a brief cannot
  disagree with the score it describes, and no aggregate query is issued.
* **AI is never load-bearing.** Any ``AIUnavailableError``, schema failure or
  grounding failure returns the template with 200 and a closed reason code. No
  brief is stored on a failure, so a later attempt can still succeed.
* **Nothing half-written.** A successful generate commits once. The one other
  commit is the failure path's, which only persists the AI call ledger's audit
  row - see ``_record_attempt``.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Final

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.ai.brief_facts import BriefFacts, build_brief_facts
from app.analytics.ai.brief_output import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    BriefOutput,
    brief_output_schema,
    build_user_prompt,
)
from app.analytics.ai.grounding import GroundingViolation, validate_grounding
from app.analytics.ai.template import build_template_brief
from app.analytics.domain.insight_vocabulary import KIND_HEALTH_BRIEF, data_origin_for
from app.analytics.models.ai_insight import AIInsight
from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
from app.analytics.repositories.ai_call_event_repository import AICallEventRepository
from app.analytics.repositories.ai_insight_feedback_repository import (
    AIInsightFeedbackRepository,
)
from app.analytics.repositories.ai_insight_repository import AIInsightRepository
from app.analytics.repositories.living_score_snapshot_repository import (
    LivingScoreSnapshotRepository,
)
from app.analytics.schemas.health_brief import (
    HealthBriefFeedbackResponse,
    HealthBriefResponse,
)
from app.common.enums import UserRole
from app.core.ai.client import DataClass
from app.core.ai.errors import AIUnavailableError
from app.core.ai.factory import get_llm_client
from app.core.ai.guard import GuardedLLMClient
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictException, NotFoundException
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.repositories.estate_repository import EstateRepository

logger = logging.getLogger(__name__)

#: The AI feature flag this service runs under (AI_INSIGHTS_ENABLED).
FEATURE: Final[str] = "insights"
KIND: Final[str] = KIND_HEALTH_BRIEF
SOURCE_AI: Final[str] = "ai"
SOURCE_TEMPLATE: Final[str] = "template"

#: Safe reason codes, closed by the response DTO.
INSUFFICIENT_REASON: Final[str] = "insufficient_data"
UNGROUNDED_REASON: Final[str] = "ungrounded_output"
INVALID_REASON: Final[str] = "invalid_output"

#: The two comparison lookbacks, in days. The facts layer owns the arithmetic.
COMPARISON_DAYS: Final[tuple[int, int]] = (30, 90)

NO_SNAPSHOT_MESSAGE: Final[str] = (
    "No Living Score has been calculated for this estate yet, so there is no "
    "brief to explain. An estate administrator can calculate the first one."
)
ALREADY_RATED_MESSAGE: Final[str] = "You have already given feedback on this brief."


def build_brief_client(settings: Settings, db: AsyncSession) -> GuardedLLMClient:
    """Compose the AI guards for this feature.

    The gated client enforces the master switch, the insights feature flag, the
    input cap and the timeout; the guarded client adds the per-estate budget and
    the append-only call ledger.
    """
    return GuardedLLMClient(
        settings, get_llm_client(settings), AICallEventRepository(db)
    )


class HealthBriefService:
    """The estate health brief: read, generate, and collect feedback."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        settings: Settings | None = None,
        llm: GuardedLLMClient | None = None,
    ) -> None:
        self._db = db
        self._settings = settings or get_settings()
        self._snapshots = LivingScoreSnapshotRepository(db)
        self._insights = AIInsightRepository(db)
        self._feedback = AIInsightFeedbackRepository(db)
        self._estates = EstateRepository(db)
        self._authorization = EstateAuthorizationService(db)
        self._llm = llm if llm is not None else build_brief_client(self._settings, db)

    # ---- shared helpers ------------------------------------------------

    async def _latest_snapshot_or_404(self, estate_id: int) -> LivingScoreSnapshot:
        snapshot = await self._snapshots.latest_for_estate(estate_id=estate_id)
        if snapshot is None:
            raise NotFoundException(NO_SNAPSHOT_MESSAGE)
        return snapshot

    async def _require_member(self, user: User, estate_id: int) -> None:
        await self._authorization.require_membership(actor=user, estate_id=estate_id)

    async def _require_estate_admin(self, admin: User, estate_id: int) -> None:
        await self._authorization.require_role(
            actor=admin, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,)
        )

    async def _origin(self, estate_id: int) -> str:
        """'demo' or 'live', read from the estate and mapped in one place."""
        estate = await self._estates.get_by_id(estate_id)
        if estate is None:
            raise NotFoundException(f"Estate with id {estate_id} was not found.")
        return data_origin_for(is_demo=bool(estate.is_demo))

    async def _build_facts(
        self, estate_id: int, snapshot: LivingScoreSnapshot
    ) -> BriefFacts:
        """Project the stored snapshot and its two comparisons into FACTS.

        Two extra snapshot reads, and nothing else: the comparison snapshots are
        the newest at or before 30 and 90 days before the score being explained.
        """
        previous_30d = await self._snapshots.latest_on_or_before(
            estate_id=estate_id, as_of=snapshot.as_of - timedelta(days=COMPARISON_DAYS[0])
        )
        previous_90d = await self._snapshots.latest_on_or_before(
            estate_id=estate_id, as_of=snapshot.as_of - timedelta(days=COMPARISON_DAYS[1])
        )
        return build_brief_facts(snapshot, previous_30d, previous_90d)

    async def _stored_insight(
        self, estate_id: int, snapshot_id: int
    ) -> AIInsight | None:
        return await self._insights.get_for_snapshot(
            estate_id=estate_id,
            snapshot_id=snapshot_id,
            kind=KIND,
            prompt_version=PROMPT_VERSION,
        )

    @staticmethod
    def _ai_response(insight: AIInsight, snapshot: LivingScoreSnapshot) -> HealthBriefResponse:
        """Shape a stored brief. Never regenerates and never re-grounds it."""
        # A brief that does not belong to the snapshot it explains would be a bug
        # in a query, not an input problem, so this is an assertion.
        assert insight.estate_id == snapshot.estate_id, "insight/estate mismatch"
        return HealthBriefResponse(
            source=SOURCE_AI,
            insight_id=insight.insight_id,
            ai_unavailable_reason=None,
            data_origin=insight.data_origin,
            snapshot_id=snapshot.snapshot_id,
            as_of=snapshot.as_of,
            generated_at=insight.created_at,
            facts=BriefFacts.model_validate(insight.facts),
            output=BriefOutput.model_validate(insight.output),
            provider=insight.provider,
            model=insight.model,
            prompt_version=insight.prompt_version,
        )

    @staticmethod
    def _template_response(
        snapshot: LivingScoreSnapshot,
        facts: BriefFacts,
        *,
        origin: str,
        reason: str | None,
    ) -> HealthBriefResponse:
        """Shape the deterministic template. It is never stored."""
        return HealthBriefResponse(
            source=SOURCE_TEMPLATE,
            insight_id=None,
            ai_unavailable_reason=reason,
            data_origin=origin,
            snapshot_id=snapshot.snapshot_id,
            as_of=snapshot.as_of,
            generated_at=None,
            facts=facts,
            output=build_template_brief(snapshot, facts),
            provider=None,
            model=None,
            prompt_version=None,
        )

    async def _record_attempt(self) -> None:
        """Commit only what the guard already wrote to the call ledger.

        The guard flushes an audit row before raising - a rejection, a timeout, a
        provider failure - and returning the template without committing would
        roll that row away, which would make exactly the failures worth auditing
        invisible (ADR-004). Nothing else is pending on this path: the brief is
        only ever added after a successful, grounded generation.
        """
        await self._db.commit()

    @staticmethod
    def _validated_output(parsed: Any) -> BriefOutput:
        """Validate untrusted provider output against the brief contract."""
        if not isinstance(parsed, dict):
            raise AIUnavailableError(INVALID_REASON)
        return BriefOutput.model_validate(parsed)

    # ---- use cases -----------------------------------------------------

    async def read(self, estate_id: int, user: User) -> HealthBriefResponse:
        """The estate's brief for its latest snapshot. Any member may read it.

        Returns the stored AI brief when one exists, otherwise the template built
        on the fly. A read never calls a provider and never writes.
        """
        await self._require_member(user, estate_id)
        snapshot = await self._latest_snapshot_or_404(estate_id)

        stored = await self._stored_insight(estate_id, snapshot.snapshot_id)
        if stored is not None:
            return self._ai_response(stored, snapshot)

        facts = await self._build_facts(estate_id, snapshot)
        return self._template_response(
            snapshot, facts, origin=await self._origin(estate_id), reason=None
        )

    async def generate(self, estate_id: int, admin: User) -> HealthBriefResponse:
        """Ask for the brief for the latest snapshot, creating it at most once.

        Idempotent by construction: an existing brief is returned untouched, an
        unmeasurable score is answered with the template, and a failure stores
        nothing so a later attempt can still succeed.
        """
        await self._require_estate_admin(admin, estate_id)
        snapshot = await self._latest_snapshot_or_404(estate_id)

        stored = await self._stored_insight(estate_id, snapshot.snapshot_id)
        if stored is not None:
            return self._ai_response(stored, snapshot)

        facts = await self._build_facts(estate_id, snapshot)
        origin = await self._origin(estate_id)

        # Nothing to explain yet: no provider call, and none is warranted.
        if snapshot.status != "scored":
            return self._template_response(
                snapshot, facts, origin=origin, reason=INSUFFICIENT_REASON
            )

        try:
            result = await self._llm.generate_json(
                estate_id=estate_id,
                system=SYSTEM_PROMPT,
                user=build_user_prompt(facts),
                schema=brief_output_schema(),
                data_class=DataClass.aggregate,
                feature=FEATURE,
            )
            output = self._validated_output(result.parsed)
            validate_grounding(output, facts)
        except AIUnavailableError as exc:
            # The layer is optional: the estate still gets a brief, and the
            # attempt stays auditable. Only the closed reason code is logged -
            # never a prompt, an output or any estate content.
            logger.info(
                "Health brief fell back to the template for estate %s (reason=%s).",
                estate_id,
                exc.reason,
            )
            await self._record_attempt()
            return self._template_response(
                snapshot, facts, origin=origin, reason=exc.reason
            )
        except ValidationError:
            logger.info(
                "Health brief output failed the contract for estate %s (reason=%s).",
                estate_id,
                INVALID_REASON,
            )
            await self._record_attempt()
            return self._template_response(
                snapshot, facts, origin=origin, reason=INVALID_REASON
            )
        except GroundingViolation as exc:
            # The model wrote a number FACTS do not contain. The answer is
            # discarded rather than shown; nothing is stored.
            logger.info(
                "Health brief output was ungrounded for estate %s (code=%s).",
                estate_id,
                exc.code,
            )
            await self._record_attempt()
            return self._template_response(
                snapshot, facts, origin=origin, reason=UNGROUNDED_REASON
            )

        try:
            insight = await self._insights.add(
                estate_id=estate_id,
                snapshot_id=snapshot.snapshot_id,
                kind=KIND,
                prompt_version=PROMPT_VERSION,
                provider=result.provider,
                model=result.model,
                facts=facts.model_dump(mode="json"),
                output=output.model_dump(mode="json"),
                data_origin=origin,
            )
            await self._db.commit()
        except IntegrityError:
            # Another request stored the same brief between our read and our
            # write. Roll back and return what won.
            await self._db.rollback()
            winner = await self._stored_insight(estate_id, snapshot.snapshot_id)
            if winner is None:  # pragma: no cover - a non-race integrity failure
                raise
            return self._ai_response(winner, snapshot)

        return self._ai_response(insight, snapshot)

    async def feedback(
        self,
        insight_id: int,
        estate_id: int,
        user: User,
        *,
        helpful: bool,
        comment: str | None = None,
    ) -> HealthBriefFeedbackResponse:
        """Record one member's verdict on one stored brief. Once per member.

        The comment is a resident's own words: it stays in this database and is
        never sent to a provider or folded into a brief.
        """
        await self._require_member(user, estate_id)

        insight = await self._insights.get_by_id_in_estate(
            insight_id=insight_id, estate_id=estate_id
        )
        if insight is None:
            # Another estate's brief is not "forbidden", it does not exist here.
            raise NotFoundException(f"Brief with id {insight_id} was not found.")

        existing = await self._feedback.get_by_insight_and_user(
            insight_id=insight_id, user_id=user.user_id
        )
        if existing is not None:
            raise ConflictException(ALREADY_RATED_MESSAGE)

        try:
            row = await self._feedback.add(
                insight_id=insight_id,
                estate_id=estate_id,
                user_id=user.user_id,
                helpful=helpful,
                comment=comment,
            )
            await self._db.commit()
        except IntegrityError:
            # Same person, two requests, one row: the unique constraint is the
            # arbiter, not a read-then-write check.
            await self._db.rollback()
            raise ConflictException(ALREADY_RATED_MESSAGE) from None

        return HealthBriefFeedbackResponse.model_validate(row)
