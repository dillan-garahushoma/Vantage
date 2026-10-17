"""Operator-run smoke test for the optional AI assist layer.

It uses the real settings and the real factory, sends one trivial
schema-constrained request, and prints provider, model, latency and ok/fail.
It never prints API keys. Exits non-zero on any failure.

Run it from the backend directory with a real key configured:

    venv\\Scripts\\python.exe scripts\\ai_smoke.py
    venv\\Scripts\\python.exe scripts\\ai_smoke.py --feature triage

It is deliberately NOT run automatically: without a key it can only report
"no key", which is not a useful signal. If no key is present the script simply
reports the disabled/policy reason and exits non-zero.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

# Allow "python scripts/ai_smoke.py" from the backend directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.ai.client import DataClass  # noqa: E402
from app.core.ai.errors import AIUnavailableError  # noqa: E402
from app.core.ai.factory import get_llm_client  # noqa: E402
from app.core.config import get_settings  # noqa: E402

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


async def _run(feature: str) -> int:
    settings = get_settings()
    client = get_llm_client(settings)

    try:
        result = await client.generate_json(
            system="You are a health check. Reply with JSON only.",
            user='Reply with exactly {"ok": true}.',
            schema=SCHEMA,
            data_class=DataClass.aggregate,
            feature=feature,
        )
    except AIUnavailableError as exc:
        print(f"AI smoke: FAIL provider={settings.AI_PROVIDER} reason={exc.reason}")
        return 1
    except Exception as exc:  # noqa: BLE001 - report, never leak details
        print(f"AI smoke: FAIL provider={settings.AI_PROVIDER} error={type(exc).__name__}")
        return 1

    print(
        "AI smoke: OK "
        f"provider={result.provider} model={result.model} "
        f"latency_ms={result.latency_ms} input_chars={result.input_chars} "
        f"parsed={result.parsed}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test the AI assist layer.")
    parser.add_argument(
        "--feature", choices=("insights", "triage"), default="insights"
    )
    args = parser.parse_args()
    return asyncio.run(_run(args.feature))


if __name__ == "__main__":
    raise SystemExit(main())
