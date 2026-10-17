# residency-approvals — admin-approved resident registration + HOA email

**Session:** 13 October 2026. **Branch:** `valora-work`.
**Request:** a senior product/UX + full-stack brief covering three verticals (image
uploads & galleries, resident approvals replacing join codes, HOA email, dashboard /
Living Score). **Scope chosen with the user before implementation:** the
**resident-approval workflow with HOA email**, added **beside** the existing join-code
path (the user selected "coexist" — nothing that works today is removed). The image
uploader, public-gallery and dashboard/Living-Score work in the brief are **not** in
this session (see §5).

---

## 1. What changed and why

A resident could previously enter an estate only by redeeming a manual join code. That
is a code-sharing workflow with no per-person review. This session adds the
**approval-based path**: a resident asks to join a specific unit, an estate
administrator of that estate approves or rejects, and only an approval grants access.

**Join codes are untouched.** `app/identity/services/membership_service.py` and its
tests still pass unchanged; the code remains the estate office's instant tool. The new
path is a sibling: both produce the same `estate_memberships` row, so everything
downstream is unaffected.

**Backend (new capability, layered)**

- `EstateResidencyRequest` model + additive migration — one row per ask, carrying the
  applicant's contact snapshot, the decision, the deciding administrator and the
  decision time. Never deleted: it is the estate's record of who was admitted.
- `ResidencyRequestService` owns the rules: submitting grants nothing; approving is the
  only write that creates a membership; the request is read `FOR UPDATE` so two
  administrators cannot both decide it; one *pending* request per person per estate
  (partial unique index) while a rejected applicant may re-apply. Approval and its
  membership event commit **once**.
- Notifications (`app/notifications/`) — a transport-agnostic `EmailSender`, an
  `smtplib` implementation (no new dependency), and a safe default that sends nothing.
  The new-request email goes to the estate's **own HOA-admin members**, resolved from
  membership, never a configured address.

**Frontend**

- Resident: `/request-access` — find the complex in the published directory, name the
  unit, submit, and see your own requests with plain-language statuses. Residents with
  no estate now land here by default (`roleRouting`), with the code path still linked.
- Administrator: `/admin/residency` — a pending-count badge, a searchable/filterable
  queue, a detail drawer, and **node-to-node confirmation** before an approve or reject.
  A notification email's deep link (`?request=<id>`) opens that request.

**Security properties held:** a resident requests, an administrator decides; the two
roles cannot overlap, so self-approval is impossible. Every admin read/write goes through
`EstateAuthorizationService.require_role`; a foreign-estate request id is a 404. Submitting
is the one place a client `estate_id` is legitimate — it is a *target*, and the service
still verifies the estate and unit exist and rate-limits unknown-unit attempts. Rejection
never grants privileges.

---

## 2. Tests added and passing

| Suite | What it pins |
|---|---|
| `backend/tests/test_residency_requests.py` (37 + 3 integration) | DTO bounds and `extra="forbid"`; submit records pending and creates **no** membership; unknown estate/unit → 404 + limiter; already-member / duplicate-pending / concurrent-race → 409; a **failing email never fails the request**; approve creates membership + one `joined` event + stamps the decider, locks the row, and refuses a resident actor and an already-decided request; reject creates nothing; queue filters/pagination and admin-only; notifier recipients, content, header-injection refusal, and a dead relay reported not delivered; route guards (401/403/422, no estate in a path); migration SQL is additive and does not touch the join-code path. |
| `frontend/src/routes/RequestAccess.test.tsx` (5) | The approval promise; complex+unit required before spending a request; the exact POST body; a 409 shown as the server's message; the person's own statuses. |
| `frontend/src/routes/AdminResidency.test.tsx` (8) | Pending badge and queue contents; status filter goes through the API; "no requests yet" vs filtered-empty; admin-only; **confirmation before sending** then approve; reject with reason and never approve; a 409 decided elsewhere surfaces in the drawer; a deep link opens the right request. |
| `frontend/src/lib/roleRouting.test.ts` | A resident with no estate now goes to `/request-access`; a non-resident still goes to `/join`. |
| `frontend/src/routes/Members.test.tsx` | Updated copy: the register now names both approvals and join codes. |
| `frontend/e2e/residency.spec.ts` (new, 3) | **Real browser**: resident submits (asserted from the sent body); administrator confirms then approves (no decide request before confirmation); administrator rejects with a reason and never sends an approve. |
| `frontend/e2e/mobile.spec.ts` (+2 routes) | `/request-access` and `/admin/residency` do not scroll sideways at 390px. |

---

## 3. Commands actually run, with results

From the repository root unless noted. Interpreter `backend/venv/Scripts/python.exe`.

| Command | Result |
|---|---|
| `pytest tests/test_residency_requests.py -q` | **37 passed, 3 skipped** (integration; `TEST_DATABASE_URL` unset) |
| `pytest tests -q` (full) | **749 passed, 1 failed, 114 skipped**. The 1 failure is **pre-existing and unrelated** — see §4 |
| `python -m compileall -q app` | exit 0 |
| `flake8 app tests --count --select=E9,F63,F7,F82` | `0` |
| `alembic -c alembic.ini heads` | `e7a1b3c5d9f2 (head)` — single head |
| `alembic -c alembic.ini upgrade head --sql` | exit 0; the new `CREATE TABLE estate_residency_requests` and its two indexes are present |
| `python -m app.cli export-openapi` | rewrote `docs/openapi.json`; **+572 lines, 0 deletions** (purely additive) |
| `npm run gen:api` / `npm run check:api` | exit 0 / "the generated API files match docs/openapi.json" |
| `npm run typecheck` | exit 0 |
| `npx vitest run` (full) | **23 files, 165 tests, all passed** |
| `npm run build` | exit 0; `dist/assets/index-*.js` 482.56 kB (gzip 137.13) |
| `npx playwright test e2e/residency.spec.ts` | **3 passed** (real Chromium) |
| `npx playwright test e2e/mobile.spec.ts -g "request-access\|admin/residency"` | **2 passed** |
| `git diff --check` | clean |

---

## 4. The one failing test (pre-existing, not caused here)

`backend/tests/test_living_score_snapshots.py::test_no_api_module_reaches_the_calculation_service`
asserts that no module outside an allow-list names `LivingScoreService`. It fails
because `backend/app/seed_demo.py` contains that name. Verified as pre-existing:

```
git status --short app/seed_demo.py            # (empty — unmodified by me)
git show HEAD:backend/app/seed_demo.py | grep -c LivingScoreService   # 3
```

It is committed at HEAD and I did not touch that file or the demo seed. **Not fixed**,
because it is outside this session's scope and changing the seed could affect demo
behaviour. It should be triaged on purpose.

---

## 5. Not done this session (the brief's other verticals)

Explicitly **not** implemented, and not claimed:

- **Multi-select / drag-drop image upload, previews, cover selection, blurred `+N more`
  overflow tile.** The public gallery and card redesign were already done in the prior
  `ui-showcase-redesign` session; the admin uploader in `AdminSetup.tsx` still takes one
  file at a time with no previews. Untouched here.
- **Dashboard / Living Score elevation.** Untouched.
- **Replacing join codes.** Deliberately not done — the user chose coexistence.
- **A joined/decision email sent to a real relay.** `EMAIL_ENABLED` is false, so the
  default `NullEmailSender` was exercised; the SMTP path is unit-shaped but not run
  against a live server.

## 6. Written, not run

- The **PostgreSQL integration tests** for the new workflow (3, above) — skipped because
  `TEST_DATABASE_URL` is unset in this terminal. They are **not** counted as passing.
  The DB-backed authorization path therefore has not been exercised against a real
  database this session.
- **`SmtpEmailSender` against a live SMTP server** — the class and its wiring are unit
  tested only indirectly (constructor + `build_email_sender` selection). No relay was
  configured and no message was sent anywhere.
- **Visual inspection by eye.** Layout was verified automatically (the 390px sweep), and
  the flows were driven in a real browser, but I did not open the screens in a preview
  pane and inspect pixels.

## 7. Database / configuration required

- **Migration:** `backend/alembic/versions/e7a1b3c5d9f2_add_estate_residency_requests.py`
  (new table only; additive; downgrade drops it). Run `alembic upgrade head`.
- **Env vars** (documented in `backend/.env.example`): `EMAIL_ENABLED` (default false),
  `EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
  `SMTP_USE_STARTTLS`, `APP_BASE_URL`. The app **refuses to start** with
  `EMAIL_ENABLED=true` and no `SMTP_HOST` rather than silently dropping notifications.

## 8. Open questions / remaining limitations

1. **No automatic retry of a failed notification.** A send that fails is logged and the
   request stays in the queue (the durable record), but there is no queue/worker to
   retry it — consistent with the project's no-queue rule. Worth a deliberate decision.
2. **Estates with no HOA-admin email** cannot be notified; the send is skipped with a
   warning and the request still appears in the queue.
3. **Discovery is limited to published estates.** A resident of a private estate cannot
   find their complex on `/request-access`; they still need a join code from the estate
   office. Publishing the estate makes it findable.
4. **`APP_BASE_URL` must be set per environment** or notification links point at
   `localhost:5173`.
5. **Deep-link authorization** relies on the page's own `RequireEstate` + admin check;
   the `estate_id` in a linked URL is not trusted (the active estate comes from the
   session), so a link to another estate's request simply opens the queue for the
   caller's current estate.
