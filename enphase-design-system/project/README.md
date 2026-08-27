# Enphase Design System

A design system for **Enphase Energy** — the global leader in solar microinverters, batteries, EV chargers, and home energy management. Founded in 2006, headquartered in Fremont, CA. Enphase has shipped 60M+ microinverters across 145+ countries and powers 3.5M+ homes worldwide.

This system is derived from the official **Enphase Visual Identity Guidelines v1.3** (provided as `uploads/Enphase_Guidelines_V1_3.pdf`, plain-text extract at `research/guidelines.txt`) and the public marketing site at https://enphase.com.

---

## Sources used

| Source | Type | Notes |
|---|---|---|
| `uploads/Enphase_Guidelines_V1_3.pdf` | Brand guidelines | Official 86-page identity guide. Authoritative source for color, type, layout. |
| https://enphase.com/homepage | Marketing site | Tone, content vocabulary, product naming, photo direction. |
| https://enphase.com/trademark-usage-guidelines | Trademark | Legal usage rules for the marks. |

---

## Products represented

Enphase ships a system of products, all branded **IQ**:

- **IQ Microinverters** — IQ7, IQ8 Series, IQ9 (commercial); core technology
- **IQ Batteries** — IQ Battery 5P, IQ Battery 10C; lithium iron phosphate storage
- **IQ EV Charger 2** — Home & commercial EV charging
- **IQ PowerPack** — Portable power station
- **IQ Solid-State Transformer** — Data-center power conversion (new product line)
- **IQ Gateway / IQ Combiner / IQ System Controller** — Communication & control hardware
- **Enphase App** — Mobile + web app for system monitoring (formerly Enlighten)

**Audiences:** Homeowners · Business owners · Installers · Data centers

---

## Index — what's in this folder

```
README.md                  This file
SKILL.md                   Agent skill manifest (Claude Code compatible)
colors_and_type.css        Color + type tokens as CSS vars + semantic classes
research/
  guidelines.txt           Plain-text extract of the official PDF
assets/
  enphase-logo.svg         Horizontal logo lockup (orange mark + dark gray wordmark)
  enphase-logo-white.svg   Horizontal lockup, all-white (use on dark / imagery)
  enphase-mark.svg         The "E" arc mark only (orange)
  product-iq8.svg          IQ8 microinverter product placeholder render
  product-battery.svg      IQ Battery placeholder render
  product-ev-charger.svg   IQ EV Charger 2 placeholder render
  hero-rooftop.svg         Lifestyle illustration placeholder (rooftop/sun)
  illustration-sun.svg     Sun gradient illustration
preview/                   Design System tab cards (700×N each)
ui_kits/
  marketing-website/       Enphase.com-style components
  enphase-app/             Mobile app (energy dashboard) components
```

---

## Content Fundamentals — voice & copy

Enphase writes for homeowners who want clean energy without engineering jargon, while still respecting the technical reader (installer, data-center buyer). The voice is **confident, optimistic, technically literate, and warm** — never hyped, never preachy.

**Casing**
- Headlines and CTAs: **sentence case, always.** Never all-caps for headlines.
- Technical labels (eyebrows, data, captions): **ALL CAPS** in T-Star Pro with 150-unit letter-spacing.
- Product names: title case — *IQ Battery 10C*, *IQ8 Microinverter*, *Enphase App*.

**Pronouns**
- "**You**" and "**your**" speak directly to the reader. ("Take control of your energy.")
- "**We**" / "our" refer to Enphase as a company in editorial/about contexts.

**Tone & vibe**
- Calm certainty, not exclamation. Periods, not exclamation points.
- Short, declarative sentences for headlines: *"The best just got better."*, *"Make, use, save, and sell — on your terms."*
- Body copy is plain English with the tech lifted to the surface: *"With one microinverter per module, solar production keeps working even if a microinverter fails."*

**No emoji.** Emoji are not part of the Enphase voice.

**Trademarks** — registered marks (®, ™) appear at first prominent use of the wordmark and product names per Enphase trademark guidelines.

**Examples (verbatim from enphase.com)**
- *"Take control of your energy. Make, use, save, and sell — on your terms."*
- *"On or off the grid, our smartest microinverter ever."*
- *"Smarter. Tougher. Future-ready."*
- *"Your ultimate solar guide."*

---

## Visual Foundations

### Colors — neutrals
A **warm, sunlight-on-a-white-wall** neutral palette. Avoid cold tech grays.
- White `#FFFFFF`, Warm White `#FAF6EF`, Gray 04 `#F4F3F0`, Gray 03 `#DCDCD6`, Gray 02 `#7D7D7D`, Gray 01 `#3C3C3C`, Black `#000000`.

### Colors — brand
Two parallel sets, **light-theme** (use on white/warm white) and **dark-theme** (use on black/gray 01). The orange is *Enphase Orange* (PMS 1665 historically; in v1.3, light-theme Orange 02 = `#EA6100`, dark-theme Orange 01 = `#FF8B49`). Coral, Indigo, Teal, Yellow, Green, Pink, Light Blue round out the optimistic, "colors found around the home" palette. **Avoid harsh, synthetic, digital colors.**

### Gradients
Five named, all 90° vertical, end-to-end fixed to container height:
- **Brand gradient** (Orange 01 → Coral → Yellow → Teal-green) — workhorse background, depth, product backdrops
- **Sunrise** (warm orange → coral → light blue), **Sunset** (pink → coral → indigo) — illustration backgrounds only
- **Spotlight Orange / Green / Blue** — UI moments and illustration backgrounds

**Misuse**: don't add stops, layer, flip angle, or invent new gradients.

### Typography
- **Primary: Enphase Visuelt** — humanist geometric sans for headlines, body, CTAs. Sentence case only. Regular default; Medium for sub-heads; Bold only for in-body emphasis.
- **Secondary: T-Star Pro** — mono-line grotesque, technical feel. **Always uppercase, 150-unit letter-spacing, 1.5× leading.** Used for eyebrows, captions, data labels, technical info. Never for body copy or headlines.

> **Visuelt is loaded from `fonts/`** as the official licensed family (Light/Regular/Medium/Bold + italics, woff2 + woff). T-Star Pro is still substituted with **DM Mono** until the licensed files are provided.

### Layout & composition
- Compositions built on **rounded-corner Tile Cards** — derived from solar-cell shapes.
- **Margins**: 5% of width (vertical/square) or 5% of height (horizontal); extreme formats may use 6–20%.
- **Gutters**: ¼ of margin (so 5% margin → 1.25% gutter).
- **Columns**: prefer multiples of 3 (6 col vertical, 12 col horizontal).
- **Corner radius = ½ margin.** A 96px margin → 48px radius.
- Composition modules: single-image tile, stacked tiles, text-and-image, split tiles, asymmetric tile grids.

### Photography & imagery
- **Lifestyle**: warm light, real homes/families, everyday moments, illumination as narrative device.
- **Outdoor**: long-exposure dawn/dusk, starlight, adventure-but-approachable.
- **Product**: 3D renders on solid black or brand-gradient backgrounds, lit as if at sunrise/sunset (warm light cast on hardware).
- **Illustration**: simple shapes + gradient color + light texture; editorial feel; dawn/dusk themes.
- **Color vibe**: warm, never cold/grainy/desaturated.

### Iconography
- Constructed on **24×24 grid, 1-unit stroke**.
- **Rounded corners and terminals** — friendly, approachable.
- See `ICONOGRAPHY` section below for detail.

### Animation, hover, press states
The brand guidelines do not specify motion. From observed product behavior on enphase.com:
- **Hover**: subtle darken on text/links (gray 01 → black) or fill on buttons (Orange 02 → Orange 01-darker).
- **Press**: 95% scale + reduced shadow, no color change.
- **Transitions**: 150–250ms, ease-out. No bounce. No spring.
- **Loading**: simple spinner or skeleton; brand gradient may animate as backdrop.

### Borders & shadows
- **Borders**: Gray 03 `#DCDCD6` for hairlines, 1px.
- **Shadows**: subtle, warm-tinted using Gray 01 at low alpha (see `--enph-shadow-*` tokens).
- **No drop shadows on the logo.** No inner shadows in general.

### Radii summary
- Buttons / pills: fully rounded (`--enph-radius-pill`)
- Cards / inputs: 16–24px (`--enph-radius-md` / `--enph-radius-lg`)
- Hero tiles: up to 48px (`--enph-radius-xl`)

### Transparency & blur
Used sparingly. Glassy/blurred surfaces are **not** native to Enphase — opaque tiles and gradient backdrops are preferred.

---

## Iconography

Enphase uses a **custom outlined icon set** built on a 24×24 grid with 1-unit strokes and rounded terminals. We did not have access to the Enphase icon font directly. As a substitute the system uses **[Lucide Icons](https://lucide.dev)** loaded from CDN — the closest free match (rounded, 1u stroke, 24×24 grid). Specific Enphase product icons (microinverter, IQ Battery, gateway) are stylized SVGs in `assets/`.

> **Substitution flagged**: please share Enphase's official icon library (Figma symbols or SVG sprite) so we can swap in 1:1.

**Usage rules**
- Icons are **outlined**, not filled, except for the Enphase mark itself.
- Stroke weight scales with icon size: 1u at 24px, 1.5u at 32px, 2u at 48px.
- Icons inherit `currentColor` so they recolor with surrounding text.
- **Emoji are never used** as icons in the Enphase brand voice.
- **Unicode characters** (arrows like `→`) are acceptable in CTA links — see CTA construction page in guidelines: `Learn more →`.

---

## CAVEATS

- **Visuelt is now official** — loaded from `fonts/EnphaseVisuelt-*` (woff2/woff/ttf). T-Star Pro is still substituted with DM Mono.
- **Logo is a hand-built stylized recreation** — the shapes match the lockup spec (orange "e" donut + lowercase wordmark) but are not the official outlined SVG. Drop in the official `enphase-logo.svg` if pixel-perfect output is required.
- **Product imagery is placeholders** — we draw stylized SVGs for IQ8, IQ Battery, IQ EV Charger, sun, rooftop. Replace with the official 3D renders for production work.
- **Icons are Lucide CDN** — substituted.
- **Voice examples** are quoted verbatim from public enphase.com pages; we treat them as illustrative, not exhaustive.

See `SKILL.md` for skill manifest. See `preview/` for individual design-system cards. See `ui_kits/` for component recreations.
