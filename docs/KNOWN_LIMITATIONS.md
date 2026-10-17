# KNOWN LIMITATIONS

Everything here is a known, accepted gap in this build. It is written so that
nobody discovers a limitation during a sales conversation or, worse, during a
pilot. Each item says what it means in practice and what the current workaround
is. Nothing in this list is a test failure — the tests that exist pass; these are
things that are not built.

## Accounts and access

1. **No email of any kind.** There is no address verification, no invitation
   email, no "forgot password" email, and no notification email. A resident who
   self-registers can use the account immediately (their address is unverified),
   and a locked-out account is recovered by an operator running
   `backend/scripts/reset_password.py --email … --apply`, which prints a new
   password once. That is the interim: a real deployment needs a transactional
   email provider before it can call itself self-service.
2. **Public registration creates residents only.** An estate administrator
   account creates a new estate; a service provider account cannot join an estate
   by itself — an HOA administrator adds a provider by email, and only a provider
   who already has a linked provider profile can be added.
3. **An HOA administrator cannot change a member's unit or role, or add a
   resident by email.** The API has no endpoint for any of those, so the members
   screen says so rather than offering a dead end. Moving a resident between units
   means removing and re-joining.
4. **Removing a member does not revoke a join code they hold.** Removal ends
   their membership; a live code they copied earlier still works until it is
   rotated. The removal drawer states this and points at rotation.

## Deployment and operations

5. **No HTTPS and no hosting story.** `docker compose` is a local development and
   demonstration stack: plain HTTP, one API process, one Postgres, one static
   frontend. Nothing here has been hardened for the public internet, and there is
   no TLS anywhere in the repository.
6. **No automated backups, no monitoring, no log aggregation.** The pilot runbook
   documents a backup procedure; it has never been run against a real database
   (it says so itself).
7. **Rate limiting is single-process, in-memory state.** Login attempts and join
   attempts are limited per account within this process (5 per 15 minutes). A
   restart clears the counters, and two API processes would each keep their own;
   the limiter is a brake against guessing, not a security control.
8. **Uploads live on local disk** (`UPLOAD_DIR`, default `backend/uploads`). That
   is single-host storage: a second API instance would not see the first one's
   photographs, and nothing replicates the directory.
9. **No malware or content scanning on uploads.** Images are decoded with Pillow,
   re-encoded, size- and pixel-capped, EXIF/GPS-stripped, and stored under a
   random name — but nobody inspects their contents. A hostile image inside the
   format limits is stored like any other.

## Privacy and data

10. **Public photo links are unlisted, not private.** A photograph is served by an
    unguessable `public_id` and the response is cacheable for an hour; the rule
    that "a photo of an unpublished estate is still reachable by whoever holds the
    link" is a deliberate, recorded open question, not an accident. Do not upload
    a photograph that must not leave the estate.
11. **The AI layer has never been run against a real provider in this checkout,
    and never against real personal data.** Its wiring is tested with a
    deterministic fake provider; the switch to Gemini is documented in
    [GETTING_STARTED.md](GETTING_STARTED.md). Triage (which sends a person's own
    words to a third party) additionally requires `AI_PERSONAL_DATA_ALLOWED=true`,
    and must stay off for real residents until the pilot runbook's AI checklist
    has been worked through.
12. **The POPIA review is pending.** There is no record of the formal
    privacy-impact assessment, no data-processing agreement with any provider, and
    no retention schedule for complaints, photographs or AI call records. Treat
    the pilot runbook's POPIA checklist as the work to do, not as work done.

## Quality gates

13. **No linter and no accessibility tooling in CI.** The repository runs
    `compileall` and a targeted `flake8` (`E9,F63,F7,F82`) over the backend, and
    the frontend has a typecheck, unit tests and Playwright specs — but there is
    no ESLint, no style formatter, and no axe/Lighthouse pass. Accessibility is a
    design intent in the components (real labels, focus management, aria
    attributes, contrast-checked tokens), not a measured property of the app.
14. **No performance or load testing.** The demo database holds one estate with
    ~40 complaints; nobody has measured the app with thousands of complaints,
    hundreds of units or two hundred concurrent residents.

## Product edges

15. **The Living Score needs a scored snapshot and at least part of the estate's
    history to be measurable.** A brand-new estate legitimately shows "not enough
    data yet" instead of a number; it is not a bug. A score only moves when
    somebody (or a scheduled job) recalculates it — the API never computes on read.
16. **Provider reviews are legacy-gated.** The "rate a provider" HTTP routes are
    behind `ENABLE_LEGACY_ROUTES` (off by default); the resident↔provider sharing
    rule is enforced in the service and tested there. The shipped UI lets a
    resident rate a *completed work order*, which is what feeds the score.
17. **GIF uploads are refused, and an animated WebP is stored as its first
    frame.** Both are untested behaviours rather than decisions with test
    evidence behind them.
18. **Estate names are not editable** through the profile endpoint; only the
    description, the two publish switches and the photographs are.
