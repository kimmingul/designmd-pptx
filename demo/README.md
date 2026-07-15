# designmd-pptx demos (v2.1.2)

Premium product intro decks built on the **ui_kit** spacing contract
(`docs/ui-kit.md`) — content-height text, stage margins, no hollow slabs.

## Ship these

| File | Slides | Notes |
|------|--------|--------|
| **`designmd-pptx-best-v2.1.2.pptx`** | 12 | Motif showcase narrative (primary) |
| **`designmd-pptx-intro-v2.1.2.pptx`** | 12 | Same as best (stable name) |
| `*.contact.png` | — | Gate 3 contact sheets |
| `motifs/*` | ~66 | Full Infograpify structural motif goldens |

## Sources

| File | Role |
|------|------|
| `apple.DESIGN.md` | Spacious black stage · left cover · **pt** type |
| `content.best.deck.json` | 12-slide motif narrative |
| `content.flagship.deck.json` | Earlier 9-slide flagship |
| `content.intro.deck.json` | Deprecated 20-slide catalog (do not ship) |
| `scaffold/` | Latest tokens / recipes / apply wrappers |
| `motifs/` | Golden one-pagers (`scripts/generate_motif_goldens.py`) |
| `a11y.report.json` | Accessibility audit |

## Narrative (best / intro)

| # | Recipe | Motif / beat |
|---|--------|--------------|
| 1 | `cover` | `sparse_hero` — product name |
| 2 | `section_opener_numbered` | `section_mark` — contract |
| 3 | `kpi_row` | `kpi_band` — at a glance |
| 4 | `big_number` | **DESIGN.md** as source of truth |
| 5 | `before_after_slider` | Before → After |
| 6 | `process` | `step_rail` — authoring pipeline |
| 7 | `feature_cards` | `card_row` — three promises |
| 8 | `funnel_stages` | `funnel_cascade` |
| 9 | `matrix_2x2` | `matrix_quad` |
| 10 | `stairs_ascent` | Quality staircase |
| 11 | `checklist_board` | Hard rules |
| 12 | `close` | `doctor --ensure` |

**Not in this deck:** fake hex, circle segments, RACI grids, risk heat,
or catalog exhibition of all 75 builders.

## Rebuild

```bash
export PYTHONPATH=python
export OFFICECLI_LEGACY_BIN="$HOME/.local/share/designmd-pptx/officecli-legacy/officecli"

python -m designmd_pptx scaffold demo/apple.DESIGN.md \
  -o demo/scaffold \
  --content demo/content.best.deck.json \
  --apply --force --screenshot

cp demo/scaffold/Apple-Keynote-Flagship.pptx demo/designmd-pptx-best-v2.1.2.pptx
cp demo/scaffold/Apple-Keynote-Flagship.contact.png demo/designmd-pptx-best-v2.1.2.contact.png
cp demo/designmd-pptx-best-v2.1.2.pptx demo/designmd-pptx-intro-v2.1.2.pptx
cp demo/designmd-pptx-best-v2.1.2.contact.png demo/designmd-pptx-intro-v2.1.2.contact.png

python -m designmd_pptx animate demo/designmd-pptx-best-v2.1.2.pptx \
  -o demo/designmd-pptx-best-v2.1.2.pptx --entrance fade --transition fade --force
```

Requires **legacy** OfficeCLI for precision geometry.

## Motifs + UI kit

- **Motifs** (`docs/motifs.md`): SmartArt-like originals (`card_row`, `split_hero`,
  `step_rail`, `kpi_hero`, …) from Infograpify *structure* analysis — never
  vendor slides. Recipes call `render_motif`.
- **UI kit** (`docs/ui-kit.md`): margin/gap/pad contract; content-height body;
  no hollow text frames.

React UI libraries are **out of scope** for this product path.
