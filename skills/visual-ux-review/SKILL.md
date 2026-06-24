---
name: visual-ux-review
description: "Adversarial visual UX review of a LIVE RENDERED web page — drives Playwright/Chrome DevTools to screenshot it at 5 breakpoints, measure every interactive element's geometry, audit font sizes and color contrast, and click every sort/filter/tab to catch layout jumps, then uses vision to adversarially critique the rendered UI against a UX rubric and can emit an annotated HTML/PDF report with boxes drawn on the screenshots. Catches undersized touch targets, inconsistent padding/spacing, misaligned elements, layout jumps, illogical control placement, weak visual hierarchy, overflow, sub-16px text, and low-contrast text. Use whenever the user wants to review, check, or audit the UI/UX of a running page — phrasings like 'review the UI', 'check the UX', 'is the UI good', 'visual review', 'adversarial UI check', 'visual-ux-review', 'the buttons look too small', 'the padding/spacing looks off', 'the chips/buttons jump around when clicked', or 'something looks misaligned' — or wants an annotated UI report with screenshots, or has just built or polished frontend work and wants the rendered result verified before shipping. Trigger proactively after any frontend feature, UI polish, or responsive-layout change, and as an explicit step in a review workflow — e.g. invoked right after a code review to visually check the screens a PR changed before merging. It reviews AND can address what it finds. NOT for code/PR review of the diff itself, writing tests, implementing unrelated features, converting designs to code, or abstract design-theory questions — only for reviewing how an actual rendered page looks and behaves."
---

# Visual UX Review — Adversarial Rendered-UI Critique

## Purpose

This skill catches UI bugs that pass tests but look wrong to a real user: buttons too small to tap, padding that feels off, elements that aren't aligned, controls in illogical positions, layout that jumps when state changes, and visual hierarchy that confuses rather than guides.

It operates **adversarially** — the default posture is "assume it's broken, hunt for what's wrong." A charitable reviewer looks at a screenshot and says "looks fine." This skill assumes every pixel is suspicious until proven innocent.

## Prerequisites

This skill drives a live page through six **capabilities** — `navigate`, `set-viewport`,
`evaluate-js-in-page`, `screenshot` (full-page PNG), `accessibility-snapshot`, `click` — mapped to
whatever browser tool your harness exposes. Playwright MCP is the recommended default
(`npx @playwright/mcp@latest`); Chrome DevTools MCP also works. See
[`references/browser-tools.md`](references/browser-tools.md) for the mapping table and how to
enable a driver.

The page under review must be running and accessible at a URL. **Any framework on any port works** — the skill just navigates to the URL you give it (Vite `:5173`, Next.js/CRA `:3000`, Angular `:4200`, Vue/Nuxt `:8080`, a static server, a deployed `https://` URL — whatever). Nothing keys off the port or framework. To start it, use the project's own dev workflow — discover it rather than assuming: check for a `LOCAL_DEV.md` or `CONTRIBUTING.md`, then the README, `package.json`/`Makefile` scripts, or a `docker-compose` file.

## Before you start — driver conformance (MANDATORY)

Do this ONCE, up front. Using [`references/browser-tools.md`](references/browser-tools.md), detect
which browser tool your harness exposes and fill the **conformance checklist** there — record the
concrete tool for each of the six capabilities, confirming `set-viewport` is non-destructive,
`evaluate-js-in-page` returns data, and `screenshot` is full-page PNG.

If any required capability is missing or unverified, emit **only** the `BROWSER_DRIVER_MISSING`
block from that file and **stop**: no findings, no scores, no coordinates, **no verdict**. This skill
measures a real rendered page — when it cannot, the correct output is "couldn't run," never an
estimated review.

## Where this runs in a workflow

This skill is built to be dropped into a review chain as an explicit step — typically **after** a code review, because code review reads the diff and can't see spatial/visual problems (a 22px tap target, chips that reflow on click, a header that wraps badly). A user will often invoke it mid-workflow, e.g.:

> "For PR #42, run your cleanup and simplify pass, then your code review and fix issues, then **this visual review** and address any findings, then test the e2e flow."

So assume the code review is already done; your job is the visual pass on the screens that changed, then **report the findings and fix them** (this runs as part of a review-and-fix flow, not a read-only audit).

## Workflow

Each phase has a **completion gate**. Do not advance to the next phase until the gate is satisfied. If a check was skipped, report it as `NOT CHECKED` in the final report — a skipped check is itself a finding.

---

### Phase 0: Scope — which screens, and where

Settle two things before capturing anything.

**1. Which routes to review** (in priority order):
- If the user named specific screens/routes, use those.
- If reviewing a PR ("PR #XX"), get its changed files: `gh pr diff XX --name-only` (or `git diff --name-only <base>...HEAD` for the current branch — base = the repo's default branch, e.g. `origin/main` or `origin/master`).
- Filter to frontend files and map them to routes:
  - a changed **route/page file** → its URL path;
  - a changed **shared component/hook/util** → grep for which route/page files import it (`grep -rl <ComponentName> src/`) to find the screens it actually affects.
- Present the candidate route list **with the reason each is included**, and confirm/trim with the user before proceeding — a shared component can fan out to many screens, and reviewing all of them may be overkill.
- If the diff→route mapping is unclear (or there's no diff), ask the user which routes to review.

**2. Where to load the app** — ask the user unless they already specified:
- **Local** — start/use the project's local dev stack and review `localhost`. Discover how to start it from the project's own docs/config (a `LOCAL_DEV.md`/`CONTRIBUTING.md` if present, else the README, `package.json`/`Makefile` scripts, or a compose file). Right for pre-merge review of a branch's changes.
- **Deployed** — point at the deployed URL. Reviews what's live, not the local branch.

Each chosen route becomes one page of the report — use the multi-page `pages[]` form (see `references/report-schema.md`).

---

### Phase 1: Capture

Take screenshots, geometry, and font/contrast data at **all 5 breakpoints**:

| Breakpoint | Width | Device class |
|-----------|-------|-------------|
| Small mobile | 320px | iPhone SE |
| Mobile | 375px | iPhone standard |
| Tablet | 768px | iPad portrait |
| Desktop | 1024px | Small laptop |
| Wide | 1440px | Desktop monitor |

For **each** breakpoint:

1. **Resize** the viewport to target width × 900px height via the **set-viewport** capability (must not reset page state)
2. **Full-page screenshot** (PNG) via the **screenshot** capability → save as `review-{width}px.png`
3. **Interactive element geometry** — run via the **evaluate-js-in-page** capability. Coordinates are **document-relative** (`+ scrollX/Y`) so they map onto the full-page screenshot for report annotation:
   ```js
   () => {
     const els = document.querySelectorAll('a, button, input, select, textarea, [role="button"], [role="link"], [role="tab"], [tabindex]');
     const results = [];
     els.forEach(el => {
       const r = el.getBoundingClientRect();
       if (r.width === 0 && r.height === 0) return;
       results.push({
         tag: el.tagName.toLowerCase(),
         text: (el.textContent || '').trim().slice(0, 60),
         x: Math.round(r.left + window.scrollX), y: Math.round(r.top + window.scrollY),
         w: Math.round(r.width), h: Math.round(r.height),
         small: r.width < 44 || r.height < 44
       });
     });
     return results;
   }
   ```
4. **Font size audit** — run via the **evaluate-js-in-page** capability:
   ```js
   () => {
     const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
     const seen = new Set();
     const issues = [];
     while (walker.nextNode()) {
       const el = walker.currentNode.parentElement;
       if (!el || seen.has(el) || !el.offsetHeight) continue;
       seen.add(el);
       const size = parseFloat(getComputedStyle(el).fontSize);
       if (size < 16) {
         issues.push({
           tag: el.tagName.toLowerCase(),
           text: el.textContent.trim().slice(0, 40),
           fontSize: size
         });
       }
     }
     return issues;
   }
   ```
5. **Overflow check** — run via the **evaluate-js-in-page** capability:
   ```js
   () => ({
     scrollWidth: document.documentElement.scrollWidth,
     clientWidth: document.documentElement.clientWidth,
     overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
   })
   ```
6. **Lighthouse audit** (only if your driver exposes a Lighthouse capability — see browser-tools.md): run with `device: mobile` for 320/375px, `device: desktop` for the rest. If unavailable, record `Lighthouse: NOT AVAILABLE`.

**Completion gate:** Confirm data collected at ALL 5 breakpoints before proceeding:
```
Geometry: 320 [x] 375 [x] 768 [x] 1024 [x] 1440 [x]
Fonts:    320 [x] 375 [x] 768 [x] 1024 [x] 1440 [x]
Overflow: 320 [x] 375 [x] 768 [x] 1024 [x] 1440 [x]
Screenshot: 320 [x] 375 [x] 768 [x] 1024 [x] 1440 [x]
```

---

### Phase 2: Mechanical Checks

These are deterministic, objective checks. No opinion needed — just math.

#### 2a. Touch Target Sizing (at every breakpoint)
- Flag every interactive element with `width < 44` OR `height < 44` CSS pixels
- Severity: `< 24px` = **Critical** (fails WCAG AA), `24-43px` = **High** (below recommended)
- Also flag interactive elements with less than 8px gap to their nearest interactive sibling

#### 2b. Font Size Audit (at 320px and 375px — mobile is where this matters)
- Flag any visible text element with `fontSize < 16px` as **High**
- Flag any with `fontSize < 12px` as **Critical**
- Exception: labels, captions, and legal text can be 12-14px if intentional

#### 2c. Horizontal Overflow (at every breakpoint)
- If `scrollWidth > clientWidth`, identify offending elements
- Any overflow = **Critical** at mobile, **High** at desktop

#### 2d. Spacing Consistency
For repeated element groups (table rows, card lists, chip/pill sets, nav items):
```js
// Measure gaps between consecutive items in a group
() => {
  const cards = document.querySelectorAll('[data-testid*="row"], .card, tr, [class*="chip"]');
  const gaps = [];
  for (let i = 1; i < cards.length; i++) {
    const prev = cards[i-1].getBoundingClientRect();
    const curr = cards[i].getBoundingClientRect();
    gaps.push(Math.round(curr.top - prev.bottom));
  }
  const median = gaps.sort((a,b) => a-b)[Math.floor(gaps.length/2)];
  return gaps.map((g, i) => ({ index: i, gap: g, median, deviation: Math.abs(g - median) }))
    .filter(g => g.deviation > 4);
}
```
Flag any gap that deviates more than 4px from the group's median as **Medium**.

#### 2e. Layout Stability (MANDATORY — do not skip)
This is the most important mechanical check. The user's known bugs live here.

1. **Identify all interactive controls** on the page: sort chips, filter toggles/dropdowns, tabs, pagination, expandable sections
2. **For each control:**
   - Record bounding boxes of 3-5 nearby elements BEFORE clicking
   - Click the control
   - Wait 500ms for any animation/rerender
   - Record the same elements' bounding boxes AFTER
   - Flag any element that shifted more than **5px** in either axis
   - Flag any element that **disappeared or changed size** unexpectedly
3. **Specifically test:** clicking each sort chip/pill in sequence — does the active chip cause other chips to reflow/jump?

**Completion gate:** Every interactive control on the page must be clicked and measured. List each one with its result:
```
Sort chip "Name": clicked, 0 shifts
Sort chip "Date": clicked, 2 shifts (filter row moved 8px)
Filter toggle: clicked, 0 shifts
...
```

---

### Phase 3: Vision Critique (adversarial, opinionated)

Read each screenshot and evaluate against this rubric. Think like a **skeptical designer reviewing a junior developer's work** — unimpressed by default, looking for what's wrong.

#### Rubric

**1. Touch & Interaction (CRITICAL)**
- Are all interactive elements large enough to comfortably tap?
- Is there adequate spacing between clickable things?
- Do buttons look like buttons? Do links look like links?
- Are there invisible or near-invisible interactive affordances?
- Could a user accidentally tap the wrong element due to proximity?

**2. Spacing & Padding (HIGH)**
- Is the spacing rhythm consistent? Same gap between similar elements?
- Does padding inside containers feel balanced?
- Is the spacing scale systematic (multiples of 4px/8px) or arbitrary?
- Are section gaps between logical groups (header → filters → content → pagination) consistent?

**3. Alignment (HIGH)**
- Are elements that should be aligned actually aligned? (Left edges, baselines, centers)
- Do headings align with their content below?
- In a row of chips/pills/buttons, are they on the same baseline?
- Does the back/nav element align properly with the page title?

**4. Visual Hierarchy (HIGH)**
- Is it immediately clear what's most important?
- Is there one clear primary action, or do multiple things compete?
- Do headings and body text have enough size/weight contrast?
- Are secondary controls visually subordinate to primary ones?

**5. Layout Stability (MEDIUM)**
- When interacting with controls, do other elements jump or shift?
- Do expanding/collapsing sections push content jarringly?
- Is there content that "snaps" into position rather than flowing?

**6. Control Placement Logic (MEDIUM)**
- Are controls where a user would expect them?
- Controls that act on a data table (filter, sort, search, export) must be visually anchored to that table — within the same container or immediately adjacent. Flag any control that is visually orphaned from the content it governs.
- Does mobile make different placement choices than desktop where appropriate?

**7. Typography (MEDIUM)**
- Is body text readable (16px+ on mobile)?
- Is there a clear type scale with consistent sizes?
- Are font weights used to reinforce hierarchy (not random bold)?
- Do numbers use tabular figures in data contexts?

**8. Unexplained Visual Elements (MEDIUM)**
- Are there badges, icons, colors, or labels that lack explanation?
- Would a new user understand every visual indicator without training?
- Does every colored badge have a tooltip or legend?

**9. Responsive Adaptation (LOW)**
- Does the layout gracefully adapt between breakpoints?
- Does mobile prioritize different content than desktop?
- Are there breakpoints where elements overlap or truncate badly?

---

### Phase 4: Structured Report

Every finding must reference a specific element, breakpoint, and evidence (measurement or screenshot observation).

```markdown
## Visual UX Review — [URL] — [timestamp]

### Summary
- Critical: N findings
- High: N findings
- Medium: N findings
- Low: N findings
- **Driver:** [the browser tool used, from your conformance checklist]
- **Verdict: SHIP / SHIP WITH FIXES / BLOCK**

### Critical Findings
#### [C1] [Short description]
- **Element:** [what element]
- **Breakpoint:** [where observed]
- **Issue:** [what's wrong]
- **Evidence:** [measurement: "width=22px, threshold=44px" or visual observation]
- **Fix suggestion:** [concrete CSS/component change]

### High / Medium / Low Findings
(same structure)

### Mechanical Check Results
- Touch targets: N/N pass at 320px, N/N at 375px, ... (list ALL failures with measurements)
- Font sizes: N elements below 16px at mobile (list them)
- Horizontal overflow: pass/fail per breakpoint
- Spacing consistency: N groups checked, N deviations > 4px
- Layout stability: N controls clicked, N shifts detected (list each)
- Lighthouse a11y: N/100 (or NOT AVAILABLE)
- Lighthouse best-practices: N/100 (or NOT AVAILABLE)
- Color contrast: checked/NOT CHECKED
```

### Verdict Criteria

- **SHIP**: Zero Critical, zero High findings
- **SHIP WITH FIXES**: Zero Critical, 1-3 High findings with clear fixes
- **BLOCK**: Any Critical finding, OR 4+ High findings, OR High findings with no clear fix

---

### Phase 5: Annotated Report (offer it)

After presenting the inline report, offer to generate a visual report with bounding boxes drawn over the screenshots. The generator emits all formats at once (HTML + MD + PDF + annotated PNGs); mention them so the user knows what they're getting.

1. Write a `findings.json` matching `references/report-schema.md`. **Box accuracy is critical — never estimate coordinates.** Each finding's `box` MUST be the exact `getBoundingClientRect` (document-relative, `+ scrollX/Y`) of *that specific element*, taken from your Phase-1 geometry capture — look the element up by what it is; do **not** eyeball or guess coordinates off the screenshot. A guessed box lands on the wrong element and makes the whole report nonsense (e.g. a "sort chip" finding boxing the page title). A box is valid for only the **one breakpoint** it was measured at — an element sits at a different position per breakpoint — so a finding that carries a box must list a **single** `breakpoint`. If you don't have a measured rect for the element, **omit the box**: a text-only finding beats a wrong box. Before generating, spot-check by re-querying a couple of boxed elements and confirming the box matches. For a single page use the top-level form; for several screens use the `pages[]` form. `verdict`/`summary` auto-derive — don't hand-set them.
2. Run the generator:
   ```bash
   python <skill-dir>/scripts/generate_report.py \
     --findings findings.json \
     --screenshots-dir <dir with the screenshots> \
     --out-dir <report output dir>
   ```
   (Limit formats with `--format`, e.g. `--format html,pdf`.)
3. Outputs in the report dir:
   - **`report.html`** — interactive: page switcher, breakpoint tabs, box overlays, per-finding 👍/👎 + comment box, "Export feedback" → JSON
   - **`report.pdf`** — shareable PDF: cover + summary table, then each finding as a card with a **focused crop** (the box ± context, captioned) beside its text — not giant full-page screenshots. Rendered via headless Edge/Chrome (reportlab fallback)
   - **`report.md`** — Markdown, one chapter per page
   - **`<page>-<bp>px-annotated.png`** — boxes burned into the screenshots
4. Tell the user the paths. For the interactive HTML, they open it in a browser (or you serve it — `file://` is blocked in the automation browser but fine in theirs), review each box, vote agree/disagree, leave comments, then click "Export feedback" to download a JSON of their verdicts — which you can read back to refine the findings. The PDF is the artifact to share with people who won't open the HTML.

---

## How to Run

1. **Phase 0 — scope:** determine the routes (from the PR/branch diff or user-specified) and the app source (local/deployed). Confirm the route list with the user before proceeding.
2. Ensure each route is reachable (quick navigate).
3. For **each** route, execute Phases 1→2→3→4 in strict order, respecting completion gates. Collect all routes into one multi-page report.
4. Present the report; generate the annotated report (Phase 5).
5. **Address the findings** — fix the issues found (or offer to, if the user wants to review first). This skill runs inside a review-and-fix flow, so don't stop at reporting.

## Sibling Skills

- **`ux-flow-walkthrough`** _(planned)_ — click-by-click journey as a naive user. Complements per-screen review.
- **`ui-ux-pro-max`** — the 99-guideline design rubric. This skill's rubric is derived from it.
- **`browser-qa`** — broader QA (smoke, interaction, visual regression, a11y). This skill goes deeper on the visual/UX dimension.

## Key Technical Notes

- **axe-core `target-size` is OFF by default.** Enable with `.withTags(['wcag22aa'])` or `.withRules(['target-size'])`.
- If your driver returns element boxes alongside the accessibility snapshot, they're `[x, y, width, height]` in CSS pixels (the exact tool is in browser-tools.md).
- An element's bounding box may be null/empty when it's off-viewport — scroll it into view before measuring.
- **Cross-OS font rendering** differs — this skill uses vision critique (semantic), not pixel comparison.
- **Read `references/ux-heuristics.md`** for the full threshold table and severity decision tree.
