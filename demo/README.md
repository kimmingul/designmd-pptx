# designmd-pptx flagship demo (v2.1.2)

**External-facing product intro** — **9 slides**, English, spacious Keynote-inspired
stage. Built as a **flagship vertical slice**, not a recipe catalog.

> This replaces the earlier 20-slide Wave 4 inventory demo, which exposed weak
> geometries (fake hex / segments / RACI grids) and failed as marketing quality.

## Deliverable

| File | Description |
|------|-------------|
| **`designmd-pptx-intro-v2.1.2.pptx`** | Precision pipeline + fade animations |
| `designmd-pptx-intro-v2.1.2.contact.png` | Gate 3 contact sheet |
| `apple.DESIGN.md` | Spacious black stage · `title_placement: left` · **pt** type sizes |
| `content.flagship.deck.json` | 9-slide product narrative |
| `content.intro.deck.json` | Legacy catalog draft (do not ship) |
| `scaffold/` | Tokens, recipes, sequence, apply wrappers |
| `a11y.report.json` | Accessibility audit |

## Narrative (9 slides)

| # | Recipe | Purpose |
|---|--------|---------|
| 1 | `cover` | Left-hero product name |
| 2 | `big_number` | **DESIGN.md** as the contract |
| 3 | `before_after_slider` | Without → with |
| 4 | `process` | Brief → Gate 3 (glued connectors) |
| 5 | `feature_cards` | Precise geometry · gates · agents |
| 6 | `pillar_columns` | Legacy / official / offline |
| 7 | `stairs_ascent` | Quality staircase |
| 8 | `checklist_board` | Hard rules |
| 9 | `close` | `doctor --ensure` |

**Intentionally omitted:** fake hex, circle segments, mindmap-as-chips, RACI,
risk heat, and other structural-role showcases that dilute the sales argument.

## What we fixed vs the catalog demo

| Problem | Flagship response |
|---------|-------------------|
| Catalog exhibition (20 roles) | 9-slide persuasion arc |
| Fake diagram geometries | Only recipes that read as product truth |
| “Airy” ignored | `whitespace_density: spacious` → margin 2.2 / gap 1.1 |
| SF Pro → silent shrink via px | Type sizes in **pt** (48 / 36 / 18) |
| Same chrome every slide | Left cover edge, process connectors, stairs, pillars |
| Engineering gates only | Contact sheet + human narrative review |

## Rebuild

Requires **legacy** shape-level OfficeCLI (`OFFICECLI_LEGACY_BIN` or PATH).

```bash
export PYTHONPATH=python
export OFFICECLI_LEGACY_BIN="$HOME/.local/share/designmd-pptx/officecli-legacy/officecli"
# macOS: https://github.com/iOfficeAI/OfficeCLI/releases

python -m designmd_pptx scaffold demo/apple.DESIGN.md \
  -o demo/scaffold \
  --content demo/content.flagship.deck.json \
  --apply --force --screenshot

cp demo/scaffold/Apple-Keynote-Flagship.pptx demo/designmd-pptx-intro-v2.1.2.pptx
cp demo/scaffold/Apple-Keynote-Flagship.contact.png demo/designmd-pptx-intro-v2.1.2.contact.png
python -m designmd_pptx animate demo/designmd-pptx-intro-v2.1.2.pptx \
  -o demo/designmd-pptx-intro-v2.1.2.pptx \
  --entrance fade --transition fade --force
```

## Honest limits

- OfficeCLI is **required** for materialization.
- SF Pro is not embedded; Helvetica Neue / Arial is the portable stack.
- This deck proves a **small set of strong recipes**, not “75 builders look
  premium.” Catalog depth is a product claim for docs — not this demo.
- Original design tokens only; no vendor templates.

## Related engine changes (this branch)

- `compile.py`: `spacious` / `compact` density maps to real `margin_cm` / `gap_cm`
- `recipes.py`: stronger cover (left hero), process (numbered + connectors),
  big_number scale, close CTA, stairs detail text
