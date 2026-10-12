# ADR-004 — AI Assist Layer

- **Status:** Accepted (BATCH AI-1 infrastructure; BATCH AI-2 guardrails, ledger and redaction)
- **Date:** 2026-10-10
- **Numbering:** this ADR was briefly created as `ADR-002-AI-Assist-Layer.md`, which collided
  with the existing `ADR-002-estate-authorization.md`. BATCH AI-2 renamed it to `ADR-004`; every
  reference now points here.

## Context

The MVP roadmap deliberately excluded LLMs, and that exclusion still holds for every
core capability. VALORA's Living Score, authorization, lifecycle and money paths are
deterministic and must stay that way. This ADR records a **deliberate, flagged
exception**: a narrow, optional assist layer that may *help a human* — draft an insight
sentence, suggest a triage category — and nothing more.

The failure mode this ADR exists to prevent is an AI feature that quietly becomes
load-bearing: a score that changes when a provider is down, a resident's data leaving
the estate boundary because a flag defaulted to on, or a provider response written
straight into the database.

## Decision

We add `backend/app/core/ai/` — provider adapters plus **one** guardrail wrapper. AI-1 shipped
the layer as infrastructure only (no endpoints, no business logic, no database access) switched
**off**, with tests. AI-2 adds the two controls that need persistence — a per-estate daily call
budget and an append-only call ledger — plus best-effort input redaction and a 503 mapping, so a
later batch can call AI from a service under these constraints.

AI-3 adds the first real caller — advisory HOA triage suggestions on a complaint (see below).
The complaint workflow is unchanged: with AI off there is simply no suggestion.

### Invariants

1. **The LLM never computes scores.** It may summarise inputs the backend already
   computed. All Living Score maths stays in `analytics/services/living_score_service.py`.
2. **The LLM never writes data and has no tools.** It returns text that must pass
   schema validation; only backend code decides what to persist, and always with a
   non-AI fallback.
3. **AI is never load-bearing.** With `AI_ENABLED=false`, or with any provider failure,
   the product behaves exactly as before. Every failure surfaces as
   `AIUnavailableError(reason)` and the caller falls back.
4. **Default everything OFF.** All `AI_*` flags default to false; the provider default
   (`gemini`) is only a *selector*, never an enablement.

### Guardrails (implemented in one place)

The gates live only in `GatedLLMClient` in `app/core/ai/client.py`. Adapters cannot be
called around them because the factory always returns the wrapper, and no adapter
re-checks the gates on its own:

| Gate | Rule |
| --- | --- |
| Master switch | `AI_ENABLED=false` → `disabled`, no provider is even constructed |
| Per-feature flag | `AI_INSIGHTS_ENABLED` / `AI_TRIAGE_ENABLED` must be true; unknown feature names are refused with `policy` |
| Personal data | `data_class=personal` requires `AI_PERSONAL_DATA_ALLOWED=true`, else `policy` |
| Input size | `len(system) + len(user) > AI_MAX_INPUT_CHARS` → `policy`, checked **before** any HTTP |
| Output size | `AI_MAX_OUTPUT_TOKENS` is passed to the provider on every request |
| Time | One attempt, hard `asyncio.wait_for(AI_TIMEOUT_SECONDS)`. No retry loops |
| Output trust | Provider output is JSON-decoded and schema-validated; failure → `invalid_output` |
| Estate scope | `GuardedLLMClient` requires an `estate_id` on every call; it cannot be omitted |
| Budget | `AI_DAILY_CALL_CAP_PER_ESTATE` counted over the last 24h from the ledger; over cap → `budget` |

Reason codes are closed: `disabled, policy, budget, timeout, network, provider_error,
invalid_output`.

`GatedLLMClient` is the only gate for the checks that need no persistence. `GuardedLLMClient`
(`app/core/ai/guard.py`) wraps it and is the **only** way a feature may call AI: it adds the
estate requirement, the budget gate and the ledger, and it cannot be bypassed because features
receive the guarded client.

### Call ledger

`ai_call_events` (one additive migration, `f6c9d3a8b2e1`) records one row per estate-scoped
attempt: `estate_id` (FK to `estates`, ON DELETE RESTRICT), `feature`, `provider`, `model`,
`status`, `reason`, `latency_ms`, `input_chars`, `created_at`. The status set is closed and
constrained in the database: `ok`, `provider_failed`, `rejected_policy`, `rejected_budget`.

**The ledger stores metadata only.** There is deliberately no column for a prompt, a provider
response or any resident-written text, so an audit of the table cannot leak content.
`AICallEventRepository` is append-only — it has `record()` and `count_since()` and no update or
delete. Every read is scoped by `estate_id`, and `record()` flushes so the owning service commits
once.

`ok` and `provider_failed` rows consumed a provider attempt and therefore count against the
budget; rejections are auditable but free. A `disabled` outcome is not recorded at all: while the
layer is off nothing was attempted and nothing was sent, and logging every refused call would
bury the real rows in noise.

Failure policy, deliberate and asymmetric:

* The budget **count fails closed**. If the ledger cannot be read, the cap cannot be verified, so
the call is refused with `budget`. This is the safe direction for cost control, and it is still a
clean `AIUnavailableError`, so callers fall back.
* Ledger **writes are best-effort**. A row that cannot be written is logged (status and exception
type only) and the call still succeeds, because the provider call has been paid for and AI is
never load-bearing. A dropped row means the next count under-reports, which is why it is logged
loudly.

### Redaction

`app/core/ai/redaction.py` replaces recognised personal data with fixed markers before a prompt
is sent: `[EMAIL]`, `[PHONE]`, `[ID]`, `[NAME]`, `[UNIT]`. It handles email addresses, South
African phone formats (`+27 ...`, `0XX XXX XXXX` with spaces, dots or hyphens), 13-digit South
African ID numbers, caller-supplied names (case-insensitive, whole word, name parts of three or
more characters) and caller-supplied unit numbers.

It is **best-effort and cannot catch a name it was not told about**, or personal data that matches
no pattern. It reduces exposure; it does not make a prompt safe, and it is never a substitute for
the `data_class=personal` gate, for keeping resident text out of the system instruction, or for
simply not sending personal data when a feature does not need it.

### First caller: HOA triage suggestions (BATCH AI-3)

`app/community/services/complaint_triage_service.py` is the reference implementation of "AI as
advisory only". An HOA admin may ask for one suggestion per complaint; a human then accepts,
overrides or dismisses it, and the labels are frozen at that point. Nothing in the path can
modify a complaint row or dispatch a work order.

* **Vocabulary, not free text.** The provider may only return a category, a priority and a trade
  from `app/community/domain/triage_vocabulary.py`. That module is the single source of truth for
  the provider JSON schema, the API validators and the database check constraints, so the three
  cannot drift apart, and there is deliberately no field in which a provider could store prose.
* **Eligibility.** Only a non-anonymous complaint still in `submitted`/`reviewed` is triaged.
  Anonymous complaints are refused (409): redaction would need the author's identity, and holding
  it at all is the disclosure we refuse. Revisit after the POPIA review.
* **What leaves the building.** The redacted category and description plus the resident-chosen
  priority, wrapped in `<complaint>` markers with a system prompt stating the content is untrusted
  data and never instructions, at `data_class=personal`. Never a user id, a name, a unit number, an
  estate name or a timestamp.
* **Untrusted output.** The response is re-validated against the vocabulary before anything is
  stored. An out-of-vocabulary or extra field is `invalid_output` → 503 and no row, so a jailbroken
  or drifting model cannot write a value the database would have to reject.
* **Nothing is logged or stored but labels.** The suggestion row holds the labels, the provider,
  the model and `prompt_version` (`triage-v1`). No prompt, no provider response, no complaint text —
  in the table or in a log line.
* **Write-once decision.** `accepted` copies the suggestion, `overridden` records corrected labels
  (at least one differing), `dismissed` records none. The update is conditional on
  `decision IS NULL`, so two admins deciding at once produce exactly one decision rather than a
  last-write-wins race.

### HTTP mapping

`AIUnavailableError` maps to HTTP **503** with envelope code `AI_UNAVAILABLE`, a generic message,
the closed reason code in `details.reason`, and the request id — registered in `app/main.py`.
An optional feature being off is not a server bug, and the body never carries a key, a prompt or a
provider response. Callers that treat 503 as retryable must not turn it into a hot loop: the guard
already refuses over-budget calls, so retrying spends nothing, but it still costs a request.

### Data protection

- Resident-written text is **untrusted data and personal data**. It is placed in the
  `user` role, never the system instruction, and callers must pass
  `data_class=personal` when it is present. Provider text is data, never instructions.
- Personal data that must be sent is reduced with `redact()` first (see above), with the
  caller passing the names and unit numbers it knows.
- Keys are `SecretStr`. Nothing in the layer logs a key, a prompt, or a raw provider
  response; errors carry a reason code only, and schema errors never echo the offending
  value.
- The Gemini adapter sends `store: false` so the provider does not retain the
  interaction.
- `AI_DAILY_CALL_CAP_PER_ESTATE` (200) is enforced per estate over a rolling 24 hours from
  the `ai_call_events` ledger, including failed attempts.

### Kill switch

Turning AI off must never require a deploy of new code:

1. `AI_ENABLED=false` in the environment (or remove the key) — the wrapper refuses
   before building a client.
2. Per-feature: set `AI_INSIGHTS_ENABLED=false` / `AI_TRIAGE_ENABLED=false` to disable
   one capability while leaving the other untouched.
3. `AI_PERSONAL_DATA_ALLOWED=false` revokes personal-data egress instantly even if a
   feature flag is left on by mistake.
4. `AI_PROVIDER=fake` gives a deterministic, network-free client for development and
   tests; configuration **refuses** it when `ENVIRONMENT` is not `development` or `test`.
5. `AI_DAILY_CALL_CAP_PER_ESTATE=0` refuses every call while leaving the feature flags on,
   which stops spend without editing any other flag.

Configuration fails fast at startup if `AI_ENABLED` is set without the selected
provider's model and credentials, if `AI_PROVIDER=fake` outside development/test, or if
`AI_PERSONAL_DATA_ALLOWED=true` while `AI_ENABLED=false`. A half-configured AI layer
must not boot.

### Provider contracts (verified, not guessed)

The Gemini adapter targets the **Interactions API**, which Google documented as
generally available and "recommended for all new projects" as of June 2026:

- `POST https://generativelanguage.googleapis.com/v1beta/interactions`
- auth header `x-goog-api-key` (no `Authorization: Bearer`)
- body: `model`, `input`, `system_instruction`,
  `response_format: {type: "text", mime_type: "application/json", schema: <JSON Schema>}`,
  `generation_config.max_output_tokens`
- response: `steps[].content[].text` holds the JSON string (top-level `output_text` is
  preferred when present)

Sources read 2026-10-10:
[Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output),
[Interactions API reference](https://ai.google.dev/api/interactions-api),
[Text generation](https://ai.google.dev/gemini-api/docs/text-generation),
[Interactions API GA announcement](https://blog.google/innovation-and-ai/technology/developers-tools/interactions-api-general-availability/).

The OpenAI-compatible adapter targets `POST <base_url>/v1/chat/completions` with
`Authorization: Bearer <key>`, `response_format: {"type": "json_object"}`, `max_tokens`,
and reads `choices[0].message.content`. That API has no schema field, so the schema is
enforced locally after the response arrives.

No new dependency was added; both adapters use `httpx`, which is already present.

## Consequences

- AI features cost one extra config block, one guarded wrapper call and one ledger row, and
  cannot bypass the guardrails by construction.
- Adapters are testable without network (`httpx.MockTransport`) and the guard without a
  database (an in-memory ledger), so the safety net is cheap.
- The budget gate needs the ledger read to succeed; a database outage therefore disables AI
  rather than risking uncontrolled spend. That is the intended trade-off, not an accident.
- Every AI attempt is attributable to exactly one estate, in a table that cannot hold content.
- The ledger has no retention policy yet: rows are small and metadata-only, but a busy estate
  produces a row per call and nothing prunes them. Review when a caller exists.
