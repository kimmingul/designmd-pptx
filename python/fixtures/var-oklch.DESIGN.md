---
version: alpha
name: Var-OKLCH-Sample
description: "Fixture exercising CSS variables, oklch, and color-mix for designmd-pptx v1.1."

colors:
  --brand: "#0B5FFF"
  --canvas: "#0A0A0B"
  --ink: "#F5F5F5"
  canvas: "var(--canvas)"
  primary: "var(--brand)"
  ink: "var(--ink)"
  surface-1: "color-mix(in srgb, var(--canvas) 80%, white 20%)"
  accent-ok: "oklch(0.65 0.18 250)"
  gradient: "linear-gradient(120deg, var(--brand), oklch(0.75 0.12 200))"
  semantic-success: "hsl(140 45% 38%)"

typography:
  display-xl:
    fontFamily: Arial
    fontSize: 48px
  body:
    fontFamily: Calibri
    fontSize: 18px
---

## Overview

Uses `var(--brand)` without requiring a fallback when defined in colors.
Also documents a free CSS custom property:

```css
:root {
  --extra-muted: #9AA0A6;
}
```
