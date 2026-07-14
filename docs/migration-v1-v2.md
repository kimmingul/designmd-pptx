# Migration guide: v1.x → v2.0

## What stayed the same

- `compile` / `scaffold` / `apply` / `extract` / `restyle` / `master` / `compose`
- Staging-safe `--force` / `DESIGNMD_FORCE=1`
- Gate 3 `--screenshot` / `--gate3`
- Deck-spec shape (`slides[].recipe` + `content`)
- Literal `default` house style

## New in the v1.7 → v2.0 line

| Area | Change |
|---|---|
| Backends | Dual: legacy shape-level + official agent-bridge (`render`) |
| Compatibility | `compatibility.json` is the only OfficeCLI version pin |
| Install | `pip install` wheel; `doctor --install` pins official OfficeCLI |
| a11y | `a11y` command — contrast, reading order, alt/notes |
| Benchmark | `benchmark` command + `benchmark_thresholds.json` |
| Vision | `apply --vision` / `--gate3-vision` (opt-in) |
| Compose LLM | `compose --llm` (opt-in narrative planner) |
| Corpus | `anonymize` + `corpus` for validation sets |
| Patterns | Premium + academic/medical recipes (Phase 2) |

## Breaking / behavioral notes

1. **Two binaries named `officecli`** — discovery is by capability probe.
   Set `OFFICECLI_LEGACY_BIN` / `OFFICECLI_BRIDGE_BIN` if PATH is ambiguous.
2. **`render` ≠ scaffold** — render is outline-level; do not expect engine cm
   geometry from agent-bridge.
3. **Layout engine recipes** — do not reintroduce hand coordinates into
   engine-solved patterns (bullets, feature_cards, comparison_2col,
   image_text_2col, …).
4. **Text overflow** — over-budget content must be shortened or split; font
   shrink is not a fix.
5. **a11y is opt-in on CLI but recommended pre-ship** — exit code 1 means do
   not treat the deck as clean.

## Suggested upgrade steps

```bash
git pull
pip install -r python/requirements.txt
python -m designmd_pptx doctor --install --dry-run
python -m designmd_pptx doctor
# re-scaffold existing content.deck.json against current recipes
python -m designmd_pptx scaffold default -o out/migrated --content path/to/content.deck.json
python -m designmd_pptx a11y --tokens out/migrated/tokens.slide.json --deck path/to/content.deck.json
python -m designmd_pptx benchmark -o out/benchmark
```

## Removed / deferred

- Windows MSI installer → Phase 5 (#35)
- Animation API → Phase 5 (#40)
- Public 100-deck gallery hosting → Phase 5 / v3.0
