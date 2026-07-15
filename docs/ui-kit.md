# UI kit contract

designmd-pptx recipes share a **React-like spacing system** in
`python/designmd_pptx/ui_kit.py`. Do not invent one-off cm constants for stage
chrome; derive geometry from `StageMetrics`.

## Tokens → metrics

| Token / density | StageMetrics field | Role |
|-----------------|--------------------|------|
| `margin_cm` (from `whitespace_density`) | `margin` | Outer stage inset |
| `gap_cm` | `gap` | Between siblings (cards, columns) |
| ≈ `0.5 × margin` | `pad` | Inside a card/surface |
| — | `title_band` | Fixed slide-title height |
| — | `card_title_band` | Fixed in-card title height |
| — | `title_to_body` | Stack gap title → body |

`compile.py` maps density → margin/gap (`spacious` → 2.2 / 1.1, `compact` → 1.27 / 0.55, `comfortable` → historical floors).

## Hard rules

1. **Body text is content-height** — never put `weight=1` on a `Text` leaf.
2. **Free space uses `Spacer`** — empty surface, not a hollow text frame.
3. **Equal columns share height via Spacers inside cards**, not stretched copy.
4. **Bottom stage margin ≈ side margin** — do not fill the canvas with panels.
5. **Column gap comes from `gap`**, not a hard-coded `0.5cm`.

## API surface

```python
from designmd_pptx import ui_kit as UI

st = UI.stage_metrics(tokens)
# Layout trees (feature_cards, comparison_2col, bullets, …)
UI.feature_card(st, index=1, title=…, body=…, density=d)
UI.titled_stage(st, title, UI.equal_columns(cols, st, density=d), title_name="FeatTitle")
UI.solve_stage(build, bg=st.c["content_background"])

# Fixed-cm comparison (before/after)
UI.comparison_panels(st, title=…, left_title=…, left_body=…, right_title=…, right_body=…)
```

## Migrated recipes (contract consumers)

- `feature_cards`, `bullets`, `comparison_2col`, `before_after_slider`
- `close`, `big_number`, `process` (metrics for margin/gap/vertical band)
- `_title_op` (shared title chrome)

Other recipes still use local coordinates; new work should call `stage_metrics`
or the helpers above.

## Why this exists

Web UI (React + design tokens) looks clean because **gap/pad/auto-height** are
systemic. The old recipe style used fixed cm slabs and `weight=1` text boxes,
so demos failed as product UI even when OfficeCLI issues were green.
