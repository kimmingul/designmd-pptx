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

## Catalog (v1)

| Motif id | Role | Recipes |
|----------|------|---------|
| `split_hero` | Two equal panels | `before_after_slider`, `mission_vision_split` |
| `card_row` | 2–4 indexed cards | `feature_cards` |
| `step_rail` | Numbered process + connectors | `process` |
| `kpi_hero` | Mega metric | `big_number` |
| `stair_ascent` | Rising maturity steps | `stairs_ascent` |
| `check_stack` | Checklist rows | `checklist_board` |
| `tile_row` | Equal tiles | `puzzle_pieces` |

Machine-readable: `python/designmd_pptx/motifs/catalog.json`.

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
