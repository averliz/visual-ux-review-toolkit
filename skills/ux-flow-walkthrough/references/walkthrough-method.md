# Walkthrough Method Reference

Detail behind the SKILL.md loop: the cognitive-walkthrough questions, the adversarial probe checklist for auto-explore, and state de-dup. Read this when you need the full method.

## Cognitive Walkthrough — the four questions (per step)

The cognitive walkthrough (Wharton, Rieman, Lewis & Polson, 1994) evaluates learnability by stepping through a task as a first-time user. At each action, ask:

| # | Question | A "no" means |
|---|----------|--------------|
| **CW1** | Will the user try to achieve the right effect? Do they know this sub-step is needed? | The required step is unguessable / hidden in the mental model |
| **CW2** | Will the user notice the correct control is available? | The control is invisible, below the fold with no cue, or an unlabeled icon |
| **CW3** | Will the user associate the control with the effect they want? | The label/affordance doesn't match the user's words or intent |
| **CW4** | After acting, will the user see progress toward the goal? | No feedback, silent success, or ambiguous result |

Record each failure with the failing question (CW1–CW4), the step number, and what the newcomer experiences. CW1/CW2 failures usually map to Blocker/High (the user is stuck or lost); CW3 to High/Medium (misled or hesitant); CW4 to High/Medium (acted but unsure).

## First-click test

The single strongest predictor of task success is whether the user's **first click** is on a path that leads to the goal. At the first decision point of each (sub)flow, note: was the obvious first click correct? If a newcomer's most-likely first click leads away from the goal, that's a High finding even if recovery is possible.

## Adversarial probe checklist (auto-explore / Mode C)

A naive user makes mistakes. From each state, where applicable, try these and record the result — many of the worst UX traps only appear here:

- **Empty submit** — submit a form with nothing filled. Is the error clear and near the field?
- **Junk input** — wrong email format, letters in a number field, past dates. Does validation explain the fix?
- **Back mid-flow** — hit browser Back partway through a multi-step flow. Is state preserved, or is the user dumped/looped?
- **Refresh mid-flow** — reload mid-flow. Is progress kept or silently lost?
- **Double action** — double-click submit / rapidly toggle. Duplicate submissions? Broken state?
- **Open-then-dismiss** — open a modal/drawer/menu then close it (Esc, backdrop, X). Does it close cleanly and restore focus?
- **Dead-end check** — from every leaf state, can the user get back to a primary flow without the Back button?
- **Destructive path** — follow a delete/pay/send-looking action **to its confirmation only**. Note the wording. **Never confirm.**

## State de-dup (auto-explore)

To keep traversal finite:
- **State signature** = normalized URL (drop volatile query params / ids) + a hash of the visible interactive elements (their roles + accessible names). Two states with the same signature are "the same screen."
- Maintain a `visited` set of signatures. Before exploring a state, check it; if seen, skip and `log()` the skip.
- Explore **breadth-first** from the entry point so coverage is wide before deep; respect `MAX_DEPTH` so you don't tunnel into one flow.
- Maintain a frontier of `(state, untried-element)` pairs; stop when the frontier is empty or the budget is hit.

## Severity decision tree (friction)

```
Can the user complete the task at all from here?
  NO  → Blocker
  YES →
    Would a typical first-timer get lost / give up here?
      YES → High
      NO  →
        Did they hesitate or briefly go the wrong way?
          YES → Medium
          NO  → Low (polish)
```

## What this method does NOT cover

- **Per-screen visual correctness** (spacing, alignment, tap-target size, contrast) → that's `visual-ux-review`.
- **Accessibility conformance** (full WCAG audit) → use an axe-based pass; this skill only notices a11y issues a confused sighted user would hit (e.g., an unlabeled icon button).
- **Functional correctness / bugs** → this judges whether the flow *makes sense*, not whether the backend is correct. A flow can make perfect sense and still have a bug, and vice-versa.
