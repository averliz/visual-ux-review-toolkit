# npx skills Harness-Agnostic Port — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Onboard the two skills onto `npx skills` and make them verifiably harness-agnostic, with a hard gate that prevents fabricated reviews when no browser driver is present.

**Architecture:** The skills already live at `skills/<name>/SKILL.md` (discoverable by `npx skills` as-is). We (1) neutralize Claude-specific tool references in the two SKILL.md bodies into a closed **capability** vocabulary, (2) add a per-skill `references/browser-tools.md` (driver mapping + detection + a `BROWSER_DRIVER_MISSING` stop-gate), (3) add report provenance, (4) fix two shipping bugs, and (5) add docs + a `verify-skills` check. No new runtime dependencies; no own CLI.

**Tech Stack:** Markdown skills; Python 3.8+ (`generate_report.py`, Pillow/reportlab); Node (`npx skills`, a small ESM verify script); pytest for the one Python test.

## Global Constraints

- Repo / install slug: **`averliz/visual-ux-review-toolkit`** (verified from git remote).
- Skill frontmatter stays **exactly `name` + `description`** — do NOT add `allowed-tools`, `user-invocable`, or other fields.
- SKILL.md **bodies must name NO concrete browser tool**; all tool names live only in `references/browser-tools.md`. (Grep target: zero `mcp__` anywhere in a SKILL.md.)
- The two `references/browser-tools.md` copies must be **byte-identical**.
- Recommended default driver: **Playwright MCP** (`npx @playwright/mcp@latest`). Non-Playwright mappings ship marked `UNVERIFIED` unless confirmed against that tool's docs.
- Capability vocabulary (closed set, exact spelling): `navigate`, `set-viewport`, `evaluate-js-in-page`, `screenshot`, `accessibility-snapshot`, `click`.
- Keep universal CLI references as-is (`gh pr diff`, `git diff`, `python …/generate_report.py`, axe `.withTags`).
- Reference docs other than `report-schema.md`, and `marketplace.json`, are unchanged.
- Nothing is committed to `main`: do all work on branch `feat/npx-skills-harness-agnostic` (created in Task 0). Commit after each task.
- Tests/checks live at **repo root** (`tests/`, `scripts/`), never inside `skills/<name>/` (those dirs ship to users).

---

### Task 0: Branch + recon the `npx skills` contract

De-risks the central assumption (local-path discovery) before anything depends on it.

**Files:**
- None modified. Produces: the confirmed list command string, used in Tasks 4 & 8.

- [ ] **Step 1: Create the working branch**

```bash
git checkout -b feat/npx-skills-harness-agnostic
```

- [ ] **Step 2: Confirm the CLI exists and inspect its flags**

```bash
npx -y skills@latest --help
```
Expected: help text listing an `add` subcommand with `--list` and `--skill` flags. Note the installed version (run `npx -y skills@latest --version`) — record it for the README "tested with" line.

- [ ] **Step 3: Confirm local-directory discovery lists BOTH skills**

```bash
npx -y skills@latest add . --list
```
Expected: output mentions both `visual-ux-review` and `ux-flow-walkthrough`.
If `add .` is rejected for local paths, try `npx -y skills@latest add ./ --list` then `npx -y skills@latest list`; record whichever form lists both skills as **`<LIST_CMD>`** for use in later tasks. If none work locally, fall back to the remote form in Step 4 as `<LIST_CMD>` and note the limitation.

- [ ] **Step 4: Confirm remote discovery works too**

```bash
npx -y skills@latest add averliz/visual-ux-review-toolkit --list
```
Expected: both skills listed. (Repo must be public; it is.)

- [ ] **Step 5: Record findings (no commit — nothing changed yet)**

Write the confirmed `<LIST_CMD>` and version into your working notes; Tasks 4 and 8 consume them. Proceed.

---

### Task 1: Housekeeping — stop shipping `__pycache__`

**Files:**
- Modify: `.gitignore`
- Delete (from tracking): `skills/visual-ux-review/scripts/__pycache__/generate_report.cpython-311.pyc`

- [ ] **Step 1: Verify the stray artifact is tracked**

```bash
git ls-files skills/visual-ux-review/scripts/__pycache__/
```
Expected: prints `…/generate_report.cpython-311.pyc` (confirming it's tracked and would ship).

- [ ] **Step 2: Append the ignore rule**

Add these lines to the end of `.gitignore`:

```gitignore

# Python bytecode (must never ship inside a skill directory)
__pycache__/
*.pyc
```

- [ ] **Step 3: Untrack the committed bytecode**

```bash
git rm --cached "skills/visual-ux-review/scripts/__pycache__/generate_report.cpython-311.pyc"
```

- [ ] **Step 4: Verify it's gone from tracking and ignored**

```bash
git ls-files skills/visual-ux-review/scripts/__pycache__/   # expect: (empty)
git check-ignore skills/visual-ux-review/scripts/__pycache__/x.pyc   # expect: prints the path
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: stop tracking/shipping __pycache__ in skill scripts"
```

---

### Task 2: Canonical `browser-tools.md` for `visual-ux-review`

**Files:**
- Create: `skills/visual-ux-review/references/browser-tools.md`

**Interfaces:**
- Produces: the canonical driver-mapping + detection + `BROWSER_DRIVER_MISSING` contract that both SKILL.md bodies point to and Task 3 copies verbatim.

- [ ] **Step 1: Create the file with this exact content**

````markdown
# Browser Driver — Capabilities, Detection & Fallback

This skill drives a live page through a small, fixed set of **capabilities**. It assumes no
specific harness. Before reviewing: map each capability to a concrete tool your harness exposes,
fill the **conformance checklist**, and if any required capability is missing, **stop** (see
`BROWSER_DRIVER_MISSING`) — never guess measurements.

## Required capabilities (closed set)

| Capability | Meaning | Hard requirement |
|---|---|---|
| `navigate` | Load a URL. | — |
| `set-viewport` | Resize the **existing** viewport to W×H. | Must NOT reload or reset page state (no destructive device-emulation). |
| `evaluate-js-in-page` | Run a JS function in the page and return its value. | Return value must come back as **data the agent can read** (not only printed/logged). |
| `screenshot` | Capture the page. | **Full-page, PNG.** |
| `accessibility-snapshot` | Get the accessibility tree. | Refs may go stale after DOM changes — re-snapshot after navigation. |
| `click` | Activate a control. | Prefer selector/role targeting over driver-specific refs. |

## Capability → tool mapping

**Playwright MCP is the recommended, verified default** (one install, same on every harness:
`npx @playwright/mcp@latest`). Other columns are **best-effort, `UNVERIFIED`** until confirmed
against that tool's own docs.

| Capability | Playwright MCP (verified) | Chrome DevTools MCP (UNVERIFIED) |
|---|---|---|
| navigate | `browser_navigate` | `navigate_page` |
| set-viewport | `browser_resize` | `resize_page` |
| evaluate-js-in-page | `browser_evaluate` | `evaluate_script` |
| screenshot (full-page PNG) | `browser_take_screenshot` (`type:"png"`, full page) | `take_screenshot` |
| accessibility-snapshot | `browser_snapshot` | `take_snapshot` |
| click | `browser_click` | `click` |
| lighthouse (optional) | — | `lighthouse_audit` |

If your harness exposes a different browser tool (`chrome-devtools-axi`, `gsd-browser`, a native
driver, …), map the same six capabilities to it and treat any unverified mapping as best-effort.

## Conformance checklist — do this ONCE, before any review

Resolve the capabilities against the driver your harness actually exposes and record:

```
Driver: <name of the browser tool detected>
navigate               -> <tool>     [ok]
set-viewport           -> <tool>     [ok — confirm NON-DESTRUCTIVE]
evaluate-js-in-page    -> <tool>     [ok — confirm it RETURNS DATA]
screenshot             -> <tool>     [ok — confirm FULL-PAGE PNG]
accessibility-snapshot -> <tool>     [ok]
click                  -> <tool>     [ok]
```

Any line you cannot fill with a verified tool = a missing capability → go to
`BROWSER_DRIVER_MISSING`. Do not proceed on a partial mapping.

## BROWSER_DRIVER_MISSING — the only legal output when a driver is absent

If any required capability is unmapped, emit **only** this block and stop. Produce **no** findings,
**no** scores, **no** coordinates, and **no** verdict:

```
BROWSER_DRIVER_MISSING
Missing capability: <which one(s)>
This skill measures a live rendered page and cannot run without a browser driver.
Enable one, then re-run:
  Claude Code:   claude mcp add playwright npx '@playwright/mcp@latest'
  Other harness (MCP config):
    { "mcpServers": { "playwright": { "command": "npx", "args": ["@playwright/mcp@latest"] } } }
```

Never substitute estimated geometry, contrast, or screenshots for measured data.

## Maintainer note
This file is duplicated **byte-for-byte** in both skills (`visual-ux-review`,
`ux-flow-walkthrough`) so each installs standalone. `scripts/verify-skills.mjs` enforces that the
two copies are identical — edit both, or run the check.
````

- [ ] **Step 2: Verify required anchors exist**

```bash
grep -c "BROWSER_DRIVER_MISSING" skills/visual-ux-review/references/browser-tools.md   # expect: >=2
grep -c "UNVERIFIED" skills/visual-ux-review/references/browser-tools.md               # expect: >=1
```

- [ ] **Step 3: Commit**

```bash
git add skills/visual-ux-review/references/browser-tools.md
git commit -m "feat: add browser-tools capability/detection reference (visual-ux-review)"
```

---

### Task 3: Mirror `browser-tools.md` to `ux-flow-walkthrough` + the drift check

**Files:**
- Create: `skills/ux-flow-walkthrough/references/browser-tools.md` (copy of Task 2's file)
- Create: `scripts/verify-skills.mjs` (repo root — does NOT ship)

**Interfaces:**
- Consumes: `<LIST_CMD>` confirmed in Task 0.
- Produces: `node scripts/verify-skills.mjs` → exit 0 when both copies match and `npx skills` lists both skills.

- [ ] **Step 1: Copy the canonical file verbatim**

```bash
cp skills/visual-ux-review/references/browser-tools.md \
   skills/ux-flow-walkthrough/references/browser-tools.md
```

- [ ] **Step 2: Write the verify script**

Create `scripts/verify-skills.mjs`. Replace the `LIST_ARGS` value with the form Task 0 confirmed (default shown):

```js
#!/usr/bin/env node
// Repo-health check (does NOT ship inside any skill).
//   node scripts/verify-skills.mjs
// 1) the two browser-tools.md copies are byte-identical
// 2) `npx skills` discovers both skills from this repo
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const LIST_ARGS = ['-y', 'skills@latest', 'add', '.', '--list']; // <- match Task 0's <LIST_CMD>
const SKILLS = ['visual-ux-review', 'ux-flow-walkthrough'];
const A = 'skills/visual-ux-review/references/browser-tools.md';
const B = 'skills/ux-flow-walkthrough/references/browser-tools.md';

let failed = false;
const fail = (m) => { console.error('FAIL: ' + m); failed = true; };

if (readFileSync(A).equals(readFileSync(B))) console.log('ok: browser-tools.md copies identical');
else fail(`${A} and ${B} differ — keep them byte-identical`);

try {
  const out = execFileSync('npx', LIST_ARGS, { encoding: 'utf8' });
  for (const s of SKILLS) out.includes(s) ? console.log(`ok: npx skills lists ${s}`) : fail(`npx skills did not list ${s}`);
} catch (e) {
  fail('could not run `npx skills … --list`: ' + (e.stderr?.toString() || e.message));
}

process.exit(failed ? 1 : 0);
```

- [ ] **Step 3: Run it — expect PASS (identical copies, both skills listed)**

```bash
node scripts/verify-skills.mjs
```
Expected: `ok: browser-tools.md copies identical`, `ok: npx skills lists visual-ux-review`, `ok: npx skills lists ux-flow-walkthrough`, exit 0.

- [ ] **Step 4: Prove the drift check actually fails on drift**

```bash
printf '\n<!-- drift -->\n' >> skills/ux-flow-walkthrough/references/browser-tools.md
node scripts/verify-skills.mjs; echo "exit=$?"        # expect: FAIL …differ, exit=1
git checkout -- skills/ux-flow-walkthrough/references/browser-tools.md   # restore identical copy
node scripts/verify-skills.mjs; echo "exit=$?"        # expect: all ok, exit=0
```

- [ ] **Step 5: Commit**

```bash
git add skills/ux-flow-walkthrough/references/browser-tools.md scripts/verify-skills.mjs
git commit -m "feat: mirror browser-tools.md + add verify-skills drift/discovery check"
```

---

### Task 4: Neutralize `visual-ux-review/SKILL.md` (capabilities + conformance gate)

**Files:**
- Modify: `skills/visual-ux-review/SKILL.md`

- [ ] **Step 1: Baseline grep (these are what we remove)**

```bash
grep -n "mcp__\|browser_evaluate\|browser_snapshot\|boundingBox\|/simplify\|/code-review\|/visual-ux-review" skills/visual-ux-review/SKILL.md
```
Expected: several matches (Prerequisites, Phase-1 capture, Key Technical Notes, workflow example). These must all be gone by Step 8.

- [ ] **Step 2: Replace the Prerequisites block**

Replace:

```markdown
## Prerequisites

At least one browser MCP must be available:
- **Playwright MCP** (`mcp__plugin_playwright_playwright__*` — preferred, supports `boxes: true`)
- **Chrome DevTools MCP** (`mcp__chrome-devtools__*` — has `lighthouse_audit`)
```

with:

```markdown
## Prerequisites

This skill drives a live page through six **capabilities** — `navigate`, `set-viewport`,
`evaluate-js-in-page`, `screenshot` (full-page PNG), `accessibility-snapshot`, `click` — mapped to
whatever browser tool your harness exposes. Playwright MCP is the recommended default
(`npx @playwright/mcp@latest`); Chrome DevTools MCP also works. See
[`references/browser-tools.md`](references/browser-tools.md) for the mapping table and how to
enable a driver.
```

- [ ] **Step 3: Insert the mandatory conformance gate (right after the Prerequisites block, before "## Where this runs in a workflow")**

```markdown
## Before you start — driver conformance (MANDATORY)

Do this ONCE, up front. Using [`references/browser-tools.md`](references/browser-tools.md), detect
which browser tool your harness exposes and fill the **conformance checklist** there — record the
concrete tool for each of the six capabilities, confirming `set-viewport` is non-destructive,
`evaluate-js-in-page` returns data, and `screenshot` is full-page PNG.

If any required capability is missing or unverified, emit **only** the `BROWSER_DRIVER_MISSING`
block from that file and **stop**: no findings, no scores, no coordinates, **no verdict**. This skill
measures a real rendered page — when it cannot, the correct output is "couldn't run," never an
estimated review.
```

- [ ] **Step 4: Neutralize the Phase-1 capture tool references**

Make these replacements (each `old` → `new`):
- `1. **Resize** viewport to target width × 900px height` → `1. **Resize** the viewport to target width × 900px height via the **set-viewport** capability (must not reset page state)`
- `2. **Full-page screenshot** → save as `review-{width}px.png`` → `2. **Full-page screenshot** (PNG) via the **screenshot** capability → save as `review-{width}px.png``
- `3. **Interactive element geometry** — run via `browser_evaluate`. Coordinates are` → `3. **Interactive element geometry** — run via the **evaluate-js-in-page** capability. Coordinates are`
- `4. **Font size audit** — run via `browser_evaluate`:` → `4. **Font size audit** — run via the **evaluate-js-in-page** capability:`
- `5. **Overflow check** — run via `browser_evaluate`:` → `5. **Overflow check** — run via the **evaluate-js-in-page** capability:`
- `6. **Lighthouse audit** (if Chrome DevTools MCP available): `lighthouse_audit` with `device: mobile`` → `6. **Lighthouse audit** (only if your driver exposes a Lighthouse capability — see browser-tools.md): run with `device: mobile``

- [ ] **Step 5: Neutralize the workflow-example slash commands**

Replace the blockquote under "## Where this runs in a workflow":

```markdown
> "For PR #42, run `/simplify`, then `/code-review` and fix issues, then **`/visual-ux-review`** and address any findings, then test the e2e flow with Playwright."
```

with:

```markdown
> "For PR #42, run your cleanup/simplify pass, then your code review and fix issues, then **this visual review** and address any findings, then test the e2e flow."
```

- [ ] **Step 6: Neutralize the Key Technical Notes tool names**

Replace:

```markdown
- **`browser_snapshot(boxes: true)`** returns `[x, y, width, height]` in CSS pixels.
- **`boundingBox()` returns null if element is off-viewport** — scroll into view before measuring.
```

with:

```markdown
- If your driver returns element boxes alongside the accessibility snapshot, they're `[x, y, width, height]` in CSS pixels (the exact tool is in browser-tools.md).
- An element's bounding box may be null/empty when it's off-viewport — scroll it into view before measuring.
```

- [ ] **Step 7: Add driver provenance to the report template**

In "### Phase 4: Structured Report", under the `### Summary` block, add a `- **Driver:**` line:

```markdown
### Summary
- Critical: N findings
- High: N findings
- Medium: N findings
- Low: N findings
- **Driver:** [the browser tool used, from your conformance checklist]
- **Verdict: SHIP / SHIP WITH FIXES / BLOCK**
```

- [ ] **Step 8: Verify all Claude-specific tokens are gone**

```bash
grep -n "mcp__\|browser_evaluate\|browser_snapshot\|boundingBox\|/simplify\|/code-review\|/visual-ux-review" skills/visual-ux-review/SKILL.md
```
Expected: **no matches.** (The in-page JS snippets and `gh pr diff` / `python …generate_report.py` lines remain — those are correct.)

- [ ] **Step 9: Commit**

```bash
git add skills/visual-ux-review/SKILL.md
git commit -m "refactor: capability-based, harness-agnostic visual-ux-review SKILL + driver gate"
```

---

### Task 5: Neutralize `ux-flow-walkthrough/SKILL.md` (capabilities, gate, solo-report fallback)

**Files:**
- Modify: `skills/ux-flow-walkthrough/SKILL.md`

- [ ] **Step 1: Baseline grep**

```bash
grep -n "mcp__\|browser_evaluate\|browser_snapshot\|log()\|visual-ux-review/scripts\|scripts/generate_report" skills/ux-flow-walkthrough/SKILL.md
```
Expected: matches in Prerequisites, Mode C (`log()` ×2), and the "Optional: annotated visual report" section.

- [ ] **Step 2: Replace the Prerequisites block**

Replace:

```markdown
At least one browser MCP must be available:
- **Playwright MCP** (`mcp__plugin_playwright_playwright__*` — preferred) — for navigating, clicking, typing, and screenshots.
- **Chrome DevTools MCP** (`mcp__chrome-devtools__*`) — alternative driver.
```

with:

```markdown
This skill drives a live app through a small set of **capabilities** — `navigate`, `click`,
`accessibility-snapshot`, `screenshot`, `evaluate-js-in-page`, `set-viewport` — mapped to whatever
browser tool your harness exposes. Playwright MCP is the recommended default
(`npx @playwright/mcp@latest`). See [`references/browser-tools.md`](references/browser-tools.md) for
the mapping and how to enable a driver.
```

- [ ] **Step 3: Insert the mandatory conformance gate (right after the Prerequisites paragraph, before "## The persona")**

```markdown
## Before you start — driver conformance (MANDATORY)

Once, up front: using [`references/browser-tools.md`](references/browser-tools.md), detect your
harness's browser tool and fill the conformance checklist. If a required capability is missing or
unverified, emit **only** the `BROWSER_DRIVER_MISSING` block and **stop** — no journey, no findings,
no verdict. A walkthrough with no real browser is not a walkthrough.
```

- [ ] **Step 4: Neutralize the two `log()` references**

- `track visited states ... Don't re-explore a state you've already covered; `log()` when you skip one.` → `… Don't re-explore a state you've already covered; **note** each skip in the report.`
- `Always honor `MAX_STEPS`/`MAX_DEPTH` and de-dup visited states, and `log()` what you skipped or truncated` → `Always honor `MAX_STEPS`/`MAX_DEPTH` and de-dup visited states, and **note** what you skipped or truncated`

- [ ] **Step 5: Rewrite the "Optional: annotated visual report" section for solo-install safety**

Replace the paragraph:

```markdown
### Optional: annotated visual report
For a shareable artifact, this skill can reuse the sibling **`visual-ux-review`** report generator (`scripts/generate_report.py`) by writing a `findings.json` whose **pages = journey steps** (each step's screenshot is the page; the frictions at that step are its findings, optionally with a box around the confusing control). See that skill's `references/report-schema.md`. This gives the same interactive HTML + PDF, but as a step-by-step journey.
```

with:

```markdown
### Output & optional annotated report
The **Markdown journey report above is the complete, self-sufficient deliverable** — always produce
it. *If* the sibling `visual-ux-review` skill is installed alongside this one, you may additionally
reuse its report generator for a shareable HTML/PDF: write a `findings.json` whose **pages = journey
steps** (each step's screenshot is the page; that step's frictions are its findings, optionally with
a box around the confusing control) and run
`python ../visual-ux-review/scripts/generate_report.py` (see that skill's `references/report-schema.md`).
If `visual-ux-review` is **not** installed, skip the annotated report and note it — do not invent a
different report format.
```

- [ ] **Step 6: Verify**

```bash
grep -n "mcp__\|browser_evaluate\|log()" skills/ux-flow-walkthrough/SKILL.md     # expect: no matches
grep -n "self-sufficient deliverable\|BROWSER_DRIVER_MISSING\|conformance" skills/ux-flow-walkthrough/SKILL.md  # expect: matches
```

- [ ] **Step 7: Commit**

```bash
git add skills/ux-flow-walkthrough/SKILL.md
git commit -m "refactor: capability-based ux-flow-walkthrough SKILL + gate + solo-report fallback"
```

---

### Task 6: Report provenance — schema + generator + test

**Files:**
- Modify: `skills/visual-ux-review/references/report-schema.md`
- Modify: `skills/visual-ux-review/scripts/generate_report.py:371-375` (`generate_md`) and `:350-366` (`generate_html`)
- Create: `tests/test_report_provenance.py` (repo root — does NOT ship)

**Interfaces:**
- Consumes: existing `generate_report.py` CLI (`--findings`, `--out-dir`, `--format`).
- Produces: an optional top-level `driver` string in `findings.json`, rendered into `report.md` and `report.html` headers; absence is a no-op (back-compatible).

- [ ] **Step 1: Write the failing test**

Create `tests/test_report_provenance.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

GEN = Path("skills/visual-ux-review/scripts/generate_report.py")

def _run(tmp_path: Path, data: dict) -> Path:
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out"
    subprocess.run(
        [sys.executable, str(GEN), "--findings", str(findings),
         "--out-dir", str(out), "--format", "md,html"],
        check=True,
    )
    return out

def _data(**extra) -> dict:
    return {"title": "T", "url": "http://x", "timestamp": "2026-06-24",
            "screenshots": {}, "findings": [], **extra}

def test_driver_rendered_when_present(tmp_path):
    out = _run(tmp_path, _data(driver="playwright-mcp"))
    assert "playwright-mcp" in (out / "report.md").read_text(encoding="utf-8")
    assert "playwright-mcp" in (out / "report.html").read_text(encoding="utf-8")

def test_no_driver_is_backcompat(tmp_path):
    out = _run(tmp_path, _data())  # no driver key
    assert (out / "report.md").exists()  # still generates, no crash
```

- [ ] **Step 2: Run it — verify it fails**

```bash
python -m pytest tests/test_report_provenance.py -v
```
Expected: `test_driver_rendered_when_present` FAILS (driver not in output); `test_no_driver_is_backcompat` PASSES.

- [ ] **Step 3: Render `driver` in the Markdown report**

In `generate_md` (after the `**Overall verdict:**` line, ~line 375), insert:

```python
    if data.get("driver"):
        L.append(f"**Driver:** {data['driver']}\n")
```

- [ ] **Step 4: Render `driver` in the HTML header**

In `generate_html` (~line 358), change the `__TIMESTAMP__` replacement so the header line carries the driver:

```python
    ts = data.get("timestamp", "")
    if data.get("driver"):
        ts = f"{ts} · driver: {data['driver']}"
    html = (HTML_TEMPLATE
            .replace("__TITLE__", data.get("title", "Visual UX Review"))
            .replace("__TIMESTAMP__", ts)
```
(Keep the remaining `.replace(...)` chain unchanged.)

- [ ] **Step 5: Run the test — verify it passes**

```bash
python -m pytest tests/test_report_provenance.py -v
```
Expected: both tests PASS.

- [ ] **Step 6: Document the field in the schema**

In `report-schema.md`, add a row to the Field reference table (after the `summary` row):

```markdown
| `driver` | no | The browser tool used for measurement (e.g. `playwright-mcp`); rendered in the report header for provenance. Omit if unknown |
```

- [ ] **Step 7: Commit**

```bash
git add skills/visual-ux-review/scripts/generate_report.py skills/visual-ux-review/references/report-schema.md tests/test_report_provenance.py
git commit -m "feat: optional driver provenance in report header (schema + generator + test)"
```

---

### Task 7: Docs — README install matrix, AGENTS.md, CLAUDE.md

**Files:**
- Modify: `README.md` (the `## Install` section ~24-38 and `## Compatibility & roadmap` ~101-104)
- Create: `AGENTS.md`
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: the confirmed install commands from Task 0.

- [ ] **Step 1: Replace the README `## Install` section**

Replace the existing `## Install` section body with:

```markdown
## Install

### Any agent (Claude Code, Codex, Cursor, Gemini, OpenCode, …)

```text
npx skills add averliz/visual-ux-review-toolkit
```

Installs both skills via the open [`npx skills`](https://github.com/vercel-labs/skills) tool. Add
`--skill visual-ux-review` (or `ux-flow-walkthrough`) to install just one. Tested with `skills`
<VERSION-FROM-TASK-0>.

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
```
(Substitute the version recorded in Task 0 for `<VERSION-FROM-TASK-0>`.)

- [ ] **Step 2: Replace the `## Compatibility & roadmap` section**

Replace:

```markdown
## Compatibility & roadmap

- **v0.1 — Claude Code only.** Plugins are a Claude Code construct, and the skills drive Claude Code's browser MCPs.
- The `SKILL.md` files are plain markdown and portable; **other harnesses** (Codex, Gemini, Copilot, …) are planned for a later iteration.
```

with:

```markdown
## Compatibility

- **Harness-agnostic.** Installable on any agent via `npx skills`; the skill bodies are written in a
  neutral browser-**capability** vocabulary (navigate / set-viewport / evaluate-js / screenshot /
  accessibility-snapshot / click) mapped per harness in each skill's `references/browser-tools.md`.
- **Driver:** Playwright MCP recommended (works the same on every harness); Chrome DevTools MCP
  mappings are best-effort. No driver ⇒ the skill stops cleanly rather than guessing.
- The Claude Code plugin path remains for native slash commands.
```

- [ ] **Step 3: Create `AGENTS.md`**

```markdown
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
```

- [ ] **Step 4: Create `CLAUDE.md`**

```markdown
See [AGENTS.md](AGENTS.md).
```

- [ ] **Step 5: Verify the "Claude Code only" claim is gone**

```bash
grep -rn "Claude Code only" README.md   # expect: no matches
grep -n "npx skills add averliz/visual-ux-review-toolkit" README.md AGENTS.md   # expect: matches in both
```

- [ ] **Step 6: Commit**

```bash
git add README.md AGENTS.md CLAUDE.md
git commit -m "docs: npx skills install matrix, harness-agnostic compat, AGENTS.md"
```

---

### Task 8: Acceptance sweep (the spec's verification gates)

**Files:**
- None modified (verification only). May produce notes appended to the PR description.

- [ ] **Step 1: De-Claude grep across both bodies**

```bash
grep -rn "mcp__" skills/*/SKILL.md            # expect: no matches
grep -rln "browser_evaluate\|browser_snapshot" skills/*/SKILL.md   # expect: no matches
```

- [ ] **Step 2: Discovery + drift via the verify script**

```bash
node scripts/verify-skills.mjs; echo "exit=$?"     # expect: all ok, exit=0
```

- [ ] **Step 3: Per-skill solo install carries references + scripts**

```bash
npx -y skills@latest add averliz/visual-ux-review-toolkit --skill ux-flow-walkthrough --list
# Then do a real temp install of each skill alone (project scope) into a scratch dir and confirm
# each installed skill dir contains references/browser-tools.md (and, for visual-ux-review,
# scripts/generate_report.py). Record the installed paths.
```
Expected: `references/browser-tools.md` present in each installed skill; `generate_report.py` present for `visual-ux-review`.

- [ ] **Step 4: Generator tests + no shipped bytecode**

```bash
python -m pytest tests/ -v                                   # expect: PASS
git ls-files | grep -E "__pycache__|\.pyc$"; echo "exit=$?"  # expect: no matches
```

- [ ] **Step 5: Preflight-gate behavior (manual)**

In a session with NO browser driver available, invoke `visual-ux-review`. Confirm it emits **only**
the `BROWSER_DRIVER_MISSING` block — no findings, no verdict. (Documents that the fabrication gate
fires.)

- [ ] **Step 6: Real cross-harness run — the core claim (honest scoping)**

Attempt a minimal end-to-end run of `visual-ux-review` on a **non-Claude** harness (Codex CLI):
install via `npx skills`, fill the conformance checklist against whatever driver is wired there, and
capture one breakpoint via the capability path. Record the result. **If a browser driver cannot be
provisioned on that harness in-session, document that explicitly** and scope the claim in the PR to
"installs on all; verified running on Claude Code + <harness actually tested>." Do not claim untested
harnesses work.

- [ ] **Step 7: No-Claude-regression smoke**

On Claude Code (Playwright MCP wired), run `visual-ux-review` against any local page for ONE
breakpoint end-to-end through the rewritten capability instructions. Confirm capture + a finding +
the report header showing the `Driver:` line. Confirms the abstraction didn't break the working path.

- [ ] **Step 8: Open the PR**

```bash
git push -u origin feat/npx-skills-harness-agnostic
gh pr create --title "feat: onboard onto npx skills + harness-agnostic capability port" \
  --body "Implements docs/superpowers/specs/2026-06-24-npx-skills-harness-agnostic-port-design.md. See acceptance sweep (Task 8) results, including which harnesses were verified running vs install-only."
```

---

## Self-Review (completed against the spec)

**Spec coverage:** §1 onboarding → Tasks 0,7,8; §2 capability enum + conformance → Tasks 2,4,5; §3 browser-tools.md (mapping/detect-all/drift/UNVERIFIED) → Tasks 2,3; §4 de-Claude → Tasks 4,5; §5 bug fixes (`__pycache__`, cross-skill path/solo report) → Tasks 1,5; §6 fabrication gate + provenance → Tasks 2,4,5 (gate) + Task 6 (provenance); §7 AGENTS/CLAUDE → Task 7; Risks (young CLI, host-model variance, unverified mappings) → Task 0 (pin/verify), gate in Tasks 2/4/5, `UNVERIFIED` in Task 2; Acceptance items 1–10 → Task 8. No uncovered spec sections.

**Placeholder scan:** The only intentional fill-ins are `<LIST_CMD>`/`<VERSION-FROM-TASK-0>`, produced by Task 0's recon and substituted in Tasks 3 & 7 — not open-ended TODOs. All code/edits show full content.

**Type/name consistency:** capability spellings, `BROWSER_DRIVER_MISSING`, `driver` field, and `scripts/verify-skills.mjs` are used identically across tasks and match the Global Constraints.
