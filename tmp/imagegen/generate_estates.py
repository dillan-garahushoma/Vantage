"""Generate the outstanding estate-demo images from the prepared prompt spec.

Why this exists: the native `image-generator` subagent that produced the first
five assets is not available in this environment, and the upstream Gemini image
model it called is quota-exhausted until 2026-10-20. This script instead calls a
free, key-less text-to-image HTTP endpoint, so the remaining assets can be
produced without inventing credentials or waiting on a quota.

It is deliberately boring: one asset at a time, validated on arrival, resumable,
and never overwriting an existing valid file.

    python tmp/imagegen/generate_estates.py                    # the 15 outstanding
    python tmp/imagegen/generate_estates.py --only eastbank-court-01-hero.jpg
    python tmp/imagegen/generate_estates.py --verify-only

Run from the repository root. Writes directly into `estate-demo-images/`.
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image

SPEC = "tmp/imagegen/estate-demo-images.prompts.jsonl"
OUT_DIR = "estate-demo-images"
ENDPOINT = "https://image.pollinations.ai/prompt/"

# The free tier serves at most a 1024px long edge: a 1536x864 request comes back
# as 1024x576, and 1920x1080 is refused outright with 402 Payment Required.
DEFAULT_SIZE = (1024, 576)
MIN_BYTES = 20_000
RETRIES = 4
BACKOFF = (15, 45, 90, 150)


def log(message):
    print(message, flush=True)


def target_size(width, height):
    return width / height


def build_url(prompt, width, height, model, seed):
    query = urllib.parse.urlencode(
        {
            "width": width,
            "height": height,
            "model": model,
            "nologo": "true",
            "seed": seed,
            "private": "true",
        }
    )
    return f"{ENDPOINT}{urllib.parse.quote(prompt, safe='')}?{query}"


def is_valid(path, expected_ratio, tolerance=0.02):
    """A file counts as done only if it opens, decodes and has the right shape."""
    if not os.path.exists(path) or os.path.getsize(path) < MIN_BYTES:
        return False
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
    except Exception:
        return False
    return abs(width / height - expected_ratio) <= tolerance


def fetch(url, path):
    """Download, then hand back either the size or the reason it was refused."""
    request = urllib.request.Request(url, headers={"User-Agent": "valora-asset-gen/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response:
        status = response.status
        content_type = response.headers.get("Content-Type", "")
        body = response.read()
    if status != 200:
        return None, f"HTTP {status}"
    if not content_type.startswith("image/"):
        return None, f"not an image ({content_type!r}): {body[:120]!r}"
    if len(body) < MIN_BYTES:
        return None, f"only {len(body)} bytes"

    part = path + ".part"
    with open(part, "wb") as handle:
        handle.write(body)
    try:
        with Image.open(part) as image:
            image.verify()
        with Image.open(part) as image:
            size = image.size
    except Exception as exc:
        os.remove(part)
        return None, f"undecodable: {exc}"
    os.replace(part, path)
    return size, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", default=None, help="one filename to do")
    parser.add_argument("--size", default=f"{DEFAULT_SIZE[0]}x{DEFAULT_SIZE[1]}")
    parser.add_argument("--model", default="flux")
    parser.add_argument("--delay", type=float, default=8.0, help="seconds between requests")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--force", action="store_true", help="redo files that already exist")
    args = parser.parse_args()

    width, height = (int(part) for part in args.size.lower().split("x"))
    ratio = target_size(width, height)

    with open(SPEC, encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    if args.only:
        wanted = set(args.only)
        records = [r for r in records if r["out"] in wanted]
        missing = wanted - {r["out"] for r in records}
        if missing:
            log(f"not in the spec: {', '.join(sorted(missing))}")
            return 2

    os.makedirs(OUT_DIR, exist_ok=True)

    if args.verify_only:
        done = [r for r in records if is_valid(os.path.join(OUT_DIR, r["out"]), ratio)]
        log(f"valid: {len(done)} of {len(records)} in the spec")
        for record in records:
            state = "ok  " if record["out"] in {d['out'] for d in done} else "MISS"
            log(f"  {state} {record['out']}")
        return 0

    todo = [
        record
        for record in records
        if args.force or not is_valid(os.path.join(OUT_DIR, record["out"]), ratio)
    ]
    log(f"{len(records)} in spec, {len(todo)} to generate at {width}x{height} via {args.model}")

    failures = []
    for index, record in enumerate(todo, 1):
        name = record["out"]
        path = os.path.join(OUT_DIR, name)
        # Deterministic seed per asset, so a re-run reproduces the same image
        # rather than silently drifting to a different one.
        seed = random.Random(name).randint(1, 2_000_000_000)
        url = build_url(record["prompt"], width, height, args.model, seed)

        log(f"[{index}/{len(todo)}] {name} (seed {seed})")
        for attempt in range(RETRIES):
            started = time.time()
            try:
                size, problem = fetch(url, path)
            except Exception as exc:
                size, problem = None, f"{type(exc).__name__}: {exc}"
            if size:
                log(f"    ok {size[0]}x{size[1]} in {time.time() - started:.1f}s")
                break
            log(f"    attempt {attempt + 1} failed: {problem}")
            if attempt < RETRIES - 1:
                time.sleep(BACKOFF[min(attempt, len(BACKOFF) - 1)])
        else:
            failures.append((name, problem))

        if index < len(todo):
            time.sleep(args.delay)

    for name, problem in failures:
        log(f"FAILED {name}: {problem}")
    log(f"done — generated/skipped {len(todo) - len(failures)} of {len(todo)}, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
