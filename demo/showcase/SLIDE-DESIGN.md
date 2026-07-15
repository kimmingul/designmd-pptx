# SLIDE-DESIGN.md — Northstar-Board-Flagship

> Compiled from `demo/northstar.DESIGN.md` by designmd-pptx v2.1.2.

## Atmosphere

Series B board showcase — deep indigo stage, multi-hue accent system (violet / cyan / magenta / lime / amber). Original tokens, not a vendor template. Tuned for a colorful 20-slide motif narrative.

**Motif:** `hairline-card-on-dark`  
**Dark-first:** `True`  
**Content BG policy:** `match_canvas`

## Tokens (officecli props)

| Role | Hex | Provenance |
|---|---|---|
| `background` | `0B0B1A` | sourced |
| `content_background` | `0B0B1A` | sourced |
| `surface` | `16162E` | sourced |
| `surface_elevated` | `22224A` | sourced |
| `accent` | `7C5CFF` | charts.series_colors[0] |
| `on_accent` | `FFFFFF` | sourced |
| `text` | `F4F2FF` | derived |
| `text_on_surface` | `F4F2FF` | derived |
| `text_on_content` | `F4F2FF` | derived |
| `muted` | `A0A6B0` | sourced |
| `hairline` | `3A3570` | sourced |
| `success` | `3DDC97` | sourced |
| `risk` | `FF4D6D` | sourced |
| `chart_series1` | `7C5CFF` | charts.series_colors |
| `chart_series2` | `22D3EE` | charts.series_colors |
| `chart_series3` | `F472B6` | charts.series_colors |

## Type

- Heading font: **Arial**
- Body font: **Arial**
- Cover: 48pt · Title: 36pt · Body: 18pt
- KPI: 60pt · Micro/chip: 14pt · Caption: 12pt

## Canvas

- 33.87 × 19.05 cm
- Margin ≥ 2.2 cm · Gap ≥ 1.1 cm

## Patterns

- `cover` → recipes/cover.json
- `section_divider` → recipes/section_divider.json
- `kpi_row` → recipes/kpi_row.json
- `feature_cards` → recipes/feature_cards.json
- `bullets` → recipes/bullets.json
- `quote` → recipes/quote.json
- `comparison_2col` → recipes/comparison_2col.json
- `timeline` → recipes/timeline.json
- `process` → recipes/process.json
- `table` → recipes/table.json
- `image_full` → recipes/image_full.json
- `image_text_2col` → recipes/image_text_2col.json
- `chart_insight` → recipes/chart_insight.json
- `close` → recipes/close.json

## Compiler warnings

- font.heading: 'Helvetica Neue' → 'Arial' (PowerPoint-safe substitute)
- font.body: 'Helvetica Neue' → 'Arial' (PowerPoint-safe substitute)

## Dropped web concerns

- hover
- focus
- breakpoints
- responsive
- nav
- inputs
- forms
- touch-targets
- scroll
- z-index-stacking-beyond-shapes
- css-gradients-as-background-unless-officecli-gradient-prop

## Agent rules

1. Use only hex tokens above for `background`, `fill`, `color`, chart series.
2. Never go below body 18pt / title 36pt (micro chips may be 12–16pt).
3. One idea per slide; use section_divider between arcs.
4. Prefer `batch` with recipe JSON; then `validate` + `view issues`.
5. Do not reintroduce hover, nav, or form components.
6. If provenance is `fallback`, treat color as untrusted — prefer fixing DESIGN.md keys.
