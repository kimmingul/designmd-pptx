# Example gallery walkthrough

End-to-end path: **house style DESIGN.md → deck-spec → a11y → (optional) PPTX**.

## 1. Inputs

| Asset | Path |
|---|---|
| Design | `python/designmd_pptx/default.DESIGN.md` (or `default` literal) |
| Content | `python/examples/content.deck.json` |
| Medical catalog example | `python/examples/content.medical.deck.json` |
| Brand fixtures | `python/fixtures/*.DESIGN.md` |

## 2. Scaffold (tokens + recipes; no OfficeCLI required)

```bash
export PYTHONPATH=python
python -m designmd_pptx scaffold default -o out/gallery-demo \
  --content python/examples/content.deck.json
```

Outputs:

- `out/gallery-demo/tokens.slide.json`
- `out/gallery-demo/recipes/deck.sequence.json`
- `out/gallery-demo/deck.spec.json`
- `apply.ps1` / `apply.sh` wrappers

## 3. Accessibility gate

```bash
python -m designmd_pptx a11y \
  --tokens out/gallery-demo/tokens.slide.json \
  --deck python/examples/content.deck.json \
  --show-order -o out/gallery-demo/a11y.report.json
```

Expect **PASS** for the house style + example deck. Add `src`+`alt` on image
slides before a client deliverable.

## 4. Benchmark smoke

```bash
python -m designmd_pptx benchmark -o out/gallery-demo/benchmark
```

## 5. Materialize PPTX (needs legacy OfficeCLI)

```bash
python -m designmd_pptx apply --force --screenshot --gate3 \
  out/gallery-demo/deck.pptx \
  out/gallery-demo/recipes/deck.sequence.json
```

Inspect the contact sheet (Gate 3). Fix content, re-apply until clean.

## 6. Quick draft path (needs official officecli)

```bash
python -m designmd_pptx render python/examples/content.deck.json \
  -o out/gallery-demo/draft.pptx --design default
```

Outline-level fidelity only — use scaffold/apply for DESIGN.md-precise decks.

## 7. Compose from a brief

```bash
# brief.md: # Title, ## per slide, lists, tables, CTA: lines
python -m designmd_pptx compose brief.md -o out/composed --design default
# review compose.report.json, then:
python -m designmd_pptx scaffold default -o out/from-brief \
  --content out/composed/content.deck.json --apply --force --screenshot
```

## Recipe catalog (patterns)

cover · section_divider · section_opener_numbered · agenda_toc · kpi_row ·
kpi_dashboard_grid · big_number · feature_cards · pricing · bullets · quote ·
comparison_2col · matrix_2x2 · quadrant_matrix_rich · vs_scorecard · timeline ·
story_timeline · process · funnel_stages · roadmap_swimlane · pyramid_levels ·
table · appendix_table · chart_insight · chart_callout_panel · team · logo_strip ·
image_full · image_text_2col · close · consort_flow · kaplan_meier · forest_plot ·
study_design · results_table_insight · multi_panel_figure
