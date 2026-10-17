# VALORA — Frontend Design Direction

> **Status:** Research / direction — not yet implemented (frontend not in this repo yet).
> **Purpose:** Capture the visual taste we want for VALORA before the React app is built, so
> login, dashboard, property pages and the Living Score all share one deliberate look.
> **Date:** 10 October 2026

---

## 1. Where this taste comes from (research)

We looked at two very different shelves of inspiration on purpose: prop-tech dashboards
(what a property product *has* to show) and the 2026 retro/brutalist movement (how a
property product can *feel* like something a person made, not a template).

### Prop-tech UI references (Dribbble boards to browse)
- [Property Management](https://dribbble.com/tags/property-management) — 2,500+ shots
- [Property Management Dashboard](https://dribbble.com/tags/property-management-dashboard)
- [Real Estate UI](https://dribbble.com/tags/real-estate-ui) — 1,100+ shots
- [property dashboard](https://dribbble.com/search/property-dashboard), [property CRM](https://dribbble.com/search/property-crm), [real estate table](https://dribbble.com/search/real-estate-table)

Recurring patterns worth stealing: a left rail with one primary section highlighted, a KPI
tile row across the top, a map/list split for properties, status chips (paid / open / urgent),
a right-side detail drawer instead of full-page navigation, and dense-but-scannable tables.

### Retro / brutalist / Y2K references
- [Retro and brutalist UI design: a 2026 field guide — Setproduct](https://www.setproduct.com/blog/retro-brutalist-ui-design-2026)
- [Awwwards — Retro websites](https://www.awwwards.com/websites/retro/)
- [Figma — Web design trends 2026](https://www.figma.com/resource-library/web-design-trends/)
- Production examples the field guide points to: **Gumroad** (brutalist), **Poolsuite FM** (Y2K), **Are.na** (anti-minimalist, dense), **Vercel** (stark mono dev aesthetic), **98.css** / **system.css** (old-OS chrome toolkits).

**The one warning to carry forward:** the field guide is explicit that full retro/brutalist
treatment suits portfolios, editorial and creator tools — *not* products handling money or
health data, where low-contrast "raw" styling and playful chrome hurt trust and conversion.
VALORA handles valuations, complaints, security incidents and HOA money. So we take the
*technical edge* of the retro movement and leave the chaos behind.

---

## 2. The direction: **"Calm Intelligence, Technical Edge"**

ETHOS — a trustworthy instrument, not a novelty. Clean and legible like the best prop-tech
dashboards, but with a distinctive retro-technical signature that makes it unmistakably
VALORA and unmistakably South African.

The look borrows four things from the 2026 movement and refuses three:

**Take**
1. **Monospaced numerals** for every figure — valuations (R 1 250 000), Living Score (91/100),
   resolution times (2.4 days), KPI deltas. Tabular mono reads as "instrument" and makes
   numbers align and compare. (Berkeley Mono / Departure Mono vibe → use **JetBrains Mono** or **IBM Plex Mono** in code.)
2. **Hard 1–2px borders and near-zero radius** with one *real* accent colour — structure exposed,
   no soft haze. This is the brutalist honesty, used sparingly.
3. **A signature accent** — one saturated colour used only for meaning (score, primary action, alert),
   never decoration.
4. **Density.** Are.na-style information density on the HOA/admin screens; residents get the airy version.

**Refuse**
1. Full brutalist palette (no default-blue links, no harsh black/white only — accessibility risk).
2. Y2K sparkle/chrome overload (gimmick; wrong signal for a financial/community product).
3. Fake OS window chrome trapping real tasks behind windows.

Position on the spectrum: **80% clean prop-tech, 20% retro-technical signature.**

---

## 3. Design tokens (proposed)

Colours should feel like a South African highveld estate: cool neutral base, one confident accent.

| Token | Value (proposed) | Use |
|---|---|---|
| `--valora-ink` | `#14181C` | Primary text, borders on dark |
| `--valora-paper` | `#F6F4EF` | Warm off-white app background (not pure white) |
| `--valora-surface` | `#FFFFFF` | Cards / panels |
| `--valora-line` | `#14181C` @ 14% | Hairline borders, table rules |
| `--valora-accent` | `#1F6F5C` (deep estate green) | Primary action, brand |
| `--valora-signal` | `#E4572E` (terracotta) | Alerts, unresolved / urgent |
| `--valora-score-hi` | `#1F6F5C` | Living Score 75–100 |
| `--valora-score-mid` | `#C08A2E` (ochre) | Living Score 50–74 |
| `--valora-score-lo` | `#B3261E` (brick) | Living Score 0–49 |

- **Type:** UI — a neutral, slightly technical sans (Inter / IBM Plex Sans). **Data — a mono for all numbers and IDs.** One display weight for page titles only.
- **Radii:** `2px` default, `0` on data tables and chips. Reserve `8px` for nothing — avoid rounded-card sameness.
- **Spacing:** 4px base scale; generous section padding for residents, tighter for admin.
- **Shadow:** near-none. Use 1px borders + a single hard offset shadow on the one primary CTA (the brutalist move, used once).

---

## 4. Screen-level guidance

- **Living Score is the hero.** A large mono numeral with a 3-part breakdown bar
  (maintenance / security / governance). Never show the number without its contributing
  factors — PRD principle 4: *"a score without a reason is marketing."*
- **Dashboard:** KPI tile row (mono figures) → trend sparkline → "needs attention" list →
  recent activity. Status via chips, not colour alone (icon + label too).
- **Property page:** map/list split, right-side detail drawer, valuation with an explicit
  "why it's worth it" factor list — this is the differentiator vs Property24.
- **Complaint / work-order lifecycles:** horizontal timeline, mono timestamps, clear current stage.
- **Provider ratings:** stars plus a mono count; show distribution, not just an average.

---

## 5. Motion & accessibility (non-negotiable for a trust product)

- Motion is functional only: 120–200ms, ease-out, no bounce. No Y2K glints.
- **WCAG AA** contrast on every accent (validate the ochre/brick chips against `--valora-paper`).
- Visible focus rings (a retro dotted focus ring is a tasteful nod that also helps keyboard users).
- Never rely on colour alone for score or status.
- `prefers-reduced-motion` disables non-essential motion.

---

## 6. Do / Don't

| Do | Don't |
|---|---|
| Mono numbers, aligned and comparable | Rounded pastel dashboard clichés |
| One accent colour with real meaning | Accent used for pure decoration |
| Hard hairlines and visible structure | Heavy drop shadows / glassmorphism fog |
| Dense, scannable admin tables | Fake OS windows hiding real tasks |
| Score always with its reasons | A number with no explanation |

---

## 7. Tooling installed to build this

Free, no-API-key MCP servers are wired in [`.agents/mcp.json`](../../.agents/mcp.json)
(restart / reload the app so they load, and ask from inside the repo):

| Server | Package | What it gives the design workflow |
|---|---|---|
| **playwright** | `@playwright/mcp` | Drive a real browser, take accessibility snapshots, screenshot and iterate on the live UI. |
| **chrome-devtools** | `chrome-devtools-mcp` | Console/network debugging, performance traces, DOM/CSS inspection, emulation. |
| **shadcn** | `shadcn mcp` | Browse & install shadcn/ui components from registries directly into the project. |
| **context7** | `@upstash/context7-mcp` | Up-to-date docs for React, Tailwind, Radix, Chart.js etc. while coding. |

Optional (needs a free account/key, not enabled):
- **Figma** — `figma-developer-mcp`, needs a personal Figma API token (`FIGMA_API_KEY`), for pixel-accurate handoff.
- **21st.dev** — note the old `@21st-dev/magic` package is now only a compatibility proxy; skip unless a current key-backed package is confirmed.

The account skills that pair with this (design, ui-styling, design-system, banner-design, brand,
slides) already describe the token/spec workflow — use them alongside these servers.

---

## 8. Open questions for the human
- Accent colour: estate green vs a bolder SA-signal accent (e.g. aloe / protea)?
- How much retro edge is acceptable on the **login/signup** screen (the only UI that exists today)?
- Which charting library (Chart.js per the `slides` skill, or Recharts) for the score trends?
