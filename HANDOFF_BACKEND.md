# Backend — remaining work

FastAPI, async SQLAlchemy, PostgreSQL and Alembic. Tenant boundary: **estate**. Current migration head: `c03f4a8d6e12`.

## Already implemented

- Estate membership/authorization, complaints, work orders, incidents, photos, announcements and stored Living Scores.
- Deterministic ROI/yield calculations and private immutable investment scenarios: `/api/v1/investment-scenarios`.
- Grounded Intelligence summaries/Ask and durable briefing history: `/api/v1/analytics/intelligence`.
- Verified marketing authority, sale/rental requests, HOA decisions/agent assignment, listings, asking-price history and confirmed sale/rental outcomes: `/api/v1/property-market`.

Legacy `/listings` and `/sales` remain disabled. Use the current namespace. API schemas are in `docs/openapi.json` and running `/docs`.

## Build next

1. **Agent administration:** trusted account/estate-role provisioning, eligible-agent discovery and reassignment. Public registration must continue creating residents only.
2. **Calculated valuation:** agree a transparent method, appropriate comparable/property evidence, calculation date/version, limitations and immutable history. An asking price or Living Score alone is not a valuation. No valuation model has been trained.
3. **Enquiries:** persistent conversations/replies with participant and estate authorization.
4. **Remaining operations:** actual budgets/levies/arrears, equipment/service history, surveys, provider attendance/proof uploads and supported settings/notifications. Current previews are not operational data.
5. **Acceptance:** broader privacy/security review, reliable email/recovery, production backup/restore and real-backend browser journeys. Review aggregate counts outside Intelligence. CI needs a disposable PostgreSQL service so integration tests do not skip.

Keep prices, valuations and saved ROI assumptions separate. Recorded sale/rental outcomes do not process payments, transfer title or administer leases. External AI/workflow integrations need proper estate principals and validated evidence.

## Local setup — Windows, no Docker

Install Python, Node.js and npm, then run from the repo root:

```powershell
py -m venv backend/venv
backend/venv/Scripts/python.exe -m pip install -r backend/requirements.txt -c backend/constraints.txt
npm --prefix frontend ci
./Install-LocalPostgres.ps1
. ./Local-Database.ps1 -Action Initialize
. ./Local-Database.ps1 -Action Use -Database Development
./Start-Local.ps1 -Migrate
```

This creates fresh local databases/credentials; no account data or existing estate is included. Provision the estate, units and authorized users before using workflows. The development database starts empty. API: port 8000; UI: 5173.

Run all backend tests against the separate disposable test database: `./Local-Database.ps1 -Action Test`. The latest local run passed **982 tests with no skips**. Real authenticated HTTP and migration checks also passed; rerun on your machine.

## Working rules

Router → service → estate-scoped repository. Resolve persisted estate access before queries; privileged actions need both global role and matching membership. Services commit once; repositories flush. Add migrations instead of editing applied ones. Do not add ML/LLM infrastructure without an agreed scope. Keep secrets and private resident data out of Git and responses.
