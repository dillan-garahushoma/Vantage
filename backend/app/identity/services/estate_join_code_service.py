"""Application service for estate join codes.

An HOA admin who administers an estate may read the currently active code and
rotate it. "Administers" means both halves of the credential: the global
``hoa_admin`` role *and* an ``hoa_admin`` membership of that estate, which is what
``EstateAuthorizationService.require_role`` enforces before anything is read or
written.
"""
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utcnow
from app.common.enums import UserRole
from app.core.exceptions import NotFoundException
from app.identity.domain.join_code import generate_join_code
from app.identity.models.user import User
from app.identity.repositories.estate_join_code_repository import EstateJoinCodeRepository
from app.identity.schemas.join_code import JoinCodeResponse
from app.identity.services.estate_authorization_service import EstateAuthorizationService

# A collision with an existing code is astronomically unlikely; the loop only
# exists so that the unique constraint can never surface as a 500.
_MAX_CODE_DRAWS = 10


class EstateJoinCodeService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._codes = EstateJoinCodeRepository(db)
        self._estate_authorization = EstateAuthorizationService(db)

    async def _require_estate_admin(self, actor: User, estate_id: int) -> None:
        await self._estate_authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.hoa_admin.value,),
        )

    @staticmethod
    def _to_response(row) -> JoinCodeResponse:
        return JoinCodeResponse(
            code=row.code,
            estate_id=row.estate_id,
            created_at=row.created_at,
            expires_at=row.expires_at,
        )

    async def get_current(self, actor: User, *, estate_id: int) -> JoinCodeResponse:
        """Return the usable code for this estate, or 404 when there is none."""
        await self._require_estate_admin(actor, estate_id)
        row = await self._codes.get_active_for_estate(estate_id=estate_id, now=utcnow())
        if row is None:
            raise NotFoundException("This estate has no active join code.")
        return self._to_response(row)

    async def rotate(
        self, actor: User, *, estate_id: int, expires_in_days: int | None = None
    ) -> JoinCodeResponse:
        """Revoke the current code and issue a fresh one, in one transaction.

        There is only ever one live code per estate, so "rotate" is revoke-then-
        create rather than "add another": a code that leaked cannot be kept alive
        by accident once a new one is issued.
        """
        await self._require_estate_admin(actor, estate_id)
        now = utcnow()

        previous = await self._codes.get_unrevoked_for_estate(estate_id)
        if previous is not None:
            await self._codes.revoke(previous, revoked_at=now)

        expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None

        code = ""
        for _ in range(_MAX_CODE_DRAWS):
            candidate = generate_join_code()
            if await self._codes.get_by_code(candidate) is None:
                code = candidate
                break
        else:  # pragma: no cover - only reached if the source of randomness fails
            raise RuntimeError("Could not draw an unused join code.")

        row = await self._codes.add(
            estate_id=estate_id,
            code=code,
            created_by=actor.user_id,
            expires_at=expires_at,
        )
        # One commit for the whole use case: the revocation and the new code land
        # together, so the estate is never left with zero or two live codes.
        await self._db.commit()
        return self._to_response(row)
