---
name: ux-flow-walkthrough
description: "Journey-level UX walkthrough — drives a LIVE app as a clueless first-time user, one click at a time, to judge whether the flow actually makes sense. Runs an automated cognitive walkthrough: at each step it reasons as a naive user (do I know what to do? is the right control obvious? does its label make sense? is there feedback?), takes the most-obvious action, and logs every hesitation, dead-end, missing feedback, confusing label, unexpected navigation, or trap. Three modes: goal-directed (attempt a named task like 'sign up' or 'create a post'), free-explore (wander from an entry URL with no goal), and full auto-explore (exhaustively + adversarially traverse all reachable flows). Produces a step-by-step journey report with friction flagged by severity and a 'can a real first-timer actually complete this?' verdict. Use whenever the user wants to test a flow/journey/user-path or sense-check the experience — phrasings like 'does this flow make sense', 'walk through the app as a user', 'test the signup/checkout/onboarding flow', 'click through it like a confused user', 'find the UX dead-ends', 'is this confusing for a first-timer', or as a review step after building a feature to validate the end-to-end experience. Complements visual-ux-review (which checks how each SCREEN looks); this checks whether the FLOW between screens works. NOT for per-screen visual/pixel critique (use visual-ux-review), code/PR review, writing automated test scripts, or implementing features — only for experiencing and judging a live user journey."
---

# UX Flow Walkthrough — Naive-User Journey Testing

## Purpose

A screen can look perfect and still trap users: a primary action that's hard to find, a label that means nothing to a newcomer, a step with no feedback so people don't know it worked, a dead-end with no way back. Per-screen review can't catch these — they only show up when you actually **walk the path**.

This skill drives the app as a **clueless first-time user with zero context** and judges whether the journey makes sense. It's an automated **cognitive walkthrough** (an established UX method): step through a task as a novice and, at each step, ask whether a real first-timer would know what to do and whether the system helps them.

It operates **adversarially** — it doesn't use insider knowledge of where things are. If the right action isn't obvious to a confused newcomer, that's a finding, even if an expert would breeze through.

## Prerequisites

This skill drives a live app through a small set of **capabilities** — `navigate`, `click`,
`accessibility-snapshot`, `screenshot`, `evaluate-js-in-page`, `set-viewport` — mapped to whatever
browser tool your harness exposes. Playwright MCP is the recommended default
(`npx @playwright/mcp@latest`). See [`references/browser-tools.md`](references/browser-tools.md) for
the mapping and how to enable a driver.

## Before you start — driver conformance (MANDATORY)

Once, up front: using [`references/browser-tools.md`](references/browser-tools.md), detect your
harness's browser tool and fill the conformance checklist. If a required capability is missing or
unverified, emit **only** the `BROWSER_DRIVER_MISSING` block and **stop** — no journey, no findings,
no verdict. A walkthrough with no real browser is not a walkthrough.

The app must be running and reachable at a URL. **Any framework on any port** works — the skill just drives the URL you give it. To start it, use the project's own dev workflow (a `LOCAL_DEV.md`/`CONTRIBUTING.md` if present, else the README, `package.json`/`Makefile` scripts, or a compose file). Reviews can also run against a deployed URL.

## The persona — hold it the whole time

You are a **first-time user who has never seen this app and has no idea how it's built**. At every step:
- You only know your own goal, not the app's internal model.
- You read labels literally. Jargon, icons without labels, and insider abbreviations confuse you.
- You take the **most obvious** action, not the optimal one. If two or more controls tie for "most obvious," pick the one whose **label most literally matches your goal's verb**, take it, and log the rejected alternative as a discoverability finding — the tie itself is friction.
- You get frustrated by missing feedback, surprise navigation, and dead-ends.
- You do **not** open dev tools, read code, or guess hidden affordances.
- If the app drops you into a privileged/admin role (a seeded or auto-login), still act as a first-timer: ignore power-user-only surfaces, or flag them as "a real new user wouldn't even see this."

Never let app knowledge leak into the persona. "I know the menu is under the hamburger" is exactly the assumption a real newcomer doesn't have.

## Modes

Pick the mode from the user's request; default to **goal-directed**.

### Mode A — Goal-directed (default)
The user names a task: "sign up", "create a post", "buy something", "invite a teammate", or the primary flow a PR changed. Attempt that task end-to-end as the naive persona. Stop when the goal is achieved, you hit a blocker, or you're genuinely stuck/looping.

### Mode B — Free-explore (no goal given)
Given just an entry URL, wander like a curious newcomer: follow the most prominent affordances, open the primary navigation, try the obvious "main" actions. Map the primary flows you discover and flag confusion. Good for "just click around and tell me what's confusing."

### Mode C — Full auto-explore (exhaustive + adversarial)
Systematically traverse the reachable state space to surface unknown-unknowns. This is the "full-fledged" pass — bounded so it stays tractable:
- **Budget:** stop after `MAX_STEPS` (default 60) or `MAX_DEPTH` (default 8) from the entry point, whichever first. State the budget in the report.
- **State de-dup:** track visited states by a signature (normalized URL + a hash of the visible interactive elements). Don't re-explore a state you've already covered; **note** each skip in the report.
- **Coverage:** from each new state, enumerate interactive elements and visit unexplored ones breadth-first, so you get wide coverage before deep.
- **Adversarial probes** (the naive user makes mistakes — try them): submit forms empty and with junk input; hit the browser Back button mid-flow; double-click submit; open something then dismiss it; refresh mid-flow; follow a "destructive" looking action to the confirmation (don't confirm). Record what happens.
- **Safety:** never confirm destructive/irreversible actions (delete, pay, send) — stop at the confirmation and note it. Don't spam external sends. Treat any real-money or real-comms action as a hard stop.

## The walkthrough loop (every step)

For each step, do all five — this is the cognitive walkthrough:

1. **Observe.** Prefer the **accessibility snapshot** (cheap text), scoped to the relevant subtree (e.g. the open modal/form) when you can. Take a **screenshot only at decisive moments** — a key decision point, the final state, or to confirm a visual issue — not every step (it burns budget fast). Note what a newcomer sees.
2. **Form intent (as the persona).** "I'm trying to `<goal / sub-goal>`. Right now I want to `<next sub-step>`."
3. **Apply the four cognitive-walkthrough questions:**
   - **CW1 — Goal match:** Will the user even know this sub-step is what they need to do next? Or is the required action unguessable?
   - **CW2 — Visibility:** Is the correct control **visible and obviously interactive**? (Not buried, not an unlabeled icon, not below the fold with no cue.)
   - **CW3 — Label/affordance match:** Does the control's label/appearance clearly connect to the effect the user wants? (A newcomer reads it literally.)
   - **CW4 — Feedback:** After acting, will the user **see clear progress** toward the goal? (State change, confirmation, the next step appearing.)
   Any "no" is a friction finding — record it with the question it failed.
4. **Act.** Take the most-obvious action the naive persona would take. If the obvious action is wrong, that mistake **is** the finding — follow where it leads before recovering.
5. **Record the step:** what you saw, what you intended, what you did, what you expected, what actually happened, and any friction (with severity + which CW question failed).

Then check progress: closer to the goal? stuck? looping? hit a stopping condition?

**Two operational rules that prevent false findings:**
- **Driver timeouts are not findings.** On SPAs (React/Vue/etc. with background polling) the browser tool may return a network-idle/settle `TimeoutError` even though the action actually worked. After any click/navigation error, **re-observe (snapshot) before judging** — only flag a UX finding if the *app* visibly didn't respond, never because the *driver* timed out.
- **For data-changing goals, verify it persisted.** Success isn't "I saw a confirmation" — re-read the value (or reload) to confirm the change actually stuck. A confirmation with no real change is a High finding.

## Friction taxonomy (severity)

- **Blocker** — the user cannot proceed or cannot complete the task (dead-end, broken control, required step with no discoverable path, trap with no way back).
- **High** — likely abandonment: the correct action is effectively undiscoverable, a label actively misleads, a step gives no feedback so the user thinks it failed, or an error message doesn't say how to fix it.
- **Medium** — real hesitation that's recoverable: ambiguous label, unclear which of several controls to use, mild surprise navigation.
- **Low** — polish: slightly unclear wording, minor inconsistency, a nicety that would smooth the path.

## Stopping conditions

Stop and report when:
- **Goal-directed:** goal achieved; or a Blocker with no naive-user workaround; or 3 consecutive steps with no progress (stuck/looping).
- **Free-explore:** the primary flows have been covered, or ~`MAX_STEPS` reached.
- **Auto-explore:** budget (`MAX_STEPS`/`MAX_DEPTH`) reached, or no unvisited states remain.
- **Always:** at any destructive/irreversible confirmation — stop, note it, don't confirm.

If you stop early, say why; a truncated walkthrough is itself a finding about reachability.

## Output — the journey report

Narrate the journey as an ordered path, with friction called out where it happened.

```markdown
## UX Flow Walkthrough — [task / "free-explore" / "auto-explore"] — [URL] — [timestamp]

### Summary
- Mode: goal-directed | free-explore | auto-explore
- Goal: [the task, or "explore"]
- Outcome: COMPLETED / COMPLETED-WITH-FRICTION / BLOCKED / ABANDONED
- Steps taken: N (budget: …)
- Friction: B Blockers, H High, M Medium, L Low
- **Verdict: a naive first-timer WOULD / WOULD-WITH-EFFORT / WOULD-NOT complete this**

### The journey (step by step)
**Step 1 — [what the user wanted]**
- Saw: [what a newcomer sees]
- Did: [action taken] → [result]
- Friction: none — or a one-line pointer → [H1] (don't restate it here; full detail lives in Friction findings below)
…

### Friction findings (grouped by severity)
#### [B1] [short title]
- **Step:** N
- **CW failure:** CW2 (visibility) / …
- **What a newcomer experiences:** …
- **Evidence:** [screenshot ref / observation]
- **Fix:** [concrete change]

### Coverage (free/auto-explore only)
- States visited: N (skipped M already-seen)
- Flows reached: [list]
- Not reached / blocked: [list with why]
```

### Output & optional annotated report
The **Markdown journey report above is the complete, self-sufficient deliverable** — always produce
it. *If* the sibling `visual-ux-review` skill is installed alongside this one, you may additionally
reuse its report generator for a shareable HTML/PDF: write a `findings.json` whose **pages = journey
steps** (each step's screenshot is the page; that step's frictions are its findings, optionally with
a box around the confusing control) and run
`python ../visual-ux-review/scripts/generate_report.py` (see that skill's `references/report-schema.md`).
If `visual-ux-review` is **not** installed, skip the annotated report and note it — do not invent a
different report format.

## How to Run

1. **Determine mode + target:** task/goal (Mode A), entry URL only (Mode B), or "exhaustive/auto" (Mode C). Confirm the app source (local vs deployed) if not given.
2. Confirm the app is reachable (quick navigate to the entry URL).
3. Run the walkthrough loop, holding the naive persona, until a stopping condition.
4. Present the journey report. For auto-explore, report coverage + budget honestly.
5. **Address the findings** — fix the friction (or offer to), since this runs inside a review-and-fix flow.

## Sibling skills

- **`visual-ux-review`** — the per-screen half: does each screen *look and behave* right (geometry, spacing, contrast, layout jumps). Run it on the screens; run **this** on the flow between them. Together they cover the full UI/UX surface.
- **`ui-ux-pro-max`** — the underlying UX rubric/heuristics library, for fixing what either skill finds.

## Key notes

- **Persona discipline is the whole game.** The moment you use app knowledge a newcomer wouldn't have, the walkthrough stops finding real friction. When unsure, assume the user is confused.
- **Mistakes are signal, not noise.** If the obvious action is wrong, that's the most valuable finding — follow it.
- **Bound auto-explore.** Always honor `MAX_STEPS`/`MAX_DEPTH` and de-dup visited states, and **note** what you skipped or truncated — silent truncation reads as "covered everything" when it didn't.
- **Never confirm destructive/irreversible actions.** Stop at the confirmation and note it.
