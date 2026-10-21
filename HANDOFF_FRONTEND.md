# Frontend — remaining work

React/Vite is now JavaScript/JSX. Keep the current Vantage layout. All calculations and permission decisions belong in the backend.

## Build next

1. **ROI and rental yield:** connect `/api/v1/investment-scenarios` to input forms, backend results, annual cash-flow charts, saved scenarios and revisions. Clearly label fictional assumptions.
2. **Sale/rental requests:** connect `/api/v1/property-market` to owner requests, HOA marketing-authority verification, approval/rejection, agent assignment and request history. Residency alone does not permit selling.
3. **Listings and prices:** add draft/publish/edit/withdraw screens, asking-price editor and price history. Send the current `expected_version`; reload after a 409 conflict.
4. **Sales/rentals register:** add the HOA completion form and authorized outcome history. Keep proposed price, asking price and actual sale amount/monthly rent separate.
5. **Intelligence history:** build a history/detail view using `/api/v1/analytics/intelligence/history`. Current summaries, Ask and saving a dated briefing already work.

## After that

- Connect calculated valuation once its backend exists.
- Add enquiry conversations once their backend exists.
- Replace labelled finance, equipment, community and provider-attendance previews with real APIs; keep unsupported actions disabled.
- Finish supported settings/notifications, agent onboarding, error/loading states, mobile/accessibility checks and signed-in tests against the real backend.
- Review counts on other screens for first-page-only aggregation; reduce the large main bundle.

## Rules

- Use the authenticated API and selected estate; respect returned estate capabilities.
- Clear previous estate data on switching. Never replace errors with made-up findings or direct webhook responses.
- Do not implement ROI, valuation or Living Score maths in React.

## Run

See [backend setup](HANDOFF_BACKEND.md). Frontend alone: `cd frontend`, `npm ci`, `npm run dev`. API defaults to `http://localhost:8000`; UI runs on port 5173.

Checks: `npm test`, `npm run check:api`, `npm run build`. Playwright checks are separate: `npm run test:e2e`.
