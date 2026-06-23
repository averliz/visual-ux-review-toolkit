# Findings JSON Schema

The `generate_report.py` script consumes a `findings.json` file. Write it after Phase 3, then run the generator. Two shapes are supported: **single-page** and **multi-page**.

> The `url` in the examples below is just illustrative — it can be **any** address the page is served at (Vite `:5173`, Next.js/CRA `:3000`, Angular `:4200`, a deployed `https://` URL, …). Neither the skill nor the generator cares about the port or framework.

## Single-page (one URL)

```json
{
  "title": "Visual UX Review — Settings",
  "url": "http://localhost:5173/settings",
  "timestamp": "2026-01-15 11:42 GMT+8",
  "screenshots": {
    "320": "review-320px.png",
    "375": "review-375px.png",
    "768": "review-768px.png",
    "1024": "review-1024px.png",
    "1440": "review-1440px.png"
  },
  "findings": [
    {
      "id": "C1",
      "severity": "critical",
      "title": "Back arrow link is dangerously undersized",
      "element": "Back arrow link in page header",
      "breakpoint": "320",
      "box": { "x": 16, "y": 138, "w": 22, "h": 36 },
      "issue": "The back navigation is a single ← character with a 22×36px clickable area — fails WCAG AA (24px) and Apple HIG (44px).",
      "evidence": "width=22px height=36px, threshold=44px",
      "fix": "Wrap in a 44×44px inline-flex button with centered icon."
    }
  ]
}
```

## Multi-page (review several screens at once)

Use a top-level `pages` array. Each page has its own `name`, `url`, `screenshots`, and `findings`. The interactive HTML gets a page-switcher strip, assets are namespaced per page (`<page-slug>-<bp>px-annotated.png`), and the MD/PDF get a chapter per page.

```json
{
  "title": "Visual UX Review — my app",
  "timestamp": "2026-01-15 12:25 GMT+8",
  "pages": [
    {
      "name": "Settings",
      "url": "http://localhost:5173/settings",
      "screenshots": { "320": "settings-320px.png", "1440": "settings-1440px.png" },
      "findings": [ /* ... */ ]
    },
    {
      "name": "Checkout",
      "url": "http://localhost:5173/checkout",
      "screenshots": { "320": "checkout-320px.png", "1440": "checkout-1440px.png" },
      "findings": [ /* ... */ ]
    }
  ]
}
```

Each page can list a different set of breakpoints — the HTML's breakpoint tabs adapt per page.

## Verdict & summary are auto-derived

`verdict` and `summary` are **optional** — the generator derives them from the findings (`SHIP` = 0 crit/0 high; `SHIP WITH FIXES` = 0 crit, 1–3 high; `BLOCK` = any crit or 4+ high). The overall verdict is the worst across pages. Provide them explicitly only to override; if you do, keep them consistent with the findings.

## Field reference

For multi-page, `url`, `screenshots`, and `findings` move inside each `pages[]` entry (which also needs a `name`); `title` and `timestamp` stay top-level.

| Field | Required | Notes |
|-------|----------|-------|
| `title` | yes | Report heading |
| `timestamp` | yes | Human-readable, include timezone |
| `url` | yes | Page reviewed (per page in multi-page form) |
| `verdict` | no | Auto-derived from findings; provide only to override (`SHIP` / `SHIP WITH FIXES` / `BLOCK`) |
| `summary` | no | Auto-derived counts per severity |
| `pages[]` | multi-page | Array of `{name, url, screenshots, findings}`; omit for single-page |
| `pages[].name` | yes (multi) | Page label shown in the switcher; also the asset filename slug |
| `screenshots` | yes | Map of breakpoint (string) → PNG filename, relative to `--screenshots-dir` |
| `findings[]` | yes | One per issue |
| `findings[].id` | yes | `C1`, `H2`, `M3`, `L1` — severity letter + number |
| `findings[].severity` | yes | `critical` / `high` / `medium` / `low` |
| `findings[].title` | yes | One-line summary |
| `findings[].element` | yes | What element |
| `findings[].breakpoint` | yes | Primary breakpoint for the box, as a string. Can be comma-separated (`"320,375"`) — the box is drawn on each listed breakpoint's screenshot |
| `findings[].box` | optional | `{x, y, w, h}` in **document-relative CSS pixels** (NOT viewport-relative — see below). Omit for findings with no single element (e.g. "overall spacing rhythm") |
| `findings[].issue` | yes | What's wrong |
| `findings[].evidence` | optional | Measurement or observation, rendered as code |
| `findings[].fix` | optional | Concrete remediation |

## CRITICAL: box coordinates must be document-relative

`getBoundingClientRect()` returns **viewport-relative** coordinates. Full-page screenshots are **document-relative**. For a box on an element below the fold to land correctly, add the scroll offset:

```js
const r = el.getBoundingClientRect();
const box = {
  x: Math.round(r.left + window.scrollX),
  y: Math.round(r.top + window.scrollY),
  w: Math.round(r.width),
  h: Math.round(r.height)
};
```

Capture geometry at `scrollY = 0` and add `window.scrollY` (which is 0), OR capture after any scroll and the offset corrects it. The screenshots are taken with `scale: 'css'`, so 1 CSS px = 1 image px — coordinates map 1:1, no DPR scaling needed.

## Output

```bash
python scripts/generate_report.py \
  --findings findings.json \
  --screenshots-dir <dir with review-*.png> \
  --out-dir <report output dir>
```

Produces:
- `report.html` — interactive (page switcher, breakpoint tabs, box overlays, agree/disagree + comments, "Export feedback" → JSON)
- `report.md` — Markdown, one chapter per page
- `report.pdf` — shareable PDF (rendered via headless Edge/Chrome; falls back to reportlab if no browser, then to `report-print.html` you can print manually)
- `<page-slug>-<bp>px-annotated.png` — boxes burned into the screenshots (needs Pillow)

Control output with `--format` (default `html,md,png,pdf`), e.g. `--format html,pdf`.

## PDF rendering notes

- The PDF is built from a print-optimized `report-print.html` (cover + summary table + per-page chapters), rendered by headless Chrome/Edge `--print-to-pdf`.
- **Per-finding focused crops, not full-page screenshots.** A full-page mobile screenshot is ~1:8 aspect — embedding it whole makes it span several pages, read poorly, and strand chapter headings on near-empty pages. Instead each finding with a `box` gets a short crop (the box ± ~70px vertical context) drawn with its numbered box, shown **side-by-side with the finding text** and an italic **caption** (`[n] element — bpx`). Findings without a box render as text-only cards. This follows print-report best practice (legible focused figures, captions, controlled whitespace, keep-figures-whole via `page-break-inside: avoid`). Wide desktop crops (source ≥600px) stack above the text instead of beside it.
- The full-page annotated PNGs are still emitted as separate files and power the HTML overlays; the PDF just doesn't embed them whole.
- The generator auto-detects a browser at the common Windows paths or on `PATH`; set `CHROME_BIN`/`EDGE_BIN` to override.
- If no browser is found, it falls back to **reportlab** (pure Python, same crop-beside-text card layout). If that's also missing, `report-print.html` is still written for manual printing.
