"""Diagnose why a live brief is rejected by the grounding validator.

Read-only: the AI call goes through the real guarded client, but the session is
rolled back so nothing is stored. Prints the offending sentence and the numbers
on both sides, so the mismatch is visible instead of guessed.
"""
import asyncio
import json
import sys
from decimal import Decimal

sys.path.insert(0, ".")

from app.analytics.ai.brief_output import SYSTEM_PROMPT, BriefOutput, brief_output_schema, build_user_prompt
from app.analytics.ai.grounding import allowed_values, fact_numbers, numbers_in, validate_grounding
from app.analytics.services.health_brief_service import HealthBriefService
from app.core.ai.client import DataClass
from app.db.session import AsyncSessionLocal


async def main() -> None:
    estate_id = 4
    async with AsyncSessionLocal() as session:
        svc = HealthBriefService(session)
        snapshot = await svc._latest_snapshot_or_404(estate_id)
        facts = await svc._build_facts(estate_id, snapshot)
        result = None
        last: Exception | None = None
        for attempt in range(1, 5):
            try:
                result = await svc._llm.generate_json(
                    estate_id=estate_id,
                    system=SYSTEM_PROMPT,
                    user=build_user_prompt(facts),
                    schema=brief_output_schema(),
                    data_class=DataClass.aggregate,
                    feature="insights",
                )
                break
            except Exception as exc:  # noqa: BLE001 - transient provider failures
                last = exc
                print(f"attempt {attempt} failed: {type(exc).__name__} {exc}")
        await session.rollback()
        if result is None:
            print("no answer after retries:", last)
            return
        print("provider:", result.provider, result.model, "latency_ms:", result.latency_ms)

    output = BriefOutput.model_validate(result.parsed)
    print("headline:", output.headline)
    print("summary:", output.summary)
    for d in output.drivers:
        print("  driver:", d.component, d.direction, "|", d.statement)
    for a in output.actions:
        print("  action:", a.component, "|", a.action)

    permitted = allowed_values(facts)
    print("\npermitted magnitudes:", sorted(str(v) for v in permitted))
    print("fact numbers:", sorted(str(v) for v in fact_numbers(facts)))

    texts = [output.headline, output.summary] + [d.statement for d in output.drivers] + [a.action for a in output.actions]
    for text in texts:
        for number in numbers_in(text):
            if abs(number) not in permitted:
                print("\nUNGROUNDED:", number, "in:", text)

    try:
        validate_grounding(output, facts)
        print("\ngrounding: OK")
    except Exception as exc:  # noqa: BLE001 - diagnostic
        print("\ngrounding: FAILED", type(exc).__name__, exc)


asyncio.run(main())
