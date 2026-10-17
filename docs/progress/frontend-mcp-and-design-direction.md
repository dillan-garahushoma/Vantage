# Progress — Frontend design research + MCP tooling

**Type:** Ad-hoc request (outside the `batches/` flow — no batch file was assigned).
**Date:** 10 October 2026

## Done
- Researched design taste for VALORA: prop-tech UI boards (Dribbble property
  management / real-estate UI) and the 2026 retro/brutalist/Y2K movement.
- Wrote the direction doc: [`docs/design/VALORA-DESIGN-DIRECTION.md`](../design/VALORA-DESIGN-DIRECTION.md)
  → *"Calm Intelligence, Technical Edge"*, 80% clean prop-tech / 20% retro-technical signature,
  with tokens, screen guidance, motion/accessibility rules, and do/don't.
- Found and wired four **free, no-API-key** frontend/design MCP servers in
  [`.agents/mcp.json`](../../.agents/mcp.json): `playwright`, `chrome-devtools`, `shadcn`, `context7`.

## Verified (ran it, saw the output)
- `npm`/`npx`, Node v24, uv/uvx, Python 3.12, Docker all present.
- Registry lookup: `@playwright/mcp@0.0.83`, `chrome-devtools-mcp@1.10.1`, `shadcn@4.21.4`,
  `@upstash/context7-mcp@4.3.0`, `figma-developer-mcp@0.13.2` all published.
- `npx @playwright/mcp@latest --help` → exit 0. `npx chrome-devtools-mcp@latest --help` → exit 0.
- `printf '' | npx chrome-devtools-mcp@latest --headless --isolated` → started, printed banner, no browser error.
- `printf '' | npx @upstash/context7-mcp@latest` and `... shadcn@latest mcp` → ran and waited on stdin (exit 124 = timeout kill, i.e. started fine).
- `.agents/mcp.json` parses as valid JSON. Playwright browsers already cached (`ms-playwright/chromium-1243`).

## Written, not run
- No frontend exists in this repo, so no UI was built or tested.
- The MCP servers are **not** active in the current session; Freebuff loads `.agents/mcp.json`
  at startup, so **reload/restart the app** and launch from inside the repo for them to appear.

## Deviations / notes
- `@21st-dev/magic` is now only a deprecated compatibility proxy → skipped.
- `figma-developer-mcp` needs a free Figma API token → documented as optional, not enabled.
- Only Microsoft Edge is installed (no Chrome); `playwright` is pinned to bundled `chromium`.
  Chrome DevTools MCP downloads Chrome for Testing on first use if no Chrome is found.
- `--no-usage-statistics --no-performance-crux` added to Chrome DevTools for privacy.

## Open questions
- Accent colour (estate green vs bolder SA accent), how much retro edge on login/signup,
  and charting library choice (Chart.js vs Recharts) — see the design doc, section 8.

## Commands run (exact, with result)
```
npx @playwright/mcp@latest --help                                   # exit 0
npx chrome-devtools-mcp@latest --help                               # exit 0
printf '' | npx chrome-devtools-mcp@latest --headless --isolated    # started, banner only
printf '' | npx @upstash/context7-mcp@latest                        # started (exit 124 = timeout)
printf '' | npx shadcn@latest mcp                                   # started (exit 124 = timeout)
python -c "import json;json.load(open('.agents/mcp.json'))"         # valid JSON
```
