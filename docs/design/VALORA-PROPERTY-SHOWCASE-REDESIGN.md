# VALORA — property showcase redesign

> **Status:** implemented (see `docs/progress/ui-showcase-redesign.md`).
> **Scope:** the two screens that showcase an estate to someone without an account —
> the public directory (`/estates`) and the published estate page (`/estates/:id`).
> **Not in scope:** the marketing landing page, and every screen behind the sign-in wall.
> **Date:** 12 October 2026.

---

## 1. What we measured before changing anything

Baseline, taken in the running app against the seeded demo estate
(`http://127.0.0.1:4173`, Chromium at 1440 × 900 and 380 × 619):

| Screen | Measurement | Value |
|---|---|---|
| `/estates` | grid at 1200px content width | 3 columns, 20px gap, 373px cards |
| `/estates` | cover photograph | 371 × 160 — **42% of a 384px card**; a 2.3:1 letterbox |
| `/estates` | primary action | a 289 × 36 text link at the bottom of the card |
| `/estates` | key facts on the card | one uppercase chip: `◫ 24 UNITS` |
| `/estates/:id` | hero | one image, 699 × 320, out of a 1200px content column |
| `/estates/:id` | the other four photos | 80 × 56 thumbnails in a strip below |
| `/estates/:id` | photo count / all-photos entry | **absent** |
| `/estates/:id` | right column | not sticky; the score and the join steps scroll away |
| both | loading | a 12px pulsing square plus "Loading…"; the grid's geometry is unknown, so the page reflows when data lands |
| both | a photo that fails to load | the browser's broken-image icon inside a reserved box |

The diagnosis: **the photographs are decoration and the text is the product.** On a
property directory that is the wrong way round — a visitor scanning a grid of estates
is comparing photographs first, and location and scale second. The page also has no
answer to "how many photographs are there and can I see them all", and no way to
reach the score or the joining steps once you have scrolled past them.

## 2. What the reference products do (research)

Three parallel research passes: Airbnb's own pages plus usability research on
accommodation search; the property portals (South African and international); and
WCAG/MDN/web.dev guidance for image-led card grids and galleries.

**Airbnb — what is verifiable and worth copying**
- Photographs are cropped to a **square** in search results, so the image is the card.
  ([Airbnb photo guidance](https://www.airbnb.com/resources/hosting-homes/a/how-to-add-the-best-photos-of-your-space-367))
- The **stay total including fees** is the search price, switched on globally in 2025 —
  the price is content, not decoration. ([Airbnb, Apr 2025](https://news.airbnb.com/total-price-display-is-now-standard-globally))
- A rating appears **next to the listing title** once there are ≥3 reviews; the detail
  page opens with **title → type/location → capacity summary**, then a gallery.
  ([Ratings](https://www.airbnb.com/help/article/1257), [reviews](https://www.airbnb.com/help/article/13))
- The desktop gallery is **one large image plus smaller tiles**, with the first five
  photos given prominence and a "show all photos" affordance.
  ([GoodUI teardown](https://goodui.org/leaks/airbnb-made-3-changes-to-their-property-page/))
- Reviews carry a **rating breakdown and topic chips** — the pattern to copy for a
  published score: always show the number with what it is made of.
  ([Review tags](https://www.airbnb.com/help/article/2658))
- The booking panel **stays in view while the page scrolls**.
  ([GoodUX](https://goodux.appcues.com/blog/airbnbs-sticky-widget))
- **What Airbnb does not publish:** current column counts, gutters, card padding,
  type sizes, radius, or sticky offsets. The research says so explicitly, and those
  numbers below are our own decisions, not Airbnb's.

**Property portals** (Property24, Private Property, Pam Golding, Seeff, Zillow,
Rightmove, Redfin, Booking.com)
- A comparison card carries **price, property type and area, beds/baths, parking/size
  and a status badge**; Private Property shows Promoted/New/Under Offer/Sold/HD Media
  as *distinct* badges. ([Private Property Cape Town results](https://www.privateproperty.co.za/for-sale/western-cape/cape-town/55), [Rightmove](https://www.rightmove.co.uk/overseas-property-for-sale/New-York.html))
- Detail pages are **structured, not one paragraph**: Pam Golding lists room by room,
  then building features, exterior, garden, pool, security, power.
  ([Pam Golding listing](https://www.pamgolding.co.za/property-details/house-for-sale-eye-of-africa/1gv1730311))
- Property24 tells sellers to disclose **square metres, beds, baths, taxes and levies**.
  ([Property24 listing advice](https://www.property24.com/articles/top-tips-to-make-your-property-listing-stand-out/32500))
- "Quality" data is always **attributed and caveated**: Redfin names GreatSchools as
  its source and warns proximity is not enrolment; Trulia *removed* its crime tab in
  2022 for accuracy and bias reasons; Zillow removed listing climate scores in 2025.
  ([Redfin schools](https://support.redfin.com/hc/en-us/articles/360001432452-School-Data), [GeekWire on Trulia](https://www.geekwire.com/2021/trulia-to-drop-neighborhood-crime-data-from-home-listings-after-redfin-speaks-out-against-practice/), [Marketplace on Zillow](https://www.marketplace.org/story/2025/12/01/why-zillow-removed-climate-risk-information-from-listings))
- Usability research that transfers: keep **price/facts comparable across cards**
  (Baymard: 50% of benchmarked sites fail the listing-information balance), and prefer
  **"Load more"/pagination over unbounded infinite scroll**, which makes an item hard
  to re-find and breaks the footer (NN/g).
  ([Baymard listing information](https://baymard.com/research-articles/product-listing-information), [NN/g infinite scrolling](https://www.nngroup.com/articles/infinite-scrolling-tips/))

**Accessibility and layout** (W3C, MDN, web.dev)
- Reserve the image box with `aspect-ratio` so a slow photograph cannot shift the
  grid. ([MDN aspect-ratio](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Box_sizing/Aspect_ratios))
- A skeleton should mirror the final geometry, sit behind `aria-busy`, be
  `aria-hidden`, and be announced by a separate polite status; shimmer off under
  `prefers-reduced-motion`. ([MDN aria-busy](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-busy), [web.dev reduced motion](https://web.dev/articles/prefers-reduced-motion))
- A full-screen image viewer is a **modal dialog**: focus moves in, `Tab` stays in,
  `Escape` closes, focus returns to the trigger, labelled prev/next/close buttons,
  a counter announced politely. WCAG 2.2 AA also requires 24 × 24px minimum targets,
  visible focus, and reflow at a 320px-equivalent width.
  ([APG dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/), [Target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html))
- A sticky panel needs a real `top` offset, must be shorter than the viewport, and must
  not sit above content the user is focused on. ([MDN position](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/position))
- Grid: `repeat(auto-fit, minmax(min(100%, 17rem), 1fr))` with a clamped gap, and a
  fixed image-crop rule per row — a consistent grid scans better than masonry.
  ([web.dev one-line layouts](https://web.dev/articles/one-line-layouts))

## 3. The redesign

The visual language does **not** change. `docs/design/VALORA-DESIGN-DIRECTION.md`
already decided hard hairlines, near-zero radius, mono numerals for every figure, one
accent with meaning and no haze — and the research above supports that for a
trust product. What changes is **what the screens are made of, and in what order.**

### 3.1 The directory card — photograph first, facts comparable

| Element | Decision | Why |
|---|---|---|
| Media | `aspect-[3/2]` reserved box, `object-cover`, hairline rule under it | 3:2 is the safe photographic default and shows **1.55×** the image height of the old 2.3:1 strip (measured: 371 × 160 → 371 × 247, i.e. 42% → 56% of the card's height) |
| Image failure | keep the box, show a hatched "No photograph yet" panel | the mocked browser tests and a real 404 must not collapse the card |
| Title | the estate name, as the card's **only link**, stretched over the card (`after:absolute after:inset-0`) | one link per card with a real destination name, and the whole card is the target (≥24px, in fact the whole card) |
| Location | `suburb, city, province` with a pin, directly under the title | a visitor compares *where* first |
| Facts | a mono meta row: `<n> units` | a countable, comparable fact — the analogue of beds/baths |
| Body | the description, clamped to 3 lines | enough to judge, short enough that every card is the same height |
| Affordance | a plain `View this complex →` line | keeps the "this opens something" signal now that the whole card is clickable |
| Column | no price, no rating, no badge | VALORA publishes neither; inventing one would be a lie about a real place |

### 3.2 The directory page

- The same search (label text unchanged), but the field and button read as one capsule.
- A **results range**: "showing 1–12 of 24 published complexes", so pagination is
  legible rather than a guess.
- A **Clear the search** control whenever a query is active — the documented
  empty-state recovery pattern.
- A **skeleton grid** (same 3:2 media + 3 text lines) behind `aria-busy`, with a
  visually hidden `role="status"` "Loading published complexes…".
- Pagination stays Previous/Next on page-sized chunks (NN/g over infinite scroll),
  restyled onto the same hairline as everything else.

### 3.3 The estate page — gallery, then evidence

Order becomes: breadcrumb → **title + location + facts strip** → **hero gallery** →
**sticky section nav** → two columns.

- **Facts strip** under the title: `24 units · 5 photographs · Gauteng`, and, when the
  administrator has published one, a compact `Living Score 75.6 · Healthy` chip that
  anchors to the score card. This is the Airbnb "rating next to the title" move, using
  the only trust figure VALORA actually has.
- **Hero gallery**, from the photographs the estate published:
  - 1 photo → one 3:2 image; 2 → two 4:3 tiles; 3 → one tall + two stacked;
    4 → 2 × 2; 5 or more → the 1 + 4 mosaic.
  - `Show all N photos` opens the viewer; on a phone the mosaic is replaced by the
    single lead photograph and the same button (the desktop-only mosaic keeps a 390px
    page from overflowing).
  - Every tile is a button, so the viewer opens on the photograph you clicked.
- **Photo viewer**: a modal dialog — `role="dialog"`, `aria-modal`, Escape to close,
  ← / → and Previous/Next buttons, a polite `1 of 5` counter, the caption, body scroll
  locked, focus returned to the tile that opened it. Captions are the alt text.
- **Sticky section nav**: Photos · About · Location · Living Score · Joining, with the
  Living Score entry present only when a score was published.
- **Sticky right column** on `lg` and up (score card, join card), with a real top
  offset and `scroll-mt` on every anchored section so a jump does not land under the
  two sticky bars.
- **Location** is a card, not a map: the published suburb, city and province on the
  survey-grid motif, plus the explicit note that VALORA never publishes a street
  address, a unit number or a pin. There is no coordinates column in the contract, so
  drawing anything map-shaped would be fabrication.
- **Living Score card**: the same four published fields, but led by a 44px mono
  numeral with its band label from the shared `display.ts` bands, and a line saying
  what the score is — a stored calculation over the estate's own operational history,
  published by its administrator, without its internal breakdown. No maths in React.

### 3.4 Shared primitives added

- `Photo` (`components/Photo.tsx`) — one image with a reserved box and a shaped
  fallback, used by the card, the mosaic, and the viewer.
- `Skeleton`, `SkeletonText` (`components/ui.tsx`) — `aria-hidden`, motion-safe, on the
  existing pulse animation.
- `PhotoGallery` + viewer (`components/PhotoGallery.tsx`).
- New icons: photo stack, chevron pair, expand.

## 4. What we refuse

- **No invented data.** No price, no rating, no "featured", no walk score, no crime
  statistic, no map. The contract publishes `name, suburb, city, province,
  description, unit_count, photos[], living_score?` and the UI shows exactly that.
- **No unlabelled composite.** The score keeps its status, its as-of date, its engine
  version and its demo badge, and says plainly that the breakdown is not published.
- **No decorative accent.** Accent stays on the primary action, links and the score.
- **No new dependencies.** No shadcn/Radix, no chart library, no animation library: the
  project's Tailwind 4 + hand-rolled primitives are enough for every decision above.
- **No infinite scroll, no autoplaying carousel, no masonry.**

## 5. How this gets verified

### 5.1 Measured after the change

Same app, same widths, the real components against the published-directory contract
(http://127.0.0.1:4173, Chromium 1440 × 900 and 390 × 844). `/estates` was served a
six-estate page; `/estates/1` a five-photograph estate with a published score.

| Screen | Measurement | Before | After |
|---|---|---|---|
| `/estates` | grid | 3 cols, 20px gap, 373px cards | **3 cols, 20px gap, 373px cards** (unchanged) |
| `/estates` | cover photograph | 371 × 160 — 42% of the card | **371 × 247 — 56% of the card** (1.55× taller) |
| `/estates` | card height | 384px wide, short text card | **373 × 440** |
| `/estates` | screenshot of the slice on screen | absent | **"showing 1–6 of 6 published complexes"** |
| `/estates/:id` | lead photograph | 699 × 320 hero | **574 × 432**, plus four real tiles |
| `/estates/:id` | other four photos | 80 × 56 thumbnails | 4 × **282 × 211** tiles |
| `/estates/:id` | all-photos entry | absent | **"Show all 5 photos"** |
| `/estates/:id` | section nav | absent | present, `position: sticky` |
| `/estates/:id` | join rail at `lg` | not sticky | **`position: sticky`** |
| `/estates/:id` at 390px | gallery | 1 hero + 4 tiny thumbs | **1 lead photograph + "Show all 5 photos"** (1 visible tile, by design) |
| both | horizontal overflow at 390px | — | **none**: `scrollWidth === clientWidth` on `/estates`, `/estates/1`, `/estates/2` |
| both | score card | number + status | number + band chip + status + as-of + engine + provenance paragraph |

- `npm run typecheck` and `npm run build` (the build also re-checks the generated
  contract).
- `npm test` — unit and component tests, including new tests for the directory card,
  the skeleton state, the estate page, and the viewer's keyboard contract.
- `npm run test:e2e` — the 390px sweep, now extended with a second directory entry
  (`/estates/2`) that publishes five photographs, so the multi-photo arrangement is
  measured at phone width too, with every photograph mocked as a 404.
- A live render in the browser pane, with the measurements above taken after the change.

> When these measurements were taken the demo database was unreachable from this
> machine (its managed Postgres refused the connection, and Docker was not running),
> so the *API* was stood in for by a session-only fixture serving the same three
> unauthenticated endpoints and their exact DTOs. Everything else — the app, the
> components, the CSS, the routing — is the real thing. The fixture lives outside the
> repository and is not part of the project.
