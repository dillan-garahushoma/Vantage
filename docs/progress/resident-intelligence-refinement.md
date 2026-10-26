# VALORA Intelligence — resident guidance refinement

## Scope
Refine the existing VALORA Intelligence experience with a resident-specific, evidence-grounded journey while preserving HOA and service-provider access boundaries.

## Implemented
- Extracted deterministic resident intent handling for personal request status, request filtering by ID, open/resolved requests, repair-timeline questions, new-issue reporting, missing unit/access questions, published notices, Living Score availability, emergency guidance, and unsupported questions.
- Kept resident answers limited to the authenticated resident's own request records and information returned by the estate's announcement/score repositories. The fallback path does not query estate-wide operational aggregates.
- Expanded the resident LLM system guidance with the real complaint-reporting flow, explicit no-invented-ETA/policy rules, emergency guidance, and private-data boundaries.
- Made streaming provider/network errors end with a generic, non-sensitive SSE error instead of leaking upstream exception detail.
- Prevented the current question from being included twice in the LLM history; only previous user questions are replayed, not untrusted assistant output.
- Restricted the resident Living Score repository read to snapshots marked `published`.
- Updated resident prompts and rebuilt the resident Intelligence composition around their requests, report action, community health availability, and published estate notices. Removed fabricated recent-conversation entries, invented location/unit counts, fake work-order/complaint links, and hard-coded fallback metrics.
- Kept the HOA briefing/history and evidence/recommendation workbench role-specific. Providers get the assistant without HOA-only panels.
- Added backend intent/security tests, frontend resident-role tests, and updated the browser assertion for the corrected empty state.

## Validation
- Tests were added/updated but **not run in this GitHub-only editing session**.
- Required CI commands: frontend Vitest suite; backend pytest for `test_intelligence_security.py`, `test_resident_intelligence_guidance.py`, and `test_intelligence_contract.py`; frontend Playwright `intelligence.spec.js`.
- Live LLM-provider behavior and deployed environment configuration still require a real configured deployment smoke test. The application does not claim that a provider is available merely because the UI is present.

## Remaining risks / review notes
- Announcements currently have no explicit publication-state column in the model; repository semantics treat non-expired estate announcement records as visible. If draft/unpublished announcements are introduced, add a persisted publication field and filter it at the repository boundary.
- Confirm that the deployed Living Score writer consistently uses `status='published'` before releasing the new resident query filter.
- Browser screenshots at mobile/tablet/desktop widths remain to be reviewed.
