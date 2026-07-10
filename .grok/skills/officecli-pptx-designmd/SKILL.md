---
name: officecli-pptx-designmd
description: "Grok plugin designmd-pptx v1.1: compile awesome-design-md / Stitch DESIGN.md into officecli PPTX tokens, ordered decks, process connectors, image_text_2col, staging-safe apply. Trigger on DESIGN.md, getdesign.md, brand design for slides, /designmd-pptx, /officecli-pptx-designmd."
---

# officecli-pptx-designmd (plugin v1.1)

## Locate the plugin toolkit

Resolve **plugin root** from this skill file:

```text
SKILL.md → .grok/skills/officecli-pptx-designmd/
plugin root = ../../../   (three levels up)
Python package root = {plugin root}/python
```

Absolute fallback on this machine (if skill is installed):

```text
~/.grok/installed-plugins/designmd-pptx-local/python
```

Set for CLI:

```powershell
$PLUGIN = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path  # when cwd is skill dir
# or:
$PLUGIN = "$env:USERPROFILE\.grok\installed-plugins\designmd-pptx-local"
$env:PYTHONPATH = Join-Path $PLUGIN "python"
pip install -r (Join-Path $PLUGIN "python\requirements.txt")
```

Also accept project-local `./designmd-pptx/` or `DESIGNMD_PPTX_ROOT` if set (project wins for edits).

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
$env:PYTHONPATH = "<plugin>/python"
python -m designmd_pptx scaffold path\to\DESIGN.md -o out\brand --content <plugin>\python\examples\content.deck.json
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

- Python 3.10+ with PyYAML (`pip install -r python/requirements.txt`)
- Optional: [officecli](https://github.com/iOfficeAI/OfficeCLI) for materializing `.pptx`
