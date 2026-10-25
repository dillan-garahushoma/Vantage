# Implementation Plan: VALORA Experience Completion & Intelligence UI Overhaul

## 1. Overview & Objective

Deliver the completed VALORA experience by integrating and finalizing the upgrades from the active feature worktrees while preserving VALORA's established South African private-estate visual identity:
1. **Multi-step Estate Onboarding Flow**: Complete 3-step registration for HOA administrators (Step 1: Account credentials, Step 2: Estate details, Step 3: Review & confirmation).
2. **VALORA Intelligence UI Overhaul**: Implement the approved high-fidelity 3-column AI workbench matching the design reference (`valora-intelligence-design-reference.png`).
3. **Core UX & Interaction Fixes**:
   - Resolve message click / Enter auto-scroll defect by constraining scroll to the chat viewport container instead of scrolling the whole window.
   - Eliminate frame cut-off and clipping by using a full-height flex-col workspace layout.
   - Automatic full-view mode transition on Enter press or question submit.
   - Rich interactive AI features: Key finding callouts, 2-column Evidence vs. Impact breakdown, numbered actionable next steps, interactive "Explore further" follow-up prompt chips, feedback actions (helpful / not helpful), copy-to-clipboard, and expandable Sources (N) citations linking to estate records.
   - Contextual sidebars: Left sidebar for Recent Conversations & deep insights teaser; Right sidebar for Live Estate Context (KPIs, Living Score deltas, and Related Documents).

---

## 2. Architectural & Component Breakdown

```
VALORA Intelligence Experience
 ├── Top Hero Header: Banner, Title, Estate panorama thumbnail, "Powered by AI" badge
 ├── 3-Column Workbench Layout:
 │    ├── Left Sidebar (280px):
 │    │    ├── "Recent conversations" thread list (active state, time ago, title, preview)
 │    │    └── "Get deeper insights" prompt/sample teaser card
 │    │
 │    ├── Center Conversational Canvas (Flexible):
 │    │    ├── Active Question Header / Box with context & estate selector
 │    │    ├── Interactive AI Response Stream:
 │    │    │    ├── Key Finding Callout (highlight banner with alert icon)
 │    │    │    ├── 2-Column Matrix ("What the evidence shows" & "Why it matters")
 │    │    │    ├── Recommended Next Steps (numbered actionable items)
 │    │    │    ├── Explore Further (clickable interactive query prompt pills)
 │    │    │    ├── Feedback & Action Toolbar (thumbs up, thumbs down, copy, share)
 │    │    │    └── Sources (N) Drawer / Accordion (underlying WO/Complaint/Score citations)
 │    │    └── Sticky / Fixed Bottom Input Bar (Sparkle prompt input, attachment trigger, send)
 │    │
 │    └── Right Intelligence Context Drawer (300px):
 │         ├── Tabs: [Context] [Evidence] [Related]
 │         ├── Active Estate Profile Card (photo, name, suburb/city, status, unit count)
 │         ├── Key Operational Metrics Card (Living Score, Open Complaints, Work Orders with deltas)
 │         ├── Related Documents Quick Links (Work orders, Complaint logs, Maintenance plans)
 │         └── "Need something else?" New Chat trigger card
```

---

## 3. Worktree Integration Strategy

1. **`estate-onboarding-multistep-flow`**:
   - Step 1: HOA account details (name, email, password, phone).
   - Step 2: Estate profile (name, suburb, city, province dropdown with empty placeholder option, description).
   - Step 3: Review card & confirm creation.
   - Integration status: Tested and validated on `main-publish` (`Register.test.jsx` 12 passed).

2. **`valora-intelligence-redesign-ux`**:
   - Replaces window `scrollIntoView` with viewport `scrollTop = scrollHeight`.
   - Passes role context to AI renderer for role-safe operational suggestions.
   - Integrate into unified `Intelligence.jsx` route.

3. **`requesting-help-assistance`**:
   - Ensure clean merge without regressing live estate migrations or non-compulsory unit access requests.

---

## 4. Quality & Verification Gates

- **Frontend Tests**: `npx vitest run src/routes/Intelligence.test.jsx src/routes/Register.test.jsx src/routes/RequestAccess.test.jsx`
- **Backend Tests**: `pytest backend/tests -q`
- **Compile & Lint**: `flake8 backend/app backend/tests` and `compileall -q backend/app`
- **Browser Verification**: Real headless browser check of Intelligence workbench, Enter full-view trigger, and interactive pill clicks.
