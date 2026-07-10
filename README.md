# designmd-pptx

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.0-brightgreen)](plugin.json)

**awesome-design-md / Stitch `DESIGN.md` → [officecli](https://github.com/iOfficeAI/OfficeCLI) PPTX** — packaged as a **Grok Build plugin** (v1.1).

Drop a brand `DESIGN.md` in, scaffold an ordered deck, and materialize slides with staging-safe apply.

## What you get

| Piece | Role |
|---|---|
| `.grok/skills/officecli-pptx-designmd/` | Auto-loaded agent skill |
| `.grok/commands/designmd-pptx.md` | `/designmd-pptx` slash command |
| `python/designmd_pptx/` | Python CLI (`python -m designmd_pptx`) |
| `python/examples/`, `fixtures/`, `tests/` | Samples + tests |

Grok plugin layout: `plugin.json` + `.grok/skills` (not a Claude marketplace package by default).

## Requirements

- Python 3.10+
- `pip install -r python/requirements.txt` (PyYAML)
- Optional: [officecli](https://github.com/iOfficeAI/OfficeCLI) to write real `.pptx` files
- Node 18+ only for `node scripts/check-plugin.mjs`

## Install (Grok)

```powershell
git clone https://github.com/kimmingul/designmd-pptx.git
cd designmd-pptx

$dst = "$env:USERPROFILE\.grok\installed-plugins\designmd-pptx-local"
robocopy $PWD $dst /E /XD __pycache__ .git out /NFL /NDL /NJH /NJS
pip install -r "$dst\python\requirements.txt"
node "$dst\scripts\check-plugin.mjs"
```

See [.grok/docs/install.md](.grok/docs/install.md).

## CLI quick start

```powershell
$env:PYTHONPATH = "$PWD\python"   # or the installed-plugins path
python -m designmd_pptx scaffold python\fixtures\linear.DESIGN.md `
  -o out\demo --content python\examples\content.deck.json --brand Linear

# needs officecli on PATH
python -m designmd_pptx apply --force out\demo\Linear.pptx out\demo\recipes\deck.sequence.json
```

In Grok chat: mention DESIGN.md for slides, or run `/designmd-pptx`.

## Features (v1.1)

- **Deck-spec** — ordered, repeatable recipes (`kpi_row` twice, custom order)
- **Colors** — hex, rgb/hsl, oklch (approx), color-mix, `var(--token)`, linear-gradient
- **Process** — glued officecli connectors with arrowheads
- **`image_text_2col`** — image + body columns
- **Staging-safe apply** — destination replaced only after validate + issues pass

## Commands

```text
python -m designmd_pptx compile DESIGN.md -o tokens.slide.json
python -m designmd_pptx recipes tokens.slide.json -o recipes/ --content deck.json
python -m designmd_pptx scaffold DESIGN.md -o out/brand --content deck.json
python -m designmd_pptx apply [--force] dest.pptx recipes/deck.sequence.json
```

## Tests

```bash
export PYTHONPATH=python   # Windows: $env:PYTHONPATH = "python"
python -m unittest discover -s python/tests -v
node scripts/check-plugin.mjs
```

## License

MIT — see [LICENSE](LICENSE). Brand DESIGN.md tokens remain under their upstream collection terms.
