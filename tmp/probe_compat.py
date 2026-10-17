"""Probe the configured OpenAI-compatible endpoint with the adapter's exact body.

Read-only against the provider. Prints status, elapsed time and a short body head
so a hang can be told apart from a rejection. Never prints the API key.
"""
import asyncio
import json
import sys
import time

import httpx

sys.path.insert(0, ".")

from app.core.ai.openai_compat import _chat_completions_url
from app.core.config import get_settings

SYSTEM = "You are a health check. Reply with JSON only."
USER = 'Reply with exactly {"ok": true}.'
SCHEMA_HINT = '{"ok": true}'


async def attempt(label: str, *, use_response_format: bool, timeout: float = 120.0) -> None:
    settings = get_settings()
    body = {
        "model": settings.AI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        "max_tokens": settings.AI_MAX_OUTPUT_TOKENS,
    }
    if use_response_format:
        body["response_format"] = {"type": "json_object"}

    url = _chat_completions_url(settings.AI_COMPAT_BASE_URL or "")
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json=body,
                headers={
                    "Authorization": f"Bearer {settings.AI_COMPAT_API_KEY.get_secret_value()}",
                    "Content-Type": "application/json",
                },
            )
    except httpx.HTTPError as exc:
        print(f"{label}: transport {type(exc).__name__} after {time.perf_counter() - started:.1f}s")
        return

    elapsed = time.perf_counter() - started
    print(f"{label}: HTTP {response.status_code} in {elapsed:.1f}s")
    text = response.text
    if response.status_code >= 400:
        print("   body:", text[:300])
        return
    try:
        payload = response.json()
        choice = (payload.get("choices") or [{}])[0]
        print("   finish_reason:", choice.get("finish_reason"))
        print("   usage:", payload.get("usage"))
        content = (choice.get("message") or {}).get("content")
        print("   content head:", (content or "")[:160].replace("\n", " "))
    except ValueError:
        print("   non-json body:", text[:200])


async def main() -> None:
    settings = get_settings()
    print("base_url:", settings.AI_COMPAT_BASE_URL, "| model:", settings.AI_MODEL)
    await attempt("A adapter body (response_format json_object)", use_response_format=True)
    await attempt("B no response_format", use_response_format=False)


asyncio.run(main())
