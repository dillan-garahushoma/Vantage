# Session: "my AI isn't working — is it the API key?"

Not a batch. Triggered by a report that the AI features were dead. No batch file was
in play; the work below is the smallest correct response to that report.

## Verdict

**Neither key is the problem.** Both credentials authenticate against their provider.
The layer was broken by three separate, compounding causes: an operator setting that was
too small for a thinking model, an unbounded provider schema, and a reason vocabulary that
could not tell those failures apart from a real key or quota problem. On top of that, the
provider configured at 01:05 (NVIDIA NIM, `deepseek-ai/deepseek-v4.1-flash`) does not answer
at all, and the Gemini key's free-tier daily quota was exhausted by the time of the
diagnosis.

## Evidence (all commands run, with results)

| # | Command | Result |
| --- | --- | --- |
| 1 | `venv\Scripts\python.exe scripts\ai_smoke.py --feature insights` (provider `gemini`, model `gemini-3.8-flash`) | **OK** `latency_ms=25934 parsed={'ok': True}` — the key works |
| 2 | same, `--feature triage` | **OK** `latency_ms=7301` |
| 3 | `ai_call_events` ledger, group by status | `ok` **1**, `provider_failed/invalid_output` **5**, `provider_failed/provider_error` **3** — the brief had never once succeeded |
| 4 | raw brief request, `max_output_tokens=600` | HTTP 200, `status=incomplete`, `total_output_tokens=9`, `total_thought_tokens=577` — the cap was spent on **thinking**, so no answer existed |
| 5 | same request, `max_output_tokens=8192` | HTTP 200, `status=completed`, `out=705`, `thought=749` → extraction **and** schema validation OK |
| 6 | same request, `thinking_level="low"`, cap 2048 | HTTP 200, `status=completed`, `out=562`, `thought=0` — the answer arrives without burning the budget |
| 7 | `GET https://integrate.api.nvidia.com/v1/models` (current `AI_COMPAT_BASE_URL`) | HTTP **200** in 3.4s, 80 models, `deepseek-ai/deepseek-v4.1-flash` present — **the key is valid** |
| 8 | adapter's exact chat body to that endpoint, non-streaming and streaming | **ReadTimeout** after 125s / 150s / 92s, **0 chunks** — the model never answers |
| 9 | raw brief request to Gemini with the current model id | HTTP **404** "Model 'deepseek-ai/deepseek-v4.1-flash' not found" — the model id belongs to the other provider |
| 10 | `ai_smoke.py` with the configuration live at 01:05 | **FAIL** `provider=openai_compatible reason=timeout` |
| 11 | raw brief request, Gemini, correct model id | HTTP **429** "Rate limit exceeded for model gemini-3.8-flash (limit: 20 requests per day on Free Tier). Please retry in 31m50s" |
| 12 | grounding check against estate 4's real FACTS, using the wording the shipped template itself uses ("93.20 out of 100") | **passes** — `score_max=100` is a fact, so grounding does not reject normal phrasing |
| 13 | `venv\Scripts\python.exe -m pytest tests -q` | **769 passed, 114 skipped** (integration skips: `TEST_DATABASE_URL` unset) |
| 14 | `venv\Scripts\python.exe -m compileall -q app` | OK |
| 15 | `venv\Scripts\python.exe -m flake8 app tests --select=E9,F63,F7,F82 --count` | **0** |
| 16 | `git diff --check` | clean |
| 17 | `venv\Scripts\python.exe -m alembic -c alembic.ini heads` / `current` | both `f1a2b3c4d5e6`, and every AI table exists (`ai_call_events`, `ai_insights`, `complaint_ai_suggestions`, …) — **no migration was needed** |
| 18 | `python -m app.cli export-openapi`, `npm run gen:api`, `npm run check:api` | contract and generated TS types regenerated and **in sync** |
| 19 | `npm run typecheck` | **1 error, pre-existing and unrelated**: `src/routes/Dashboard.tsx(13,39) TS6133: 'fullDate' is declared but its value is never read` — a file I did not touch |
| 20 | `npx vitest run src/components/HealthBrief.test.tsx` | 18 passed |

## What was changed

Root cause 1 — **output cap too small for a thinking model.** Thinking tokens count against
`max_output_tokens`, so the 600 default was consumed before any answer was written and the
provider returned an empty `incomplete` envelope, which surfaced as `invalid_output`.

* `app/core/config.py`: `AI_MAX_OUTPUT_TOKENS` default **600 → 2048**; new
  `AI_THINKING_LEVEL` (`minimal | low | medium | high | default`, default **low**, `default`
  sends nothing and leaves reasoning effort to the provider).
* `app/core/ai/gemini.py`: sends `generation_config.thinking_level` when configured.
* `app/core/ai/factory.py`: passes the level through, `default` → omit the field.

Root cause 2 — **the brief's provider schema did not bound the lists the DTO bounds.** One
live probe returned **5 drivers** against `BriefOutput(max_length=3)`, so a usable brief was
discarded.

* `app/analytics/ai/brief_output.py`: `maxItems` on `drivers`/`actions`, from the same
  `MAX_DRIVERS`/`MAX_ACTIONS` constants the DTO uses.
* `app/core/ai/client.py`: the local schema subset validator now honours
  `maxItems`/`minItems` (documented as supported by the provider), so the two validators
  cannot disagree about what is valid.

Root cause 3 — **failure reasons could not be told apart.**

* `truncated` (Gemini `status: incomplete`; OpenAI-compatible `finish_reason: length`) is now
  distinct from `invalid_output`. A valid answer still wins: the reason is only substituted
  when parsing/extraction actually failed.
* `rate_limited` (HTTP 429) is now distinct from `provider_error`.
* Added to `app/core/ai/errors.py`, `PROVIDER_FAILURE_REASONS` in `app/core/ai/guard.py` (both
  consume a provider attempt, so both stay audited and counted) and
  `BriefUnavailableReason` in `app/analytics/schemas/health_brief.py`.
* `app/core/ai/openai_compat.py` also documents that it deliberately sends **no**
  reasoning-effort field: that parameter is gateway-specific, and guessing it would turn a
  working provider into a 400.

Tests added (written first, all failing before the fix): a truncated Gemini interaction, a
truncated OpenAI-compatible answer (partial content and empty content), a complete answer at
the limit still being used, `thinking_level` sent/omitted, the two new reasons end-to-end to
the 503 body, `maxItems`/`minItems` enforcement, the brief schema bounds, `truncated` counted
as a failed ledger call, and the brief service falling back with `truncated`.
Plus `backend/.env.example`, `backend/docker-compose.yml`, `docs/ADR-004-AI-Assist-Layer.md`
(closed reason list, the three distinctions, and the provider contract re-checked against
Google's docs on 2026-10-15), and the regenerated `docs/openapi.json` +
`frontend/src/api/generated/schema.d.ts`.

## Written but not run

* No live run of the **fixed** layer against a working provider. Every end-to-end attempt was
  refused by the environment, not by the code: Gemini answered 429 (free-tier daily quota,
  ~20 requests/day for `gemini-3.8-flash`, resetting about 32 minutes after the last probe),
  and the currently configured NVIDIA NIM model never answered at all. The fixes are
  verified by unit tests and by the raw provider probes (rows 4–6), **not** by a successful
  brief through the running app.
* The one live HTTP attempt that did get through (throwaway server on port 8011, before the
  `.env` switch, one attempt) fell back to the template with
  `ai_reason=ungrounded_output`. Not reproduced and not diagnosed further — with a working
  provider this needs one more run. Row 12 shows the validator accepts the product's own
  template wording, so the rejection was most likely a genuinely invented number (grounding
  working as designed), but that is an inference, not a verification.

## Remaining / recommended next steps

1. **Get a working provider back.** Either enable Gemini billing (or wait for the free-tier
   reset), or point `AI_MODEL` at something on the NIM endpoint that actually answers.
   `scripts/ai_smoke.py` is the one-command check; it prints `provider=… reason=…`.
2. **Restart the backend.** The server on port 8000 is still running the old process and the
   old settings; `AI_MAX_OUTPUT_TOKENS` is read at startup (`get_settings()` is `lru_cache`d).
   Nothing in `.env` had to change for the cap fix to take effect, because the repo default
   was the value in play — but a restart is still required.
3. Re-run the brief live and confirm `source=ai`. The repository, Compose fallback,
   and `.env.example` now default `AI_TIMEOUT_SECONDS` to 75 because Gemini answered
   one brief in 55s while under load. An existing `.env` or host environment value
   overrides that default and must also be raised; restart the API after changing it.
4. Decide whether an over-long `drivers`/`actions` list should really discard the whole brief
   (`BriefOutput` raises, so the template is shown). Bounding the provider schema reduces how
   often this happens, but a lenient truncation would be a product decision, not a bug fix.

## Deviations, and things worth knowing

* `.env` was rewritten by someone else **during this session** (01:05:33): the provider moved
  from `gemini`/`gemini-3.8-flash` to `openai_compatible`/NVIDIA NIM. I did not edit `.env`,
  and never printed its secret values — only the key *names* and whether they are set.
* `docs/openapi.json` was stale before this session (the committed contract was missing the
  `residency-requests` endpoints already present in code). Regenerating it picked those up
  along with the two new reason codes; that is pre-existing drift, not this session's work.
* All temporary probes live in `tmp/` (untracked): `diag_brief_grounding.py`,
  `probe_compat.py`, `probe_compat2.py`, `probe_gemini_brief.py`.
* No migration was added, nothing was committed, and the user's own dev server on port 8000
  was left running untouched. The throwaway verification server I started on 8011 was stopped.
