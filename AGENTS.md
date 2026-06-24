# AGENTS.md

Notes for coding agents working **on this repo**. Runtime instructions for *using* the review skills
live in each skill's `SKILL.md`, not here.

## What this is
Two harness-agnostic skills for adversarial UI/UX review of a live page:
- `skills/visual-ux-review/` — per-screen visual/geometry/a11y critique + annotated report.
- `skills/ux-flow-walkthrough/` — naive-user journey / cognitive walkthrough.

## Install (both channels supported)
- Any harness:  `npx skills add averliz/visual-ux-review-toolkit`
- Claude Code:  `/plugin marketplace add averliz/visual-ux-review-toolkit` → `/plugin install ui-ux-review@visual-ux-review-toolkit`

## Layout
- `skills/<name>/SKILL.md` — the skill (capability-based, harness-neutral).
- `skills/<name>/references/` — thresholds, methods, and `browser-tools.md` (driver mapping + gate).
- `skills/visual-ux-review/scripts/generate_report.py` — HTML/MD/PDF report generator.

## Browser driver
Skills drive a live page via six capabilities mapped in each skill's `references/browser-tools.md`.
Playwright MCP is the default (`npx @playwright/mcp@latest`). No driver ⇒ the skill emits
`BROWSER_DRIVER_MISSING` and stops; it never fabricates measurements.

## Verify before publishing
- `node scripts/verify-skills.mjs` — both skills discovered by `npx skills`; the two
  `browser-tools.md` are byte-identical.
- `python -m pytest tests/` — report generator tests pass.
- Keep the two `references/browser-tools.md` byte-identical (the verify script enforces this).
