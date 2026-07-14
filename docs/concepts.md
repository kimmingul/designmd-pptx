# Concepts

## DESIGN.md → tokens → deck-spec → PPTX

1. **DESIGN.md** — brand colors, type, optional composition tokens (schema v2).
2. **tokens.slide.json** — compiled, contrast-floored token object (`compile`).
3. **deck-spec / content.deck.json** — ordered slides with `recipe` + `content`
   (`compose` from a markdown brief, or extract from an existing pptx).
4. **recipes / sequence** — OfficeCLI ops (`scaffold` / `recipes`).
5. **PPTX** — materialize with staging-safe `apply` (legacy backend) or draft
   via `render` (official agent-bridge).

## Backends

| Backend | Binary | Commands | Fidelity |
|---|---|---|---|
| Legacy shape-level | iOfficeAI OfficeCLI | apply, scaffold --apply, restyle, master, Gate 3 screenshots | DESIGN.md-exact geometry |
| Official agent-bridge | `npm i -g officecli@pin` | render | outline-level `office.render` |

Both may install as `officecli` — discovery is by probe, not name. See
[officecli-backends.md](officecli-backends.md).

## Layout systems

- **Engine** — bullets, feature_cards, comparison_2col, image_text_2col (and more):
  100% layout-engine solved; no hand cm coordinates.
- **Hybrid / structured / fixed** — remaining recipes; never mix systems in one recipe.

## Quality gates

| Gate | What |
|---|---|
| Structural | validate tokens/deck content |
| Fit | CJK-aware text budgets; shorten or split, never font-shrink |
| Gate 3 | contact sheet from staging before overwrite (`--screenshot` / `--gate3`) |
| Vision | optional model or offline heuristic (`--vision`) |
| a11y | WCAG contrast, reading order, alt/notes (`a11y` command) |
| Benchmark | before/after metrics vs thresholds (`benchmark` command) |

## Staging-safe overwrite

Destination `.pptx` replacement requires `--force` or `DESIGNMD_FORCE=1`.
Apply writes to staging, validates, optionally screenshots, then renames.
