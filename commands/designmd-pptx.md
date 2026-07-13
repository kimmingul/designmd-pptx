---
name: designmd-pptx
description: Scaffold or apply a DESIGN.md → officecli PPTX deck via designmd-pptx
argument-hint: "[scaffold|apply|compile] [DESIGN.md path] [options]"
---

# /designmd-pptx

Use the **designmd-pptx** toolkit (skill `officecli-pptx-designmd`).

## Default when args empty

1. Locate the Python package root per the skill's "Locate the toolkit" resolution order.
2. If user gave a DESIGN.md path, run scaffold with `examples/content.deck.json`.
3. If officecli is available and user wants a pptx, run `python -m designmd_pptx apply --force …`.

## Args

- `scaffold <DESIGN.md> [-o out/dir]` — compile + recipes + apply wrappers
- `apply <pptx> <deck.sequence.json> [--force]` — staging-safe materialize
- `compile <DESIGN.md>` — tokens only
- `extract <pptx> [-o extracted/]` — existing deck → deck-spec draft + report + assets (review before scaffold)
- `restyle <pptx> <DESIGN.md|tokens.json> [-o new.pptx] [--force]` — rebrand existing deck in place (theme + explicit colors/fonts)
- `master <pptx> <DESIGN.md|tokens.json> [--potx brand.potx] [--empty-potx]` — brand theme/slide master; export .potx template
- `doctor [--strict]` — verify officecli + per-platform skill routing, print remedies

Pass the literal `default` instead of a DESIGN.md path to use the bundled neutral house style. Add `--screenshot` to apply/scaffold for a Gate 3 contact-sheet PNG.

Always load skill `officecli-pptx-designmd` and follow its hard rules + officecli-pptx QA gates.

$ARGUMENTS
