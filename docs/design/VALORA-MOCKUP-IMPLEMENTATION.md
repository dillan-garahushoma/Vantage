# VALORA resident and HOA mockup implementation

**Status:** In progress on `codex/valora-mockup-faithful-ui`  
**Reference:** `wide_clean_ui_mockup_dashboard_composite_on_a_li.png` (design reference from the working session)

## Visual contract

Treat the split-screen reference as the visual authority for the signed-in workspaces, while using real estate-scoped API data and preserving the existing permissions, routes, forms and operational actions.

### Shared workspace shell
- Use the light lavender canvas and VALORA violet action/selection colour, white surfaces and fine lilac separators.
- Give the left rail enough room for a complete logo, an estate switcher with image thumbnail, a short role-relevant primary menu, and a persistent identity/sign-out area.
- Keep less-frequent destinations available under a collapsible **More tools** group; opening a secondary route should reveal that group.
- The top bar stays compact, with workspace search, notifications, the role-appropriate primary action, and account identity.
- Use architectural imagery as context, not as proof of the actual selected estate. The current `/estate-hero.jpg` remains a temporary asset.

### Resident home
- Lead with a wide, image-led estate banner.
- Follow it with a personal greeting, concise estate context and the primary **Report an issue** action.
- Render requests as status rows with their real status and available unit/category/age data, not a grid of matching cards.
- Give the latest official announcement a lilac editorial treatment with its real title, timestamp and message.
- Show Living Score as a compact summary with a path to Estate Health. Missing scores must remain explicitly unavailable; never coerce them to zero.

### HOA overview
- Open with a personal greeting, then pair an estate image/context panel with the compact Living Score summary.
- Make the primary section a row-based priority queue with issue, priority, actual assigned owner where one exists, and a status-derived next-step label.
- Clicking a row opens the existing, full-featured right-side complaint drawer. Review, assignment, work-order, AI triage, lifecycle and resident/HOA permissions continue to use the existing API-backed component; do not build a decorative dummy drawer.
- Place estate-profile shortcuts, current announcements, work in motion and an operational pulse alongside/below the queue. Figures must come from the current estate-scoped API responses, not illustrative counts.
- Avoid repeated equal-size KPI cards, nested card stacks, and oversized briefings that push urgent work below the fold.

## Non-negotiable functional constraints

- Do not change backend authorization, tenant scoping, status transitions, route guards, or API request contracts to match a screenshot.
- Never add hard-coded resident/estate data, fictional counts, dummy recommendations, fake evidence, or pretend work-order ownership.
- The image shows an issue drawer open to communicate its design. In the product it opens only when a user selects an issue; it does not block the initial dashboard.
- Preserve the public directory, estate selector, account switching, resident registration handoff, global scroll-to-top and both mobile navigation paths.
- Test responsive layout at desktop and mobile; ensure the drawer is keyboard dismissible and the secondary navigation stays discoverable.
