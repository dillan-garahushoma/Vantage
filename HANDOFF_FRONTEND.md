# Frontend handoff — remaining work

VALORA manages residents, maintenance and building health for an apartment complex. Keep the Vantage layout and JavaScript/JSX. Living Score and maintenance Intelligence stay. The backend scope change is implemented; the UI work below remains.

## 1. Remove retired features

- Remove investor/estate-agent menus, onboarding choices, dashboard cards and landing-page promises.
- Remove the Property & investment workspace and ROI/yield, valuation, pricing, sale/rental marketing requests, listings, sales and buyer/agent enquiry entry points. Their backend endpoints now return 404.
- Update `App.jsx`, `lib/nav.js`, `lib/roleRouting.js`, `PropertyWorkflows.jsx` and `lib/propertyWorkflows.js`, including old redirects and related tests. Keep residential units (`Properties.jsx`) and resident registration approvals.
- Hide unfinished finance, telemetry/maps, survey/sentiment and provider-attendance previews from the first release. Keep notices, incident reporting, resident feedback and normal provider job completion.

## 2. Connect management workflows

| UI work | Existing backend endpoint (prefix `/api/v1`) |
|---|---|
| Resident-only public signup | POST `/auth/register`; remove manager/provider choices. Trusted accounts are operator-provisioned through POST `/auth/provision`. |
| Edit a unit | PATCH `/properties/{unit_id}` with address/size/bedrooms/bathrooms |
| Move a resident to another unit | PATCH `/memberships/{membership_id}/unit` with `{property_id}` |
| Move-out / revoke resident or provider access | DELETE `/memberships/{membership_id}`; keep historical records |
| Reopen a resolved repair | POST `/complaints/{complaint_id}/reopen` with `{note}` |
| Complete repair and collect feedback | Existing complaint/work-order/provider flows; POST `/work-orders/{id}/rating` with `{rating}` |
| Notification inbox and read state | GET `/notifications`; POST `/notifications/{id}/read` |
| Notification preference | GET/PATCH `/auth/preferences` with `{maintenance_notifications}` |
| Forgot/reset password | POST `/auth/recovery/request` with `{email}`; POST `/auth/recovery/confirm` with `{token,password}` |

Estate-scoped requests require the selected `estate_id`. Collection pagination uses `page` and `size`, except existing member-list/score-history endpoints that publish `page_size`; follow the OpenAPI contract. Recovery mail needs SMTP configuration. Never display or log recovery codes/passwords in diagnostics.

## 3. Finish building health and Intelligence

- Dashboard: show real authorized counts, overdue work and the dated stored Living Score; remove sample operational totals.
- Keep the score's five pillars, explanation, history and insufficient-data state. Backend owns all calculations; recalculation is an explicit manager action.
- Connect Intelligence history list/detail to GET `/analytics/intelligence/history` and `/history/{briefing_id}`. Existing summary, Ask and saving a briefing already work.
- Render maintenance priorities with their source records and measurement dates. Record-level recommendations are manager-only; residents/providers receive safe aggregate summaries.
- Preserve null `savingsZar`, `confidenceValue` and `avoidableZar` as unavailable. Current frontend parsing converts null to zero and must change; do not show invented R0 savings or 0% confidence.
- An overdue recommendation points to an existing job: offer review/open-job, not duplicate job creation. An unassigned complaint must be reviewed and assigned to an authorized provider by the manager.

## 4. Acceptance

Verify manager, resident and provider journeys against the real API: resident reports a leak → manager reviews/assigns → provider starts/completes → resident rates → manager views health evidence and a saved briefing. Also test reopening, moving out, notifications, error states, estate switching, mobile layout and accessibility. Check totals beyond the first results page.

Current browser verification covers real sign-in and complaint viewing; it does not prove the new forms above exist. Backend verification: 908 full-suite tests passed; 41 final focused tests passed (overlapping runs).

See [backend handoff](HANDOFF_BACKEND.md) and `docs/openapi.json` or running `/docs` for contracts. Run locally without Docker. Frontend checks: `npm test`, `npm run check:api`, `npm run build`, then `npm run test:e2e`.
