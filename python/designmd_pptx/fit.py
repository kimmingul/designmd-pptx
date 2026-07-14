"""Text-fit estimation (v1.5) — east-asian-width-aware budgets per recipe field.

Closes the "oversized content fails" gap: caps used to count list items only,
so a 400-character bullet sailed through validation and overflowed its fixed
box. This module estimates rendered width in *em units* (CJK glyphs ≈ 1.0 em,
Latin ≈ 0.55 em) against each field's box width and line count, so Korean/
Japanese/Chinese text — wider per glyph — is budgeted correctly.

Estimates are deliberately conservative approximations, not font metrics;
they exist to reject content that cannot plausibly fit, with an actionable
message, before officecli ever runs.
"""

from __future__ import annotations

import unicodedata
from typing import Any

# 1 pt ≈ 0.0353 cm; an "em unit" of width ≈ the font size
_PT_TO_CM = 0.0353
# Grace factor: estimates are rough; only reject clearly-overflowing text
_TOLERANCE = 1.25

_CANVAS_W = 33.87
_DEFAULT_MARGIN = 1.27


def text_units(s: Any) -> float:
    """Approximate rendered width of text in em units (CJK-aware)."""
    total = 0.0
    for ch in str(s):
        eaw = unicodedata.east_asian_width(ch)
        if eaw in ("F", "W"):
            total += 1.0
        elif eaw == "H":
            total += 0.5
        elif ch == " ":
            total += 0.3
        else:
            total += 0.55 if ch.isalpha() else 0.5
    return total


# (width_cm | "full" | "per_item", type-key or fixed pt, max_lines)
# "full" = canvas minus margins; "per_item" = adaptive column width.
_BUDGETS: dict[str, dict[str, tuple[Any, Any, int]]] = {
    "cover": {"title": (26.0, "cover_pt", 2), "subtitle": (26.0, "body_pt", 2)},
    "section_divider": {"title": ("full", "section_pt", 2), "blurb": (26.0, "body_pt", 2)},
    "kpi_row": {
        "title": ("full", "title_pt", 1),
        "kpis.value": ("per_item", "kpi_pt", 1),
        "kpis.label": ("per_item", "micro_pt", 2),
        "kpis.chip": ("per_item", "micro_pt", 1),
    },
    "kpi_dashboard_grid": {
        "title": ("full", "title_pt", 1),
        "subtitle": ("full", "body_pt", 1),
        "kpis.value": ("per_item", "kpi_pt", 1),
        "kpis.label": ("per_item", "micro_pt", 2),
        "kpis.chip": ("per_item", "micro_pt", 1),
    },
    "agenda_toc": {
        "title": ("full", "title_pt", 1),
        "items.label": ("full", "body_pt", 1),
    },
    "section_opener_numbered": {
        "title": ("full", "title_pt", 2),
        "blurb": (22.0, "body_pt", 2),
    },
    "feature_cards": {
        "title": ("full", "title_pt", 1),
        "cards.title": ("per_item", "section_pt", 2),
        "cards.body": ("per_item", "body_pt", 5),
    },
    "bullets": {"title": ("full", "title_pt", 1), "bullets": ("full", "body_pt", 2)},
    "quote": {"quote": (26.0, "section_pt", 4), "attribution": (26.0, "body_pt", 1)},
    "comparison_2col": {
        "title": ("full", "title_pt", 1),
        "left.body": (14.5, "body_pt", 8),
        "right.body": (14.5, "body_pt", 8),
    },
    "chart_insight": {
        "title": ("full", "title_pt", 1),
        "insight_title": (9.0, "section_pt", 2),
        "insight_body": (9.0, "body_pt", 10),
    },
    "timeline": {"title": ("full", "title_pt", 1), "steps.label": ("per_item", "body_pt", 2)},
    "process": {"title": ("full", "title_pt", 1)},
    "table": {"title": ("full", "title_pt", 1)},
    "image_full": {"title": ("full", "title_pt", 1), "caption": ("full", "micro_pt", 2)},
    "image_text_2col": {"title": ("full", "title_pt", 1), "body": (14.0, "body_pt", 10)},
    "close": {
        "title": (26.0, "cover_pt", 2),
        "body": (26.0, "body_pt", 2),
        "cta": (10.0, "body_pt", 1),
    },
    "big_number": {
        "value": (26.0, "mega_pt", 1),
        "label": (26.0, "section_pt", 1),
        "context": (26.0, "body_pt", 2),
    },
    "matrix_2x2": {
        "title": ("full", "title_pt", 1),
        "quadrants.title": (13.0, "section_pt", 1),
        "quadrants.body": (13.0, "body_pt", 4),
    },
    "team": {
        "title": ("full", "title_pt", 1),
        "members.name": ("per_item", "section_pt", 1),
        "members.role": ("per_item", "micro_pt", 1),
        "members.blurb": ("per_item", "body_pt", 4),
    },
    "logo_strip": {"title": ("full", "title_pt", 1), "logos.label": ("per_item", "body_pt", 1)},
    "pricing": {
        "title": ("full", "title_pt", 1),
        "tiers.name": ("per_item", "section_pt", 1),
        "tiers.price": ("per_item", "kpi_pt", 1),
        "tiers.features": ("per_item", "micro_pt", 2),
    },
    "appendix_table": {"title": ("full", "title_pt", 1)},
}

_PT_DEFAULTS = {
    "cover_pt": 52, "title_pt": 36, "section_pt": 28, "body_pt": 18,
    "micro_pt": 12, "kpi_pt": 60, "mega_pt": 96,
}


def _field_width(spec: Any, margin: float, items: int) -> float:
    if spec == "full":
        return _CANVAS_W - 2 * margin
    if spec == "per_item":
        n = max(1, min(4, items))
        usable = _CANVAS_W - 2 * margin - (n - 1) * 0.76
        return usable / n - 0.8  # inner padding
    return float(spec)


def check_text(
    recipe: str, field: str, text: Any, tokens: dict[str, Any], *, items: int = 1
) -> str | None:
    """Return a human-actionable error when text cannot fit its box."""
    budget = _BUDGETS.get(recipe, {}).get(field)
    if budget is None or text is None:
        return None
    width_spec, pt_key, max_lines = budget
    typ = tokens.get("type") or {}
    pt = float(typ.get(pt_key, _PT_DEFAULTS.get(pt_key, 18)))
    margin = float(tokens.get("margin_cm", _DEFAULT_MARGIN))
    width_cm = _field_width(width_spec, margin, items)
    units_per_line = max(1.0, width_cm / (pt * _PT_TO_CM))
    max_units = units_per_line * max_lines * _TOLERANCE
    units = text_units(text)
    if units <= max_units:
        return None
    approx_latin = int(max_units / 0.55)
    approx_cjk = int(max_units)
    return (
        f"{field} too long (~{units:.0f} width-units > {max_units:.0f} budget at "
        f"{pt:.0f}pt / {max_lines} line(s) — roughly {approx_latin} Latin or "
        f"{approx_cjk} CJK chars). Shorten the text or split the slide."
    )


def _iter_field_texts(field: str, content: dict[str, Any]):
    """Yield (text, items_count) for a budget field like 'kpis.label'."""
    if "." not in field:
        value = content.get(field)
        if field == "bullets":
            value = content.get("bullets") or content.get("items")
        if isinstance(value, list):
            for v in value:
                yield v, 1
        elif value is not None:
            yield value, 1
        return
    coll_key, sub = field.split(".", 1)
    coll = content.get(coll_key)
    if isinstance(coll, dict):  # left.body / right.body style
        v = coll.get(sub)
        if v is not None:
            yield v, 1
        return
    if not isinstance(coll, list):
        return
    n = len(coll)
    for item in coll:
        if isinstance(item, dict):
            v = item.get(sub)
            if isinstance(v, list):  # e.g. pricing tiers.features
                for f in v:
                    yield f, n
            elif v is not None:
                yield v, n
        elif sub == "label" and isinstance(item, str):
            yield item, n


def validate_deck_text_fit(deck: dict[str, Any], tokens: dict[str, Any]) -> list[str]:
    """Text-length validation for every budgeted field in the deck."""
    errors: list[str] = []
    for i, slide in enumerate(deck.get("slides") or []):
        recipe = slide.get("recipe")
        content = slide.get("content") or {}
        for field in _BUDGETS.get(recipe, {}):
            for text, items in _iter_field_texts(field, content):
                err = check_text(recipe, field, text, tokens, items=items)
                if err:
                    errors.append(f"slides[{i}] ({recipe}): {err}")
                    break  # one error per field is enough signal
    return errors
