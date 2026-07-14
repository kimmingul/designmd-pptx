# DESIGN.md schema v2 — richer design tokens (issue #11)

v2 adds five **optional** frontmatter sections — `composition`, `charts`,
`tables`, `images`, `master`. They are fully **backward compatible**: a v1
DESIGN.md compiles unchanged and every field defaults, so you adopt only what you
need. Invalid values fall back to the default with a compiler warning rather than
failing the build.

## Migrating

Add any of these blocks to your DESIGN.md YAML frontmatter. Nothing else changes.

```yaml
---
name: Acme
colors:
  primary: "#3B82F6"
  canvas: "#FFFFFF"
  ink: "#0F172A"

# --- v2 sections (all optional) ---
composition:
  whitespace_density: comfortable   # comfortable | compact | spacious
  title_placement: top              # top | left | center

charts:
  default_style: modern             # modern | classic | minimal
  series_colors: ["#3B82F6", "#10B981", "#F59E0B"]   # else derived from palette

tables:
  header_style: filled              # filled | underline | plain
  cell_padding_cm: 0.15             # 0.0–1.0
  stripe: true

images:
  crop_mode: fill                   # fill | fit | none
  placement: auto                   # auto | left | right | full

master:
  footer: "Confidential"            # string, or omit for none
  page_number: false
  navigation: false

# --- Phase 5 / #40 (optional; disabled unless present) ---
animation:
  enabled: true
  entrance: fade                    # none | appear | fade | wipe | fly_in
  transition: fade                  # none | fade | push | wipe | cut | cover
  transition_speed: med             # slow | med | fast
  stagger_ms: 150
  emphasis: none                    # only 'none' implemented (v2.1.x)
---
```

## Defaults

| Section | Field | Default |
|---|---|---|
| `composition` | `whitespace_density` | `comfortable` |
| | `title_placement` | `top` |
| `charts` | `default_style` | `modern` |
| | `series_colors` | derived from palette (`accent`, `chart_series2/3`, `success`, `risk`, …) |
| `tables` | `header_style` | `filled` |
| | `cell_padding_cm` | `0.15` |
| | `stripe` | `true` |
| `images` | `crop_mode` | `fill` |
| | `placement` | `auto` |
| `master` | `footer` | `null` |
| | `page_number` | `false` |
| | `navigation` | `false` |
| `animation` | `enabled` | `false` (omit block = off) |
| | `entrance` | `fade` |
| | `transition` | `fade` |

## In the compiled tokens

Each section appears as a top-level object in `tokens.slide.json`:

```json
{
  "version": "1.1",
  "composition": { "whitespace_density": "comfortable", "title_placement": "top" },
  "charts": { "default_style": "modern", "series_colors": ["3B82F6", "10B981"] },
  "tables": { "header_style": "filled", "cell_padding_cm": 0.15, "stripe": true },
  "images": { "crop_mode": "fill", "placement": "auto" },
  "master": { "footer": null, "page_number": false, "navigation": false }
}
```

The schema ([`tokens.slide.schema.json`](../python/designmd_pptx/schema/tokens.slide.schema.json))
enum-validates every field when `jsonschema` is installed (`pip install designmd-pptx[schema]`);
without it, structural checks still run.

> These tokens are the durable **input contract**. Downstream consumption is
> incremental: the layout engine, chart/table styling, and slide-master footer
> emission read these sections as those features land (Phase 1+). Defining the
> contract first means later work doesn't churn the DESIGN.md surface.
