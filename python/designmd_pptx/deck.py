"""Ordered deck specification — repeatable recipes, explicit slide order."""

from __future__ import annotations

from typing import Any, Callable

from . import recipes as R
from .validate import validate_content_overlay

RECIPE_CONTENT_VALIDATORS: dict[str, Callable[[dict, list[str]], None]] = {}


def _warn(warnings: list[str], msg: str) -> None:
    warnings.append(msg)


def migrate_flat_to_deck(flat: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    """
    Convert legacy flat {recipe: content} map into ordered deck using DEFAULT_SEQUENCE.
    Emits deprecation warning.
    """
    warnings = [
        "content: flat overlay format is deprecated; prefer "
        '{"version":"1.0","slides":[{"recipe":"...","content":{...}}]}'
    ]
    flat = flat or {}
    # normalize aliases
    normalized: dict[str, dict] = {}
    for k, v in flat.items():
        if not isinstance(v, dict):
            continue
        canon = R.RECIPE_ALIASES.get(k, k)
        normalized[canon] = v

    slides: list[dict[str, Any]] = []
    for name in R.DEFAULT_SEQUENCE:
        if name in normalized:
            slides.append({"id": name, "recipe": name, "content": normalized[name]})
        elif name in ("cover", "close"):
            # always include open/close with defaults when missing
            slides.append({"id": name, "recipe": name, "content": {}})
    # include any extra keys not in default sequence
    for name, content in normalized.items():
        if name not in R.RECIPE_BUILDERS:
            warnings.append(f"content: unknown recipe skipped: {name}")
            continue
        if not any(s.get("recipe") == name for s in slides):
            slides.append({"id": name, "recipe": name, "content": content})

    return {"version": "1.0", "slides": slides}, warnings


def is_deck_spec(obj: Any) -> bool:
    return isinstance(obj, dict) and isinstance(obj.get("slides"), list)


def normalize_deck_spec(obj: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    """Accept deck-spec or flat overlay; return (deck, warnings)."""
    if obj is None:
        # catalog / demo: one of every pattern with empty content
        slides = [
            {"id": name, "recipe": name, "content": {}}
            for name in R.DEFAULT_SEQUENCE
        ]
        return {"version": "1.0", "slides": slides}, ["deck: using full pattern catalog defaults"]
    if is_deck_spec(obj):
        warnings: list[str] = []
        slides_in = obj["slides"]
        slides_out: list[dict[str, Any]] = []
        for i, slide in enumerate(slides_in):
            if not isinstance(slide, dict):
                raise ValueError(f"slides[{i}] must be object")
            recipe = slide.get("recipe") or slide.get("pattern")
            if not recipe:
                raise ValueError(f"slides[{i}] missing recipe")
            recipe = R.RECIPE_ALIASES.get(str(recipe), str(recipe))
            if recipe not in R.RECIPE_BUILDERS:
                raise ValueError(f"slides[{i}] unknown recipe: {recipe}")
            content = slide.get("content") or {}
            if not isinstance(content, dict):
                raise ValueError(f"slides[{i}].content must be object")
            # also allow flat keys on slide itself
            if not content:
                content = {
                    k: v
                    for k, v in slide.items()
                    if k not in ("id", "recipe", "pattern", "content")
                }
            sid = slide.get("id") or f"s{i+1}_{recipe}"
            slides_out.append({"id": str(sid), "recipe": recipe, "content": content})
        return {"version": str(obj.get("version", "1.0")), "slides": slides_out}, warnings
    # flat
    return migrate_flat_to_deck(obj)


def validate_deck_content_caps(deck: dict[str, Any]) -> list[str]:
    """Hard reject oversized content (no silent truncation)."""
    errors: list[str] = []
    for i, slide in enumerate(deck.get("slides") or []):
        recipe = slide.get("recipe")
        content = slide.get("content") or {}
        prefix = f"slides[{i}] ({recipe})"
        if recipe in ("kpi_row", "kpi_3"):
            kpis = content.get("kpis") or []
            if isinstance(kpis, list) and len(kpis) > 4:
                errors.append(f"{prefix}: kpis max 4 (got {len(kpis)}); split into another kpi_row slide")
            if isinstance(kpis, list) and len(kpis) == 1:
                errors.append(f"{prefix}: kpis need 2–4 items (got 1)")
        if recipe in ("feature_cards", "feature_cards_3"):
            cards = content.get("cards") or []
            if isinstance(cards, list) and len(cards) > 4:
                errors.append(f"{prefix}: cards max 4 (got {len(cards)}); split slides")
        if recipe == "timeline":
            steps = content.get("steps") or []
            if isinstance(steps, list) and len(steps) > 6:
                errors.append(f"{prefix}: timeline steps max 6 (got {len(steps)})")
            if isinstance(steps, list) and 0 < len(steps) < 2:
                errors.append(f"{prefix}: timeline needs ≥2 steps")
        if recipe == "process":
            steps = content.get("steps") or []
            if isinstance(steps, list) and len(steps) > 5:
                errors.append(f"{prefix}: process steps max 5 (got {len(steps)})")
        if recipe == "table":
            headers = content.get("headers") or []
            rows = content.get("rows") or []
            if isinstance(headers, list) and len(headers) > 6:
                errors.append(f"{prefix}: table headers max 6; split table")
            if isinstance(rows, list) and len(rows) > 8:
                errors.append(f"{prefix}: table rows max 8; split table")
            if isinstance(headers, list) and isinstance(rows, list):
                for ri, row in enumerate(rows):
                    if isinstance(row, list) and len(row) != len(headers):
                        errors.append(
                            f"{prefix}: row {ri} length {len(row)} != headers {len(headers)}"
                        )
        if recipe == "bullets":
            items = content.get("bullets") or content.get("items") or []
            if isinstance(items, list) and len(items) > 5:
                errors.append(f"{prefix}: bullets max 5 (got {len(items)})")
        if recipe in ("image_full", "image_text_2col"):
            src = content.get("src")
            alt = content.get("alt")
            if src and not alt:
                errors.append(f"{prefix}: {recipe}.alt is required when src is set")
        if recipe == "matrix_2x2":
            quads = content.get("quadrants") or []
            if isinstance(quads, list) and len(quads) > 4:
                errors.append(f"{prefix}: quadrants max 4 (got {len(quads)})")
        if recipe == "team":
            members = content.get("members") or []
            if isinstance(members, list) and len(members) > 4:
                errors.append(f"{prefix}: members max 4 (got {len(members)}); split slides")
        if recipe == "logo_strip":
            logos = content.get("logos") or []
            if isinstance(logos, list) and len(logos) > 6:
                errors.append(f"{prefix}: logos max 6 (got {len(logos)}); split slides")
            for li, logo in enumerate(logos if isinstance(logos, list) else []):
                if isinstance(logo, dict) and logo.get("src") and not (
                    logo.get("alt") or logo.get("label")
                ):
                    errors.append(f"{prefix}: logos[{li}] needs alt or label when src is set")
        if recipe == "pricing":
            tiers = content.get("tiers") or []
            if isinstance(tiers, list) and len(tiers) > 3:
                errors.append(f"{prefix}: tiers max 3 (got {len(tiers)})")
            for ti, tier in enumerate(tiers if isinstance(tiers, list) else []):
                feats = tier.get("features") if isinstance(tier, dict) else None
                if isinstance(feats, list) and len(feats) > 5:
                    errors.append(f"{prefix}: tiers[{ti}].features max 5 (got {len(feats)})")
        if recipe == "appendix_table":
            headers = content.get("headers") or []
            rows = content.get("rows") or []
            if isinstance(headers, list) and len(headers) > 8:
                errors.append(f"{prefix}: appendix_table headers max 8; split table")
            if isinstance(rows, list) and len(rows) > 14:
                errors.append(f"{prefix}: appendix_table rows max 14; split table")
    return errors


def generate_deck(
    tokens: dict[str, Any],
    deck_or_flat: dict[str, Any] | None = None,
    *,
    strict: bool = True,
) -> tuple[list[dict], dict[str, Any], list[str]]:
    """
    Returns (ops_sequence, normalized_deck, warnings).
    Passes 1-based slide_index into builders so process connectors use absolute paths.
    """
    deck, warnings = normalize_deck_spec(deck_or_flat)

    for s in deck["slides"]:
        errs = validate_content_overlay({s["recipe"]: s["content"]})
        if errs and strict:
            raise ValueError("content invalid:\n- " + "\n- ".join(errs))
        warnings.extend(errs)

    cap_errs = validate_deck_content_caps(deck)
    if cap_errs:
        if strict:
            raise ValueError("deck content caps exceeded:\n- " + "\n- ".join(cap_errs))
        warnings.extend(cap_errs)

    from .fit import validate_deck_text_fit

    fit_errs = validate_deck_text_fit(deck, tokens)
    if fit_errs:
        if strict:
            raise ValueError("deck text does not fit:\n- " + "\n- ".join(fit_errs))
        warnings.extend(fit_errs)

    ops: list[dict] = []
    for i, s in enumerate(deck["slides"]):
        slide_index = i + 1  # officecli 1-based
        builder = R.RECIPE_BUILDERS[s["recipe"]]
        ops.extend(R._call_builder(builder, tokens, s["content"], slide_index))
    return ops, deck, warnings
