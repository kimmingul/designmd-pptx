# Production-readiness checklist

Use this before treating a deck (or a release of the toolkit) as shippable.

## Machine / install

| # | Check | Threshold / command | Pass? |
|---|---|---|---|
| 1 | Python ≥ 3.10 | `python --version` | |
| 2 | Package importable | `python -c "import designmd_pptx"` | |
| 3 | Deps | `pip install -r python/requirements.txt` (or wheel) | |
| 4 | Doctor | `python -m designmd_pptx doctor` — no unexpected MISS for required path | |
| 5 | Official pin (render path) | `doctor --install --dry-run` shows `officecli@` from `compatibility.json`; install if needed | |
| 6 | Legacy binary (precision path) | scaffold/apply path: legacy OfficeCLI on PATH or `OFFICECLI_LEGACY_BIN` | |

## Content quality

| # | Check | Threshold | Pass? |
|---|---|---|---|
| 7 | Tokens compile clean | `compile` warnings reviewed; no hard `assert_tokens_valid` errors | |
| 8 | Deck-spec validates | `scaffold` / deck generation without content errors | |
| 9 | Text budgets | No font-shrink workarounds; shorten or split over-budget CJK/Latin | |
| 10 | Gate 3 contact sheet | `--screenshot` (and `--gate3` for hard fail) reviewed by a human | |
| 11 | Vision QA (optional) | `--vision` / `--gate3-vision` when a model is configured | |

## Accessibility (#39)

| # | Check | Threshold | Pass? |
|---|---|---|---|
| 12 | WCAG contrast | `python -m designmd_pptx a11y --design … --content …` → **0 errors** (AA default) | |
| 13 | Alt text | Every `src` has non-empty `alt` (or logo `alt`/`label`) | |
| 14 | Reading order | `--show-order` reviewed for narrative slides | |
| 15 | Notes | Speaker notes on narrative recipes (use `--require-notes` for hard gate) | |

## Regression (#37)

| # | Check | Threshold | Pass? |
|---|---|---|---|
| 16 | Fixture benchmark | `python -m designmd_pptx benchmark -o out/` → **PASS** | |
| 17 | Metric ceilings | corruption ≤ 0, layout_failure ≤ 0, visual_gate_failure ≤ 0, a11y_error ≤ 0, extraction_loss ≤ 5 | |
| 18 | Corpus (if present) | `benchmark --manifest corpus.manifest.json` held-out fails = 0; skips documented when assets absent | |

## Release hygiene

| # | Check | Threshold | Pass? |
|---|---|---|---|
| 19 | Unit suite | `npm test` / `python -m unittest discover -s python/tests -q` → OK | |
| 20 | Plugin adapters | `npm run check` → all checks passed | |
| 21 | Version alignment | `plugin.json`, package.json, `__init__.__version__` agree | |
| 22 | No licensed assets committed | `infograpify_ppt_templates/` gitignored; no force-added pptx | |

Threshold source of truth for metrics: `python/designmd_pptx/benchmark_thresholds.json`.
