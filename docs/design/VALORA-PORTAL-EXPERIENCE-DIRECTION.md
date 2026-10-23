# VALORA portal experience direction

**Purpose:** Product-specific visual and interaction contract for the resident and HOA workspaces.
**Parent brief:** `docs/CODEX_UX_REDESIGN_BRIEF.md`
**Current implementation batch:** `batches/ux-experience-completion.md`

This is not a wireframe to copy pixel-for-pixel. It describes the experience outcomes that must guide component decisions in the actual Vantage repository.

## Brand and overall feeling

VALORA's existing light-purple/violet identity is the source of truth. Preserve its tokens and refine them only when the result remains recognisably VALORA. Aim for confident, welcoming, intelligent, and composed—not sterile enterprise software and not a generic dashboard kit.

Use photographs as editorial context: a wide architectural image can establish an estate and its sense of place; small images can provide evidence or support a gallery. Use the real published estate photograph when available. Never imply a decorative stock photo is a verified photograph of the actual complex. If a real image is unavailable, use a graceful neutral/lavender placeholder with meaningful text.

Create visual rhythm through differences in scale and layout: one dominant section, generous negative space, selective use of rules, typography, a dense operational list where it makes sense, an image-led region where context helps, and compact metadata. Do not put every idea inside a rounded rectangle. A section can be an open canvas with a heading, dividers, and a list.

## Resident portal

The first viewport after sign-in must answer, in this order:

1. Which estate am I viewing?
2. What has happened with my own requests?
3. Is there an important notice I need to read?
4. What is the next meaningful action?

Use a welcoming estate header and one obvious primary action to report an issue. Present active requests as a readable list or status timeline, not a grid of identical cards. Each request should communicate title, location where authorised, current state, and the next expected step. Notices can use a distinct editorial/announcement treatment with a date and small purposeful icon. Estate health should be a compact secondary summary with a link to the dedicated Estate Health page; do not repeat full score detail in navigation, dashboard, and other pages.

## HOA administrator portal

The first viewport must answer: what requires intervention, and what should I do next?

Start with compact estate identity/context and one primary action such as creating a work order. Give urgent and overdue work clear typographic/state hierarchy in an actionable queue/table: issue, priority/status, accountable party if known, age/due date, and next action. Link every row to its actual authorised record. Keep measured operational status separate from suggestions.

Estate health can appear as one concise summary with as-of date and a path to detailed analysis. Place secondary context (recent activity or trend) lower on the page, using open layout and a compact sparkline/chart only when the data makes the visualization useful. Do not show four equal KPI cards as a default hero. Do not let an oversized briefing headline push actionable work below the fold.

Use a contextual side drawer for issue detail, supporting evidence, and actions. The drawer must preserve the list context, close by button and Escape, manage focus properly, and respond gracefully at mobile widths.

## VALORA Intelligence and the assistant

Intelligence is a task-driven workspace, not a report followed by a permanently embedded chat panel. Let a user inspect the stored briefing and current evidence; keep Ask VALORA clearly present on this page without duplicating it in global navigation. The assistant starts in a compact but welcoming compose state; an actual conversation grows into the available workspace, with an intentional expanded state when useful.

Use response layout suited to the content: concise takeaway, meaningful section headings, evidence/source rows, a small number of relevant follow-up prompts, and detail disclosure as needed. Do not put the whole response in another card or occupy half the screen with a fixed empty panel. A failed briefing request must not conceal an otherwise available assistant, and provider/configuration failures must be stated honestly.

## Shared navigation and behaviour

- Keep a stable, scannable left navigation and a compact top bar. Highlight only the current destination. Do not place duplicated domain metrics in the global navigation.
- Dialogs and drawers open only when invoked, close with an explicit control and Escape, return focus to the trigger, and preserve page context.
- Secondary actions and advanced filters appear when called or when relevant. Use short, unobtrusive transitions and honour reduced-motion preferences.
- Every interactive element must have a real outcome, a proper accessible label, visible focus, and loading/error/disabled feedback as applicable.
- Empty states should be helpful and calm, with one relevant action—not a large boxed paragraph.
- On phones, prioritise the main task and turn side-by-side layouts into a sensible reading sequence. Avoid fixed-height panels that hide content or make the page feel like a nested app.

## Prohibited shortcuts

No arbitrary metric data, fake recommendations, fabricated live status, fake scores, made-up resident or provider information, or invented property claims. No generic gradient blob in place of real visual storytelling. No sea of same-size cards, nested card-on-card content, random charts, meaningless icons on every line, or excessive uppercase micro-labels. Do not make the UI quieter by hiding information users need; remove duplication and reveal the rest contextually.

## Completion review

Review actual component hierarchy and rendered layouts for resident and HOA roles. A successful build is not visual acceptance. Look at the first viewport at 1440px and 390px, check scrolling and drawer behaviour, and confirm that navigation, permissions, and record actions remain real. Use live data for functional verification; use deterministic fixtures only for visual layout checks and clearly distinguish the two.
