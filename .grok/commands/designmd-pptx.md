---
name: designmd-pptx
description: Scaffold or apply a DESIGN.md → officecli PPTX deck via designmd-pptx plugin
argument-hint: "[scaffold|apply|compile] [DESIGN.md path] [options]"
---

# /designmd-pptx

Use the **designmd-pptx** plugin (skill `officecli-pptx-designmd`).

## Default when args empty

1. Locate plugin Python root (`installed-plugins/designmd-pptx-local/python` or project `designmd-pptx/`).
2. If user gave a DESIGN.md path, run scaffold with `examples/content.deck.json`.
3. If officecli is available and user wants a pptx, run `python -m designmd_pptx apply --force …`.

## Args

- `scaffold <DESIGN.md> [-o out/dir]` — compile + recipes + apply wrappers
- `apply <pptx> <deck.sequence.json> [--force]` — staging-safe materialize
- `compile <DESIGN.md>` — tokens only

Always load skill `officecli-pptx-designmd` and follow its hard rules + officecli-pptx QA gates.
