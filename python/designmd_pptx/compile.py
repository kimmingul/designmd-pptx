"""Compile DESIGN.md → tokens.slide.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from . import fonts, tokens as T
from .colors_parse import collect_css_vars
from .validate import validate_content_overlay, validate_tokens_against_schema_file

COMPILER_VERSION = "1.7.1"

DEFAULT_PATTERNS = [
    "cover",
    "section_divider",
    "kpi_row",
    "feature_cards",
    "bullets",
    "quote",
    "comparison_2col",
    "timeline",
    "process",
    "table",
    "image_full",
    "image_text_2col",
    "chart_insight",
    "close",
]


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter between leading --- fences."""
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    raw_yaml, body = m.group(1), m.group(2)
    try:
        data = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid DESIGN.md frontmatter YAML: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("DESIGN.md frontmatter must be a YAML mapping")
    return data, body


def _resolve_refs(node: Any, root: dict, depth: int = 0) -> Any:
    """Resolve simple {colors.primary} style refs inside frontmatter."""
    if depth > 12:
        return node
    if isinstance(node, str):
        m = re.fullmatch(r"\{([a-zA-Z0-9_.-]+)\}", node.strip())
        if not m:
            return node
        path = m.group(1).split(".")
        cur: Any = root
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return node
            cur = cur[p]
        return _resolve_refs(cur, root, depth + 1)
    if isinstance(node, dict):
        return {k: _resolve_refs(v, root, depth + 1) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_refs(v, root, depth + 1) for v in node]
    return node


def extract_overview_snippet(body: str, max_chars: int = 600) -> str:
    # Case-insensitive heading hunt for Overview / Theme / Atmosphere
    for pat in (
        r"^##\s+Overview\b",
        r"^##\s+Visual\s+Theme",
        r"^##\s+Atmosphere",
        r"^#\s+Overview\b",
        r"^##\s+.+Theme",
    ):
        m = re.search(pat, body, re.I | re.M)
        if m:
            chunk = body[m.start() : m.start() + max_chars * 2]
            rest = re.split(r"\n##\s+", chunk, maxsplit=1)[0]
            return rest.strip()[:max_chars]
    return body.strip()[:max_chars]


def compile_design_md(
    source: str | Path,
    *,
    brand: str | None = None,
) -> dict[str, Any]:
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"DESIGN.md not found: {path}")
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    fm = _resolve_refs(fm, fm)

    warnings: list[str] = []
    colors_raw = fm.get("colors") if isinstance(fm.get("colors"), dict) else {}
    typography_raw = fm.get("typography") if isinstance(fm.get("typography"), dict) else {}
    rounded_raw = fm.get("rounded") if isinstance(fm.get("rounded"), dict) else {}

    if not colors_raw:
        colors_raw = scrape_colors_from_markdown(body)
        if colors_raw:
            warnings.append(
                "colors: frontmatter empty — scraped keyword-adjacent hex from markdown body"
            )
        else:
            warnings.append("colors: no extractable palette — using neutral fallbacks only")

    var_map = collect_css_vars(colors_raw, body)
    palette, provenance, color_warnings, extras = T.extract_semantic_colors(
        colors_raw, body=body, var_map=var_map
    )
    warnings.extend(color_warnings)

    type_sizes, type_warnings = T.extract_type_sizes(typography_raw)
    warnings.extend(type_warnings)

    heading_font, body_font, mono_font, font_warnings = fonts.pair_from_typography(typography_raw)
    warnings.extend(font_warnings)

    name = brand or fm.get("name") or path.parent.name or path.stem
    description = str(fm.get("description") or extract_overview_snippet(body) or "")

    motif = T.motif_from_atmosphere(palette, description)

    design_v2, v2_warnings = T.extract_design_v2(fm, palette)
    warnings.extend(v2_warnings)

    card_radius_px = None
    for k in ("lg", "md", "xl"):
        if k in rounded_raw:
            card_radius_px = T.parse_px(rounded_raw[k])
            break
    use_round_rect = True if card_radius_px is None else card_radius_px >= 6

    result: dict[str, Any] = {
        "version": "1.1",
        "source": str(path.as_posix()),
        "brand": str(name),
        "description": description[:500],
        "canvas_cm": [T.CANVAS_W_CM, T.CANVAS_H_CM],
        "margin_cm": T.MARGIN_CM,
        "gap_cm": T.GAP_CM,
        "colors": palette,
        "color_provenance": provenance,
        "css_vars": {k: v for k, v in list(var_map.items())[:40]},
        "warnings": warnings,
        "type": {
            **type_sizes,
            "heading_font": heading_font,
            "body_font": body_font,
            "mono_font": mono_font,
        },
        "shape": {
            "card_preset": "roundRect" if use_round_rect else "rect",
            "card_radius_px_source": card_radius_px,
        },
        "motif": motif,
        "composition": design_v2["composition"],
        "charts": design_v2["charts"],
        "tables": design_v2["tables"],
        "images": design_v2["images"],
        "master": design_v2["master"],
        "dark_first": T.is_dark(palette["background"]),
        "content_bg_policy": "match_canvas",
        "background_gradient": extras.get("background_gradient"),
        "drop": list(T.DROPPED_WEB_CONCERNS),
        "patterns": list(DEFAULT_PATTERNS),
        "raw_color_keys": sorted(str(k) for k in colors_raw.keys()),
        "compiler": {"name": "designmd-pptx", "version": COMPILER_VERSION},
    }

    schema_errors = validate_tokens_against_schema_file(result)
    if schema_errors:
        result["schema_errors"] = schema_errors
        warnings.extend(f"schema: {e}" for e in schema_errors)
        result["warnings"] = warnings

    return result


def assert_tokens_valid(tokens: dict[str, Any], *, strict: bool = True) -> list[str]:
    """Return schema errors; raise if strict and any error."""
    errors = validate_tokens_against_schema_file(tokens)
    if strict and errors:
        raise ValueError("tokens failed validation:\n- " + "\n- ".join(errors))
    return errors


def assert_content_valid(content: dict[str, Any] | None, *, strict: bool = True) -> list[str]:
    errors = validate_content_overlay(content)
    if strict and errors:
        raise ValueError("content overlay failed validation:\n- " + "\n- ".join(errors))
    return errors


def scrape_colors_from_markdown(body: str) -> dict[str, str]:
    """Fallback: pull #RRGGBB near role keywords from markdown body.

    Does NOT assign first-hex-as-primary (order-dependent pollution).
    """
    found: dict[str, str] = {}
    role_patterns = [
        (r"primary[^#\n]{0,60}#([0-9A-Fa-f]{6})", "primary"),
        (r"canvas[^#\n]{0,60}#([0-9A-Fa-f]{6})", "canvas"),
        (r"background[^#\n]{0,60}#([0-9A-Fa-f]{6})", "canvas"),
        (r"surface[-\s]?1[^#\n]{0,60}#([0-9A-Fa-f]{6})", "surface-1"),
        (r"\bink\b[^#\n]{0,60}#([0-9A-Fa-f]{6})", "ink"),
        (r"muted[^#\n]{0,60}#([0-9A-Fa-f]{6})", "ink-muted"),
        (r"accent[^#\n]{0,60}#([0-9A-Fa-f]{6})", "accent"),
        (r"brand[^#\n]{0,60}#([0-9A-Fa-f]{6})", "primary"),
    ]
    for pat, key in role_patterns:
        m = re.search(pat, body, re.I)
        if m and key not in found:
            found[key] = f"#{m.group(1)}"
    return found


def write_tokens(tokens: dict[str, Any], dest: str | Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(tokens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest
