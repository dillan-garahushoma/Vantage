# Backend handoff — property management

VALORA manages residents, maintenance and building health for an apartment complex. The backend scope change is implemented locally; no commit or push was made. FastAPI, async SQLAlchemy, PostgreSQL and Alembic remain. Current migration head: `d14a5b9e7f23`.

## Implemented

- Retired investment/ROI/yield and property-market APIs. Enabling legacy routes cannot restore listings or sales. Historical data and applied migrations remain intact.
- Retired investor/estate-agent login and estate access. Existing accounts are preserved without automatic promotion or role conversion.
- Public registration creates residents only. `POST /api/v1/auth/provision` is operator-only and provisions managers/estates or providers. It returns the new user, not their login token.
- Manager unit editing and audited resident unit transfers; membership removal revokes access while preserving history.
- Complaint → review → provider assignment → progress → completion → resident rating, plus reopening and repeat repair orders. Completed/cancelled jobs cannot be edited; historical ratings cannot close a newer repair cycle.
- Living Score calculation, five pillars, snapshots and history retained. Recalculation remains an explicit manager operation; reads return stored dates/values.
- Grounded maintenance priorities from overdue jobs and urgent/high unassigned complaints. Manager-only record details; safe member summaries and immutable briefing history remain.
- Persistent, recipient-scoped in-app maintenance notifications, read acknowledgements and saved notification preferences.
- Expiring, single-use password recovery via configured SMTP; password changes revoke earlier sessions. Disabled/failed mail is not treated as delivery.
- Regenerated OpenAPI, real local HTTP/browser acceptance helper and native PostgreSQL integration setup in the existing CI workflow.

## Frontend work remains

Remove investor/agent and investment/marketplace UI. Public signup must offer resident accounts only; manager/provider accounts are provisioned by an operator. Connect unit transfer/editing, repair reopening, notification/preferences and recovery forms, and Intelligence history. Preserve `null` savings/confidence values as unavailable; do not convert them to R0 or 0%. Route overdue-job recommendations to the existing job, not a duplicate job creation form.

The Vantage JavaScript layout is retained. See [frontend plan](HANDOFF_FRONTEND.md) and the published `docs/openapi.json` contract.

## Verification and limits

Migration upgrade/downgrade/re-upgrade passed. A downgrade that conflicts with repeat repair history is safely refused. Real TCP HTTP checks passed for manager/resident/provider logins, retirement, repairs/rating/reopening, score calculation, Intelligence and notifications. Real browser sign-in and complaint viewing passed against the backend. Backup/restore into a separate test database matched the head and key row counts. Compile, fatal lint and API drift checks passed.

Full PostgreSQL suite: **908 passed, no skips**. Final focused checks after the repeat-repair rating corrections: **41 passed, no skips**, including real database journeys and the local SMTP transport test. These runs overlap; do not add their counts together. CI configuration is written, not run on GitHub. External inbox delivery requires relay configuration. No new frontend forms or complete browser journey for those forms is claimed.

## Local setup — Windows, no Docker

From the repository root:

```powershell
py -m venv backend/venv
backend/venv/Scripts/python.exe -m pip install -r backend/requirements.txt -c backend/constraints.txt
npm --prefix frontend ci
./Install-LocalPostgres.ps1
. ./Local-Database.ps1 -Action Initialize
. ./Local-Database.ps1 -Action Use -Database Development
./Start-Local.ps1 -Migrate
```

Fresh development databases contain no accounts/estate. An operator bootstraps trusted accounts; public signup cannot create managers/providers. API: port 8000; UI: 5173. Restart an already-running API to load changed routes.

Backend tests: `./Local-Database.ps1 -Action Test`, against its separate disposable test database. Never use the development database for tests. Role/archive inventory: after selecting Development, `Invoke-LocalPython -Arguments @('scripts/management_inventory.py')`; output contains counts only.

## Retained boundaries

Every estate-scoped use case resolves persisted estate access; manager/provider privilege needs matching global role and membership. Nonmembers receive 403; foreign-estate objects receive 404. Services own transactions; repositories used in multi-step operations flush. No Docker, ML training, queues or additional cloud infrastructure was added.

Full accounting/levies, rent collection, leases, surveys, telemetry, GPS attendance, asset inventory and scheduled preventive maintenance remain outside the agreed initial backend scope. Historical investment/market records are retained pending an explicit archive/retention decision.
