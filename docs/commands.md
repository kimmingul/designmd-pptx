# Command reference

```text
python -m designmd_pptx <command> …
# or after pip install:
designmd-pptx <command> …
```

| Command | Purpose |
|---|---|
| `compile <DESIGN.md> [-o tokens.json]` | DESIGN.md → tokens |
| `recipes <tokens.json> -o recipes/ [--content deck.json]` | Generate recipe ops |
| `scaffold <DESIGN.md\|default> -o out/ [--content] [--apply --force]` | Full pipeline to out dir |
| `apply <pptx> <deck.sequence.json> [--force] [--screenshot] [--gate3] [--vision]` | Staging-safe materialize |
| `extract <pptx> [-o extracted/]` | pptx → deck-spec draft + loss ledger |
| `restyle <pptx> <DESIGN.md> [-o new.pptx]` | Rebrand colors/fonts in place |
| `master <pptx> <DESIGN.md> [--potx] [--empty-potx] [--layouts]` | Brand masters / template |
| `compose <brief.md> [-o composed/] [--design] [--llm]` | Markdown outline → deck-spec |
| `render <brief\|deck.json> -o out.pptx [--design] [--images]` | Quick draft via agent-bridge |
| `reference <path\|dir> [-o .ref-analysis] [--catalog]` | License-safe structure inventory |
| `anonymize <pptx> [-o out.pptx] [--redact-text]` | PII strip for corpus admission |
| `corpus <manifest.json>` | Validate corpus + train/held-out split |
| `a11y [--tokens] [--deck] [--design] [--content] [--fix-contrast] …` | WCAG + order + alt/notes |
| `benchmark [-o out/] [--manifest] [--design] [--content]` | Before/after regression harness |
| `doctor [--strict] [--install [--dry-run]]` | Env + skill routing; pinned install |

Pass the literal `default` instead of a DESIGN.md path for the bundled neutral
house style.

## a11y

```bash
python -m designmd_pptx a11y --design default \
  --content python/examples/content.deck.json \
  --show-order -o out/a11y.report.json

# Opt-in repairs (still report warnings for generated fields):
python -m designmd_pptx a11y --tokens tokens.json --deck deck.json \
  --fix-contrast --generate-missing --write-corrected -o out/a11y.report.json
```

Exit code **1** when any error-severity finding remains — treat as “not clean”
before shipping.

## benchmark

```bash
# Fixture suite (CI default — no private corpus required)
python -m designmd_pptx benchmark -o benchmark-out

# Corpus held-out (skips missing assets with reason)
python -m designmd_pptx benchmark --manifest corpus/corpus.manifest.json -o benchmark-out
```

Thresholds: `python/designmd_pptx/benchmark_thresholds.json`.
