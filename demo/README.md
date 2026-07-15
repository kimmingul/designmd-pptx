# designmd-pptx demos (v2.1.2)

Premium product intro decks built on the **ui_kit** spacing contract
(`docs/ui-kit.md`) — content-height text, stage margins, no hollow slabs.

## Ship these

| File | Slides | Notes |
|------|--------|--------|
| **`designmd-pptx-best-v2.1.2.pptx`** | 10 | Best-craft narrative (primary) |
| **`designmd-pptx-intro-v2.1.2.pptx`** | 10 | Same as best (stable name) |
| `*.contact.png` | — | Gate 3 contact sheets |

## Sources

| File | Role |
|------|------|
| `apple.DESIGN.md` | Spacious black stage · left cover · **pt** type |
| `content.best.deck.json` | 10-slide best narrative |
| `content.flagship.deck.json` | Earlier 9-slide flagship |
| `content.intro.deck.json` | Deprecated 20-slide catalog (do not ship) |
| `scaffold/` | Latest tokens / recipes / apply wrappers |
| `a11y.report.json` | Accessibility audit |

## Narrative (best / intro)

| # | Recipe | Beat |
|---|--------|------|
| 1 | `cover` | Left-hero product name |
| 2 | `big_number` | **DESIGN.md** as contract |
| 3 | `before_after_slider` | Before → After |
| 4 | `process` | Brief → Gate 3 + connectors |
| 5 | `feature_cards` | Three promises (01–03) |
| 6 | `pillar_columns` | Legacy / Official / Offline |
| 7 | `mission_vision_split` | North star |
| 8 | `stairs_ascent` | Quality staircase |
| 9 | `checklist_board` | Hard rules |
| 10 | `close` | `doctor --ensure` |

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

## UI kit (why this looks better than catalog demos)

- `StageMetrics`: margin / gap / pad from DESIGN.md density
- Body text = **content height**; free space → Spacer / stage air
- Layout engine strips vertical `weight` on Text leaves globally
- Comparison panels (before/after, mission/vision) share one contract

See `docs/ui-kit.md`.
