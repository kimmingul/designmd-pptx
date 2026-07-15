# designmd-pptx demos (v2.1.2)

Premium decks on the **ui_kit** spacing contract (`docs/ui-kit.md`) —
content-height text, stage margins, no hollow slabs.

## Ship these

| File | slides | Notes |
|------|--------|--------|
| **`designmd-pptx-showcase-northstar.pptx`** | 20 | **Primary motif showcase** — Series B board story |
| **`designmd-pptx-best-v2.1.2.pptx`** | 12 | Product intro (designmd-pptx itself) |
| **`designmd-pptx-intro-v2.1.2.pptx`** | 12 | Same as best (stable name) |
| `*.contact.png` | — | Gate 3 contact sheets |
| `motifs/*` | ~66 | Structural motif goldens (atlas, not a narrative) |

## Sources

| File | Role |
|------|------|
| `northstar.DESIGN.md` | Showcase brand (apple token fork · **pt** type) |
| `content.showcase.deck.json` | 20-slide Northstar board narrative |
| `apple.DESIGN.md` | Product intro house style |
| `content.best.deck.json` | 12-slide product intro |
| `content.flagship.deck.json` | Earlier 9-slide flagship |
| `content.intro.deck.json` | Deprecated catalog (do not ship) |
| `showcase/` | Northstar scaffold + apply wrappers |
| `scaffold/` | Best-intro tokens / recipes |
| `motifs/` | Golden one-pagers (`scripts/generate_motif_goldens.py`) |

## Narrative (Northstar showcase)

| # | Recipe | Motif / beat |
|---|--------|--------------|
| 1 | `cover` | `sparse_hero` — Northstar AI |
| 2 | `section_opener_numbered` | `section_mark` — The bet |
| 3 | `kpi_row` | `kpi_band` — ARR / NRR / runway |
| 4 | `big_number` | `kpi_hero` — 3.4× coverage |
| 5 | `before_after_slider` | `split_hero` |
| 6 | `process` | `step_rail` — decide loop |
| 7 | `funnel_stages` | `funnel_cascade` |
| 8 | `feature_cards` | `card_row` — three promises |
| 9 | `section_opener_numbered` | The machine |
| 10 | `org_tree` | `org_cascade` |
| 11 | `cycle_loop` | operating loop |
| 12 | `timeline` | milestones |
| 13 | `pillar_columns` | invest |
| 14 | `matrix_2x2` | `matrix_quad` + axes |
| 15 | `roadmap_swimlane` | H2 lanes |
| 16 | `pricing` | packaging |
| 17 | `risk_heat_matrix` | risk heat |
| 18 | `project_status_rag` | program RAG |
| 19 | `checklist_board` | `check_stack` — board asks |
| 20 | `close` | one ask |

**Not a catalog** of all 66 motifs — a single business story that *uses* them.

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

### Northstar showcase (primary)

```bash
export PYTHONPATH=python
export OFFICECLI_LEGACY_BIN="$HOME/.local/share/designmd-pptx/officecli-legacy/officecli"

python -m designmd_pptx scaffold demo/northstar.DESIGN.md \
  -o demo/showcase \
  --content demo/content.showcase.deck.json \
  --apply --force --screenshot

cp demo/showcase/Northstar-Board-Flagship.pptx demo/designmd-pptx-showcase-northstar.pptx
cp demo/showcase/Northstar-Board-Flagship.contact.png demo/designmd-pptx-showcase-northstar.contact.png

python -m designmd_pptx animate demo/designmd-pptx-showcase-northstar.pptx \
  -o demo/designmd-pptx-showcase-northstar.pptx --entrance fade --transition fade --force
```

### Product intro (best / intro)

```bash
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
