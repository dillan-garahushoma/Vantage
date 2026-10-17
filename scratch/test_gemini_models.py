import sys
sys.path.insert(0, ".")
import httpx
import time
from app.core.config import get_settings

s = get_settings_fn = get_settings
# Read key directly from .env line without printing it
key = None
with open(".env") as f:
    for line in f:
        if line.startswith("GEMINI_API_KEY="):
            key = line.split("=", 1)[1].strip()

models = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.8-flash"
]

for m in models:
    body = {
        "model": m,
        "input": 'Reply with exactly {"ok": true}',
        "system_instruction": "You are a health check. Respond with JSON only.",
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
        },
        "generation_config": {"max_output_tokens": 100},
        "store": False
    }
    t0 = time.time()
    try:
        r = httpx.post(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            json=body,
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            timeout=15.0
        )
        elapsed = round(time.time() - t0, 2)
        print(f"Model: {m} -> HTTP {r.status_code} in {elapsed}s")
        if r.status_code == 200:
            print("  SUCCESS!")
        else:
            print("  Error:", r.text[:200])
    except Exception as e:
        print(f"Model: {m} -> {type(e).__name__} ({round(time.time() - t0, 2)}s)")
