# register-role-picker-fix — the account-type picker could not be chosen

**Session:** 13 October 2026. **Branch:** `valora-work`.
**Request (verbatim):** *"Im unable to select roles during account creation."*

A follow-up to `residency-approvals.md` (same Vantage brief). No new feature: the
registration screen's account-type choice was reported as unusable, and it was.

---

## 1. What was wrong

Registration on `/register` offers three account types (Resident, Estate
administrator, Service provider). The user could not select one. Reproduced in real
Chromium before changing anything — clicking each part of the card in turn, in
`e2e/register.spec.ts`'s first shape (a throwaway probe, since deleted):

```
CARD COUNT 3
after card click:     Resident account          <-- clicked the card body: nothing
after blurb click:    Resident account          <-- clicked the description: nothing
after label click:    Service provider account  <-- only the exact label text worked
after ArrowDown:      Estate administrator account
```

Two separate defects, both real:

**1. The card was not the control.** Each option was a `<div>` holding a 16px
`<input type="radio">` and a separate `<label htmlFor>`. Only the radio itself and
the label's own text were click targets. The card's border, padding and the
description — the part that *explains what you are choosing*, and therefore the
part people click — did nothing, on a card that otherwise looked interactive
(it had a `hover:` border). On a touch screen the only reliable target was a 16px
dot.

**2. The chosen card was never marked.** The selected card set `border-accent`,
and unselected cards set `hover:border-ink/40`. Neither ever painted:
`.hairline` was declared in `@layer utilities`, the same layer as Tailwind's
border utilities, so equal specificity was resolved by source order — and the
custom block is appended after Tailwind's. `.hairline`'s `border` **shorthand**
therefore beat every colour utility. The selection had no visible feedback beyond
the small radio dot, and so did every hover in the product that relied on
overriding a hairline.

## 2. The fix

- `frontend/src/routes/Register.tsx`: each card is now a single `<label>` wrapping
  its radio, its title and its description, so the whole card is one click target.
  The accessible name stays exactly the account type via
  `aria-labelledby` (a label wrapping its own input would otherwise take the whole
  card's text as its name) and the description stays the control's *description*
  via `aria-describedby`. A `has-[:focus-visible]` ring was added: the 16px dot's
  own dotted ring is easy to miss on a large card.
- `frontend/src/index.css`: `.hairline` and `.rule` moved from
  `@layer utilities` to `@layer components`, so a utility can override them as
  intended. Both files are the same construct; neither is a utility.

## 3. What the layer move also repaired (same root cause)

All of these were silently flat before, and are now painted as designed:

| File | Intended | Was |
|---|---|---|
| `routes/Register.tsx` | selected card's accent border; `hover:border-ink/40` | grey hairline |
| `components/ui.tsx` (`ErrorState`) | 2px signal bar | 1px grey |
| `routes/AdminResidency.tsx` | 2px accent bar on the decision notice | 1px grey |
| `routes/RequestAccess.tsx` | 2px accent bar on "Request sent to …" | 1px grey |
| `routes/RequestAccess.tsx` | `hover:border-accent` on the complex picker | no hover |
| `routes/Dashboard.tsx` | `hover:border-ink/40` on recent items | no hover |
| `routes/AdminSetup.tsx` | `border-accent` on the public-profile step | grey hairline |

## 4. Files changed

- `frontend/src/routes/Register.tsx` — the card is the control; `aria-labelledby`;
  card focus ring.
- `frontend/src/index.css` — `.hairline` / `.rule` moved to `@layer components`,
  with the reason recorded in a comment.
- `frontend/src/routes/Register.test.tsx` — 5 tests → 9.
- `frontend/e2e/register.spec.ts` — new, 5 real-browser tests.

No API, contract, migration, environment variable or backend change. The payload
is untouched: `registrationPayload` still sends `account_type` and never a `role`.

## 5. Tests added and passing

`frontend/src/routes/Register.test.tsx` (written first, seen failing — 2 of the new
4 failed before the fix):

- chooses the type clicked, from the radio, the title **or the description**;
- the card, not just its text, is the click target;
- each radio is *named* by its account type and *described* by its blurb;
- the arrow keys move the choice.

`frontend/e2e/register.spec.ts` (real Chromium — jsdom cannot see CSS):

- the description and the card body both choose the type;
- the chosen card is marked, and by more than colour alone (computed border
  differs between the chosen and the unchosen card);
- keyboard-only focus rings the whole card — `Tab` from a cold load, asserting
  `outline: dotted 2px rgb(31, 111, 92)`, and that the ring follows `ArrowDown`;
- a rejected registration renders `ErrorState` with its signal bar actually 2px
  and `rgb(228, 87, 46)` — which is what proves the layer move, on a real screen;
- `/register` stays inside a 390px viewport.

## 6. Commands run, with results

Run from `frontend/` unless noted.

| Command | Result |
|---|---|
| `npx playwright test e2e/register.spec.ts` | **5 passed**, exit 0 |
| `npm run typecheck` | exit 0 |
| `npm run test` | **169 passed** (23 files), exit 0 — was 165, +4 here |
| `npm run build` | exit 0 (`dist/index-*.css` 40.45 kB) |
| `npm run check:api` | exit 0, generated files match `docs/openapi.json` |
| `npx playwright test --workers=1` | **29 passed**, exit 0, 2.2m |
| `npm run test:e2e` (default workers) | **29 passed**, exit 0, 2.0m |
| `git diff --check` (`git`, repo root) | exit 0 |

Compiled-CSS evidence that the fix is real, not just a class string: in
`dist/assets/index-*.css` `.hairline` is emitted at byte 7411 and
`.border-accent` at 17750 — components before utilities, which is the whole fix —
and all four `has-[:focus-visible]` utilities compile (including
`--tw-outline-style:dotted`).

**Not run:** anything backend. No backend file was touched, so `pytest` was not
re-run; the 3 PostgreSQL integration tests remain skipped for the same reason as
last session (`TEST_DATABASE_URL` unset).

## 7. Flakiness seen, and what it was not

Two full-suite runs mid-session failed with **timeouts** — `page.goto`,
`locator.fill`, `browserContext.close` — never an assertion mismatch, and a
different test each time (6.7m and 1.8m wall-clock against 59.6s for the same
suite earlier). Both the affected specs passed in isolation immediately after.
Re-run once the machine quietened: 29 passed in 2.0m, and 29 passed serially in
2.2m. Conclusion: contention on this machine at the time, not a regression. The
suite runs with `fullyParallel: true`; on a loaded machine its 30s per-test
timeout is the thing that gives way.

## 8. Side effect worth knowing

`frontend/test-results/` is **tracked in git**, and Playwright clears it at the
start of every run. So running `npm run test:e2e` deletes the previous run's
`trace.zip` / `error-context.md` artifacts and rewrites `.last-run.json`. Those
deletions in `git status` are from the project's own test command, not hand edits,
and they were already showing as modified before this session started. Suggest
`.gitignore`-ing `test-results/` so a test run cannot dirty the diff.

## 9. Remaining / open

- The same cascade pattern is worth sweeping for in areas not exercised here: any
  `hairline` (or `rule`) combined with a Tailwind border utility is now correct,
  but a `components`-layer class combined with a *variant* utility such as
  `focus:border-*` or `group-hover:border-*` has not been individually checked on
  every screen.
- Registration remains residents-only by design (`Public registration creates
  residents only`). The *account type* picker offers three types; the API still
  refuses a `role` field outright, and no role is ever client-supplied. If
  "select roles" was meant as *choosing your own role*, that is a product
  decision, not a bug — the current model derives the role from `account_type`
  server-side, deliberately.
- No human visual review of `/register` at 375/768/1280: the preview panel in
  this session would not composite, so the visual checks are programmatic
  (computed styles and geometry) rather than eyeballed.

---

# Part two — the estate photo mosaic's overflow tile

**Request (verbatim):** *"Was the properties and estates UI improved? to display more
images beyond the photo collage, some line art icons etc, glass morphism and some much
more?"* — with Airbnb screenshots of the 1 + 4 mosaic, the "Show all photos" control
and the amenity list.

## 10. The honest audit that preceded the work

| Asked for | State before this part |
|---|---|
| Estate page shows more than one image | **Yes**, since `ui-showcase-redesign.md`: a 1 + 4 mosaic, arrangements for 1–5, a modal viewer with keyboard control, skeletons, real empty/error states. |
| More images **beyond** the collage | **No.** `mosaic()` built 5 tiles and `photos.slice(0, tiles.length)` silently dropped the rest. No blurred tile, no count — an estate with twenty photographs *looked* like an estate with five. |
| Line-art icons | **Partly.** ~25 hand-rolled stroke icons in `Icons.tsx`; `IconImages` on the facts strip, `IconCheck` in the publication panel, `IconPin` on the location card. There is no amenity list like Airbnb's, because the contract publishes no amenities — inventing them would be fabrication. |
| Glassmorphism | **Deliberately absent.** `docs/design/VALORA-DESIGN-DIRECTION.md` and `index.css` specify hard hairlines, near-zero radius, near-no shadow; the original brief itself says "avoid … glassmorphism everywhere". |
| The in-app `/app/properties` screen | **Unchanged** — a data table with no photographs. Estate photographs are estate-level, not per-unit, so it has nothing honest to show yet. |

## 11. What was built

`frontend/src/components/PhotoGallery.tsx`:

- `arrangement(count)` keeps the existing geometry; **`mosaic(count)`** is now exported
  and returns `{ grid, tiles, clear, overflow }`. `clear + overflow === count` always,
  and `overflow` is 0 while the photographs fit — so a five-photograph estate wears no
  blur and no count.
- The last slot becomes the **overflow tile** when photographs are left over: the
  concealed photograph at `blur(3px)` under a scrim, reading **`+8 more`** and
  "Open the full gallery", with an accessible name of
  `Show all 12 photographs, including 8 not shown here`.
- It is interactive, and opens the viewer on **the first photograph it conceals**
  (photograph 5 of 12) rather than sending the visitor back to one they have seen.
- The floating `Show all N photos` control is hidden at `lg` when the overflow tile is
  present — the tile already says it — and stays below `lg`, where the tiles past the
  first are hidden and it is the only way in.
- One restrained, functional use of glass: that floating control is now
  `bg-surface/80 backdrop-blur-md` instead of near-opaque, so it sits over a photograph
  the estate chose without hiding it. This is the only frosting added; the rest of the
  product still holds the design direction's no-glass rule.

## 12. Tests added and passing

| Test | What it pins |
|---|---|
| `frontend/src/components/PhotoGallery.test.tsx` (8, new) | the arithmetic for **every** count 1–20 (`clear + overflow === count`, never more tiles than slots, an overflow is always ≥ 2); nothing blurred while everything fits; the count and the accessible name at 12; **no** count and no blur at 5; the tile opening at `5 of 12`; the plain button kept for below `lg`; the empty state. |
| `frontend/e2e/estate-gallery.spec.ts` (3, new) | in real Chromium: `+8 more` visible with a computed `filter` containing `blur(3px)`; exactly four clear tiles and no fifth; the mosaic's **height identical** at 5 and at 20 photographs, so the tile takes the fifth slot instead of growing a row; the tile opening the viewer at `5 of 12`, `ArrowRight` to `6 of 12`, `Escape` closing. |
| `frontend/e2e/mobile.spec.ts` (extended) | `/estates/3` publishes 12 photographs, so the overflow path is swept at 390px as well. |

## 13. Commands run, with results

Run from `frontend/`.

| Command | Result |
|---|---|
| `npx vitest run src/components/PhotoGallery.test.tsx src/routes/PublicEstateDetail.test.tsx` | **15 passed**, exit 0 — the existing estate-page tests are unaffected |
| `npx playwright test e2e/estate-gallery.spec.ts` | **3 passed**, exit 0 |
| `npx playwright test e2e/mobile.spec.ts -g "estates"` | **4 passed**, exit 0 |
| `npm run typecheck` | exit 0 |
| `npm run test` | **177 passed** (24 files), exit 0 — was 169, +8 here |
| `npm run build` | exit 0 |
| `npm run check:api` | exit 0 |
| `npm run test:e2e` | **33 passed**, exit 0, 2.2m |
| `git diff --check` | exit 0 |

**Not run:** the in-app `/app/properties` screen and the admin uploader were not touched.
The unit tests serve SVG photographs, so real JPEG decoding and EXIF orientation are
still unexercised in a browser, as `ui-showcase-redesign.md` already records.

## 14. Still open

- **Amenities.** Airbnb's third screenshot is a feature list with an icon per line. That
  cannot be built honestly: neither `PublicEstateDetail` nor the estate profile publishes
  an amenity field, and a hard-coded list would be invented data. It needs a decision and
  an additive contract change first — a real feature, not a styling task.
- **Glassmorphism** beyond the one control above. Making it a house style would reverse
  a written design decision; worth confirming rather than drifting into it.
- The admin photograph uploader (multi-select, previews, cover, reorder) from the original
  brief remains unbuilt. *(Partly built in part three, below.)*

---

# Part three — selecting several photographs at once

**Request (verbatim):** *"I also noticed when uploading images, that I can only select one
at a time, I dont like that. The system should allow me to select more than one image when
uploading images."*

## 15. What was wrong

The uploader's file input had no `multiple`, and every handler took `files[0]` — the
picker, and the drop zone. So an administrator with a folder of photographs made one
trip through the file dialog per photograph.

Two things made this a component rewrite rather than a one-word fix. The API takes **one
file per request** (`POST /api/v1/estates/photos`), so a batch is inherently N requests.
And the estate has a hard ceiling of **12 photographs**
(`MAX_PHOTOS_PER_ESTATE`), enforced server-side with a 409 — so a naive loop over twelve
files would have its answer depend on the order the requests happened to land in.

## 16. What was built

`frontend/src/routes/AdminSetup.tsx` — the uploader now holds a **queue** rather than one
file:

- `multiple` on the input, and both the picker and the drop zone take every file offered.
- A second selection **adds** to the queue instead of replacing it.
- Each queued row carries its own thumbnail (a real `blob:` object URL), filename, size,
  caption, status and — if it failed — the **server's own message and request id**, on the
  row rather than in one banner that a single failure has to hijack.
- Files are judged **one at a time** when picked, so a batch with one bad file still sends
  the good ones: a wrong type or an oversized file is refused by name and by reason, and
  the rest go.
- **`clear + overflow`-style arithmetic for the ceiling**: the queue counts against
  `MAX_ESTATE_PHOTOS - existingCount`, so the batch is never queued only for the server to
  refuse its last photograph. A full estate says so and says how to make room.
- The same photograph chosen twice is ignored, with a line saying so.
- Uploads run **sequentially**, one request per photograph — which keeps the estate's
  photo count honest between requests, since the server checks the ceiling per upload.
- Object URLs are given back when a row is removed, when the queue is cleared, and when
  the component unmounts. That is the leak this component was always going to have.
- `frontend/src/lib/estateAdmin.ts` gains `MAX_ESTATE_PHOTOS` (mirroring the service's
  constant, with a comment saying so) and `ACCEPTED_IMAGE_LABEL`; `UPLOAD_HINT` is now
  derived from them rather than repeating "5 MB" and "12" as prose.

**No backend change.** One request per file is exactly what the API already takes, and the
12-photo ceiling is still the server's to enforce.

## 17. Tests added and passing

| Test | What it pins |
|---|---|
| `frontend/src/routes/AdminSetup.photos.test.tsx` (11, new) | three files in one selection with a preview each; a second selection adding to the first; one request per photograph, each with **its own caption**; a text file and an oversized file refused by name while the third still uploads; only 2 of 4 queued when 2 places remain, with the reason; a full estate refused with "delete one first"; the same file chosen twice ignored; the removed row's object URL revoked; **every** preview revoked on unmount; the queue cleared previews and all; a rejected photograph kept with the server's message and ref. |
| `frontend/e2e/admin-photos.spec.ts` (2, new) | in real Chromium: the input really has `multiple`; two files through the real picker in one interaction queue two rows with live `blob:` previews; a second selection makes three; **three requests, one per file**, each multipart, with distinct filenames; the queue empties and the estate re-reads; a `.txt` refused while the good file is still sent. |
| `frontend/e2e/fixtures/{pool,gate,court}.png`, `notes.txt` | 70-byte real PNGs and a text file, chosen from disk. |

Three things worth recording, because they cost time and will recur:

1. **`applyAccept` is a `userEvent.setup` option in this version**, not a third argument to
   `upload` — the installed `upload` signature is `(element, fileOrFiles)`.
2. **`playwright`'s `setInputFiles` payload type is `Buffer`**, and this project carries no
   Node type definitions. Fixtures on disk avoid both `@types/node` and `Buffer`; the path is
   built from `import.meta.url` (a web standard) rather than `node:url`.
3. **`within`/`getByText` exactness differs between runners**: Testing Library matches an
   element's own text nodes exactly, Playwright's is a substring match — so a row's filename
   also matched its visually hidden "Caption for …" label under Playwright, and needed
   `{ exact: true }`.

## 18. Commands run, with results

Run from `frontend/`.

| Command | Result |
|---|---|
| `npx vitest run src/routes/AdminSetup.photos.test.tsx` | **11 passed**, exit 0 |
| `npx playwright test e2e/admin-photos.spec.ts` | **2 passed**, exit 0 |
| `npm run typecheck` | exit 0 |
| `npm run test` | **188 passed** (25 files), exit 0 — was 177, +11 here |
| `npm run build` | exit 0 |
| `npm run check:api` | exit 0 |
| `npm run test:e2e` | **35 passed**, exit 0, 1.6m |
| `git diff --check` | exit 0 |

One e2e run failed with `net::ERR_NETWORK_CHANGED` against the dev server and passed on the
next attempt; that is the environment, not the code.

## 19. Still open from the original brief

- **Choosing a cover photograph and reordering.** The API has `position`, and the list
  already moves photographs up and down one step at a time, but there is no "make this the
  cover" control and no drag-to-reorder.
- **Editing a caption after upload.** `PATCH /api/v1/estates/photos/{id}` accepts a caption
  and nothing in the UI uses it, so a typo currently means delete and re-upload.
- **Client-side cropping/decode checks.** Type and size are checked; the server decodes and
  re-encodes.
- Per the same reason as part one: no live database or real SMTP run, and no human visual
  review (the preview panel would not composite in this session).
