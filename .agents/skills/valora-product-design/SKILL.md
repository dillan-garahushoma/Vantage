---
name: valora-product-design
description: Enforces professional, restrained UI/UX design standards for VALORA to prevent generic AI-generated aesthetics. Use when designing, building, or reviewing React frontend components and pages.
---

# VALORA Product Design & Visual Standards

VALORA is an authoritative, data-driven Property Health Intelligence platform. It serves institutional investors, homeowners, and estate trustees. It must feel like Bloomberg Terminal meets Linear or Stripe — precise, restrained, and trustworthy.

## Anti-Patterns to Strictly Avoid

Do **NOT** implement generic AI-generated SaaS clichés:
- ❌ **No excessive glassmorphism** or gratuitous `backdrop-blur` layered over images.
- ❌ **No random multi-color gradients** on headings, cards, or hero backgrounds.
- ❌ **No arbitrary color blocks** or rainbow dashboards where every metric has a different bright color.
- ❌ **No meaningless card nesting** or box-inside-box layouts without informational necessity.
- ❌ **No cartoonishly oversized border radiuses** (`rounded-3xl` or pill buttons everywhere).
- ❌ **No giant, context-free numbers** floating without labels, units, or comparative context.
- ❌ **No visual noise** or decorative floating badges that distract from tabular and financial data.
- ❌ **No generic SaaS hero sections** filled with vague marketing buzzwords and purple glow spheres.
- ❌ **No heavy, muddy drop shadows** (`shadow-2xl` on every card).

## Architectural Design Principles

1. **Clear Typographic Hierarchy:**
   - Use crisp, legible sans-serif fonts (e.g. Inter, system font stack).
   - Strict size progression: clear distinction between page titles, section headers, metric values, and secondary metadata.
   - Tabular figures (`font-variant-numeric: tabular-nums`) for all financial amounts, dates, and scores.

2. **Deliberate Whitespace & Structure:**
   - Let data breathe. Consistent rhythm (using 4px/8px grid system).
   - Clean divider lines and subtle borders (`border-slate-200` / `border-slate-800`) over heavy card shadows.

3. **Semantic Color System:**
   - Neutral palette: Slate/Zinc greys for structure and typography.
   - Purposeful accent: Single primary brand tone (navy/deep slate blue).
   - Functional state colors only: Emerald/Green for healthy/resolved, Amber for pending/warning, Rose/Red for critical/sla-breached. Colors convey status, never mere decoration.

4. **Data Clarity & Information Density:**
   - High information utility: Compact data tables, clear status tags, concise event timelines.
   - Numbers must always provide context: current value, change over 90 days, benchmark target, or percentiles.

5. **Accessibility & Responsiveness (WCAG AA):**
   - High contrast ratios (minimum 4.5:1 for body text).
   - Keyboard accessible navigation, visible focus rings (`focus-visible`).
   - Seamless responsive layout across desktop, tablet, and mobile views.
