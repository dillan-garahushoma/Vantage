import asyncio
import httpx
from app.core.config import get_settings
from app.community.services.complaint_triage_service import SYSTEM_PROMPT
from app.community.domain.triage_vocabulary import suggestion_schema

async def debug_gemini_call():
    settings = get_settings()
    api_key = settings.GEMINI_API_KEY.get_secret_value()
    model = settings.AI_MODEL
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    
    schema = suggestion_schema()
    user_prompt = "<complaint>\nreported_category: other\nresident_priority: low\ndescription: Complex directional signage weathered and illegible at night.\n</complaint>"

    body = {
        "model": model,
        "input": user_prompt,
        "system_instruction": SYSTEM_PROMPT,
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": dict(schema),
        },
        "generation_config": {"max_output_tokens": settings.AI_MAX_OUTPUT_TOKENS},
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
        print("Response headers:", resp.headers)
        print("Response body:\n", resp.text)

if __name__ == "__main__":
    asyncio.run(debug_gemini_call())
