import asyncio
import json
import httpx
from app.core.config import get_settings
from app.analytics.ai.brief_output import SYSTEM_PROMPT, brief_output_schema, build_user_prompt
from app.analytics.services.health_brief_service import HealthBriefService
from app.db.session import AsyncSessionLocal

async def debug_health_brief():
    settings = get_settings()
    api_key = settings.GEMINI_API_KEY.get_secret_value()
    model = settings.AI_MODEL
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"

    async with AsyncSessionLocal() as session:
        brief_svc = HealthBriefService(session, settings=settings)
        snapshot = await brief_svc._latest_snapshot_or_404(4)
        facts = await brief_svc._build_facts(4, snapshot)
        user_prompt = build_user_prompt(facts)
        schema = brief_output_schema()

        body = {
            "model": model,
            "input": user_prompt,
            "system_instruction": SYSTEM_PROMPT,
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": dict(schema),
            },
            "generation_config": {"max_output_tokens": 2048},
            "store": False,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                json=body,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json",
                },
            )
            print(f"Status Code: {resp.status_code}")
            data = resp.json()
            print("Usage:", data.get("usage"))
            print("Status:", data.get("status"))
            from app.core.ai.gemini import _extract_text
            from app.core.ai.client import validate_json_schema
            extracted = _extract_text(data)
            print("Extracted text:\n", extracted)
            payload = json.loads(extracted)
            validate_json_schema(payload, schema)
            print("Schema validation passed!")

if __name__ == "__main__":
    asyncio.run(debug_health_brief())
