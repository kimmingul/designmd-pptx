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
| `extract <pptx> [-o extracted/]` | pptx → deck-spec draft + loss ledger (charts/tables modernized, #22) |
| `reconstruct <deck.json> [-o out.json]` | Modernize chart/table recipes in a deck-spec (#22) |
| `restyle <pptx> <DESIGN.md> [-o new.pptx]` | Rebrand colors/fonts in place |
| `master <pptx> <DESIGN.md> [--potx] [--empty-potx] [--layouts]` | Brand masters / template |
| `compose <brief.md> [-o composed/] [--design] [--llm]` | Markdown outline → deck-spec |
| `render <brief\|deck.json> -o out.pptx [--design] [--images]` | Quick draft via agent-bridge |
| `reference <path\|dir> [-o .ref-analysis] [--catalog]` | License-safe structure inventory |
| `anonymize <pptx> [-o out.pptx] [--redact-text]` | PII strip for corpus admission |
| `corpus <manifest.json>` | Validate corpus + train/held-out split |
| `a11y [--tokens] [--deck] [--design] [--content] [--fix-contrast] …` | WCAG + order + alt/notes |
| `benchmark [-o out/] [--manifest] [--public] [--design] [--content]` | Before/after harness; `--public` = ≥100-deck suite (#42) |
| `refine <deck.json> [-o refined/] [--feedback] [--findings] [--rounds]` | Iterative visual refinement (#19) |
| `generate <deck.json> [-o out/] [--directive] [--profile] [--contact]` | Hybrid generative layout (#21) |
| `animate <pptx> [-o out.pptx] [--entrance] [--transition] [--tokens]` | OOXML animation/transitions (#40) |
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

# Public ≥100-deck synthetic suite (#42) + methodology snapshot
python -m designmd_pptx benchmark --public --publish-docs -o public-benchmark-out
```

Thresholds: `python/designmd_pptx/benchmark_thresholds.json`.
Public methodology: [public-benchmark.md](public-benchmark.md).

## generate (#21)

```bash
# Natural-language style restyle (pattern map + freeform when needed)
python -m designmd_pptx generate content.deck.json -o generated \
  --directive "이 슬라이드를 Apple Keynote 스타일로 재구성해줘"

python -m designmd_pptx generate content.deck.json -o generated --profile minimal
python -m designmd_pptx generate --list-styles

# Then re-scaffold the generated deck-spec
python -m designmd_pptx scaffold default -o out/v2 \
  --content generated/content.generated.deck.json
```

Freeform placements are validated by `layout.solve_adaptive` before emission
so title/body floors still hold. Optional external layout generator:
`DESIGNMD_LAYOUT_CMD` / vision contact sheet via `--contact`.

## animate (#40)

DESIGN.md frontmatter:

```yaml
animation:
  enabled: true
  entrance: fade        # none | appear | fade | wipe | fly_in
  transition: fade      # none | fade | push | wipe | cut | cover
  transition_speed: med
  stagger_ms: 150
  emphasis: none        # none | pulse
```

```bash
# After scaffold/apply produced a .pptx
python -m designmd_pptx animate out/deck.pptx -o out/deck.animated.pptx \
  --entrance fade --transition fade --force

# Or compile animation from DESIGN.md
python -m designmd_pptx animate out/deck.pptx --design brand/DESIGN.md --force
```

Injection is namespace-safe OOXML (`opc` + lxml), not regex.

## refine (#19)

```bash
# Natural-language density feedback (2–3 rounds of deck-spec patches)
python -m designmd_pptx refine content.deck.json -o refined \
  --feedback "이 슬라이드는 너무 빽빽해요. 여백을 늘려주세요" --rounds 3

# From Gate 3 vision findings
python -m designmd_pptx refine content.deck.json -o refined \
  --findings out/deck.gate3.json --contact out/deck.contact.png

# Then re-scaffold
python -m designmd_pptx scaffold default -o out/v2 \
  --content refined/content.deck.json
```

Patches are deterministic (split lists, shorten bodies, recipe swaps, a11y notes).
Live vision models remain opt-in via `DESIGNMD_VISION_CMD` / `--vision-cmd`.
