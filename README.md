# Visual UX Review Toolkit

Adversarial **UI/UX review skills for AI coding agents** (Claude Code, Codex, Cursor, Gemini, …). Point them at a running app and they review how it actually *looks* and *works* — not by reading the diff, but by driving a real browser, measuring the rendered page, and judging it as a skeptical designer and a confused first-time user would.

Two complementary skills:

| Skill | Lens | What it does |
|-------|------|--------------|
| **`visual-ux-review`** | Per-screen (does it *look* right?) | Screenshots a page at 5 breakpoints, measures every interactive element's geometry, audits font sizes and contrast, clicks every sort/filter/tab to catch layout jumps, then adversarially critiques the rendered UI. Emits an **annotated HTML/PDF report** with boxes drawn on the screenshots. |
| **`ux-flow-walkthrough`** | Journey (does it *make sense*?) | Drives the app as a clueless first-timer, one click at a time, running an automated **cognitive walkthrough** to find friction, dead-ends, and confusing flows. Three modes: goal-directed, free-explore, and exhaustive auto-explore. |

They're deliberately separate — a per-screen geometry critique and a click-through journey test are different jobs. Together they cover the full UI/UX surface.

> Code review reads the diff; it can't see that a back arrow renders at 22px, that chips reflow when clicked, or that a first-timer can't find the "next" button. These skills close that gap.

---

## Requirements

- **Any agent harness with a browser MCP** exposing JS-evaluate + full-page screenshot — [Playwright MCP](https://github.com/microsoft/playwright-mcp) recommended (same one-line setup on Claude Code, Codex, Cursor, Gemini, …); the [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) also works.
- A **running app** reachable at a URL. Any framework, any port (Vite, Next.js/CRA, Angular, Vue/Nuxt, a deployed `https://` URL — the skills only need a URL).
- For the **annotated reports** (optional): Python 3.8+ with [Pillow](https://pypi.org/project/Pillow/) for annotated PNGs, and Chrome or Edge for PDF export (with [reportlab](https://pypi.org/project/reportlab/) as a no-browser fallback).

## Install

### Any agent (Claude Code, Codex, Cursor, Gemini, OpenCode, …)

```text
npx skills add averliz/visual-ux-review-toolkit
```

Installs both skills via the open [`npx skills`](https://github.com/vercel-labs/skills) tool. Add
`--skill visual-ux-review` (or `ux-flow-walkthrough`) to install just one. Tested with `skills`
1.5.13.

### Claude Code plugin (native slash commands + marketplace)

```text
/plugin marketplace add averliz/visual-ux-review-toolkit
/plugin install ui-ux-review@visual-ux-review-toolkit
```

Either way, invoke by name (`visual-ux-review`, `ux-flow-walkthrough`) or just describe what you want.

> **Requires a browser driver.** The skills measure a live page via a browser tool — Playwright MCP
> recommended (`npx @playwright/mcp@latest`), Chrome DevTools MCP also works. With no driver they
> stop and tell you how to enable one; they never fabricate measurements. See each skill's
> `references/browser-tools.md`.

## Usage

### Per-screen visual review

```text
review the UI of /settings on localhost:3000 — the buttons feel too small on mobile
```

It captures 5 breakpoints, measures geometry, runs the checks, critiques the screenshots, and offers an annotated report. Point it at a PR and it reviews just the changed screens:

```text
review the screens PR #42 changed
```

### Naive-user flow walkthrough

```text
# goal-directed
walk through the sign-up flow as a confused first-time user and tell me where they'd get stuck

# free-explore
click around localhost:3000 like a newcomer and find what's confusing

# exhaustive / adversarial
do a full auto-explore of the app — try every flow, mis-submit forms, hit back mid-flow — and report every dead-end
```

### As a review step in a workflow

Both are built to slot into a review chain after code review — where code review can't see spatial/journey problems:

```text
For PR #42: run your cleanup and simplify pass, then your code review and fix issues,
then visual-ux-review and address findings,
then ux-flow-walkthrough on the main flow,
then test the e2e flow.
```

## Reports

`visual-ux-review` can emit a shareable report in three forms from one findings file (`ux-flow-walkthrough` can reuse the same generator with journey steps as pages):

- **`report.html`** — interactive: page switcher, breakpoint tabs, bounding-box overlays, per-finding 👍/👎 + comments, "Export feedback" → JSON.
- **`report.pdf`** — shareable: cover + summary, then each finding as a card with a **focused, captioned crop** beside its text (rendered via headless Chrome/Edge, reportlab fallback).
- **`<page>-<bp>px-annotated.png`** — boxes burned into the screenshots.

```bash
python skills/visual-ux-review/scripts/generate_report.py \
  --findings findings.json --screenshots-dir . --out-dir ux-report
```

See [`skills/visual-ux-review/references/report-schema.md`](skills/visual-ux-review/references/report-schema.md) for the findings format (single-page and multi-page).

## How it works

- **No framework awareness.** Capture is DOM-level (`querySelectorAll` / `getComputedStyle` / `getBoundingClientRect`) run in the browser against the rendered page — identical whether it came from Vite, Angular, or server-rendered HTML.
- **Mechanical + perceptual.** Geometry, font sizes, overflow, and layout-shift are measured deterministically; the subjective "does this look/feel right" is a vision/persona pass on top.
- **Adversarial by default.** `visual-ux-review` assumes every pixel is suspect; `ux-flow-walkthrough` assumes the user is confused. That's where the real findings come from.

## Compatibility

- **Harness-agnostic.** Installable on any agent via `npx skills`; the skill bodies are written in a
  neutral browser-**capability** vocabulary (navigate / set-viewport / evaluate-js / screenshot /
  accessibility-snapshot / click) mapped per harness in each skill's `references/browser-tools.md`.
- **Driver:** Playwright MCP recommended (works the same on every harness); Chrome DevTools MCP
  mappings are best-effort. No driver ⇒ the skill stops cleanly rather than guessing.
- The Claude Code plugin path remains for native slash commands.

## License

[MIT](LICENSE) © Jeremy Teo
