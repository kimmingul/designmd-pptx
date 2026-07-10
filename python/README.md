# designmd-pptx v1.1

Compile [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) / Stitch `DESIGN.md` into **officecli PPTX** tokens, ordered decks, and batch recipes.

## Install

```bash
cd designmd-pptx
pip install -r requirements.txt
# optional: OfficeCLI for materializing .pptx
```

## Quick start

```bash
python -m designmd_pptx scaffold fixtures/linear.DESIGN.md -o out/linear \
  --content examples/content.deck.json

cd out/linear
$env:DESIGNMD_FORCE=1; .\apply.ps1   # Windows — staging-safe overwrite
```

## Pipeline

```text
DESIGN.md  →  tokens.slide.json (+ provenance, css_vars, warnings)
content.deck.json  →  deck.sequence.json (ordered slides, absolute connector paths)
officecli batch (staging)  →  validate + issues  →  atomic replace → .pptx
```

## Deck-spec (canonical)

```json
{
  "version": "1.1",
  "slides": [
    {"id": "cover", "recipe": "cover", "content": {"title": "..."}},
    {"id": "flow", "recipe": "process", "content": {"steps": ["A","B","C"]}},
    {"id": "hero", "recipe": "image_text_2col", "content": {"title":"...","body":"...","src":"...","alt":"..."}}
  ]
}
```

Oversized content is **rejected**, not silently truncated. Flat overlays still migrate with a deprecation warning.

## Patterns

cover · section_divider · kpi_row · feature_cards · bullets · quote · comparison_2col · timeline · **process** (glued connectors) · table · image_full · **image_text_2col** · chart_insight · close

## Color parsing (v1.1)

| Form | Behavior |
|---|---|
| `#RGB` / `#RRGGBB` | solid |
| `rgb()` / `hsl()` (comma or space) | solid |
| `oklch()` | approximated to sRGB + warning |
| `color-mix(in srgb, …)` | sRGB mix + warning |
| `var(--name)` | resolves from DESIGN.md color keys / `--name` declarations |
| `var(--name, fallback)` | fallback when undefined |
| `linear-gradient` multi-stop | first+last stops for officecli 2-stop form + warning |
| radial/conic | explicit diagnostic, not applied |

## Apply safety

- Existing destination is **not deleted** until staging validate + issues pass
- Overwrite requires `--force` / `DESIGNMD_FORCE=1`
- Failed staging leaves the previous pptx intact

## Non-goals (still out of scope)

- Browser-identical oklch/wide-gamut pixels
- Full CSS cascade / `@media`
- Automated Gate 3 vision QA
- Figma sync / multi-brand merge / theme masters

## Tests

```bash
python -m unittest discover -s tests -v
```

See [ACCEPTANCE.md](./ACCEPTANCE.md).

## License

MIT — compiler only.
