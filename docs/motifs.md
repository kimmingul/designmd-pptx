# Visual motifs (SmartArt-like originals)

Reusable **visual formats** for designmd-pptx — the product path to
Infograpify-class rhythm **without** copying vendor templates or depending on
React UI libraries.

## What a motif is

A motif is a named layout grammar:

| | |
|--|--|
| **Owned geometry** | Our shapes, pads, bands — never Infograpify bytes |
| **Slots** | Content holes (`title`, `cards[]`, `steps[]`, …) |
| **Chrome** | Index discs, split panels, rising stairs, connectors |
| **Spacing** | Always `ui_kit.StageMetrics` |

Not PowerPoint SmartArt (`dgm:`). Extract of SmartArt already loses geometry;
motifs emit shape-level recipes compatible with the precision pipeline.

## Infograpify → motifs (400 decks collapse)

Local library: **400** licensed decks under `infograpify_ppt_templates/`
(gitignored). They are **not** converted 1:1 into 400 motifs.

```
400 Infograpify .pptx
        │  reference --catalog / deep structural reports
        ▼
13 family_hint buckets  +  layout_hints (kpi_band, card_row, …)
        │
        ▼
~66 owned motifs   (catalog schema 2)
        │
        ▼
75 recipes  (each maps to exactly one motif via RECIPE_TO_MOTIF)
```

| Layer | Count | Commit? |
|-------|------:|---------|
| Infograpify decks | 400 | **never** |
| `.ref-analysis/` | — | **never** |
| Motifs (builders) | ~66 | yes |
| Recipes | 75 | yes |

Hard rules: [infograpify-reference.md](infograpify-reference.md).

Coverage source of truth:

- `python/designmd_pptx/motifs/coverage.py` — `FAMILY_MOTIFS`, `RECIPE_TO_MOTIF`
- `python/designmd_pptx/motifs/catalog.json` — machine catalog (schema 2)
- `python/designmd_pptx/motifs/structural.py` — family builders
- `python/designmd_pptx/motif.py` — core builders + recipe adapters

## Catalog (schema 2)

| Family (Infograpify) | Motif examples |
|----------------------|----------------|
| narrative_chrome | `sparse_hero`, `section_mark`, `agenda_list`, `close_mark`, `quote_mark` |
| kpi_dashboard | `kpi_band`, `kpi_hero`, `kpi_grid`, `stat_row` |
| process_flow | `step_rail`, `funnel_cascade`, `chevron_flow`, `hub_orbit`, `pipeline_rail` |
| timeline_roadmap | `timeline_rail`, `swimlane_roadmap`, `gantt_track` |
| hierarchy | `pyramid_stack`, `iceberg_depth`, `pillar_band`, `org_cascade` |
| org_team | `org_cascade`, `team_cards`, `persona_split` |
| comparison_matrix | `matrix_quad`, `rich_matrix`, `vs_columns`, `risk_heat`, `raci_grid` |
| pricing_table | `pricing_tiers`, `data_table` |
| strategy_canvas | `canvas_bmc`, `pestle_cells`, `scorecard_grid` |
| chart_story | `chart_panel`, `venn_duo`, `ring_segments`, `waterfall_bars` |
| geo_map | `geo_pins`, `mindmap_radial`, `empathy_quad` |
| device_mockup | `device_chrome` |
| other (long-tail) | `card_row`, `hex_honey`, `check_stack`, `calendar_grid`, … |

Recipe adapters (complex charts/tables/domain) still run original recipe
geometry under a motif id (`chart_panel` → `chart_insight`, etc.).

### Golden one-pagers

```bash
export OFFICECLI_LEGACY_BIN=…   # legacy binary
PYTHONPATH=python python scripts/generate_motif_goldens.py
# → demo/motifs/<id>.pptx + .sequence.json + .contact.png for all catalog ids
PYTHONPATH=python python scripts/generate_motif_goldens.py --motifs hub_orbit,pyramid_stack
```

| Artifact | Tracked? |
|----------|----------|
| `<id>.sequence.json` | yes (preferred) |
| `<id>.contact.png` | yes when reviewed |
| `<id>.pptx` | local only (`*.pptx` gitignored except best/intro) |

## API

```python
from designmd_pptx.motif import render_motif, list_motifs, catalog
from designmd_pptx.motifs.coverage import RECIPE_TO_MOTIF

ops = render_motif("card_row", tokens, {
    "title": "Three promises",
    "cards": [{"title": "…", "body": "…"}, …],
})

# Every recipe name also resolves via RECIPE_TO_MOTIF:
assert RECIPE_TO_MOTIF["process"] == "step_rail"
```

## Workflow

```
local infograpify_ppt_templates/   (gitignored)
        │
        ▼
python -m designmd_pptx reference … -o .ref-analysis
        │  structural roles + rhythm only
        ▼
motifs/coverage.py + structural.py + catalog.json
        │
        ▼
recipes thin-wrap render_motif(...)  (or recipe-backed adapter)
        │
        ▼
scaffold / apply / Gate 3
```
