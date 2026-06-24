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
