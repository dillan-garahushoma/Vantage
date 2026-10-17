"""Raw probe of the brief request against the Gemini interactions endpoint.

Prints the provider's own status and error body for failures (the brief prompt
carries aggregate numbers only, never resident text) and, on a success, runs the
grounding validator offline and names the number that fails.
"""
import asyncio
import json
import sys
import time

import httpx

sys.path.insert(0, ".")

from app.analytics.ai.brief_output import SYSTEM_PROMPT, BriefOutput, brief_output_schema, build_user_prompt
from app.analytics.ai.grounding import allowed_values, numbers_in, validate_grounding
from app.analytics.services.health_brief_service import HealthBriefService
from app.core.ai.client import validate_json_schema
from app.core.ai.gemini import _extract_text
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


async def main() -> None:
    settings = get_settings()
    key = settings.GEMINI_API_KEY.get_secret_value() if settings.GEMINI_API_KEY else None
    if key is None:
        print("no gemini key configured")
        return

    async with AsyncSessionLocal() as session:
        svc = HealthBriefService(session)
        snapshot = await svc._latest_snapshot_or_404(4)
        facts = await svc._build_facts(4, snapshot)

    schema = brief_output_schema()
    body = {
        "model": settings.AI_MODEL,
        "input": build_user_prompt(facts),
        "system_instruction": SYSTEM_PROMPT,
        "response_format": {"type": "text", "mime_type": "application/json", "schema": schema},
        "generation_config": {"max_output_tokens": 2048, "thinking_level": "low"},
        "store": False,
    }
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}

    for attempt in range(1, 7):
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(URL, json=body, headers=headers)
        except httpx.HTTPError as exc:
            print(f"attempt {attempt}: transport {type(exc).__name__} after {time.perf_counter() - started:.1f}s")
            continue
        elapsed = time.perf_counter() - started
        print(f"attempt {attempt}: HTTP {response.status_code} in {elapsed:.1f}s")
        if response.status_code >= 400:
            print("   body:", response.text[:200].replace("\n", " "))
            continue

        payload = response.json()
        usage = payload.get("usage") or {}
        print(f"   status={payload.get('status')} out={usage.get('total_output_tokens')} thought={usage.get('total_thought_tokens')}")
        try:
            raw = _extract_text(payload)
        except Exception as exc:  # noqa: BLE001
            print("   no text:", type(exc).__name__, exc)
            continue

        parsed = json.loads(raw)
        validate_json_schema(parsed, schema)
        output = BriefOutput.model_validate(parsed)
        print("   headline:", output.headline)
        print("   summary:", output.summary)
        for d in output.drivers:
            print("     driver:", d.component, d.direction, "|", d.statement)
        for a in output.actions:
            print("     action:", a.component, "|", a.action)

        permitted = allowed_values(facts)
        texts = [output.headline, output.summary] + [d.statement for d in output.drivers] + [a.action for a in output.actions]
        bad = [
            (n, t)
            for t in texts
            for n in numbers_in(t)
            if abs(n) not in permitted
        ]
        print("   permitted magnitudes:", sorted({str(v) for v in permitted}))
        for number, text in bad:
            print("   UNGROUNDED:", number, "in:", text)
        try:
            validate_grounding(output, facts)
            print("   grounding: OK")
        except Exception as exc:  # noqa: BLE001
            print("   grounding: FAILED", exc)
        return


asyncio.run(main())
