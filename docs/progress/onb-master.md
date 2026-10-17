# ONB MASTER — finish onboarding, make VALORA usable end to end in one live complex

**Session report** (two sittings: P0–P2, then P3). 2026-10-12, branch `valora-work`.
Nothing was committed, reset, checked out or stashed. **No applied migration was
edited.** No real-provider (Gemini) run was made or claimed.

**Phase status: P0 PASS · P1 PASS · P2 PASS · P3 PASS · P4 PASS · P5 PARTIAL**
(the dashboard Living Score wiring, P4 and most of P5 are done; the two acceptance
runs and the full backend re-run that P5.4 asks for are listed under "Still
outstanding").

Skills: the batch names `valora-security-review`, `valora-testing`,
`valora-migration-safety`, `valora-session-protocol`, `frontend-app-builder`,
`ui-ux-pro-max` and `playwright-cli` — **none of those exist in this checkout**.
`.agents/skills/` holds seven directories only: `valora-api-contracts`,
`valora-architecture`, `valora-data-strategy`, `valora-domain-model`,
`valora-living-score`, `valora-product-design`, `valora-quality-gates`. For P3 the
design guidance came from `valora-product-design` and the project's own
`docs/design/VALORA-DESIGN-DIRECTION.md` and `frontend/index.css` tokens; the
quality gates came from `valora-quality-gates`.

Databases (printed before use; no other database was touched):

```text
P0–P2      : valora_master_test_20261012      (dropped at the end of that sitting)
P3 backend : valora_p3_onb_test_20261012      (created, migrated, tests run, dropped)
P3 live    : valora_p3_journey_20261012       (created, migrated, live journey run, dropped)
```

`valora_db`, `valora_pilot_dev`, `valora_test`, `valora_test_batch7c`,
`valora_ai5_wiring`, `valora_master_test_20261012` (recreated and dropped in P1) and
the three `vantage-local-*` containers were left alone. The two P3 databases were
created with `docker exec valora_db psql -U valora_user -d postgres -c "CREATE
DATABASE …"` and dropped again with `DROP DATABASE` after the runs.

---

## P0 PREFLIGHT — PASS

Verified in the real tree (not assumed):

| Prerequisite | Evidence |
| --- | --- |
| ONB-1 account_type signup | `app/identity/schemas/auth.py` `account_type: AccountType`; `AccountType = Literal["resident","estate_admin","service_provider"]`; the cross-field validator rejects a `role`/mismatched payload |
| ONB-1 estate registration | `AuthService._register_estate_admin` — user + estate + membership, one commit |
| ONB-1 platform_admin | `app/common/enums.py`; `scripts/assign_platform_admin.py` |
| ONB-2 units/bulk | `app/property/api/properties.py` `POST /properties/bulk` |
| ONB-2 join codes | `app/identity/api/join_codes.py` — `GET /join-codes/current`, `POST /join-codes` |
| ONB-2 memberships | `app/identity/api/memberships.py` — join, list, delete |
| FE-1 generated types + tooling | `frontend/src/api/generated/{enums.ts,schema.d.ts,enums.drift.test.ts}`, `vitest.config.ts`, `playwright.config.ts`, `npm run gen:api` / `check:api` |
| AI-5 panels | `frontend/src/components/HealthBrief.tsx`, `frontend/src/components/TriageSuggestion.tsx` |
| Living Score endpoints | `app/analytics/api/living_score.py`, mounted under `/api/v1/analytics` |

## P1 PROVIDERS, JOURNEY GAPS, OPERATOR RESET — PASS

### 1.1 `POST /api/v1/memberships/providers?estate_id=` — done

`MembershipService.add_provider_by_email`: `hoa_admin` membership of that estate →
the email must belong to a user with the `service_provider` role **and** a linked
`ServiceProvider` profile → membership (`role=service_provider`, `property_id
NULL`) **plus** a `joined` event, committed once. One uniform 404 for every
unusable email (unknown / a resident's / a provider account with no profile).
Already a member → 409 (also on a lost concurrent race). Failed lookups are
counted by the **ONB-2 limiter** (`JoinAttemptLimiter`, reused: 5 per admin per
15 minutes → 429); a successful lookup clears the window.

### 1.2 Provider directory scoped to the estate — done

`GET /providers?estate_id=` and `GET /providers/{id}?estate_id=` require an
`hoa_admin` **membership of that estate** and return only providers who hold a
`service_provider` membership of it (`ServiceProviderRepository.get_all_in_estate`
/ `count_in_estate` / `get_by_id_in_estate`). Phone and email are shown only in
that admin response and in the new `GET /providers/me` (the provider's own
profile). Reviews: a resident may only review a provider they share an estate
with (`ReviewService._works_in_a_shared_estate` over
`EstateMembershipRepository.list_estate_ids`); anything else is the same 404 as an
unknown provider, and a legacy provider row with `user_id IS NULL` can never be
reviewed.

### 1.3 Work orders — done

Creating one already required a provider membership of the estate (409
otherwise) — verified by the journey test, not re-implemented. New:
`GET /work-orders/mine?estate_id=` (declared before `/{work_order_id}`) for a
`service_provider` member, paginated, only their own rows (no profile → empty
page, not an error); and `GET /complaints/{id}/work-order?estate_id=` for the
complaint's author or an `hoa_admin` of the estate, reusing `WorkOrderResponse`
unchanged (latest work order for that complaint; 404 when there is none).

### 1.4 `backend/scripts/reset_password.py` — done

Dry-run by default; `--apply` generates the password with `secrets` (4 groups of 5
from a 32-symbol alphabet with no lookalikes), prints it **once**, stores only the
bcrypt hash, never logs it. Prints the redacted target database first (from
`DATABASE_URL` only, never `.env`), honours `--expect-database`, refuses a
demo-looking database without `--allow-demo-database`.

### 1.5 Acceptance test — done

`backend/tests/test_onb_master_p1_journey.py` (13 tests: 5 integration, 8 policy).
The integration test walks the whole flow **through the HTTP API**: admin signs up
→ registers the estate → bulk units (+ a duplicate batch refused whole) → join
code → resident signs up and joins → provider signs up (sees no estate yet) →
admin adds the provider → complaint → reviewed → work order assigned → resident and
provider both see it → in_progress → completed → complaint resolved → resident
rates → members list is exactly those three people → `POST
/analytics/living-score/recalculate` → `GET /analytics/living-score` reflects the
same snapshot. Cross-estate: a second estate's admin, resident and provider are
denied (403) at 15 endpoints/actions, and another estate's unit read inside
estate A is a 404.

## P2 ESTATE PROFILE, PHOTOS, PUBLIC DIRECTORY — PASS

Dependency: **Pillow 12.3.0**, the only new backend dependency (published
2026-07-01, i.e. more than 14 days before this session's date of 2026-10-12; cp314
Windows wheels exist, so Python 3.14 needs no build toolchain). Pinned exactly in
`backend/requirements.txt` with the reason recorded inline.

### 2.1 Migration — done

`backend/alembic/versions/c3f7a1b9d4e2_add_estate_photos_and_publish_flags.py`
(revises `b1e4f7a9c2d5`, single head): `estates.is_public` and
`estates.show_living_score` (BOOLEAN NOT NULL, server default false), and
`estate_photos` with named constraints (`uq_estate_photos_public_id`,
`ck_estate_photos_dimensions_positive`, `fk_estate_photos_estate_id_estates`
RESTRICT, `fk_estate_photos_uploaded_by_users` SET NULL), index
`ix_estate_photos_estate_id_position`. Additive and non-destructive; the `false`
server defaults are metadata-only on PostgreSQL 11+, so the upgrade does not
rewrite `estates`. Downgrade drops the table and the two columns.

### 2.2 Admin endpoints — done

`GET`/`PATCH /api/v1/estates/profile?estate_id=` (members read; `hoa_admin` of the
estate writes; the name is **not** in the update DTO and an unknown field is a
422). `POST /estates/photos?estate_id=` (multipart `file` + optional `caption`),
`GET /estates/photos`, `PATCH /estates/photos/{photo_id}` (caption, position),
`DELETE /estates/photos/{photo_id}`.

### 2.3 Upload safety — done

At most 12 photos per estate (13th → 409, proven by 12 real uploads over HTTP);
5 MB ceiling (the bytes are read with a hard ceiling, never the whole file first);
jpeg/png/webp accepted; **decoded with Pillow**, so a renamed non-image is a 400;
the declared pixel count is capped at 40 MP **before** the decode, with Pillow's
own `MAX_IMAGE_PIXELS` guard left armed behind it; re-encoded to JPEG (transparency
composited onto white, EXIF orientation baked in); longest side at most 1920 plus a
480 thumbnail; **all EXIF/GPS stripped** (asserted by a GPS test); the uploaded
filename is never used (asserted with `../../../../evil.jpg`); stored under
`UPLOAD_DIR` (default `uploads`) as `<public_id>.jpg` + `<public_id>_thumb.jpg`
with a 32-char `secrets` handle; `uploads/` added to `.gitignore` and
`.dockerignore`; the files are removed when the photo is deleted (and on a failed
insert, so a row and its files cannot diverge).

### 2.4 Public endpoints, no authentication — done

`GET /api/v1/public/estates` (paginated, `page_size <= 50`, optional `q` over name
/ suburb / city, published estates only, with a unit count and cover photo id);
`GET /api/v1/public/estates/{id}` (404 unless published, adds
`photos[{public_id, caption}]` and, **only** when `show_living_score` is true and a
snapshot exists, `living_score {overall_score, status, as_of, engine_version,
data_origin}`); `GET /api/v1/public/photos/{public_id}?size=thumb|full` with
`X-Content-Type-Options: nosniff` and `Cache-Control: public, max-age=3600`. The
public DTOs are allow-lists and a test pins their **exact key sets** against a
forbidden-field list (unit numbers, addresses, emails, phones, membership ids,
photo row ids, complaints, incidents, join codes).

## P3 FRONTEND — PASS

Screens, states and tests for every P1/P2 endpoint, plus the mobile sweep the AI-5
session left open. No backend file was changed in this phase.

### 3.1 Routing and the role decision — done

`frontend/src/App.tsx` now mounts `/estates`, `/estates/:id`, `/join`,
`/provider/waiting`, `/welcome`, and the two shell-nested trees `/admin/{setup,members}`
and `/provider/work`. `frontend/src/lib/roleRouting.ts` is a pure function
(`homeRouteFor`) — an estate administrator lands on the setup checklist, a resident
with no estate on the join screen, a provider with no estate on the waiting screen,
anybody with an estate on the dashboard — and `/welcome` is the one place that
applies it after sign-in, so no account is dropped on a dashboard it cannot read.
Sign-in and registration now navigate to `/welcome`; a deep link
(`location.state.from`) still wins.

### 3.2 Screens — done

| Screen | What it does |
| --- | --- |
| `/estates`, `/estates/:id` | the public directory: search, pagination, empty/search-empty/error states, gallery, unit count, "how to join" steps, and the published score card **only** when the API sent one (with the demo badge when `data_origin=demo`) |
| `/register` | the three account types the API accepts (resident, estate administrator + estate, service provider + trade/phone); no `role` field is ever sent |
| `/join` | code + unit number, validation before spending one of five rate-limited attempts, uniform-404 and 429 states, then `/app` |
| `/provider/waiting` | the one onboarding state nobody can finish alone: what to do, their own provider profile, and a "check again" |
| `/admin/setup` | the five-step checklist (description, units, join code, photographs, publish) derived from API values, bulk unit paste with a line-number error, photo uploader with progress + caption + reorder + delete, join-code card with copy and rotate, and both publish switches |
| `/admin/members` | the register (role filter, pagination), add a provider by email, and a removal drawer that states what removal does **not** undo (the account, the history, a live join code) |
| `/provider/work` | the provider's own jobs with exactly the two transitions the API allows (`assigned → in_progress → completed`), the completion note that becomes the resolution, and the honest empty state |
| shell | nav entries for Estate setup, Members and My work; the estate selector is now shrinkable; "Find a complex" is reachable from the shell, the public header (≥sm), the hero and the footer |

### 3.3 The 390px overflow — measured, then fixed

The AI-5 session recorded a 275px dashboard overflow at 390px and could not fix it
outside its batch. It is fixed, and the sweep that found it is now a test:
`frontend/e2e/mobile.spec.ts` measures `documentElement.scrollWidth` against the
viewport for 16 routes/roles with a **mocked API** (so it needs no database, seed
or account), and on failure prints the offending elements and their ancestor chain
with widths, padding and overflow.

Four real causes, each fixed at the source:

1. **The app header.** `select` elements have a min-content width equal to their
   longest option, so an estate named "Ridge Close Lifestyle Estate" made the whole
   header — and therefore every `/app` route — 405px wide. The estate selector is
   now `min-w-0` with a capped width (the selected name truncates).
2. **The public header.** Wordmark + tagline + three buttons never fitted 390px.
   The directory link moved out of the header below `sm` (into the hero and footer),
   the tagline is desktop-only, and the bar wraps rather than widening the page.
3. **The public estate detail.** A grid item's automatic minimum is its min-content,
   and a published photograph's intrinsic width is far wider than a phone: the
   column grew to 383px inside a 350px container. Both tracks are `min-w-0`.
4. The dashboard KPI/table blocks were fine; they were only being dragged wide by
   (1).

Measurement: `/app` and every `/app/*` route were 405 > 390; `/` and `/estates`
396; `/estates/1`, `/join` and `/provider/waiting` 403–413. All 16 routes now
report `scrollWidth == clientWidth` at 390 × 844.

### 3.4 Tests — done

**Unit/component (Vitest, jsdom).** Nine new spec files, +66 tests (7 files / 52
tests → 16 files / 118 tests). They pin: the routing decision (including that it can
never return `/welcome`, so the redirect cannot loop); the bulk-unit parser
(line-numbered rejections, blank lines, bare unit numbers); the upload hints; the
setup checklist (including that an unanswered request is *not* a zero); the join
screen (validation before any attempt, the uniform 404, the 429, and that it names
no estate it was not told about); the member register (the removal promise, the
provider 404 wording, and that an administrator row has no remove button); the
provider work list (exactly the two offered transitions, the refused transition shown
verbatim, no action on a finished job); the public directory (published-vs-private
fields, the three empty/error states, and that the cover photo is fetched by its
public id); and the registration payload for all three account types with no `role`
key anywhere.

**Live journey (Playwright, real backend).**
`frontend/e2e-live/onboarding-journey.spec.ts` — four ordered tests driving the real
UI: an estate administrator self-registers and registers the estate in one step →
completes all five checklist steps (description, two units pasted, a join code, a
real JPEG upload, publishing) and sees `5 of 5`, with the code surviving a reload →
a visitor with no account finds the published estate, opens it, and sees the
description and unit count but no score, no unit numbers and no residents → a
resident self-registers, is routed to `/join`, redeems the code against their unit,
lands on the dashboard, and logs a complaint that appears as "Logged" → a provider
self-registers and is told to wait, the administrator adds them by email and the
register shows them as a service provider, and the provider then sees their (empty)
work list. It creates its own accounts from a per-invocation stamp, so it needs no
seed and can run repeatedly against a shared database; a worker restart cannot
invent a second set of accounts (`JOURNEY_STAMP`, set once by
`playwright.live.config.ts`).

This is what found four defects that unit tests could not: the setup screen
replacing itself with a loading state after every save (so the confirmation the
person just earned vanished), the verbose accessible names on the account-type
radios (fixed with `aria-describedby`), and the two spec-side assumptions (a
controlled checkbox does not flip on the click; `check()` asserts immediately).

## P4 DEMO SEED — NOT STARTED

`app/seed_demo.py` is untouched, no `valora_demo` database was created, and no
demo photos or historical Living Score snapshots were generated.

## P5 DOCKER, ACCEPTANCE, DOCS — NOT STARTED

`docker-compose.yml`, `README.md`, `docs/GETTING_STARTED.md`,
`docs/KNOWN_LIMITATIONS.md`, `tasks/todo.md` and the acceptance screenshots were
not touched. (`docker-compose.yml` still points its frontend service at the obsolete
`../FrontEnd` path.)

---

## Evidence — every command and its result

### Backend suites

| Command | Result |
| --- | --- |
| `pytest tests/test_onb_master_p1_journey.py -q` | **13 passed** (with `TEST_DATABASE_URL`); **8 passed, 5 skipped** without it |
| `pytest tests/test_onb_master_p2_photos_and_public.py -q` | **24 passed** (with `TEST_DATABASE_URL`); **16 passed, 8 skipped** without it |
| `TEST_DATABASE_URL=…valora_master_test_20261012 pytest tests -q -p no:cacheprovider` | **814 passed, 0 failed, 0 skipped** in 713.82 s (`EXIT=0`) |
| `pytest tests -q -p no:cacheprovider` (no `TEST_DATABASE_URL`) | **715 passed, 99 skipped, 0 failed** in 99.62 s |
| **P3 re-run**, on a fresh `valora_p3_onb_test_20261012`: `TEST_DATABASE_URL=… pytest tests/test_onb_master_p1_journey.py tests/test_onb_master_p2_photos_and_public.py -q -p no:cacheprovider` | **37 passed** (13 + 24) in 109.90 s, `EXIT=0` |
| `alembic -c alembic.ini upgrade head` (no `DATABASE_URL` in `.env`) | refused (exit 2) — it needs the two variables, as `AGENTS.md` says |
| `compileall -q app scripts tests`, `flake8 app tests scripts --select=E9,F63,F7,F82`, `git diff --check` | OK / **0** / clean |

No Python file was modified during P3, so `compileall`/`flake8` were not re-run in
that phase; the suite above is the check that matters for it.

### Migrations (throwaway databases, target printed first)

| Command | Result |
| --- | --- |
| `alembic -c alembic.ini heads` | `c3f7a1b9d4e2 (head)` — single head |
| `alembic upgrade b1e4f7a9c2d5:c3f7a1b9d4e2 --sql` / `downgrade … --sql` | clean offline DDL up and down |
| `alembic upgrade head` → `downgrade -1` → `upgrade head` on `valora_master_test_20261012` | clean round trip back to head |
| `alembic upgrade head` on `valora_p3_onb_test_20261012` **and** `valora_p3_journey_20261012` | both reached `c3f7a1b9d4e2` from an empty database with no error |
| `psql \d estate_photos` | the expected columns, `uq_estate_photos_public_id`, `ix_estate_photos_estate_id_position`, `ck_estate_photos_dimensions_positive` |

### Operator CLI (real database, dry run then apply)

| Command | Result |
| --- | --- |
| `scripts/reset_password.py --email p1_provider@example.com --expect-database valora_master_test_20261012` | dry run: nothing written, target printed redacted |
| `… --apply` | printed one password, replaced the hash |
| `… --expect-database valora_db --apply` | refused: "does not match the target 'valora_master_test_20261012'. Nothing was written." (exit 1) |

### Frontend suites (P3)

| Command | Result |
| --- | --- |
| `npm run typecheck` (`tsc -b --noEmit`) | exit 0 |
| `npx vitest run` | **16 files / 118 tests passed** (was 7 / 52 before P3) |
| `npm run test:e2e` (mocked API, dev server started by the config) | **18 passed** in 1.3 m — 14 route overflow checks, 2 onboarding screens, the 2 pre-existing smoke tests |
| `npm run check:api` | "the generated API files are in sync with docs/openapi.json" |
| `E2E_BASE_URL=http://localhost:5199 npm run test:e2e:live -- --grep "onboarding journey"` | **4 passed** in 1.5 m, against a real backend |

The live run's own setup, for the record: `alembic upgrade head` on
`valora_p3_journey_20261012`; `uvicorn app.main:app --host 127.0.0.1 --port 8015`
with that `DATABASE_URL`, `SECRET_KEY` and `CORS_ORIGINS=["http://localhost:5199",…]`;
`vite --port 5199 --strictPort` with `VITE_API_BASE_URL=http://127.0.0.1:8015`;
readiness checked with `curl` (api 200, web 200) **before** the run; both processes
killed by PID afterwards and the database dropped. `E2E_BASE_URL` must point at a
dev server whose `VITE_API_BASE_URL` is the backend under test — the config starts
no server, so a stale pair cannot be used silently.

## Deviations (everything that differs from the brief, on purpose)

1. **Skills missing.** Seven of the named skills are not in the checkout; the
   fallback (`valora-quality-gates`) and, for P3, `valora-product-design` were used
   and this is stated at the top.
2. **Provider review routes are legacy-gated** (`ENABLE_LEGACY_ROUTES=False` by
   default), so the new "must share an estate" rule is exercised against
   `ReviewService` directly instead of over HTTP. The routes were not moved
   (minimal change) — a resident-facing "rate a provider" flow is therefore still
   not reachable in the shipped app.
3. **`GET /providers/{id}` now requires an estate membership for a provider caller
   too** (both credential halves). A behaviour tightening, recorded rather than
   hidden.
4. **`app/core/exceptions.py` gained two exception classes** (`BadRequestException`
   400, `PayloadTooLargeException` 413) and the error-envelope status map gained
   `413: PAYLOAD_TOO_LARGE`.
5. **The join code is the proof of the right to join**, so a member of another
   estate who is *given* a live code may join. The denial test asserts the honest
   version of this (an unusable or wrong-unit code is a uniform 404).
6. **A real bug was found by the new integration tests and fixed**:
   `EstateRepository.count_public` reused the ordered public statement, which
   PostgreSQL rejects in a count. It now drops the ORDER BY.
7. **Photo ordering:** an upload appends (`position = count`), and the cover photo
   is the lowest `position`; deleting a photo does not renumber the rest.
8. **P1 was implemented before its acceptance test was written** (the session was
   interrupted mid-P1 and resumed), so "written first, failing" is not satisfied for
   P1.5 by chronology — the test does run and covers the whole flow.
9. **P3 extended `Register.tsx`** to offer the three account types. The batch's P3
   list did not mention registration, but `ONB-1` shipped an API the UI never used:
   without it an estate cannot be created from the app at all, and the whole journey
   stays curl-only. The API is unchanged; the form only sends what it already
   accepts.
10. **P3 added `/welcome`** — one post-sign-in route that applies the membership
    decision, rather than sprinkling role checks through each screen.
11. **The mobile sweep blocks the Google Fonts requests and awaits
    `document.fonts.ready`**, so the measurement is repeatable and works offline. The
    layout is therefore measured with fallback metrics; a font-metric-specific
    overflow would not be caught by this spec (it would be by a real browser).
12. **The live journey does not assign or complete a work order.** That half of the
    journey is covered by the backend acceptance test
    (`test_onb_master_p1_journey.py`); the live spec asserts the provider's honest
    empty state, and the provider's two transitions are covered by
    `ProviderWork.test.tsx` against mocked responses. Driving complaint → triage →
    assignment through the UI would have doubled the spec's length for coverage the
    backend test already has.
13. **The live spec signs in via an intermediate page.** The app returns you to
    where you were before a protected screen redirected you
    (`location.state.from`), and a browser *reload of the same URL* keeps that
    history entry's state while Playwright's `goto` on the current URL is a reload —
    so `goto('/login')` alone could carry a stale deep link. Navigating through
    `/estates` first makes `/login` a fresh entry. Test-harness detail, not an app
    defect.
14. **Signing out from a protected screen lands on `/login`, not `/`.** The
    `Protected` wrapper redirects a now-secret-less visitor, which wins over the
    shell's `navigate('/')`. Cosmetic, accepted (the sign-in page is a fine
    destination), and the journey helper allows either.
15. **`Field` labels include their hint in the same `<label>`**, so a control's
    accessible name is "Description Plain text. …". The new spec anchors on the start
    of the name. Rewiring the shared `Field` to `htmlFor` + `aria-describedby` is a
    follow-up, not a P3 change (it touches every screen).
16. **P4 and P5 are not started.** Nothing was skipped, weakened or faked.

## Open questions

1. **Public photo links are unlisted, not private** (recorded as the brief asks):
   `GET /api/v1/public/photos/{public_id}` serves a photo whose estate is *not*
   published, and one that was never in a published album. The id is unguessable,
   but the rule is worth a product decision.
2. Should an unpublished estate's photos still be served at all? Related to 1.
3. Animated WebP/GIF: GIFs are not accepted; an animated WebP would be stored as a
   single (first) frame. Untested — no test image was built for it.
4. No malware scanning, no image metadata beyond stripping, no per-estate upload
   rate limit, and uploads live on local disk (`UPLOAD_DIR`), which is single-host.
5. Removing a member still does not revoke a join code they hold (ONB-2, unchanged).
   The removal drawer now *says* so and points at rotation.
6. The two failure-mode messages for uploads ("not an image" vs "too large to
   process") are distinct; that is deliberate, but it does tell a client which limit
   it hit.
7. **The dashboard's Living Score panel still shows `score={null}`** with the
   "Engine pending" copy, even though `/analytics/living-score` now serves the latest
   snapshot and an estate can publish it. The panel was out of P3's scope; it is now
   the most visible inconsistency in the product.
8. The uploader's client-side hints duplicate the server's limits (three formats,
   5 MB, 12 photos). A contract field would remove the duplication.
9. `roleLabels` (and the trade list used as form suggestions) are hand-written in
   `lib/display.ts` because the contract publishes no role or trade vocabulary.
10. The join-code card shows one live code and rotates it; there is no view of who
    redeemed which code (the membership event log exists in the database, not in the
    UI).
11. An estate administrator cannot move a member's unit, change a member's role, or
    add a resident by email — the API has no endpoint for any of them, and the
    register screen says so rather than offering a dead end.

## What the owner can now do (plain words)

- **Onboard a real complex end to end in the browser.** Create an account as the
  estate administrator, register the estate in the same form, then work the setup
  checklist: write the description, paste a list of units, issue a join code, upload
  photographs (up to twelve, safe by construction), and publish. The estate then
  appears in a public directory anyone can search, with its score shown only if the
  owner opts in separately.
- **Bring residents and providers in.** A resident self-registers, is sent to the
  join screen, and redeems the code against their unit; a provider self-registers and
  is told to wait for an estate to add them, which the administrator does by email
  from the members screen. The register shows who is in the estate, in which role,
  and removing somebody states exactly what that does and does not undo.
- **Work an issue to resolution.** A resident logs a complaint against their unit;
  the HOA triages it and assigns a provider; the provider sees only their own jobs,
  starts the work, and completes it with the note that becomes the resolution; the
  resident rates it — and the same flow is proven end to end by one backend test.
- **Do all of it on a phone.** Every screen, signed in or not, now measures inside a
  390px viewport, and a test enforces it.
- **Recover a locked-out account.** `scripts/reset_password.py --email …` prints a
  new password once (dry run until `--apply`), because there is still no email
  transport.

## What is NOT ready

- **No demo.** No `valora_demo` database, no deterministic seed, no placeholder
  photos, no historical score snapshots, so a sales walkthrough still has to start
  from registration (P4).
- **No hosting story.** `docker-compose.yml` still points its frontend service at the
  obsolete `../FrontEnd` path; no acceptance screenshots, no README or
  getting-started guide, no known-limitations document, todo list not ticked (P5).
- **No email of any kind**: no verification, no invited-password reset (the operator
  CLI is the interim).
- **No HTTPS, no backups, no monitoring**, single-process rate limiters only.
- **The work-order assignment path is admin-only through the complaint drawer**; the
  provider directory lists contractors but does not assign from there.
- **The dashboard does not show the Living Score** the API now serves (see open
  question 7).
- **The AI layer was not exercised**: no real-provider run was made or claimed, and
  the AI-off path was not re-checked in this phase.

---

# P4 / P5 SITTING — the dashboard fix, the demo seed, Docker, acceptance, docs

## (a) Dashboard Living Score panel — DONE

`frontend/src/lib/analytics.ts`, `src/components/LivingScore.tsx` and
`src/routes/Dashboard.tsx` now read `GET /api/v1/analytics/living-score?estate_id=`
and render the **stored** snapshot: overall score, status, the five components with
their own status, `as_of`, engine version, calculated-at, the drivers, and the
`Demo data` badge when `is_demo` is true. There is no arithmetic in React, and a
missing/`insufficient_data` snapshot renders the "Not enough data yet" panel with
the engine's own explanation (never a zero). An HOA administrator of the estate
gets "Recalculate now", which POSTs and then **re-reads** the stored snapshot; a
refused recalculation is shown verbatim. Tests: `src/routes/Dashboard.livingScore.test.tsx`
(5) and `src/components/LivingScore.test.tsx` — `npx vitest run`: **20 files / 142
tests passed**.

Also fixed here, because the live journey measured it: the dashboard's cards are
grid items whose automatic minimum is min-content, so a long complaint description
(`truncate`, i.e. nowrap) pushed the page 443 px wider than a 390 px phone. Every
card in `Dashboard.tsx` and `LivingScore.tsx` is now `min-w-0`.

## P4 DEMO SEED — PASS

`backend/app/seed_demo.py` (820 lines) + `python -m app.cli seed-demo
--expect-database <db>`. Guarded (**the live connection's** `current_database()`
must equal the named database *and* contain "demo"), deterministic (no randomness;
one clock anchor per run), idempotent (a second run reports "already exists —
nothing changed"), and it **never writes `ai_insights` or
`complaint_ai_suggestions`**.

Verified content (throwaway database, exact counts from the tests): 24 units, 1
`hoa_admin`, 20 residents (`resident01` holds two units — ADR-007), 2 providers that
are both linked to a profile and members of the estate, 36 complaints covering all
six statuses with the `complaint_events` each transition implies, >20 work orders
with ≥5 resident ratings, 6 security incidents, 5 announcements, 5 placeholder
photographs **through the real upload pipeline** (re-encoded, EXIF-free, ≤1920 px,
480 px thumbnail), and 4 **real** Living Score snapshots produced by the real engine
at past `as_of` dates (the estate is backdated 120 days).

```text
TEST_DATABASE_URL=….valora_demo_test_20261012 pytest \
  tests/test_onb_master_p4_demo_seed.py tests/test_seed_demo_flag.py \
  tests/test_onb_master_p1_journey.py tests/test_onb_master_p2_photos_and_public.py -q
→ 49 passed in 159.51s      (P4 10 + seed flag 2 + P1 13 + P2 24)
```

`valora_demo` itself holds: 1 estate, 24 users, 25 memberships, 24 units, 36 seeded
complaints (+8 filed by the live journey runs), 32 work orders, 6 incidents, 5
announcements, 5 photos, 6 snapshots, **0** AI rows.

## P5.1 DOCKER — PASS

`docker compose up -d --build` from `backend/`: clean build, three containers, and
`docker compose ps` reports `backend-api-1 running healthy`, `backend-frontend-1
running healthy`, `backend-db-1 running`. Healthchecks were **added** to the api
(`/health` via urllib) and the frontend (`wget` on `/`) so that word means
something; the api's `start_period` is 120 s because the first import on a Windows
bind mount takes ~90 s. Migrations run in the api container's `CMD`: `alembic
current` → `c3f7a1b9d4e2 (head)`. The frontend answers on 4173, the api `/health`
200. The compose frontend is built from `frontend/` with the root context, publishes
4173, and `CORS_ORIGINS` (defaults and `.env.example`) include 4173.

The frontend image build **caught a real defect**: `tsc -b` failed on
`ComplaintDrawer.refresh.test.tsx` (a `string` passed where `Complaint['status']` is
required). Fixed; `npm run typecheck` is clean.

## P5.2 ACCEPTANCE — PARTIAL

| Run | Result |
| --- | --- |
| Live journey, `--project=desktop` + `--project=mobile` on `valora_demo`, fake provider pinned | **2 passed** (desktop 1.2 m, mobile 45.2 s) — assign → work order → provider completes → resident rates → HOA recalculates → dashboard shows it; screenshots in `docs/acceptance/` |
| Mobile measurement inside that run | `overflow@the resident complaint list: scrollWidth=390 clientWidth=390`; `overflow@the administrator dashboard: 390 / 390` (the P3 defect is gone with real data) |
| AI-on wiring, `AI_PROVIDER=fake`, `--project=desktop` | **4 passed** (brief, triage, resident sees no triage, 390 px panels) |
| AI-off run (template summary, triage unavailable) | **not run** — the container environment was switched to `AI_ENABLED=false` and the empty-database run below was attempted first; Docker then became unstable and could not be trusted for another browser run |
| From-scratch path on an **empty** database (fresh `valora_onb_fresh_demo_test_20261012`, migrated, 0 estates, 0 users; api recreated onto it with AI off) | **attempted, failed on infrastructure**: the first test died with `page.goto: net::ERR_EMPTY_RESPONSE at http://localhost:4173/register` (the frontend container stopped answering), and every retry after that hit a hung Docker host. Not a product failure, and not a pass |

Two things found by these runs and fixed:

- `helpers.openTriableComplaint` now **filters the register by status** ("Logged",
  then "Under review") instead of walking the newest rows: the API only suggests for
  a `submitted`/`reviewed` complaint, and a demonstration database drifts (every
  journey run ends `rated`). `ai-off.spec.ts` shares the helper now.
- **A real-provider attempt happened by accident and is on the record.** Before the
  provider was pinned, the api container inherited `AI_PROVIDER=gemini` and a real
  `GEMINI_API_KEY` from `backend/.env`; one Playwright click and one diagnostic curl
  reached out. The ledger shows exactly what happened:
  `provider=gemini model=gemini-3.8-flash status=provider_failed reason=provider_error`,
  `input_chars=3114`, latency 11.6 s and 5.4 s — aggregate brief facts only
  (`data_class=aggregate`, `AI_PERSONAL_DATA_ALLOWED=false`), the brief fell back to
  the deterministic template, nothing was stored. **No real-provider run is claimed**;
  the acceptance above was re-run with `AI_PROVIDER=fake` and
  `AI_ENABLED/AI_INSIGHTS_ENABLED/AI_TRIAGE_ENABLED/AI_PERSONAL_DATA_ALLOWED`
  passed explicitly, so it can never silently mean a real provider again.

## P5.3 DOCS — PASS (except the tick list)

`README.md` rewritten (what VALORA is, the three-command demo, the sign-in table,
status honesty); `docs/GETTING_STARTED.md` written (exact Windows `cmd` commands:
start Docker, the compose stack, seed the demo, migrations, run the app, the tests,
the real-Gemini switch including `AI_TRIAGE_ENABLED` ⇒ `AI_PERSONAL_DATA_ALLOWED`
and "keep triage off for real residents", and the operator password reset);
`docs/KNOWN_LIMITATIONS.md` written (18 honest entries: no email of any kind and the
operator CLI as the interim, no HTTPS/hosting, no backups/monitoring, single-process
rate limiters, local-disk uploads, no malware scan, unlisted-but-cacheable public
photo links, AI never run on real data, POPIA review pending, no linter or a11y
tooling, and the product edges); `docs/PILOT_RUNBOOK.md` updated (the seeder's
`--expect-database` + `demo` guards, operator-only password reset, join codes as the
proof of the right to join, the compose stack's hosting reality).
`docs/openapi.json` regenerated (`python -m app.cli export-openapi`) and
`npm run check:api` reports the generated files match.

**`tasks/todo.md` was NOT ticked** — out of time. The criteria that do have evidence
for this sitting are listed in the section below so the next session can tick them
without guessing.

## P5.4 FINAL RUNS — PARTIAL

| Check | Result |
| --- | --- |
| `python -m compileall -q app scripts tests` | OK |
| `flake8 app tests scripts --count --select=E9,F63,F7,F82` | **0** |
| `alembic -c alembic.ini heads` | single head `c3f7a1b9d4e2 (head)` |
| `git diff --check` | clean |
| `npm run check:api` | "the generated API files match docs/openapi.json" |
| `npm run typecheck` | clean |
| `npx vitest run` | **20 files / 142 tests passed** (run before the spec-only edits in `e2e-live/`; vitest does not collect those) |
| Frontend production build | passes twice: inside the Docker frontend image, and directly on the host on the **final source** after every edit — `npm run build` → `✓ 82 modules transformed`, `dist/assets/index-BQbXre_Q.js 452.11 kB (gzip 129.37 kB)`, `✓ built in 1m 13s`, `BUILD_EXIT=0` |
| Backend suite **with** `TEST_DATABASE_URL` | **not passed in this sitting.** Started; it reached ~26 % with 11 **errors**, and was killed at the owner's instruction when the session ran out. The earlier sitting's "814 passed" result does not cover today's changes — this is the one gate that must be re-run |
| Backend suite **without** `TEST_DATABASE_URL` | not re-run in this sitting |
| Migrations up → down one step → up on the throwaway database | run in the earlier sitting, not re-run here |
| Throwaway databases dropped | **no** — `valora_demo_test_20261012` and `valora_onb_fresh_demo_test_20261012` are still on the local Postgres and should be dropped with `DROP DATABASE` once the re-run is done |

**Environment note (important for whoever resumes):** Docker Desktop became
unhealthy twice during this sitting (a `docker ps` that hangs, then
`Docker Desktop is unable to start`). The last state of the machine is: Docker
Desktop **down**, so the compose stack is **not running** and the api container is
not answering. Start Docker Desktop, then `cd backend` and
`DB_NAME=valora_demo docker compose up -d` (it reuses the built images; the api needs
~90 s to report healthy). The container environment that was last requested is
`AI_ENABLED=false` with `AI_PROVIDER=fake` — safe, no key, no provider call.

## Still outstanding (the honest to-do list)

1. Re-run the backend full suite on a throwaway database
   (`TEST_DATABASE_URL=…valora_demo_test_20261012 pytest tests -q`) and fix the 11
   errors it reported before the run was killed. Everything else in this sitting is
   green, and the same files passed earlier in the day, so the failure is most likely
   environmental (Docker was already unwell) — but that is a hypothesis, not a result.
2. Re-run the two acceptance pieces that did not complete: the **AI-off** spec
   (`ai-off.spec.ts` against the container stack with `AI_ENABLED=false`) and the
   **from-scratch path on an empty database** (`onboarding-journey.spec.ts` against a
   freshly migrated, empty database, api recreated onto it).
3. Tick `tasks/todo.md` for the criteria this sitting verified: Task 8 (client
   builds; typed boundary; landing/login/register responsive), Task 9 (resident
   complaint, events, rating), Task 10 (HOA review/assign, provider transitions),
   Task 11 (coherent demo seed + current docs), Task 12 items 1 and 3 (evidence
   recorded; limitations explicit), the backend-core checkpoint (auth/lifecycle/score/
   authorization tests plus the seeded vertical slice), and the last Hardening-pass-H
   item (integration tests on a disposable PostgreSQL and a live migration apply).
4. Drop `valora_demo_test_20261012` and `valora_onb_fresh_demo_test_20261012`.

## What the owner can now do

- **See the whole system working in one command**: `cd backend`,
  `set DB_NAME=valora_demo`, `docker compose up -d --build`, then open
  **http://localhost:4173** and sign in as `admin@example.com` / `ValoraDemo123!`.
  The estate is seeded (24 units, 20 residents, 2 providers, three months of
  complaints, work orders, incidents, notices, photographs) and the dashboard shows a
  **real** Living Score with `Demo data` beside it.
- **Walk an issue from complaint to score in the UI**, on a phone or a desktop:
  a resident logs it, the HOA marks it under review and assigns a member provider
  (which creates the work order), the provider starts and completes it with a note,
  the resident rates the repair, the HOA recalculates, and the dashboard shows the
  stored number — this is the journey that passed twice in this sitting.
- **Onboard a brand-new estate from nothing**: register as an estate administrator,
  write the description, paste units, issue a join code, upload photographs, publish,
  and a resident joins with the code.

## What is NOT ready

- The backend suite has not been re-run green today, and the two acceptance runs
  named above are unrun/failed-on-infrastructure. Nothing has been faked to hide
  that.
- No hosted deployment of any kind (see `docs/KNOWN_LIMITATIONS.md`): the compose
  stack is a local development/demonstration stack — plain HTTP, one api process,
  uploads on local disk, no backups, no monitoring.
- No email (verification, invitations, password reset): the operator CLI is the
  interim.
- The AI layer has never been run against a real provider successfully here (the two
  accidental attempts failed and fell back), and triage must stay off for real
  residents until the pilot runbook's checklist is done.
