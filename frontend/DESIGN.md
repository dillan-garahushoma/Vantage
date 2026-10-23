# VALORA — DESIGN.md

The design system document for the VALORA frontend. `AGENTS.md` says how the project is built;
this says how it should look. Read it before restyling, building or reviewing any user-facing
surface.

Written 2026-10-23 after a review of the project's own references: the Audemars Piguet study, the
FibreHood about page and client portal, the Dominus Investments site, the FibreHood PRME portal,
and the Group8 resident/occupancy maintenance prototype.

## 1. The read

VALORA is not a dashboard product with an estate theme. It is an **estate record**: a dossier a body
corporate would keep, digitised — addresses, units, complaints, work orders, contractors, and one
figure that says whether the place is getting better. South African private estates: brick, face
brick, palisade, jacaranda, boom gates, a body corporate that meets on a Tuesday.

So the surfaces should feel like a well-set document — rules, tabs, margin notes, plate numbers,
measurements — far more than like a SaaS admin panel. The product already leans this way (`Keyline`,
`EstatePlan`, `scale 1:1000 · rev 03`, tabular numerals everywhere). This document makes that the
stated direction instead of an accident.

### What each reference gives us

| Reference | What we take | What we leave |
| --- | --- | --- |
| Audemars Piguet study | Restraint; one object per screen presented slowly; hover as magnification, not decoration | The luxury-watch price theatre |
| FibreHood about page | `Fraunces` as the display face against `Inter`; bone paper; a single warm accent against deep ink | The navy/amber palette itself |
| FibreHood client portal (PRME) | shadcn-style token mapping (HSL channels → semantic roles); calm portal chrome; clear record rows | Yellow-on-navy identity |
| Dominus Investments | Editorial serif + gold on coal; `cubic-bezier(0.22, 1, 0.36, 1)` as the house easing; GSAP for entrance and scroll | Dark-mode-first luxury real estate |
| Group8 prototype | The information architecture we adapt: resident dashboard, complaints, occupancy, provider directory, work orders | Per-component CSS, `window.alert`, localStorage state, client-side maths |

**The common thread in the references is a display serif over a quiet ground with one accent. VALORA
already has the quiet ground and the accent; it is missing the serif and the editorial rhythm.**

## 2. Direction: "Estate dossier"

Three registers, deliberately different, sharing one palette:

1. **Public / marketing** (`PublicShell`): editorial. Display serif headlines, bone-warm paper,
   asymmetric two-column grids, plate captions, wide margins. This is the estate brochure.
2. **Workspace** (`AppShell`): instrument. Sans headings, dense tables, chips, tabular figures.
   This is the management office.
3. **Record detail** (drawers, dialogs, reports): documentary. A title block, a metadata strip
   (`logged · assigned · resolved`), the evidence body, then actions. Every record opens the same way.

The registers differ in type voice and spacing, never in colour meaning.

## 3. Tokens

Defined in `src/index.css` (`@theme`). Additions below are additive; nothing existing is renamed.

### Type

| Role | Family | Use |
| --- | --- | --- |
| `--font-display` | `Fraunces` (fallback Georgia) — **new** | Public headlines, the wordmark lockup in marketing, pull figures on marketing pages |
| `--font-heading` | Plus Jakarta Sans | Workspace headings, record titles, dialog titles |
| `--font-sans` | Inter | All body copy |
| `--font-mono` | JetBrains Mono | Every measurement, ID, date, score, plate number |

Two families is the ceiling for body text; the serif is a *display* register only and never sets
body copy or UI labels. Never set a number in Fraunces — numbers belong to `.num`.

Scale, public surface: 44 / 52 / 68px display (clamp), 26–32px section, 16px lead, 15px body,
13px caption, 11px plate. Workspace surface keeps the existing 26–32 / 15 / 13 / 11 steps.

Line height: display 0.98–1.05, section 1.15, body 1.55. Tracking: display `-0.02em`,
plates `+0.18em` uppercase.

### Colour

Unchanged semantics — this is the part of the system that is already right:

- ink `#1F1733` ground for text and the closing band; violet `#7C3AED` is the **one** accent (actions,
  focus, links, the active nav item); mint `#2F9E73` = healthy, ochre `#D98A2B` = watch,
  signal `#C44D63` = risk; lavender hairline `#E9E3FF`; paper `#F7F5FF`.
- Rule: a colour means something or it is ink. No decorative colour. Violet never encodes health.
- Open question (see §7): whether paper warms to bone `#FAF8F4` and the accent moves to brass, which
  is what the references would do. Do not change this without an explicit decision — the palette is
  asserted by tests and used across 60+ files.

### Shape, depth, motion

- Radii: soft (12–16px) on surfaces and controls, 0 on the dossier plates and rules — a frame is
  square, a card is soft. Never mix both radii on one element.
- Depth: one soft shadow (`--shadow-soft`) for lifted surfaces; `--shadow-lift` only for the single
  primary action on a screen. Hairlines do the rest of the work.
- Motion: `--ease-soft` (`cubic-bezier(0.22, 1, 0.36, 1)`) for anything that enters, 180–280ms.
  Reveals are 400–600ms and move ≤12px. Hover is a 2% scale, a 1px lift, or an underline — never all
  three. Everything respects `prefers-reduced-motion: reduce` (the existing keyframes already do
  through `@media` guards; new ones must too).

### Imagery

Photographs are documentary: the gate, the wall, the stairwell, the repaired pipe. Caption them like
plates (`Plate 04 — North perimeter, 06:40`). No stock "happy residents", no gradients on photos, one
treatment (slight desaturation, warm highlights) applied consistently.

## 4. Section blueprints

**Public hero.** Two columns, 1.05 / 1 — the claim on the left, one artefact on the right (a plate,
a plan, a live score). The claim is a display-serif sentence, at most two lines, with the second line
carrying the accent. Under it: one 16px lead paragraph, one primary action plus one quiet text link,
then a rule and three measurements. The artefact is framed square with a hairline, captioned above
(`Ridge Close Estate · Model`) and below (`scale 1:1000 · rev 03`). The hero must clear the fold on
a 900px-tall laptop with the primary action visible.

**Public section.** Plate number and eyebrow (`01` + `HOW THE RECORD WORKS`), display-serif or strong
sans title at 26–32px, an optional 15px intro capped at 2xl, then content. Alternate the ground
(paper / surface) with a rule between sections; never two identical grounds stacked without a rule.
Vary the vertical rhythm: a tight section after the hero (py-10) and a generous one before the close
(py-16). Uniform py-14 everywhere is what makes a page read as a template.

**Record row.** Left: title (15px medium) over a metadata line (11px mono, `ink-muted`). Right: status
chip, then age in mono. Hover: hairline turns `line` → `brand-soft`, nothing moves.

**Record drawer.** Title block (record title + `#id` in mono), metadata strip, evidence body, then a
sticky action footer. Same anatomy for complaints, work orders and members.

**Empty state.** One line of what would be here, one line of what to do, one action. No illustration.

## 5. Adapting Group8's screens

Group8 supplies the workflows; VALORA supplies the architecture, tokens and the backend. Port flow,
never code: every ported screen goes through `EstateAuthorizationService`-backed endpoints, the
`AuthContext`, `useEstateScope()` and the existing primitives.

| Group8 screen | VALORA target | The design delta |
| --- | --- | --- |
| `ResidentDashboard` | `routes/Dashboard.resident.jsx` | Keep the "my unit / my open issues" pair. Numbers in `.num`, unit card as a record header, no icon grid of shortcuts |
| `Complaints`, `ResidentComplaints` | `routes/Complaints.jsx` | One list for both roles, filtered by capability. Status chips carry meaning; the lifecycle is shown as a strip, not a dropdown |
| `Maintenance` | `routes/WorkOrders.jsx` | Work order record per §4; provider assignment is a drawer action, not a modal form |
| `Providers` | `routes/Providers.jsx` | Directory as a table with a provider scorecard drawer; ratings are evidence, not stars only |
| `CommunityAnalytics` | `routes/EstateHealth.jsx`, `Dashboard.admin.jsx` | Charts keep `ChartCard`; every chart gets a `basis` caption (window, sample size) |
| `Announcements`, `CommunityAnnouncements` | `routes/Announcements.jsx` | Resident read view + admin composer; pinning is a chip, not a colour |
| `RegistrationRequests`, `UserManagement` | `routes/Members.jsx`, `AdminResidency.jsx` | Approvals are record rows with a two-step confirm dialog; no `window.confirm` |
| `Profile` | `routes/Settings.jsx` | Grouped form sections with one save action per section |
| `DashboardSidebar` | `components/layout/Sidebar.jsx` | Current rail stays; role filtering is server-derived, never from local role state |
| `LandingPageSettings` | out of scope | Estate CMS is not part of this product phase |

Retired Group8 scope (investor ROI, valuation, agent listings, marketplace) is **not** ported; its
routes return 404 in VALORA.

## 6. Never

- A chart without its basis, a score without its window, a number without its unit.
- Two accent colours on one screen, or colour used for decoration.
- `window.alert` / `confirm`, or a modal for a task that belongs in a drawer.
- Business logic, score maths or permission checks in JSX. The UI asks the API and renders the answer.
- A new font, radius, shadow or easing that is not in §3.
- Uniform card grids as a page's only structure — every page needs one asymmetric or rule-led moment.

## 7. Open decisions

1. **Palette warmth.** Keep violet on lavender paper (current, safest), or move public surfaces to
   bone `#FAF8F4` with brass as the marketing accent and keep violet inside the app. The references
   favour the second; tests and 60+ files favour the first. Decide deliberately, then encode it here.
2. **Motion library.** GSAP (references use it) versus the existing CSS keyframes plus a small
   IntersectionObserver reveal. Recommend CSS + observer until a surface needs timeline control;
   one motion system only.
3. **Imagery.** The estate photographs currently ship as a small set; a documentary set per estate is
   the missing piece for the public register.

## 8. How to check the work

1. `cd frontend && npm run build` — no class that Tailwind cannot resolve.
2. `cd frontend && npm test` — token and copy assertions stay green.
3. Screenshot it in a real browser, at 1440 / 768 / 390, and look at the picture before judging the
   code: `.agents/skills/design-taste-frontend/scripts/inspect.mjs` (see `AGENTS.md` for `CHROME_PATH`).
4. Review the diff against §6 before calling a surface done.

### Last run — 2026-10-23, `Landing.jsx`

`npm run build` green. `npm test` reached 205 vitest + 2 node tests green at 12:47 (after fixing the
`Field` accessible name and deleting two stale `*.tsbuildinfo` files from the TypeScript era);
at 13:00 seven `Intelligence.test.jsx` cases fail because `AskValora`, `ValoraChatContext`,
`FormattedMarkdown` and `AppShell` are being rewritten concurrently in this checkout — reverted my
only component change and the same seven still failed, so the break is not from this pass.
Inspector at
1440 / 768 / 390: no horizontal overflow, hero headline two lines at 1440 (h1 104px tall), primary
action inside the first fold (bottom 578 of 900), closing headline `#F7F5FF` on `#1F1733`.
Seven of the inspector's house-rule FAILs are **deliberate and defended** for this product: mono
tabular figures, plate/eyebrow labels, index numbers on the value chain, hairlines and 1px outlines
(the document metaphor), violet as the single accent, and the italic serif clause in the hero. The
open ones are `still-page` (no motion yet — see §7.2), `few-pictures` and `focal-point` (§7.3), and
the 36px mobile lockup wrapping to three lines, which is the only way to keep the two-clause claim
at a readable size on a 390px screen.
