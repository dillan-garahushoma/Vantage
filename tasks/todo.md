# Task List: VALORA Experience Upgrades & Intelligence Redesign

## Core Tasks

- [x] **Task 1: Un-archive live estates and restore production database visibility**
  - **Description**: Add reversible Alembic migration `e8c3a1f9d5b7_restore_live_estates.py` to restore the 5 live estates (`Eastbank Court`, `Lakeside Gardens`, `Quarry View Flats`, `Silverleaf Reserve`, `Willowbrook Mews`) with `is_demo=false`, `is_public=true`, `show_living_score=true`.
  - **Verification**: `python -m pytest backend/tests/test_restore_live_estates_migration.py` passed (2/2); live Render API returns 5 estates.

- [x] **Task 2: Wire residence access request without compulsory unit numbers**
  - **Description**: Update `RequestAccess.jsx` so that unit numbers are optional. Provide explicit "Request approval without a unit number" actions, handle 404 unit not found fallback.
  - **Verification**: `npx vitest run src/routes/RequestAccess.test.jsx` passed (10/10).

- [x] **Task 3: Integrate and verify multi-step estate onboarding**
  - **Description**: Ensure HOA registration multi-step flow (Account -> Estate details -> Review & Create) from `estate-onboarding-multistep-flow` has valid province selection and state retention.
  - **Verification**: `npx vitest run src/routes/Register.test.jsx` passed (12/12).

- [ ] **Task 4: Fix VALORA Intelligence scroll and viewport clipping defects**
  - **Description**: In `AskValora.jsx` and `Intelligence.jsx`:
    - Fix scrolling defect: Replace `scrollIntoView` with constrained `viewport.scrollTop = viewport.scrollHeight` so clicking/typing does not scroll the outer page.
    - Fix frame cut-off: Provide responsive full-height viewport container with proper overflow rules.
    - Auto Full-View Mode: Automatically expand / enter full view mode when Enter is pressed or a message is submitted.
  - **Acceptance Criteria**:
    - [ ] No outer window jumps or scrolls when Enter is pressed.
    - [ ] AI conversation frame occupies full available viewport without clipping.
    - [ ] Pressing Enter in compact spotlight or in-feed prompt seamlessly transitions to full workbench mode.
  - **Verification**: `npx vitest run src/components/valora/AskValoraSpotlight.test.jsx`

- [ ] **Task 5: Overhaul VALORA Intelligence UI to match approved 3-column reference design**
  - **Description**: Rebuild `Intelligence.jsx` and subcomponents to match the uploaded reference design (`valora-intelligence-design-reference.png`):
    - Top Hero Banner with estate panorama and "Powered by AI" badge.
    - Left column: Recent conversations list with active indicators, timestamps, and "Get deeper insights" promo card.
    - Center column: Main interactive canvas with active question box, rich structured AI response, and fixed bottom input bar.
    - Right column: Context & Intelligence drawer with tabs [Context] [Evidence] [Related], active estate summary, live KPI cards (Living Score, Open Complaints, Work Orders) with deltas, related documents, and "Start new chat" CTA.
  - **Acceptance Criteria**:
    - [ ] Exact visual alignment with reference image layout and VALORA house styling.
    - [ ] Conversation switcher updates active thread in center and right context panel.
    - [ ] Estate metrics display authoritative Living Score and complaints data.
  - **Verification**: `npx vitest run src/routes/Intelligence.test.jsx`

- [ ] **Task 6: Extend AI interactivity & rich answer structures**
  - **Description**: Enhance `AiAnswerRenderer.jsx` and interactive widgets:
    - Key finding highlighted banner with alert icon.
    - 2-column matrix: "What the evidence shows" vs "Why it matters".
    - Numbered "Recommended next steps" with action links.
    - Interactive "Explore further" follow-up query chips that submit on click.
    - Feedback toolbar (thumbs up, thumbs down, copy to clipboard with toast, share).
    - Expandable "Sources (N)" citation accordion listing underlying records.
  - **Acceptance Criteria**:
    - [ ] Clicking an "Explore further" chip submits that follow-up question to the assistant.
    - [ ] Thumbs up/down records feedback state optimistically.
    - [ ] Copy button copies structured answer text to clipboard.
    - [ ] Expandable sources accordion displays cited estate documents.
  - **Verification**: `npx vitest run src/components/valora/AiAnswerRenderer.test.jsx`

- [ ] **Task 7: Comprehensive regression test pass & production deployment**
  - **Description**: Run full test suites across frontend and backend, commit changes to `main`, push to origin, and verify deployed application in browser.
  - **Verification**:
    - [ ] Backend pytest: 843+ passed, 0 failed.
    - [ ] Frontend vitest: all suites passed.
    - [ ] Live browser verification of `/intelligence`, `/register`, and `/request-access`.
