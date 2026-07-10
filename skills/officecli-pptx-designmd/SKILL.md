---
name: officecli-pptx-designmd
description: "designmd-pptx v1.1: compile awesome-design-md / Stitch DESIGN.md into officecli PPTX tokens, ordered decks, process connectors, image_text_2col, staging-safe apply. Trigger on DESIGN.md, getdesign.md, brand design for slides, /designmd-pptx, /officecli-pptx-designmd."
---

# officecli-pptx-designmd (v1.1)

## Locate the toolkit

Resolve the **Python package root** — first match wins:

1. `$env:DESIGNMD_PPTX_ROOT/python` — explicit override (project wins for edits)
2. `$env:CLAUDE_PLUGIN_ROOT/python` — Claude Code plugin install
3. `<this skill dir>/python` — Codex self-contained install (`~/.codex/skills/officecli-pptx-designmd/`)
4. `<this skill dir>/../../python` — repo checkout (`skills/officecli-pptx-designmd/`)
5. `<this skill dir>/../../../python` — Grok layout (`.grok/skills/officecli-pptx-designmd/`)
6. `~/.grok/installed-plugins/designmd-pptx-local/python` — Grok local install
7. project-local `./designmd-pptx/python`

Set for CLI:

```powershell
$env:PYTHONPATH = "<resolved python root>"
pip install -r "<resolved python root>\requirements.txt"
```

## Hard rules

1. Compile DESIGN.md → tokens (provenance + css_vars + warnings).
2. Prefer **deck-spec** (ordered, repeatable recipes).
3. Floors: title ≥36pt, body ≥18pt, micro 12–16 for KPI chips only.
4. No silent truncation — oversized content fails.
5. `image_full` / `image_text_2col`: `alt` required when `src` set.
6. Process uses **glued connectors** (`/slide[N]/shape[@name=…]`).
7. Overwrite only with `--force` / `DESIGNMD_FORCE=1` (staging-safe via `apply_sequence`).
8. QA: validate → view issues → Gate 3 screenshots (officecli-pptx skill).

## Commands

```powershell
$env:PYTHONPATH = "<python root>"
python -m designmd_pptx scaffold path\to\DESIGN.md -o out\brand --content <python root>\examples\content.deck.json
python -m designmd_pptx apply --force out\brand\deck.pptx out\brand\recipes\deck.sequence.json
# or thin wrapper after scaffold:
$env:DESIGNMD_FORCE=1; .\out\brand\apply.ps1
```

```text
python -m designmd_pptx compile DESIGN.md -o tokens.slide.json --slide-md SLIDE-DESIGN.md
python -m designmd_pptx recipes tokens.slide.json -o recipes/ --content content.deck.json
python -m designmd_pptx scaffold DESIGN.md -o out/brand --content content.deck.json [--apply --force]
python -m designmd_pptx apply [--force] dest.pptx recipes/deck.sequence.json
```

## Patterns

cover · section_divider · kpi_row · feature_cards · bullets · quote · comparison_2col · timeline · process · table · image_full · image_text_2col · chart_insight · close

## Colors

hex, rgb/hsl, oklch (approx), color-mix, var(--token), linear-gradient (2-stop officecli form).

## Requires

- Python 3.10+ with PyYAML (`pip install -r <python root>/requirements.txt`)
- Optional: [officecli](https://github.com/iOfficeAI/OfficeCLI) for materializing `.pptx`
