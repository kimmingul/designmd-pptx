# Visual motifs (SmartArt-like originals)

Reusable **visual formats** for designmd-pptx — the product path to Infograpify-class
rhythm **without** copying vendor templates or depending on React UI libraries.

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

## Infograpify workflow (license-safe)

```
local infograpify_ppt_templates/   (gitignored)
        │
        ▼
python -m designmd_pptx reference … -o .ref-analysis
        │  structural roles + rhythm only
        ▼
motifs/catalog.json   +   motif.py builders   (original code, commit OK)
        │
        ▼
recipes thin-wrap render_motif(...)
        │
        ▼
scaffold / apply / Gate 3
```

Hard rules: [infograpify-reference.md](infograpify-reference.md).

## Catalog (v1 → v1.1)

Driven by local `.ref-analysis` layout_hints (kpi_band, card_row, sparse_hero,
matrix_like, connectors) — **filenames/structure only**.

| Motif id | Role | ref hint | Recipes |
|----------|------|----------|---------|
| `sparse_hero` | Cover / large type | sparse_hero | `cover` |
| `section_mark` | Numbered section | sparse_hero | `section_opener_numbered` |
| `kpi_band` | 2–4 metric cards | kpi_band | `kpi_row` |
| `kpi_hero` | Mega metric | kpi_band | `big_number` |
| `split_hero` | Two equal panels | comparison | `before_after`, `mission_vision` |
| `card_row` | Indexed cards | card_row_3/4 | `feature_cards` |
| `step_rail` | Process + connectors | has_connectors | `process` |
| `funnel_cascade` | Decreasing bands | process_flow | `funnel_stages` |
| `matrix_quad` | 2×2 cells | matrix_like | `matrix_2x2` |
| `stair_ascent` | Rising steps | hierarchy | `stairs_ascent` |
| `check_stack` | Checklist | — | `checklist_board` |
| `tile_row` | Equal tiles | card_row | `puzzle_pieces` |

Machine-readable: `python/designmd_pptx/motifs/catalog.json`.

### Golden one-pagers

```bash
export OFFICECLI_LEGACY_BIN=…   # legacy binary
PYTHONPATH=python python scripts/generate_motif_goldens.py
# → demo/motifs/<id>.pptx + contact screenshots
```

## API

```python
from designmd_pptx.motif import render_motif, list_motifs, catalog

ops = render_motif("card_row", tokens, {
    "title": "Three promises",
    "cards": [{"title": "…", "body": "…"}, …],
})
```

```bash
python -c "from designmd_pptx.motif import list_motifs; print(list_motifs())"
```

## Roadmap

1. Grow motifs from `.ref-analysis` layout_hints (card_row_3, kpi_band, …).
2. Attach **golden contact sheets** per motif (our output only).
3. Map more recipes onto motifs; leave asset-heavy roles (maps, devices) deferred.
