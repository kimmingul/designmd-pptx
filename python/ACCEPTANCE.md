# designmd-pptx v1.1 — Definition of Done

## Acceptance criteria

| # | Criterion | Evidence |
|---|---|---|
| 1 | Package/compiler **1.1.x** | `__version__`, `COMPILER_VERSION`, tokens.compiler.version |
| 2 | `var(--name)` resolves without fallback when defined | `tests/test_v11.py` ColorV11 + fixtures/var-oklch.DESIGN.md |
| 3 | Unresolved vars diagnose; fallback form works | same |
| 4 | oklch / color-mix → RRGGBB with diagnostics | ColorV11 |
| 5 | Multi-stop linear → first/last + warn; radial explicit fail | ColorV11 |
| 6 | Process emits glued `connector` ops with arrowheads | ProcessConnectors + officecli apply |
| 7 | `image_text_2col` first-class recipe + alt when src | ImageText2Col + patterns list |
| 8 | Apply staging + force refuse | ApplyStaging |
| 9 | Dark + light (+ var) fixtures compile | unittest + scaffold |
| 10 | Docs describe v1.1; closed gaps removed from "open" lists | README / skill / this file |

## Verification commands

```bash
python -m unittest discover -s tests -v
python -m designmd_pptx scaffold fixtures/linear.DESIGN.md -o out/linear --content examples/content.deck.json
python -m designmd_pptx scaffold fixtures/light-notionish.DESIGN.md -o out/light --content examples/content.deck.json
# with officecli:
$env:DESIGNMD_FORCE=1; cd out/linear; .\apply.ps1
```
