# designmd-pptx demo deck (v2.1.2)

Product introduction deck — **20 slides**, English, Apple Keynote–inspired
style, heavy use of **Wave 4 Infograpify structural recipes**.

## Deliverable

| File | Description |
|------|-------------|
| **`designmd-pptx-intro-v2.1.2.pptx`** | Precision pipeline output (legacy OfficeCLI) + fade animations |
| `designmd-pptx-intro-v2.1.2.contact.png` | Gate 3 contact sheet |
| `apple.DESIGN.md` | Black canvas · system blue · SF/Helvetica stack |
| `content.intro.deck.json` | Deck-spec (20 slides) |
| `scaffold/` | Tokens, recipes, sequence, apply wrappers |
| `a11y.report.json` | Accessibility audit (0 errors) |

## Slide map (recipes)

| # | Recipe | Topic |
|---|--------|--------|
| 1 | `cover` | Title |
| 2 | `mission_vision_split` | North star |
| 3 | `icon_stat_row` | 75 / 14 / 2 / 3 pulse |
| 4 | `section_opener_numbered` | The problem |
| 5 | `before_after_slider` | Friction → floor |
| 6 | `empathy_map_quad` | Who we serve |
| 7 | `mindmap_branches` | Toolkit coverage |
| 8 | `journey_stages` | Authoring journey |
| 9 | `section_opener_numbered` | How it works |
| 10 | `pillar_columns` | Dual backends |
| 11 | `hex_cluster` | Recipe families |
| 12 | `circle_segments` | Catalog depth |
| 13 | `feature_cards` | Infograpify roles |
| 14 | `stairs_ascent` | Precision pipeline |
| 15 | `checklist_board` | Hard rules |
| 16 | `scorecard_balanced` | Quality scorecard |
| 17 | `raci_matrix` | Who owns the deck |
| 18 | `puzzle_pieces` | Platform fit |
| 19 | `risk_heat_matrix` | What we refuse |
| 20 | `close` | Start here |

Wave 4 roles used: mission/vision, empathy, mindmap, journey, pillars, hex,
circle, stairs, checklist, scorecard, RACI, puzzle, risk heat (plus core
cover / section / cards / before-after / icon stats).

## Rebuild

Requires **legacy** shape-level OfficeCLI for precise geometry
(`OFFICECLI_LEGACY_BIN` or PATH). Official agent-bridge alone is outline-only
and will not preserve Infograpify layouts.

```bash
export PYTHONPATH=python
export OFFICECLI_LEGACY_BIN="$HOME/.local/share/designmd-pptx/officecli-legacy/officecli"
# macOS: download from https://github.com/iOfficeAI/OfficeCLI/releases

python -m designmd_pptx scaffold demo/apple.DESIGN.md \
  -o demo/scaffold \
  --content demo/content.intro.deck.json \
  --apply --force --screenshot

cp demo/scaffold/Apple-Keynote-Intro.pptx demo/designmd-pptx-intro-v2.1.2.pptx
python -m designmd_pptx animate demo/designmd-pptx-intro-v2.1.2.pptx \
  -o demo/designmd-pptx-intro-v2.1.2.pptx \
  --entrance fade --transition fade --force
```

## Notes

- **OfficeCLI is required** for real `.pptx` materialization. Without it,
  `scaffold --apply` will not produce a working deck.
- Style is **original** Apple-inspired tokens (not an Apple template).
- Infograpify influence is **structural role analysis only** — original
  recipes, no vendor content.
