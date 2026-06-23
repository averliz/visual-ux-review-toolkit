# UX Heuristic Reference — Thresholds & Sources

This reference provides the numeric thresholds and design-system citations behind each rubric dimension in the visual-ux-review skill. Read this file when you need to justify a finding or calibrate severity.

## Touch Target Thresholds

| Standard | Minimum Size | Spacing | Source |
|----------|-------------|---------|--------|
| Apple HIG | 44×44pt | 8pt gap | Human Interface Guidelines |
| Material Design 3 | 48×48dp | 8dp gap | material.io |
| WCAG 2.5.8 (AA) | 24×24px | — | W3C |
| WCAG 2.5.5 (AAA) | 44×44px | — | W3C |

**Severity calibration:**
- < 24px: **Critical** (fails WCAG AA minimum)
- 24-43px: **High** (meets AA minimum but below Apple/Material recommended)
- 44px+: Pass

## Spacing Scale

Consistent UIs use a spacing scale based on a base unit (typically 4px or 8px). Common violations:
- Random values like 13px, 17px, 22px mixed with 8px, 16px, 24px
- Inconsistent padding within the same component type (one card has 12px padding, its sibling has 16px)
- Margins that vary between instances of the same component

**Expected scales:**
- 4px system: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64
- 8px system: 8, 16, 24, 32, 40, 48, 56, 64

## Alignment

**Acceptable tolerance:** 1px (subpixel rendering can cause 0.5px offsets)
**Flag threshold:** 2px+ misalignment between elements that should be aligned

Common alignment issues:
- Text baselines in a row of chips/pills not matching
- Icons vertically offset from their label text
- List items with inconsistent left-edge indentation
- Form labels and inputs not aligned

## Layout Stability (CLS-adjacent)

**Core Web Vitals CLS target:** < 0.1
**Per-interaction shift threshold:** 5px

What counts as a "shift":
- Element moves position when a sibling changes state
- Content reflows when a filter/sort is applied
- Navigation items rearrange when viewport resizes within the same breakpoint range

What does NOT count:
- Content below a collapsed accordion moves when it expands (expected)
- Page content shifts when a modal opens (expected, if intentional)

## Typography

| Property | Minimum (mobile) | Recommended | Source |
|----------|-----------------|-------------|--------|
| Body text | 16px | 16-18px | iOS auto-zoom threshold |
| Line height | 1.4 | 1.5-1.75 | WCAG, Material |
| Line length | 35 chars | 45-75 chars | Typography best practice |
| Heading contrast | 1.2× body | 1.5-2× body | Visual hierarchy |

## Color Contrast (WCAG)

| Ratio | Level | Applies to |
|-------|-------|-----------|
| 4.5:1 | AA (normal text) | Body text, labels, links |
| 3:1 | AA (large text) | 18px+ regular, 14px+ bold |
| 7:1 | AAA | Enhanced accessibility |
| 3:1 | AA (non-text) | Icons, borders, UI controls |

## Responsive Breakpoints

| Width | Common device class | Review focus |
|-------|-------------------|-------------|
| 320px | iPhone SE | Nothing overflows, text readable |
| 375px | iPhone standard | Primary mobile experience |
| 768px | iPad portrait | Tablet layout transitions |
| 1024px | Small laptop | Desktop layout begins |
| 1440px | Standard monitor | Content max-width, whitespace balance |

## Nielsen's 10 Usability Heuristics (summarized)

Use these when evaluating element placement logic and overall UX coherence:

1. **Visibility of system status** — feedback on what's happening (loading, success, error)
2. **Match between system and real world** — language and concepts users understand
3. **User control and freedom** — undo, back, cancel always available
4. **Consistency and standards** — same action = same result everywhere
5. **Error prevention** — design that makes errors hard to commit
6. **Recognition over recall** — visible options, not memory demands
7. **Flexibility and efficiency** — shortcuts for experts, simplicity for novices
8. **Aesthetic and minimalist design** — no irrelevant information competing
9. **Help users recognize and recover from errors** — plain-language error messages
10. **Help and documentation** — easy to search, focused on the user's task

## Severity Decision Tree

```
Is the user blocked from completing their task?
  YES → CRITICAL
  NO →
    Would a reasonable user notice this without being told?
      YES →
        Does it make the UI feel broken or untrustworthy?
          YES → HIGH
          NO → MEDIUM
      NO → LOW
```
