"""Schema + content overlay validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Ships inside the package (designmd_pptx/schema/) so an installed wheel is
# self-contained — the schemas moved here from python/schema/ in #33.
SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "tokens.slide.schema.json"

HEX6 = re.compile(r"^[0-9A-Fa-f]{6}$")

CONTENT_KEYS = {
    "cover": {"title", "subtitle", "meta"},
    "section_divider": {"number", "title", "blurb"},
    "kpi_row": {"title", "kpis", "notes"},
    "kpi_3": {"title", "kpis", "notes"},
    "feature_cards": {"title", "cards"},
    "feature_cards_3": {"title", "cards"},
    "bullets": {"title", "bullets", "items", "notes"},
    "quote": {"quote", "attribution"},
    "comparison_2col": {"title", "left", "right"},
    "chart_insight": {
        "title",
        "insight_title",
        "insight_body",
        "categories",
        "series1_values",
        "series2_values",
        "series1_name",
        "series2_name",
        "notes",
    },
    "timeline": {"title", "steps", "notes"},
    "table": {"title", "headers", "rows", "notes"},
    "image_full": {"title", "src", "alt", "caption", "notes"},
    "image_text_2col": {
        "title",
        "body",
        "src",
        "alt",
        "image_side",
        "notes",
    },
    "process": {"title", "steps", "notes"},
    "close": {"title", "body", "cta"},
    "big_number": {"value", "label", "context", "watch", "notes"},
    "matrix_2x2": {"title", "quadrants", "axes", "notes"},
    "team": {"title", "members", "notes"},
    "logo_strip": {"title", "logos", "notes"},
    "pricing": {"title", "tiers", "notes"},
    "appendix_table": {"title", "headers", "rows", "notes"},
    # Phase 2 / #10 academic · medical · research
    "consort_flow": {"title", "stages", "steps", "notes"},
    "kaplan_meier": {
        "title", "categories", "series1_values", "series2_values",
        "series1_name", "series2_name", "risk_table", "rows", "risk_headers",
        "insight", "insight_title", "insight_body", "notes",
    },
    "forest_plot": {"title", "rows", "studies", "domain", "notes"},
    "study_design": {"title", "phases", "arms", "groups", "notes"},
    "results_table_insight": {
        "title", "headers", "rows", "insight", "insight_title", "insight_body", "notes",
    },
    "multi_panel_figure": {"title", "panels", "figures", "notes"},
}


def validate_tokens_struct(tokens: dict[str, Any]) -> list[str]:
    """Lightweight structural validation (no jsonschema dependency required)."""
    errors: list[str] = []
    for key in ("version", "colors", "type", "canvas_cm", "margin_cm", "gap_cm", "patterns"):
        if key not in tokens:
            errors.append(f"missing required key: {key}")

    colors = tokens.get("colors")
    if not isinstance(colors, dict):
        errors.append("colors must be object")
    else:
        for req in (
            "background",
            "content_background",
            "surface",
            "accent",
            "text",
            "muted",
            "on_accent",
        ):
            if req not in colors:
                errors.append(f"colors missing: {req}")
            elif not HEX6.match(str(colors[req])):
                errors.append(f"colors.{req} must be RRGGBB, got {colors.get(req)!r}")
        for k, v in colors.items():
            if not HEX6.match(str(v)):
                errors.append(f"colors.{k} invalid hex: {v!r}")

    t = tokens.get("type")
    if isinstance(t, dict):
        for k, mn in (
            ("title_pt", 36),
            ("body_pt", 18),
            ("cover_pt", 36),
        ):
            if k in t and int(t[k]) < mn:
                errors.append(f"type.{k}={t[k]} below floor {mn}")
        for fk in ("heading_font", "body_font"):
            if not t.get(fk):
                errors.append(f"type.{fk} required")
    else:
        errors.append("type must be object")

    cm = tokens.get("canvas_cm")
    if not (isinstance(cm, list) and len(cm) == 2):
        errors.append("canvas_cm must be [w,h]")

    if float(tokens.get("margin_cm", 0)) < 1.0:
        errors.append("margin_cm must be >= 1.0")
    if float(tokens.get("gap_cm", 0)) < 0.5:
        errors.append("gap_cm must be >= 0.5")

    return errors


def validate_tokens_against_schema_file(tokens: dict[str, Any]) -> list[str]:
    """Optional jsonschema if installed; always runs structural checks."""
    errors = validate_tokens_struct(tokens)
    if not SCHEMA_PATH.is_file():
        return errors
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return errors
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(tokens, schema)
    except Exception as e:  # noqa: BLE001
        errors.append(f"jsonschema: {e}")
    return errors


def validate_content_overlay(content: dict[str, Any] | None) -> list[str]:
    if content is None:
        return []
    if not isinstance(content, dict):
        return ["content overlay must be a JSON object"]
    errors: list[str] = []
    for key, node in content.items():
        if key not in CONTENT_KEYS:
            errors.append(f"unknown content section: {key}")
            continue
        if not isinstance(node, dict):
            errors.append(f"{key} must be object")
            continue
        if key in ("kpi_row", "kpi_3") and "kpis" in node:
            if not isinstance(node["kpis"], list):
                errors.append(f"{key}.kpis must be array")
            elif len(node["kpis"]) > 4:
                errors.append(f"{key}.kpis max 4 items (got {len(node['kpis'])})")
        if key in ("feature_cards", "feature_cards_3") and "cards" in node:
            if not isinstance(node["cards"], list):
                errors.append(f"{key}.cards must be array")
        if key == "timeline" and "steps" in node:
            if not isinstance(node["steps"], list) or not (2 <= len(node["steps"]) <= 6):
                errors.append("timeline.steps must be array length 2–6")
        if key == "process" and "steps" in node:
            if not isinstance(node["steps"], list) or not (2 <= len(node["steps"]) <= 5):
                errors.append("process.steps must be array length 2–5")
        if key == "table":
            headers = node.get("headers")
            rows = node.get("rows")
            if headers is not None and not isinstance(headers, list):
                errors.append("table.headers must be array")
            if rows is not None and not isinstance(rows, list):
                errors.append("table.rows must be array")
        if key == "image_full" and node.get("src") is not None:
            src = Path(str(node["src"]))
            # only warn if absolute path missing; relative checked at apply time
            if src.is_absolute() and not src.is_file():
                errors.append(f"image_full.src not found: {src}")
        if key == "comparison_2col":
            for side in ("left", "right"):
                if side in node and not isinstance(node[side], dict):
                    errors.append(f"comparison_2col.{side} must be object")
        if key == "matrix_2x2" and "quadrants" in node:
            if not isinstance(node["quadrants"], list) or len(node["quadrants"]) > 4:
                errors.append("matrix_2x2.quadrants must be array of ≤4 items")
        if key == "team" and "members" in node:
            if not isinstance(node["members"], list) or not (2 <= len(node["members"]) <= 4):
                errors.append("team.members must be array length 2–4")
        if key == "logo_strip" and "logos" in node:
            if not isinstance(node["logos"], list) or not (2 <= len(node["logos"]) <= 6):
                errors.append("logo_strip.logos must be array length 2–6")
        if key == "pricing" and "tiers" in node:
            if not isinstance(node["tiers"], list) or not (2 <= len(node["tiers"]) <= 3):
                errors.append("pricing.tiers must be array length 2–3")
        if key == "appendix_table":
            if node.get("headers") is not None and not isinstance(node["headers"], list):
                errors.append("appendix_table.headers must be array")
            if node.get("rows") is not None and not isinstance(node["rows"], list):
                errors.append("appendix_table.rows must be array")
    return errors
