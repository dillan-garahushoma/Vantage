# ui-showcase-redesign — the public property showcase

**Session:** 13 October 2026. **Branch:** `valora-work`.
**Request:** the property-showcase UI needs work; research comparable products
(Airbnb and the property portals), write a redesign plan, then implement it.
**Scope:** the two screens that show an estate to someone without an account —
the public directory `/estates` and the published estate page `/estates/:id`.
Nothing behind the sign-in wall, and not the marketing landing page.

Design plan: [`docs/design/VALORA-PROPERTY-SHOWCASE-REDESIGN.md`](../design/VALORA-PROPERTY-SHOWCASE-REDESIGN.md)
(with the research links and the measured before/after table).

---

## 1. Done

**Research first, then the plan.** Three parallel passes — Airbnb's own pages and
usability writing on it; the property portals (Property24, Private Property, Pam
Golding, Zillow, Rightmove, Redfin, Booking.com, Trulia); and WCAG / MDN / web.dev
on image-led grids, galleries and sticky panels. The design doc records what is
*verifiable* and worth copying, and explicitly what is our own decision rather than
a number read off Airbnb. No new dependency was added: the project's Tailwind 4 and
hand-rolled primitives cover every decision.

**The directory card is now photograph-first** (`frontend/src/routes/PublicEstates.tsx`)

- A reserved `aspect-[3/2]` media box with `object-cover`, growing the cover
  photograph from 42% to 56% of the card.
- The estate name is the card's only link, stretched over the card with
  `after:absolute after:inset-0`: one link with a real accessible name, whole card
  clickable.
- Reading order is name → location → description (3 lines, clamped) → `View this
  complex →` + unit count, so every card is the same height and the facts are
  comparable down a column.
- No price, no rating, no badge: the API publishes none of them, so the UI invents
  none of them.

**The directory page**

- Search field and action read as one capsule; label text unchanged.
- A results range ("showing 1–6 of 6 published complexes") and a Clear control
  whenever a query is active.
- A skeleton grid in the *final* geometry behind `aria-busy`, with a visually hidden
  polite `role="status"`; the shapes are `aria-hidden`, so a screen reader hears one
  "loading" instead of six decorative boxes.
- Previous/Next pagination kept (not infinite scroll), restyled onto the hairline.

**The estate page** (`frontend/src/routes/PublicEstateDetail.tsx`)

- Order: breadcrumb → title + location + **facts strip** → **hero gallery** →
  **sticky section nav** → two columns.
- Facts strip: `24 units · 5 photographs · Gauteng`, plus a Living Score chip that
  anchors to the score card — the Airbnb "rating beside the title" move, using the
  only trust figure this product actually has. The chip is absent when the estate
  did not publish a score.
- Gallery gets the full content width, not a column of it: inside two columns a
  1 + 4 mosaic is four thumbnails smaller than one photograph.
- Location is a card, not a map: the published suburb, city and province on the
  survey-grid motif, plus the explicit statement that VALORA publishes no street
  address, unit number or pin. There is no coordinates field in the contract, so
  anything map-shaped would be fabrication.
- Living Score card led by a 44px mono numeral with its band label from the shared
  `display.ts` bands; the published status, as-of date, engine version and demo badge
  all retained; no maths in React, no component breakdown.
- Publication panel: what this page publishes, next to what it never will.
- Sticky right rail on `lg` up, with `scroll-mt` on every anchored section so a jump
  does not land underneath the two pinned bars.

**A real photo gallery** (`frontend/src/components/PhotoGallery.tsx`)

- Mosaic arrangements for 1, 2, 3, 4, and 5+ photographs — because a gallery that
  only looks right at five looks broken at one, and one is the common case.
- Below `lg` the mosaic is the single lead photograph plus the same "Show all N
  photos" button: five stacked photographs on a phone would push the description,
  the location and the join steps a long way down.
- The viewer is a modal dialog: `role="dialog"`, `aria-modal`, focus moves in, `Tab`
  is trapped, `Escape` closes, ← / → step, body scroll locked, focus returned to the
  tile that opened it, a polite `1 of 5` counter, captions as alt text.

**Shared primitives**

- `frontend/src/components/Photo.tsx` — one image in a caller-reserved box, with a
  shaped `PhotoFallback` so a 404 keeps the box instead of painting a broken-image
  glyph. Used by the card, the mosaic and the viewer.
- `frontend/src/components/ui.tsx` — `Skeleton`, `SkeletonText` (motion-safe,
  `aria-hidden`).
- `frontend/src/components/Icons.tsx` — photo-stack, chevron pair, expand, search.

## 2. Tests added and passing

| Test file | What it pins |
|---|---|
| `frontend/src/routes/PublicEstates.test.tsx` (8) | the card shows only what was published; the name is the only link and its overlay is inside a `relative`/`overflow-hidden` card; a photograph-less estate still gets a card; the skeleton holds the grid's geometry and announces itself once; "no match" is told apart from "nothing published"; the range and Clear. |
| `frontend/src/routes/PublicEstateDetail.test.tsx` (7, new) | the facts strip and the score chip's anchor; no price/rating/star is invented anywhere; the score card's own provenance and its demo disclaimer, and the *absence* of the whole card when no score was published; the section nav's five entries and `scroll-mt` on anchored sections; the viewer's keyboard contract (open, `1 of 5`, full-size URL, →, wrap-around ←, `Escape`, focus returned); the loading skeleton; 404 read as "not published". |
| `frontend/e2e/mobile.spec.ts` (extended) | a second directory entry, `/estates/2`, which publishes five photographs, so the multi-photo arrangement is measured at 390px as well as the single-photo case. Every photograph is mocked as a 404 in this spec. |

## 3. Commands run, with results

All from the repository root unless noted.

| Command | Result |
|---|---|
| `cd frontend && npm run typecheck` | **exit 0**, no output |
| `cd frontend && npx vitest run` | **21 files, 151 tests, all passed** (170s) |
| `cd frontend && npm run build` | **exit 0**; 84 modules; `index.html` 0.99 kB, CSS 39.44 kB (gzip 7.75), JS 463.94 kB (gzip 132.68); built in 34.14s |
| `cd frontend && npx playwright test e2e/mobile.spec.ts -g "estates"` | **3 passed** — `/estates`, `/estates/1`, `/estates/2` |
| `cd frontend && npm run test:e2e` | **19 passed** (1.4m) — the full 390px sweep (16 routes) plus the two smoke tests |
| `git diff --check` | **exit 0** — no whitespace errors in the changes |

**Live render.** The app was served at `http://127.0.0.1:4173` and measured in the
browser pane. Recorded in the design doc's after-table: the grid is unchanged at
3 × 373px with a 20px gap; the cover photograph is 371 × 247 (was 371 × 160); the
detail lead is 574 × 432 with four 282 × 211 tiles (was one 699 × 320 hero and four
80 × 56 thumbnails); the section nav and the join rail both compute to
`position: sticky`; at 390px the gallery shows exactly one tile plus "Show all 5
photos"; and `scrollWidth === clientWidth` on all three public routes — no sideways
scroll. The viewer was opened for real and rendered as a full-screen modal with the
caption and the prev/next controls.

## 4. Written, not run

- `frontend/.vite-preview.config.mts` — a session-only, untracked Vite config (dev
  server on 4173 with a same-origin `/api` proxy) that exists only because the
  preview browser blocks cross-origin requests. It is **not** part of the project and
  should not be committed.
- `frontend/e2e-live/**` was not run: it needs a reachable backend.

## 5. Deviations from the plan

1. **The plan's "2.25× the image height" was wrong.** Measured, the cover photograph
   grew **1.55×** (371 × 160 → 371 × 247; 42% → 56% of the card). The design doc has
   been corrected to the measured figure, with the arithmetic shown.
2. **The live render used a fixture, not the demo database.** When this was verified
   the demo database was unreachable — its managed Postgres refused the connection
   (`WinError 1225`) and Docker was not running, so the API returned 500. A
   session-only Python fixture (written outside the repository, not part of the
   project) served the same three unauthenticated endpoints with their exact DTOs and
   generated SVG images. Everything else on screen was the real app. This is why the
   rendered photographs are flat gradients rather than real uploads.
3. **`/estates/2` was added to the e2e sweep**, beyond the plan, so the multi-photo
   mosaic is measured at phone width rather than only the single-photo case.

## 6. Not verified

- **Real uploaded images.** The fixture served generated SVGs, so real JPEG/PNG
  decoding, EXIF orientation, actual file weight, and the thumbnail-versus-full size
  difference were not exercised in a browser. The unit tests do pin which URL each
  tile requests (`size=thumb` for small tiles, `size=full` for the lead and the
  viewer).
- **The database-backed API.** No authenticated screen and no real public-directory
  response was read from the live API in this session.
- **The chained selection behaviour** of the existing directory tests when a real
  paginated response arrives from a database rather than a fixture.

## 7. Open questions

1. **Should the directory card carry the Living Score?** It cannot today: the list
   DTO (`backend/app/property/schemas/public_directory.py`,
   `PublicEstateListItem`) publishes no score field — only the detail response does.
   Showing one on a card would need an additive API change, and the allow-list test
   would have to be updated deliberately. Worth deciding on purpose rather than
   drifting into it.
2. **The mobile section nav shows a horizontal scrollbar at 390px** under a desktop
   pointer device. Touch browsers use overlay scrollbars and it is invisible there.
   Hiding it would remove the only signal that more sections exist, so it has been
   left alone — but it is a deliberate choice, not an oversight.
3. **Photograph ordering** is whatever the API returns. Nothing in the contract marks
   a cover, so the lead photograph of the detail gallery is simply the first row.

## 8. Working-tree note

`backend/app/analytics/ai/__init__.py` was already modified in the working tree
before this session. It is not part of this work and was not touched.
