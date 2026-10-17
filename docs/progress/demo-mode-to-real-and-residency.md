# demo-mode-to-real-and-residency — verifying Codex's work and resolving the resident-acceptance report

**Session:** 14–15 October 2026. **Branch:** `valora-work`.
**Trigger:** the user asked whether the earlier "demo mode → real mode" work was actually
done, and reported a second issue: *"I couldn't accept a resident into the complex."*
The user then answered that the acceptance attempt failed with **"it couldn't reach the
backend api"**, and asked for the local stack to be started **without Docker**.

No AI provider was called at any point in this session. No application code was changed.

---

## 1. Answer to "was the issue fixed?"

**Yes in code — and one database action was still outstanding, which is now done.**

| Claim | Evidence |
|---|---|
| The "DEMO DATA" chip is gone from the UI | [LivingScore.tsx](../../frontend/src/components/LivingScore.tsx) no longer renders a demo badge; no runtime frontend file reads `is_demo` or `data_origin` (only tests and the generated schema mention them). |
| It cannot come back through a test | `LivingScore.test.tsx`, `HealthBrief.test.tsx`, `Dashboard.livingScore.test.tsx` and `PublicEstateDetail.test.tsx` all assert `queryByText('Demo data')` is null, with `is_demo` both true and false. |
| The estates are no longer classified as demo | Migration `f1a2b3c4d5e6` applied to `valora_db`: all five estates now read `is_demo = false`. |
| Legacy AI triage cannot masquerade as live output | Same migration marks the 11 pre-existing `complaint_ai_suggestions` rows `is_seeded = true`; `ComplaintTriageService.get`/`decide` return 404 for them and `generate` replaces one in place. |
| The brief is user-triggered only | `HealthBrief.tsx` shows "No AI summary has been generated yet." until Generate is clicked. |

**The gap:** `valora_db` was at revision `e7a1b3c5d9f2` — the residency revision — so the
reclassification revision `f1a2b3c4d5e6` had never been applied. That is exactly why the
screenshot still showed `DEMO DATA` next to `HEALTHY`: the frontend had been fixed, the
database had not. It is applied now.

## 2. The resident that could not be accepted

Not a code defect. The `valora_db` state, read before any write:

```
alembic version: e7a1b3c5d9f2
estates: 4 Silverleaf Reserve is_demo=True, 5 is_demo=True, 6 is_demo=True, 7 is_demo=True, 8 is_demo=True
estate_residency_requests:
  request_id=1 estate_id=4 user_id=166 unit_no='SR-01' status='pending'
  applicant='Gugu' decided_by=NULL decided_at=NULL created_at=2026-10-14 20:45:05 UTC
```

There **was** a request waiting to be accepted — Gugu, unit SR-01 of Silverleaf Reserve
(estate 4). The approval could not happen because the API was not running.

**A second, independent cause of "cannot reach the VALORA API" was found and fixed:**
[frontend/.env](../../frontend/.env) sets `VITE_API_BASE_URL=http://127.0.0.1:8010`, but the
API was started on 8000. The frontend therefore pointed at a port nothing was listening on.
The API now runs on **8010**, the port the frontend expects.

## 3. Commands actually run, with results

| Command | Result |
|---|---|
| `pg_ctl -D C:\Users\garah\pgsql\data -l server.log start` | Server started; **`pg_ctl` itself does not return** in this shell (its output pipe stays open), so the server is now launched as a detached `postgres.exe` process instead. |
| `postgres.exe -D C:\Users\garah\pgsql\data` (background) | `database system is ready to accept connections` |
| `python ../tmp/inspect_residency.py` | Read-only state above; no writes. |
| `python -m alembic -c alembic.ini heads` | `f1a2b3c4d5e6 (head)` |
| `python -m alembic -c alembic.ini upgrade head` | `Running upgrade e7a1b3c5d9f2 -> f1a2b3c4d5e6` — exit 0. Verified after: five estates `is_demo=False`, 11 AI rows `is_seeded=True`. |
| `python ../tmp/run_integration.py tests/test_residency_requests.py -q` | **40 passed** against a real PostgreSQL `valora_test` (these were the 3+37 that skip without `TEST_DATABASE_URL`), including `test_full_residency_request_journey_is_approved_into_a_membership`. |
| `uvicorn app.main:app --host 127.0.0.1 --port 8010` | `/health` → 200 `{"status":"ok","environment":"development"}`; `/docs` → 200 |
| `GET /api/v1/residency-requests?estate_id=4` | 401 `UNAUTHENTICATED` (route live, auth enforced, no 500) |
| `GET /api/v1/residency-requests/pending-count?estate_id=4` | 401 `UNAUTHENTICATED` |
| `GET .../1/approve` | 405 Method Not Allowed (the POST decision route exists) |
| `npm run dev` (frontend) | Vite ready on `http://localhost:5173/` (bound to `::1`; `127.0.0.1` is not reachable, `localhost` is) |
| `curl /api/v1/public/estates?page=1&page_size=12` from the browser | 200 — the running frontend reaches the API on 8010 |
| `npx vitest run` (twice) | Run 1: 1 failed / 187 passed; run 2: **188 passed**. The failure was a `ComplaintDrawer` timing assertion under parallel workers — flaky, not a regression. |
| `pytest tests -q` (no `TEST_DATABASE_URL`) | **753 passed, 114 skipped in 91.9s** |
| `python ../tmp/run_integration.py tests -m integration -q` | **Not completed — timed out at 600s.** Not claimed as passing. |

## 4. What is running now

| Service | Where | Note |
|---|---|---|
| PostgreSQL 16.6 | `C:\Users\garah\pgsql\data`, port 5432 | PID logged at start; `valora_db` at head `f1a2b3c4d5e6` |
| VALORA API | `http://127.0.0.1:8010` | background PID 7300 |
| Frontend | `http://localhost:5173` | background PID 21372, registered as the thread preview |

`valora_test` (a separate database) was created for the integration run and is owned by the
application role. Nothing in `valora_db` was modified except the migration.

## 5. Written, not run / remaining

- The **full DB-backed sweep** (`-m integration`): time-boxed out at 10 minutes and not
  re-run. The residency subset did complete and pass.
- **Accepting Gugu's request** was *not* done here on purpose — it is the user's decision on
  their own data. The screen, the route and the service are verified.
- **No live AI call** was made: `.env` has `AI_ENABLED=true` with a Gemini key, and the
  seeded triage rows are now visibly non-live, but no provider request was issued.
- The frontend failure in run 1 (`ComplaintDrawer.test.tsx`) is flaky under load; nobody has
  yet made it deterministic. Worth a deliberate fix (fake timers or a longer `findBy` bound).

## 6. Open questions

1. Why does the frontend expect port **8010**? `.env.example` documents 8000. If 8010 was a
   local workaround, the two should be reconciled so the next person starts the API on the
   right port.
2. `pg_ctl start` never returns in an automated shell. Launching `postgres.exe` directly (as
   done here) is a workable pattern; the project's docs only describe Docker.
3. Gugu's pending request from 20:45 on 14 Oct is still undecided — decide it on the
   Approvals screen to confirm end to end in the browser.
