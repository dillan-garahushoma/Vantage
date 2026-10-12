# BATCH AI-1 — Optional AI assist layer (infrastructure only)

Session: 2026-10-10. Branch `valora-work`. No DB, no endpoints, no migrations.
No commit was created.

## What is done

- `docs/ADR-004-AI-Assist-Layer.md` — decision, guardrails, kill switch, data
  protection, verified provider contracts, and the numbering deviation below.
  (Created as `ADR-002-AI-Assist-Layer.md` in this batch and renamed to `ADR-004`
  by BATCH AI-2, which resolved the duplicated number.)
- `backend/app/core/ai/` (new package, infrastructure only, no business logic):
  - `errors.py` — `AIUnavailableError(reason)` with the closed reason set
    `disabled, policy, budget, timeout, network, provider_error, invalid_output`.
  - `client.py` — `DataClass`, `LLMResult`, the `LLMClient` Protocol
    (`generate_json(*, system, user, schema, data_class, feature)`), the single
    `GatedLLMClient` guardrail wrapper, HTTP-failure classification, and a minimal
    JSON Schema subset validator (type/properties/required/items/enum/additionalProperties).
  - `gemini.py` — httpx adapter for the Gemini **Interactions API**, JSON-schema
    structured output.
  - `openai_compat.py` — httpx adapter for any OpenAI-compatible chat completions
    endpoint (covers NVIDIA Build), JSON mode with local schema enforcement.
  - `fake.py` — deterministic `FakeLLMClient` (no network, no clock, no randomness).
  - `factory.py` — `get_llm_client(settings)`; always returns the gated wrapper.
- `backend/app/core/config.py` — all `AI_*` settings (keys as `SecretStr`, all optional),
  plus startup validation in a `model_validator`.
- `backend/.env.example` — AI placeholders only.
- `backend/.dockerignore` — now ignores `.env` and `.env.*` (keeps `.env.example`).
- `backend/docker-compose.yml` — passes every `AI_*` variable through as `${VAR:-default}`.
- `backend/scripts/ai_smoke.py` — operator-run smoke script.

## Tests added and passing

`backend/tests/test_ai_layer.py` — 52 tests, no network (every adapter test uses
`httpx.MockTransport`), no database.

Covered: master switch off blocks before HTTP; per-feature flag off blocks; personal data
blocked without `AI_PERSONAL_DATA_ALLOWED` and allowed with it; oversize input rejected
pre-HTTP; exactly-at-limit input allowed; the wrapper's hard timeout with no retry; both
adapters parse valid output; Gemini request shape (URL, `x-goog-api-key`, `input`,
`system_instruction`, `response_format.mime_type`, `schema`, `generation_config.max_output_tokens`,
`store: false`); OpenAI-compatible request shape (URL with/without `/v1`, bearer header,
`response_format=json_object`, `max_tokens`, `json` present in messages); 401/403/429/500/503
→ `provider_error`; non-JSON, wrong-schema JSON, and non-object JSON → `invalid_output`;
transport timeout → `timeout`; connect error → `network`; exactly one attempt on failure;
keys absent from `repr(settings)`, `str(exception)` and caplog; provider error bodies never
echoed; startup validation (gemini/openai_compatible credentials, fake outside dev/test,
`AI_PERSONAL_DATA_ALLOWED` without `AI_ENABLED`, unknown provider, defaults all off);
factory behaviour; Fake determinism and schema validity; schema validator behaviour.

## Written, not run

- `backend/scripts/ai_smoke.py` — **written, not run.** It needs real provider
  credentials, and no key is available in this session. The owner runs it:

  ```powershell
  Set-Location backend
  .\venv\Scripts\python.exe scripts\ai_smoke.py --feature insights
  ```

  It prints provider, model, latency, input_chars and parsed; never the key; exits
  non-zero on failure.
- Any real provider call whatsoever. Both adapters are verified only against
  `httpx.MockTransport`, i.e. verified against the documented contract, not against a
  live provider.

## Commands run, with results

```text
backend> venv\Scripts\python.exe -m pytest tests/test_ai_layer.py -q -p no:cacheprovider
  52 passed in 12.95s
  (before the implementation existed, the same file failed at collection with
   ModuleNotFoundError: No module named 'app.core.ai' — the failing test came first)

backend> venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
  112 passed, 2 skipped, 3 warnings in 47.13s
  With -rs the two skips are explicit:
    SKIPPED [1] tests\test_harness_safety.py:5: TEST_DATABASE_URL is not set
    SKIPPED [1] tests\test_login_rate_limit.py:136: TEST_DATABASE_URL is not set
  => integration tests did NOT run in this session. TEST_DATABASE_URL was not set.
     A skip is not counted as a pass.

backend> venv\Scripts\python.exe -m compileall -q app scripts
  exit 0

backend> venv\Scripts\python.exe -m flake8 app tests --count --select=E9,F63,F7,F82 --show-source --statistics
  0
backend> venv\Scripts\python.exe -m flake8 scripts --count --select=E9,F63,F7,F82 --show-source --statistics
  0
repo root> git diff --check
  exit 0
```

Docker, the Gemini Interactions API, and any OpenAI-compatible provider were **not**
contacted. No new dependency was added (`httpx` was already in `requirements.txt`).

## Deviations from the batch

1. **ADR path/number.** The batch asked for `docs/ADR-002-AI-Assist-Layer.md`. A
   different `ADR-002-estate-authorization.md` already exists, so the number was
   duplicated. I created the file at the requested path and flagged it in both the ADR
   and the open questions. **Resolved in BATCH AI-2**: the file is now
   `docs/ADR-004-AI-Assist-Layer.md` and every reference points at it.
2. **Schema validator instead of a dependency.** The batch said no new dependency, so
   `client.py` carries a small JSON Schema subset validator rather than `jsonschema`.
   It covers only the subset we ask providers for.
3. **`AI_PROVIDER` default is `gemini`, not `fake`.** A `fake` default would make
   startup validation fail in production for anyone who never touches the AI settings,
   which would break the "product works with AI off" invariant. `fake` is selected
   explicitly and refused outside development/test.
4. **`AI_TIMEOUT_SECONDS` is a `float` (15.0).** Needed so tests can assert the hard
   timeout without sleeping for seconds. Env value `15` still works.
5. **Gemini endpoint choice.** The batch said to verify the endpoint against current
   docs and not guess. The current docs make the **Interactions API**
   (`/v1beta/interactions`) the recommended endpoint for new projects, so the adapter
   targets it rather than the older `models/{model}:generateContent`. Details and
   source links are in the ADR.
6. **`get_llm_client(settings, *, transport=None)`** takes an optional transport. This
   exists so tests can drive the real factory through a mock transport; production
   callers omit it.
7. **`GatedLLMClient.inner` is public** (batch did not specify) so tests can assert
   which provider the factory selected.

## Open questions / remaining

- **Budget gate is not implemented.** `AI_DAILY_CALL_CAP_PER_ESTATE` is configured and
  the `budget` reason is reserved, but a real per-estate counter needs persistence,
  which this no-DB batch must not add. Until then no request is refused for budget.
- **No caller exists yet.** Nothing calls `get_llm_client` in production code, so the
  layer is inert. A later batch must decide where `insights` and `triage` plug in, what
  the output schemas are, and what each fallback path is.
- **Frontend exposure is undefined.** No endpoint returns AI output yet; the future
  contract must not leak personal data or expose raw provider text.
- **`.env.example` was edited via the shell** because the file tool declines to edit
  `.env*` paths. Only placeholders were added.
- Pre-existing dirty files from earlier sessions (`backend/app/identity/*`,
  `backend/tests/conftest.py`, `docs/openapi.json`, `frontend/`, etc.) were **not
  touched**.
