# Harness-Agnostic Port + `npx skills` Onboarding — Design

**Date:** 2026-06-24
**Status:** Approved design, **hardened after adversarial review** (2 reference-repo reviews +
Devil's-Advocate + independent Codex pass). Pending spec review → implementation plan.
**Repo:** `averliz/visual-ux-review-toolkit`
**Decisions:** Full port; capability abstraction = **Full, hardened**; no-driver fallback =
recommend Playwright MCP → else STOP.

## Goal

Make the two skills (`visual-ux-review`, `ux-flow-walkthrough`) installable and **verifiably
runnable across agent harnesses** (Claude Code, Codex, Cursor, Gemini, …) by onboarding the repo
onto the **`npx skills`** tool ([vercel-labs/skills](https://github.com/vercel-labs/skills)) and
neutralizing the Claude-Code-specific content in the skill bodies — **without letting a weaker host
model fabricate a UX verdict when no browser driver is present.**

Retires the README's current claim: *"v0.1 — Claude Code only."*

## Context

### Current state
- Claude Code **plugin marketplace** (`.claude-plugin/marketplace.json`).
- Two skills under `skills/<name>/SKILL.md`, each with `references/`; `visual-ux-review` also has
  `scripts/generate_report.py`.
- Frontmatter is already exactly `name` + `description`.
- Claude-specific content is confined to **named MCP tools** in the skill bodies
  (`mcp__plugin_playwright_playwright__*`, `browser_evaluate`, `browser_snapshot`, `boundingBox()`),
  a few **slash-command** phrasings, and one `log()` reference. Reference docs + the Python
  generator are otherwise harness-neutral.

### What `npx skills` requires (verified by research; **re-verify at implementation**)
- Discovers `skills/<name>/SKILL.md` (flat). No manifest, no registration, no build step.
  `npx skills add averliz/visual-ux-review-toolkit` works against the public GitHub repo.
- Required frontmatter: **`name` + `description` only** — ours is already clean.
- `add` copies the **entire skill directory**, so `references/` + `scripts/` ride along.
- `marketplace.json` is ignored by `npx skills` but harmless; both channels coexist.
- Install targets differ per agent — `npx skills` picks them; docs must not hardcode one.
- **Treated as a young, third-party contract** (see Risks): pin the tested version; assert
  post-install file presence rather than trusting whole-dir copy blindly.

### Adversarial-review reframe
Both reference repos (gsd-browser, chrome-devtools-axi) are *browser tools shipped as skills*; we
are a *methodology skill that borrows a browser*. Their binary-distribution machinery is **not** to
be copied. The Devil's-Advocate + Codex passes then surfaced that the abstraction's value rests on
(a) the host model following multi-step gating as well as Claude does, and (b) actually being tested
off-Claude — neither of which the first draft guaranteed. This revision hardens both.

## Design

### 1. `npx skills` onboarding (packaging + docs)
Structurally satisfied; work is docs + verification + two housekeeping fixes:
- **README:** replace the Claude-only framing with an install matrix —
  `npx skills add averliz/visual-ux-review-toolkit` (any harness) **and** the existing `/plugin`
  flow (Claude-native). Requirements line: *"any harness with a browser MCP exposing JS-evaluate +
  full-page screenshot — Playwright MCP recommended (`npx @playwright/mcp@latest`)."*
- **No** SKILL.md generator (ours are hand-authored — YAGNI).

### 2. Browser-capability abstraction (closed enum) + mandatory conformance
Rewrite both `SKILL.md` bodies to call **capabilities**, never concrete tool names (all tool names
live only in `references/browser-tools.md`). The capability set is a **fixed, closed list**:

| Capability | Precise semantics (load-bearing) |
|---|---|
| `navigate` | Go to a URL. |
| `set-viewport` | Resize the **existing** viewport to W×H. **Must NOT reload/reset page state** (destructive device-emulation is disqualifying — it invalidates the layout-stability test). |
| `evaluate-js-in-page` | Run a JS function in the page and **return its value as parseable data**. All measurement depends on it. |
| `screenshot` | **Full-page, PNG** (viewport JPEG → annotation boxes land wrong). |
| `accessibility-snapshot` | Accessibility tree. Refs may go **stale** after DOM changes. |
| `click` | Prefer **selector/role** over driver refs. |

**Mandatory up-front conformance step (new — addresses indirection risk).** Before any review, the
skill resolves the capabilities **once** against `references/browser-tools.md` and records a
**conformance checklist**: the concrete tool selected for each required capability, for the detected
driver. Unknown or partial mappings are **rejected** (→ preflight gate, §6). Resolving once up front
(not per step) keeps the body harness-neutral *and* prevents the Claude path from degrading into a
per-step doc-chase.

The in-page JS snippets stay **verbatim**; only their wrapper prose changes ("run via
`browser_evaluate`" → "run via the **evaluate-js-in-page** capability").

### 3. `references/browser-tools.md` (one per skill, self-contained, kept in lockstep)
Each skill carries its own copy (required — skills install independently). Contents:

**a. Capability → driver mapping table.** Playwright MCP column is the **verified, recommended
default**. Non-Playwright columns are **marked `UNVERIFIED — best-effort`** unless their exact tool
names/semantics are confirmed against that MCP's docs during implementation (see §"Verification").
Shipping a confidently-wrong mapping is worse than marking it unverified.

| Capability | Playwright MCP (verified default) | Chrome DevTools MCP (verify or mark UNVERIFIED) |
|---|---|---|
| navigate | `browser_navigate` | `navigate_page` |
| set-viewport (non-destructive) | `browser_resize` | `resize_page` |
| evaluate-js-in-page | `browser_evaluate` | `evaluate_script` |
| screenshot (full-page PNG) | `browser_take_screenshot {fullPage, type:png}` | `take_screenshot` |
| accessibility-snapshot | `browser_snapshot` | `take_snapshot` |
| click | `browser_click` | `click` |
| lighthouse (optional) | — | `lighthouse_audit` |

(`chrome-devtools-axi` / `gsd-browser` may be listed as informational "if present" rows — **not**
dependencies.)

**b. Detect ALL required capabilities (not just eval).** Detection must confirm: `navigate`,
**non-destructive** `set-viewport`, `evaluate-js-in-page` (returns parseable data),
**full-page-PNG** `screenshot`, and `click` (when the flow interacts). A driver that has JS-eval but
only viewport JPEG, or destructive resize, **fails** detection.

**c. No-driver / partial-driver fallback** → the preflight gate in §6 (print the copy-paste install
line — Claude Code `claude mcp add playwright npx '@playwright/mcp@latest'`; generic `mcpServers`
JSON — then STOP).

**d. Drift control (the two copies must never diverge).** A committed check
(`scripts/verify-skills.*`, run locally and in CI) asserts the two `browser-tools.md` are
**byte-identical** and fails otherwise. (Chosen over a generator to avoid a build step.)

### 4. De-Claude the incidental references
- Strip `mcp__…__` prefixes.
- Slash-command phrasing (`/visual-ux-review`, `/simplify`, `/code-review`) → neutral.
- `log()` in `ux-flow-walkthrough` Mode C → "note/record".
- **Keep** universal CLI: `gh pr diff`, `git diff`, `python …/generate_report.py`, axe `.withTags`.

### 5. Bug fixes surfaced by review
- **`.gitignore`:** add `__pycache__/`; remove the committed
  `skills/visual-ux-review/scripts/__pycache__/generate_report.cpython-311.pyc`.
- **Cross-skill path guard + solo fallback:** `ux-flow-walkthrough/SKILL.md` (~line 129) reuses the
  *sibling* skill's `generate_report.py`. Guard it AND make the **markdown journey report the
  self-sufficient default**; the Python annotated report is an *optional enhancement* only when
  `visual-ux-review` is installed alongside. A solo install must still produce a complete report.

### 6. Fabrication safety — hard preflight gate + provenance (NEW; both reviews' top issue)
The report emits precise measurements and a SHIP/BLOCK verdict — high-trust output. Therefore:
- **Hard preflight gate.** If the conformance checklist (§2) is not fully satisfied by a verified
  driver, the **only legal output** is a fixed `BROWSER_DRIVER_MISSING` block: the missing
  capability, the copy-paste install line, and **nothing else** — no findings, no scores, no
  coordinates, **no verdict**. This is an explicit output contract in the SKILL.md body, not a
  buried sentence.
- **Provenance.** The report header records the **driver name** and that measurements came from it.
  Each measured finding keeps its required `evidence` (already mandated: exact Phase-1
  `getBoundingClientRect`, never estimated) plus its **breakpoint/viewport**. "No measurement ⇒ no
  verdict" is a hard rule. `report-schema.md` gains an optional `driver` provenance field;
  `generate_report.py` displays it if present (minor, back-compatible).

### 7. Cross-harness discovery doc
- Add a short root **`AGENTS.md`**: repo layout, dual install paths (`npx skills` vs `/plugin`),
  how to run the Python generator, and how to run `scripts/verify-skills.*`. **Not** the methodology.
- Optional one-line `CLAUDE.md` → `AGENTS.md` pointer.

### Unchanged
Reference docs other than `report-schema.md`, `marketplace.json`, and the core of
`generate_report.py` (only the optional provenance line is added).

## Files touched
- `skills/visual-ux-review/SKILL.md` — capability language; up-front conformance checklist;
  detect-all; preflight `BROWSER_DRIVER_MISSING` gate; provenance in report header; pointer to its
  `references/browser-tools.md`.
- `skills/visual-ux-review/references/browser-tools.md` — **new**.
- `skills/visual-ux-review/references/report-schema.md` — add optional `driver` provenance field.
- `skills/visual-ux-review/scripts/generate_report.py` — minor: render `driver` if present.
- `skills/ux-flow-walkthrough/SKILL.md` — capability language; conformance; detect-all; gate;
  `log()`→note; guard sibling generator ref; self-sufficient markdown report for solo installs.
- `skills/ux-flow-walkthrough/references/browser-tools.md` — **new** (byte-identical to sibling).
- `scripts/verify-skills.*` — **new** (repo-root): asserts `npx skills add . --list` lists both
  skills, and the two `browser-tools.md` are byte-identical.
- `.github/workflows/ci.yml` — **new, optional**: runs `scripts/verify-skills.*`.
- `README.md` — install matrix, requirements line, roadmap.
- `AGENTS.md` — **new** (tiny). `CLAUDE.md` — **new**, optional one-liner.
- `.gitignore` — add `__pycache__/`; remove the committed `.pyc`.

## Non-goals
- Building/porting our own browser CLI; active shell-out fallback / runtime dep on
  `chrome-devtools-axi`; publishing to skills.sh or npm.
- A SKILL.md **generator** (the verify script is a *check*, not a generator); `release-please`;
  per-harness SKILL variants; multiple SKILL.md copies; gsd-browser-style distribution machinery.
- Adding `allowed-tools` or `user-invocable: false` frontmatter (Claude-only;
  `user-invocable:false` would suppress the `/visual-ux-review` slash command for zero gain).

## Risks & assumptions (made explicit)
- **Host-model variance.** Weaker harness models may not follow the detect→conform→gate discipline
  as reliably as Claude. Mitigation: the gate is the first, unmissable instruction; conformance is a
  single up-front step; the `BROWSER_DRIVER_MISSING` contract makes "couldn't run" the safe default.
- **`npx skills` is young.** Pin the tested version; assert post-install file presence; don't treat
  its discovery/local-path contract as permanent.
- **Non-Playwright mappings unproven** until verified → ship them marked `UNVERIFIED` if not.

## Verification / acceptance
1. **Discovery (local + remote):** `npx skills add . --list` **and**
   `npx skills add averliz/visual-ux-review-toolkit --list` each enumerate **both** skills. (Confirm
   the local `.` form is supported; if not, use the supported form and update docs.)
2. **Per-skill install:** temp-install **each** skill alone; assert its `references/`
   (incl. `browser-tools.md`) and any `scripts/` are present in the installed dir.
3. **Drift:** `scripts/verify-skills.*` confirms the two `browser-tools.md` are byte-identical.
4. **De-Claude:** grep both `SKILL.md` bodies → **zero** `mcp__` prefixes and no raw tool names
   outside `references/browser-tools.md`.
5. **Housekeeping:** no `__pycache__` ships; the committed `.pyc` is gone and ignored.
6. **Preflight gate:** with no driver available, the skill emits **only** `BROWSER_DRIVER_MISSING`
   (no findings/verdict). Verify by running the gate path.
7. **Real cross-harness run (the core claim):** drive one skill end-to-end on a real **non-Claude**
   harness — Codex CLI (available in this environment) — at least one breakpoint capture via the
   capability path. **If a browser driver cannot be provisioned there in-session, document that and
   scope the "verified-running" claim to the harnesses actually exercised** (e.g. "installs on all;
   verified running on Claude Code + <harness>"); do not claim untested harnesses work.
8. **No Claude regression:** the rewritten `visual-ux-review` still completes a capture end-to-end at
   one breakpoint on Claude Code.
9. **Non-Playwright mappings:** each is either verified against its MCP's docs or shipped marked
   `UNVERIFIED`.
10. **README:** shows the `npx skills add` matrix; no remaining "Claude Code only" claim.

## Open items for the user
- Commit the spec + (later) the implementation? Repo is on `main`; if committing, branch first
  (e.g. `feat/npx-skills-harness-agnostic`).
- Optional `CLAUDE.md` one-liner wanted, or `AGENTS.md` alone?
- Is the optional `.github/workflows/ci.yml` wanted, or just the local `verify-skills` script?
