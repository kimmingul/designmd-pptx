"""Intelligent chart & table reconstruction (Phase 5 / #22).

Turns extracted chart/table payloads into **modern** deck-spec content:

* normalize chart types (drop 3D / legacy aliases → officecli-friendly types)
* map chart+body → ``chart_callout_panel`` / ``waterfall_insight`` when useful
* map large tables → ``appendix_table`` (pagination) or ``results_table_insight``
* preserve series names/values/categories for lossless data handoff to recipes

Pure functions + ``modernize_deck`` post-pass used by ``extract --modern``.
"""

from __future__ import annotations

import copy
from typing import Any

# Legacy / 3D OOXML → modern officecli chartType strings
_MODERN_CHART_TYPE: dict[str, str] = {
    "bar": "bar",
    "bar3d": "bar",
    "column": "column",
    "col": "column",
    "line": "line",
    "line3d": "line",
    "area": "area",
    "area3d": "area",
    "pie": "doughnut",          # modern default: clean doughnut over 3D pie
    "pie3d": "doughnut",
    "doughnut": "doughnut",
    "ofpie": "doughnut",
    "scatter": "scatter",
    "bubble": "bubble",
    "radar": "radar",
    "surface": "area",
    "stock": "line",
    "waterfall": "waterfall",
    "funnel": "funnel",
    "treemap": "treemap",
    "sunburst": "sunburst",
    "histogram": "histogram",
    "pareto": "pareto",
    "boxwhisker": "boxWhisker",
    "boxWhisker": "boxWhisker",
}

# Rows (excluding header) above this → appendix pagination recipe
_APPENDIX_ROW_THRESHOLD = 10
# Wide tables
_APPENDIX_COL_THRESHOLD = 6


def modernize_chart_type(raw: str | None) -> str:
    """Map extracted/legacy type names to a modern officecli chartType."""
    if not raw:
        return "column"
    key = str(raw).strip().lower().replace(" ", "").replace("_", "")
    # strip trailing "chart"
    if key.endswith("chart"):
        key = key[: -len("chart")]
    if key in _MODERN_CHART_TYPE:
        return _MODERN_CHART_TYPE[key]
    # already officecli-ish
    if raw in ("column", "bar", "line", "area", "pie", "doughnut", "waterfall",
               "funnel", "scatter"):
        return str(raw)
    return "column"


def chart_payload_to_content(
    chart: dict[str, Any],
    *,
    title: str = "Chart",
    body: list[str] | None = None,
) -> tuple[str, dict[str, Any], float, list[str]]:
    """(recipe, content, confidence, warnings) from a parsed chart dict."""
    warnings: list[str] = []
    body = list(body or [])
    series = chart.get("series") or []
    cats = chart.get("categories") or []
    raw_type = chart.get("chart_type") or "column"
    modern = modernize_chart_type(raw_type)
    if modern != str(raw_type).lower() and modern != raw_type:
        warnings.append(f"chart type modernized: {raw_type} → {modern}")

    content: dict[str, Any] = {
        "title": title or "Chart",
        "chart_type": modern,
        "categories": ",".join(str(c) for c in cats),
    }
    if series:
        content["series1_name"] = series[0].get("name") or "Series 1"
        content["series1_values"] = ",".join(
            str(v) for v in (series[0].get("values") or [])
        )
    if len(series) > 1:
        content["series2_name"] = series[1].get("name") or "Series 2"
        content["series2_values"] = ",".join(
            str(v) for v in (series[1].get("values") or [])
        )
    if len(series) > 2:
        warnings.append(
            f"{len(series)} series extracted; recipes render first two "
            f"(extras preserved under content._extra_series)"
        )
        content["_extra_series"] = [
            {"name": s.get("name"), "values": s.get("values")}
            for s in series[2:]
        ]

    # Recipe selection: waterfall special-case; callouts when body bullets exist
    recipe = "chart_insight"
    if modern == "waterfall":
        recipe = "waterfall_insight"
    elif len(body) >= 2:
        recipe = "chart_callout_panel"
        content["callouts"] = body[:4]
        content["insight_title"] = "Key insight"
        content["insight_body"] = body[0]
        if len(body) > 4:
            content["notes"] = " ".join(body[4:])
    elif body:
        content["insight_title"] = "Key insight"
        content["insight_body"] = body[0]
        if len(body) > 1:
            content["notes"] = " ".join(body[1:])

    if chart.get("partial"):
        warnings.append("chart data partial — verify series/categories")
        conf = 0.65
    elif series and cats:
        conf = 0.92
    elif series:
        conf = 0.8
    else:
        conf = 0.55
    return recipe, content, conf, warnings


def table_payload_to_content(
    rows: list[list[str]],
    *,
    title: str = "Table",
    body: list[str] | None = None,
) -> tuple[str, dict[str, Any], float, list[str]]:
    """(recipe, content, confidence, warnings) from a 2D string table."""
    warnings: list[str] = []
    body = list(body or [])
    if not rows:
        return "table", {"title": title, "headers": ["—"], "rows": []}, 0.4, [
            "empty table",
        ]
    headers = [str(h) for h in (rows[0] if rows else [])]
    data = [[str(c) for c in r] for r in rows[1:]]
    n_rows, n_cols = len(data), len(headers) or (len(data[0]) if data else 0)

    content: dict[str, Any] = {
        "title": title or "Table",
        "headers": headers,
        "rows": data,
    }
    if body:
        content["insight"] = body[0]
        content["insight_title"] = "Insight"
        content["insight_body"] = body[0]
        if len(body) > 1:
            content["notes"] = " ".join(body[1:])

    # Large / wide → appendix pagination (recipe handles multi-slide)
    if n_rows > _APPENDIX_ROW_THRESHOLD or n_cols > _APPENDIX_COL_THRESHOLD:
        recipe = "appendix_table"
        warnings.append(
            f"large table ({n_rows} rows × {n_cols} cols) → appendix_table "
            f"(auto-paginated on scaffold)"
        )
        conf = 0.9
    elif body:
        recipe = "results_table_insight"
        conf = 0.88
    else:
        recipe = "table"
        conf = 0.9
    return recipe, content, conf, warnings


def modernize_slide_spec(
    slide_spec: dict[str, Any],
    *,
    extracted_slide: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Modernize one deck-spec slide in place; return (slide, warnings)."""
    warnings: list[str] = []
    out = copy.deepcopy(slide_spec)
    recipe = out.get("recipe")
    content = out.setdefault("content", {})
    if not isinstance(content, dict):
        return out, warnings

    if recipe in ("chart_insight", "chart_callout_panel", "waterfall_insight"):
        raw = content.get("chart_type")
        modern = modernize_chart_type(raw)
        if modern != raw:
            content["chart_type"] = modern
            warnings.append(f"modernized chart_type {raw!r} → {modern!r}")
        if modern == "waterfall" and recipe != "waterfall_insight":
            out["recipe"] = "waterfall_insight"
            warnings.append("recipe → waterfall_insight for waterfall data")
        # Promote body-like notes into callouts when many clauses
        notes = content.get("notes") or ""
        if recipe == "chart_insight" and notes and ";" in notes:
            parts = [p.strip() for p in notes.split(";") if p.strip()]
            if len(parts) >= 2:
                out["recipe"] = "chart_callout_panel"
                content["callouts"] = parts[:4]
                warnings.append("promoted notes → chart_callout_panel callouts")

    if recipe in ("table", "appendix_table", "results_table_insight"):
        rows = content.get("rows") or []
        headers = content.get("headers") or []
        if len(rows) > _APPENDIX_ROW_THRESHOLD or len(headers) > _APPENDIX_COL_THRESHOLD:
            if recipe != "appendix_table":
                out["recipe"] = "appendix_table"
                warnings.append("large table recipe → appendix_table")
        elif content.get("insight") or content.get("insight_body"):
            if recipe == "table":
                out["recipe"] = "results_table_insight"
                warnings.append("table+insight → results_table_insight")

    # Optional re-derive from raw extract payload when provided
    if extracted_slide:
        charts = extracted_slide.get("charts") or []
        tables = extracted_slide.get("tables") or []
        body = list(extracted_slide.get("body") or [])
        title = extracted_slide.get("title") or content.get("title") or "Slide"
        if charts and recipe in (
            None, "bullets", "section_divider", "chart_insight",
            "chart_callout_panel", "waterfall_insight",
        ):
            r, c, _conf, w = chart_payload_to_content(
                charts[0], title=title, body=body,
            )
            out["recipe"] = r
            out["content"] = c
            warnings.extend(w)
        elif tables and recipe in (None, "bullets", "table", "appendix_table"):
            r, c, _conf, w = table_payload_to_content(
                tables[0], title=title, body=body,
            )
            out["recipe"] = r
            out["content"] = c
            warnings.extend(w)

    return out, warnings


def modernize_deck(
    deck: dict[str, Any],
    *,
    extract_report: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Modernize every slide; return (deck, per-slide warning records)."""
    out = copy.deepcopy(deck)
    slides = out.get("slides") or []
    report_slides = (extract_report or {}).get("slides") or []
    records: list[dict[str, Any]] = []
    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        extracted = None
        if i < len(report_slides) and isinstance(report_slides[i], dict):
            # extract report doesn't embed full chart payload — only geometry
            extracted = None
        modernized, warns = modernize_slide_spec(slide, extracted_slide=extracted)
        slides[i] = modernized
        if warns:
            records.append({"slide": i + 1, "warnings": warns, "recipe": modernized.get("recipe")})
    out["slides"] = slides
    return out, records


def classify_chart_table_slide(
    slide: dict[str, Any],
) -> tuple[str, dict[str, Any], float, list[str]] | None:
    """If slide has charts/tables, return modern classification; else None.

    Used by extract._classify so modern mapping is the single source of truth.
    """
    title = slide.get("title") or ""
    body: list[str] = list(slide.get("body") or [])
    charts = slide.get("charts") or []
    tables = slide.get("tables") or []

    if charts:
        if len(charts) > 1:
            # classify first; warn via returned list
            recipe, content, conf, warnings = chart_payload_to_content(
                charts[0], title=title or "Chart", body=body,
            )
            warnings.insert(
                0, f"{len(charts)} charts on slide; only the first was mapped",
            )
            return recipe, content, conf, warnings
        return chart_payload_to_content(charts[0], title=title or "Chart", body=body)

    if tables:
        warnings: list[str] = []
        if len(tables) > 1:
            warnings.append("multiple tables on slide; only the first was mapped")
        recipe, content, conf, w2 = table_payload_to_content(
            tables[0], title=title or "Table", body=body,
        )
        warnings.extend(w2)
        return recipe, content, conf, warnings

    return None
