# Production deployment checks — VALORA frontend and API

The frontend is a static Vite build hosted by Cloudflare Pages. The API is a separate FastAPI service and connects to PostgreSQL/Neon. **The browser must never connect to Neon directly.**

## Cloudflare Pages

In the Pages project for `vantage-7k0.pages.dev`, open **Settings → Environment variables** and confirm the **Production** environment contains:

- `VITE_API_BASE_URL`: the absolute HTTPS origin of the deployed FastAPI service, such as the real Render service URL. Do not append `/api/v1` or a route, and do not enter a Neon connection string.
- Then trigger a new production deployment so Vite compiles that value into the static app.

Without this value, the production client now shows a clear configuration error rather than silently trying `http://localhost:8000` on the visitor's computer.

## FastAPI service

Confirm the service's `CORS_ORIGINS` includes the complete frontend origin, for example:

```json
["https://vantage-7k0.pages.dev"]
```

Keep any other legitimate origins that already exist. Do not replace the list blindly or add a trailing path to an origin. Confirm the backend's `DATABASE_URL` points to the intended Neon database and that migrations have been applied. Never expose that database URL in frontend settings.

## Verify the public estate API

Open the configured API host's endpoint directly:

```text
GET https://<actual-api-host>/api/v1/public/estates?page=1&page_size=6
```

A healthy response is JSON with `items`, `total`, `page`, and `size`. Check:

- A connection failure or CORS rejection: check `VITE_API_BASE_URL`, FastAPI availability, and `CORS_ORIGINS`.
- `items: []` and `total: 0`: the API is reachable, but no estates qualify for public listing in that database/environment. The public query intentionally returns only `is_public = true` and `is_demo = false` estates.
- A small nonzero `total`: the homepage shows the first few featured published estates; **Find a complex** opens the paginated directory for the full published set.
- Estates exist in Neon but are absent from the public endpoint: verify the target Render service is connected to the correct Neon database and have an authorised HOA admin publish each intended estate using the app's estate setup/publishing workflow. Do not remove the `is_demo` or `is_public` restrictions in client code and do not delete estate rows to resolve this.

The public list is not meant to expose every database row: unpublished private estates and demonstration data are deliberately excluded. A resident who chooses an estate in signup uses it as onboarding context only; the backend still validates the estate and unit and the HOA must approve the membership.

## Smoke-check after deployment

1. Load the homepage. The featured estate area should show a loading state, real API results, a helpful empty state, or a clear configuration/API error — never silent fake records.
2. Open **Find a complex**, search by estate name/suburb/city/province, page through results and open a profile.
3. Start resident signup. The complex selector should load from the same published API. Select an estate, enter the unit, create the resident account, then ensure the access-request form retains that estate and unit.
4. Confirm that an estate access request remains pending until an HOA administrator approves it.
