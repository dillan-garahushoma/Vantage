import asyncio
import httpx
from app.core.config import get_settings

async def test_gemini():
    settings = get_settings()
    api_key = settings.GEMINI_API_KEY.get_secret_value() if settings.GEMINI_API_KEY else None
    print(f"Provider: {settings.AI_PROVIDER}")
    print(f"Model: {settings.AI_MODEL}")
    print(f"Key configured: {bool(api_key)}")
    if not api_key:
        print("No API key configured!")
        return

    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    body = {
        "model": settings.AI_MODEL,
        "input": "test triage",
        "system_instruction": "Reply with JSON.",
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "priority": {"type": "string"},
                    "trade": {"type": "string"}
                },
                "required": ["category", "priority"]
            }
        },
        "generation_config": {"max_output_tokens": 100},
        "store": False
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                json=body,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json"
                }
            )
            print(f"Status Code: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini())
