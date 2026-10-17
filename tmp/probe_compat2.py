"""Isolate why the OpenAI-compatible chat path hangs.

1. Lists the endpoint's models and picks a small, fast instruct model.
2. Sends the same trivial prompt to that model (non-streaming).
3. Sends it to the configured model with streaming, printing time to first byte,
   so "slow" can be told apart from "never answers".

Never prints the API key.
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


def headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


async def small_model_probe(model: str, key: str, url: str) -> None:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        "max_tokens": 64,
    }
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=body, headers=headers(key))
    except httpx.HTTPError as exc:
        print(f"[small] {model}: transport {type(exc).__name__} after {time.perf_counter() - started:.1f}s")
        return
    elapsed = time.perf_counter() - started
    print(f"[small] {model}: HTTP {response.status_code} in {elapsed:.1f}s")
    if response.status_code >= 400:
        print("   body:", response.text[:200])
        return
    payload = response.json()
    choice = (payload.get("choices") or [{}])[0]
    print("   finish_reason:", choice.get("finish_reason"))
    print("   content head:", ((choice.get("message") or {}).get("content") or "").strip()[:120])


async def streaming_probe(model: str, key: str, url: str) -> None:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        "max_tokens": 128,
        "stream": True,
    }
    started = time.perf_counter()
    first: float | None = None
    chunks = 0
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream("POST", url, json=body, headers=headers(key)) as response:
                print(f"[stream] {model}: HTTP {response.status_code}")
                if response.status_code >= 400:
                    print("   body:", (await response.aread())[:200])
                    return
                async for line in response.aiter_lines():
                    if line.startswith("data:") and not line.endswith("[DONE]"):
                        chunks += 1
                        if first is None:
                            first = time.perf_counter() - started
                            print(f"   first chunk after {first:.1f}s")
                        if chunks >= 3:
                            break
    except httpx.HTTPError as exc:
        print(f"[stream] {model}: transport {type(exc).__name__} after {time.perf_counter() - started:.1f}s (chunks={chunks})")
        return
    print(f"   chunks seen: {chunks}, elapsed {time.perf_counter() - started:.1f}s")


async def main() -> None:
    settings = get_settings()
    key = settings.AI_COMPAT_API_KEY.get_secret_value()
    base = (settings.AI_COMPAT_BASE_URL or "").rstrip("/")
    chat_url = _chat_completions_url(base)

    async with httpx.AsyncClient(timeout=30.0) as client:
        listing = (await client.get(f"{base}/models", headers=headers(key))).json()
    ids = [m.get("id") for m in (listing.get("data") or [])]
    small = next(
        (i for i in ids if i and any(tag in i.lower() for tag in ("8b-instruct", "7b-instruct", "mini"))),
        None,
    )
    print("small model chosen:", small)

    if small:
        await small_model_probe(small, key, chat_url)
    await streaming_probe(settings.AI_MODEL, key, chat_url)


asyncio.run(main())
