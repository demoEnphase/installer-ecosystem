---
name: enphase-design-system
description: Use when designing for Enphase Energy — solar microinverters, IQ Batteries, EV chargers, the Enphase App, or any homeowner/installer/data-center facing surface. Loads brand voice, color, type, layout, and component conventions derived from the official Enphase Visual Identity Guidelines v1.3.
---

# Enphase Design System

When designing for Enphase, **always read `README.md` first** — it carries the canonical voice, color, type, layout, iconography, and caveat list. The CSS variable tokens live in `colors_and_type.css`; load it on every page.

## Quickstart

1. `<link rel="stylesheet" href="path/to/colors_and_type.css">`
2. Add the body class `enph-content` (warm-white background, Inter as primary, applies sensible defaults).
3. Use tokens — `var(--enph-orange-02)`, `var(--enph-warm-white)`, `var(--enph-radius-lg)`, `var(--enph-font-primary)`, etc. Do not hardcode hex.
4. Logos live at `assets/enphase-logo.svg`, `assets/enphase-logo-white.svg`, `assets/enphase-mark.svg`.

## Voice in one breath
Confident, optimistic, technically literate, warm. **Sentence case** for headlines and CTAs. **ALL CAPS** in T-Star Pro (DM Mono substitute) for eyebrows/data labels only. Speak directly: *you* / *your*. Periods, not exclamation. **Never use emoji.**

## Color in one breath
Warm whites and grays — never cold tech grays. Brand colors split into **light-theme** (use on white) and **dark-theme** (use on black) variants. Enphase Orange 02 `#EA6100` is the workhorse accent on light; Orange 01 `#FF8B49` on dark. Use the named brand gradient for hero/illustration backdrops; do not invent new gradients.

## Type in one breath
**Inter** (substituting Visuelt) for everything; tight tracking on display sizes (`-0.02em`). **DM Mono** (substituting T-Star Pro) for technical accents — uppercase, `letter-spacing: 0.15em`, `line-height: 1.5`. Body 14–16px, headlines 26–80px. The license-substitution warning lives in README — surface it whenever the user wants pixel-perfect output.

## Layout in one breath
Compositions are made of **rounded-corner Tile Cards**. Page margin = 5% width; gutter = ¼ margin; corner radius = ½ margin. Prefer 6 / 12-column grids. No drop shadows on the logo, no inner shadows in general.

## When something is missing
The brand guide does not specify **motion** or full **iconography**. README documents the conventions we adopted (150–250ms ease-out; Lucide as icon substitute; etc) and flags those as substitutions. Surface those caveats to the user.

## Files at a glance
- `README.md` — full system spec
- `colors_and_type.css` — CSS variable tokens + helper classes
- `assets/` — logos, marks, product placeholders, illustration placeholders
- `preview/` — Design-System-tab cards (one per token group/component)
- `ui_kits/marketing-website/` — enphase.com-style page recreations
- `ui_kits/enphase-app/` — Enphase App (mobile) screen recreations
- `research/guidelines.txt` — plain-text extract of the official PDF
