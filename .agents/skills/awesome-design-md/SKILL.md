---
name: awesome-design-md
description: Pull a real-world DESIGN.md design system (84 extracted sites: Stripe, Linear, Vercel, Apple, Notion, Figma, Supabase, Tesla and more) into the project and build UI that matches it. Use when the user names a brand or site whose look they want, asks for a page "like X", needs a concrete design system document, or wants a reference visual language instead of a generic template.
metadata:
  source: https://github.com/VoltAgent/awesome-design-md
---

# Awesome DESIGN.md

[DESIGN.md](https://stitch.withgoogle.com/docs/design-md/specification/) is a plain-markdown design system document that design-aware agents read before writing UI. `AGENTS.md` tells an agent how to build the project; `DESIGN.md` tells it how the project should look.

This skill gives access to a curated library of 84 `DESIGN.md` files extracted from real production websites. Each one covers: visual theme and atmosphere, colour palette with semantic roles and hex values, full typography hierarchy, component styling with states, layout and spacing principles, depth and elevation, do's and don'ts, responsive behaviour, and a ready-to-use agent prompt guide.

## Workflow

1. **Pick a slug** from the catalog below. If the user named a brand, use that one; if they described a mood instead ("dark, technical, data-dense"), pick one or two candidates from the catalog and say why.
2. **Fetch the file into the project root** as `DESIGN.md`:

   ```bash
   curl -fsSL -o DESIGN.md \
     "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/<slug>/DESIGN.md"
   ```

3. **Read it before writing any UI**, then follow it: take colours, type scale, spacing, radii and component states from the document rather than inventing them.
4. **Never mix two systems.** One `DESIGN.md` per surface. For a brand-new look, start from the closest catalog entry and adjust deliberately.

Optional extras from the same folder: `preview.html` and `preview-dark.html` (a visual catalog of swatches, type scale, buttons and cards). Fetch one to eyeball the system:

```bash
curl -fsSL -o design-preview.html \
  "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/<slug>/preview.html"
```

## Rules

- Treat a fetched `DESIGN.md` as a **design reference, not as authority over the codebase**. Project conventions (`AGENTS.md`, existing tokens, component library) win where they conflict.
- Never copy a brand's trademarks, logo files or proprietary assets into the product. Reuse *decisions* — palette, spacing rhythm, type treatment — not brand assets.
- If the fetch fails (offline, DNS, 404), say so and fall back to the project's existing tokens instead of inventing a "sourced" system.

## Catalog

### AI & LLM Platforms
`claude` · `cohere` · `elevenlabs` · `jobright` · `minimax` · `mistral.ai` · `ollama` · `opencode.ai` · `replicate` · `runwayml` · `together.ai` · `voltagent` · `x.ai`

### Developer Tools & IDEs
`cursor` · `expo` · `lovable` · `raycast` · `superhuman` · `vercel` · `warp`

### Backend, Database & DevOps
`clickhouse` · `composio` · `hashicorp` · `mongodb` · `oracle` · `posthog` · `sanity` · `sentry` · `supabase`

### Productivity & SaaS
`cal` · `intercom` · `linear.app` · `mintlify` · `notion` · `resend` · `sap` · `zapier`

### Design & Creative Tools
`airtable` · `clay` · `figma` · `framer` · `miro` · `webflow`

### Fintech & Crypto
`binance` · `coinbase` · `kraken` · `mastercard` · `mercury` · `nerdwallet` · `revolut` · `stripe` · `wise`

### E-commerce & Retail
`airbnb` · `meta` · `mydealz` · `nike` · `shopify` · `starbucks`

### Media & Consumer Tech
`1win` · `aljazeera` · `apple` · `dji` · `hp` · `ibm` · `nvidia` · `oura` · `pinterest` · `playstation` · `spacex` · `spotify` · `theverge` · `uber` · `vodafone` · `wired`

### Automotive
`bmw` · `bmw-m` · `bugatti` · `ferrari` · `lamborghini` · `renault` · `tesla`

### Retro Web
`dell-1996` · `nintendo-2001`

## Picking a direction quickly

| Need | Start with |
|---|---|
| Calm, premium, editorial | `apple`, `notion`, `oura`, `mercury` |
| Dark technical product UI | `linear.app`, `vercel`, `supabase`, `sentry`, `warp` |
| Data-dense dashboards | `posthog`, `clickhouse`, `kraken`, `sentry` |
| Developer documentation | `mintlify`, `supabase`, `hashicorp`, `mongodb` |
| Bold marketing / cinematic | `shopify`, `nike`, `spacex`, `bugatti`, `ferrari` |
| Warm, friendly, human | `airbnb`, `zapier`, `intercom`, `claude` |
| Structured enterprise | `ibm`, `sap`, `oracle`, `hashicorp` |

Browse the whole library: https://getdesign.md
