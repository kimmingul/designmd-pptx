# SLIDE-DESIGN.md — Northstar-Board-Flagship

> Compiled from `demo/northstar.DESIGN.md` by designmd-pptx v2.1.2.

## Atmosphere

Series B board showcase house style — spacious black stage, one blue accent, left-hero covers. Fork of the flagship tokens (original, not an Apple or Infograpify template). Tuned for an 18–20 slide narrative that exercises structural motifs.

**Motif:** `hairline-card-on-dark`  
**Dark-first:** `True`  
**Content BG policy:** `match_canvas`

## Tokens (officecli props)

| Role | Hex | Provenance |
|---|---|---|
| `background` | `000000` | sourced |
| `content_background` | `000000` | sourced |
| `surface` | `1C1C1E` | sourced |
| `surface_elevated` | `2C2C2E` | sourced |
| `accent` | `0B5FFF` | sourced |
| `on_accent` | `FFFFFF` | sourced |
| `text` | `F5F5F7` | derived |
| `text_on_surface` | `F5F5F7` | derived |
| `text_on_content` | `F5F5F7` | derived |
| `muted` | `A0A6B0` | sourced |
| `hairline` | `3A3A3C` | sourced |
| `success` | `30D158` | sourced |
| `risk` | `FF453A` | sourced |
| `chart_series1` | `0B5FFF` | sourced |
| `chart_series2` | `91B7FF` | derived |
| `chart_series3` | `30D158` | sourced |

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
