"""Generate officecli batch JSON recipes from tokens.slide.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _cm(n: float) -> str:
    s = f"{n:.2f}".rstrip("0").rstrip(".")
    return f"{s}cm"


def _grid_n(
    n: int,
    margin: float,
    gap: float,
    width: float = 33.87,
    *,
    max_n: int = 4,
) -> tuple[float, list[float]]:
    """Adaptive N-column grid (1–max_n)."""
    n = max(1, min(max_n, int(n)))
    usable = width - 2 * margin - (n - 1) * gap
    col = usable / n
    xs = [margin + i * (col + gap) for i in range(n)]
    return col, xs


def _micro_pt(t: dict) -> int:
    return int(t.get("micro_pt", 14))


def _base_props(tokens: dict) -> dict[str, Any]:
    c = tokens["colors"]
    t = tokens["type"]
    return {
        "c": c,
        "t": t,
        "preset": tokens.get("shape", {}).get("card_preset", "roundRect"),
        "margin": float(tokens.get("margin_cm", 1.27)),
        "gap": float(tokens.get("gap_cm", 0.76)),
        "dark": bool(tokens.get("dark_first")),
    }


def recipe_cover(tokens: dict, content: dict | None = None) -> list[dict]:
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Presentation Title")
    subtitle = content.get("subtitle", "Subtitle")
    meta = content.get("meta", "Prepared with designmd-pptx")
    bg = tokens.get("background_gradient") or c["background"]

    return [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": bg},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "CoverTitle",
                "text": title,
                "x": _cm(b["margin"]),
                "y": "7cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "3cm",
                "font": t["heading_font"],
                "size": str(t["cover_pt"]),
                "bold": "true",
                "color": c["text"],
                "align": "center",
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "CoverSubtitle",
                "text": subtitle,
                "x": _cm(b["margin"]),
                "y": "10.4cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "1.2cm",
                "font": t["body_font"],
                "size": str(max(18, t["body_pt"])),
                "color": c["muted"],
                "align": "center",
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "CoverMeta",
                "text": meta,
                "x": _cm(b["margin"]),
                "y": "16.5cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "0.9cm",
                "font": t["body_font"],
                "size": str(t["caption_pt"]),
                "color": c["muted"],
                "align": "center",
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "CoverAccent",
                "preset": "rect",
                "fill": c["accent"],
                "line": "none",
                "x": "14.44cm",
                "y": "10.1cm",
                "width": "5cm",
                "height": "0.12cm",
            },
        },
    ]


def recipe_section_divider(tokens: dict, content: dict | None = None) -> list[dict]:
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    number = content.get("number", "01")
    title = content.get("title", "Section")
    blurb = content.get("blurb", "")

    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["background"]},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "SectionNumber",
                "text": str(number),
                "x": _cm(b["margin"]),
                "y": "4.2cm",
                "width": "14cm",
                "height": "4.8cm",
                "font": t["heading_font"],
                "size": "96",
                "bold": "true",
                "color": c["accent"],
                "fill": "none",
                "opacity": "0.25",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "SectionTitle",
                "text": title,
                "x": _cm(b["margin"]),
                "y": "9.5cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "2.5cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text"],
                "fill": "none",
            },
        },
    ]
    if blurb:
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "shape",
                "props": {
                    "name": "SectionBlurb",
                    "text": blurb,
                    "x": _cm(b["margin"]),
                    "y": "12.2cm",
                    "width": "24cm",
                    "height": "2cm",
                    "font": t["body_font"],
                    "size": str(t["body_pt"]),
                    "color": c["muted"],
                    "fill": "none",
                },
            }
        )
    return ops


def recipe_kpi_row(tokens: dict, content: dict | None = None) -> list[dict]:
    """Adaptive 2–4 KPI cards (default 3)."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Key metrics")
    kpis = content.get(
        "kpis",
        [
            {"value": "—", "label": "Metric A", "chip": ""},
            {"value": "—", "label": "Metric B", "chip": ""},
            {"value": "—", "label": "Metric C", "chip": ""},
        ],
    )
    if not isinstance(kpis, list) or not kpis:
        kpis = [{"value": "—", "label": "Metric", "chip": ""}]
    n = max(2, min(4, len(kpis)))
    kpis = kpis[:n]
    col_w, xs = _grid_n(n, b["margin"], b["gap"])
    bg = c["content_background"]
    card_fill = c["surface"]
    text_card = c["text_on_surface"]
    muted_card = c["muted"]
    micro = str(_micro_pt(t))

    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": bg},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "KpiTitle",
                "text": title,
                "x": _cm(b["margin"]),
                "y": "1.2cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "1.8cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
    ]

    y, h = 4.2, 10.5
    for i, kpi in enumerate(kpis):
        x = xs[i]
        watch = bool(kpi.get("watch"))
        fill = c["risk"] if watch else card_fill
        tc = c["on_accent"] if watch else text_card
        mc = "FFFFFF" if watch else muted_card
        name = f"Kpi{i+1}"
        ops.extend(
            [
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Bg",
                        "preset": b["preset"],
                        "fill": fill,
                        "line": "none",
                        "x": _cm(x),
                        "y": _cm(y),
                        "width": _cm(col_w),
                        "height": _cm(h),
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Value",
                        "text": str(kpi.get("value", "—")),
                        "x": _cm(x),
                        "y": _cm(y + 1.5),
                        "width": _cm(col_w),
                        "height": "3cm",
                        "font": t["heading_font"],
                        "size": str(t["kpi_pt"]),
                        "bold": "true",
                        "color": tc,
                        "align": "center",
                        "fill": "none",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Label",
                        "text": str(kpi.get("label", "")),
                        "x": _cm(x + 0.4),
                        "y": _cm(y + 5.2),
                        "width": _cm(col_w - 0.8),
                        "height": "1.2cm",
                        "font": t["body_font"],
                        "size": micro,
                        "color": mc,
                        "align": "center",
                        "fill": "none",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Chip",
                        "text": str(kpi.get("chip", "")),
                        "x": _cm(x + 0.4),
                        "y": _cm(y + 6.8),
                        "width": _cm(col_w - 0.8),
                        "height": "1cm",
                        "font": t["body_font"],
                        "size": micro,
                        "bold": "true",
                        "color": c["accent"] if not watch else mc,
                        "align": "center",
                        "fill": "none",
                    },
                },
            ]
        )
    ops.append(
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "notes",
            "props": {
                "text": content.get(
                    "notes",
                    "Walk KPIs left to right; pause on any watch metric.",
                )
            },
        }
    )
    return ops


def recipe_feature_cards(tokens: dict, content: dict | None = None) -> list[dict]:
    """Adaptive 2–4 feature cards."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Capabilities")
    cards = content.get(
        "cards",
        [
            {"title": "One", "body": "First capability."},
            {"title": "Two", "body": "Second capability."},
            {"title": "Three", "body": "Third capability."},
        ],
    )
    if not isinstance(cards, list) or not cards:
        cards = [{"title": "Item", "body": "Detail."}]
    n = max(2, min(4, len(cards)))
    cards = cards[:n]
    col_w, xs = _grid_n(n, b["margin"], b["gap"])
    bg = c["content_background"]
    card_fill = c["surface"]

    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": bg},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "FeatTitle",
                "text": title,
                "x": _cm(b["margin"]),
                "y": "1.2cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "1.8cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
    ]
    y, h = 4.0, 12.5
    for i, card in enumerate(cards):
        x = xs[i]
        ops.extend(
            [
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"Card{i+1}Bg",
                        "preset": b["preset"],
                        "fill": card_fill,
                        "line": c["hairline"],
                        "x": _cm(x),
                        "y": _cm(y),
                        "width": _cm(col_w),
                        "height": _cm(h),
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"Card{i+1}Accent",
                        "preset": "rect",
                        "fill": c["accent"],
                        "line": "none",
                        "x": _cm(x),
                        "y": _cm(y),
                        "width": _cm(col_w),
                        "height": "0.18cm",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"Card{i+1}Title",
                        "text": str(card.get("title", "")),
                        "x": _cm(x + 0.6),
                        "y": _cm(y + 1.2),
                        "width": _cm(col_w - 1.2),
                        "height": "1.5cm",
                        "font": t["heading_font"],
                        "size": str(max(20, t["section_pt"])),
                        "bold": "true",
                        "color": c["text_on_surface"],
                        "fill": "none",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"Card{i+1}Body",
                        "text": str(card.get("body", "")),
                        "x": _cm(x + 0.6),
                        "y": _cm(y + 3.2),
                        "width": _cm(col_w - 1.2),
                        "height": "8cm",
                        "font": t["body_font"],
                        "size": str(t["body_pt"]),
                        "color": c["muted"],
                        "fill": "none",
                    },
                },
            ]
        )
    return ops


def recipe_bullets(tokens: dict, content: dict | None = None) -> list[dict]:
    """Title + up to 5 body bullets (one idea per slide)."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Agenda")
    items = content.get("bullets") or content.get("items") or [
        "First point",
        "Second point",
        "Third point",
    ]
    if not isinstance(items, list):
        items = [str(items)]
    items = [str(x) for x in items[:5]]
    body = "\n".join(f"• {x}" for x in items)

    return [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "BulletTitle",
                "text": title,
                "x": _cm(b["margin"]),
                "y": "1.2cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "1.8cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "BulletBody",
                "text": body,
                "x": _cm(b["margin"]),
                "y": "3.8cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "13cm",
                "font": t["body_font"],
                "size": str(t["body_pt"]),
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "notes",
            "props": {"text": content.get("notes", "Expand each bullet; do not read the slide.")},
        },
    ]


def recipe_quote(tokens: dict, content: dict | None = None) -> list[dict]:
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    quote = content.get("quote", "A single sentence the room should remember.")
    attribution = content.get("attribution", "— Source")

    return [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["background"]},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "QuoteMark",
                "preset": "rect",
                "fill": c["accent"],
                "line": "none",
                "x": _cm(b["margin"]),
                "y": "5.5cm",
                "width": "0.25cm",
                "height": "6cm",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "QuoteText",
                "text": quote,
                "x": _cm(b["margin"] + 1.2),
                "y": "5.5cm",
                "width": _cm(33.87 - 2 * b["margin"] - 1.2),
                "height": "5cm",
                "font": t["heading_font"],
                "size": str(max(24, t["section_pt"])),
                "italic": "true",
                "color": c["text"],
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "QuoteAttr",
                "text": attribution,
                "x": _cm(b["margin"] + 1.2),
                "y": "11.2cm",
                "width": "20cm",
                "height": "1cm",
                "font": t["body_font"],
                "size": str(t["body_pt"]),
                "color": c["muted"],
                "fill": "none",
            },
        },
    ]


def recipe_comparison_2col(tokens: dict, content: dict | None = None) -> list[dict]:
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Compare")
    left = content.get("left") or {"title": "Option A", "body": "Strengths of A."}
    right = content.get("right") or {"title": "Option B", "body": "Strengths of B."}
    col_w, xs = _grid_n(2, b["margin"], b["gap"])

    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "CmpTitle",
                "text": title,
                "x": _cm(b["margin"]),
                "y": "1.2cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "1.8cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
    ]
    for i, side in enumerate((left, right)):
        x = xs[i]
        ops.extend(
            [
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"Cmp{i+1}Bg",
                        "preset": b["preset"],
                        "fill": c["surface"],
                        "line": c["hairline"],
                        "x": _cm(x),
                        "y": "4cm",
                        "width": _cm(col_w),
                        "height": "12.5cm",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"Cmp{i+1}Title",
                        "text": str(side.get("title", "")),
                        "x": _cm(x + 0.8),
                        "y": "4.8cm",
                        "width": _cm(col_w - 1.6),
                        "height": "1.5cm",
                        "font": t["heading_font"],
                        "size": str(max(20, t["section_pt"])),
                        "bold": "true",
                        "color": c["text_on_surface"],
                        "fill": "none",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"Cmp{i+1}Body",
                        "text": str(side.get("body", "")),
                        "x": _cm(x + 0.8),
                        "y": "6.8cm",
                        "width": _cm(col_w - 1.6),
                        "height": "9cm",
                        "font": t["body_font"],
                        "size": str(t["body_pt"]),
                        "color": c["muted"],
                        "fill": "none",
                    },
                },
            ]
        )
    return ops


def recipe_chart_insight(tokens: dict, content: dict | None = None) -> list[dict]:
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Trend")
    insight_h = content.get("insight_title", "Key insight")
    insight_b = content.get(
        "insight_body",
        "State the takeaway in one sentence; the chart is evidence, not the story.",
    )
    cats = content.get("categories", "A,B,C,D")
    s1 = content.get("series1_values", "10,12,14,16")
    s2 = content.get("series2_values", "9,11,12,13")
    s1_name = content.get("series1_name", "Series 1")
    s2_name = content.get("series2_name", "Series 2")
    # v1.5: any officecli chartType (column, bar, line, area, pie, doughnut,
    # scatter, waterfall, funnel, stacked* aliases, ...). Single-series
    # geometries drop series2 automatically.
    chart_type = str(content.get("chart_type", "column"))
    single_series = chart_type.lower() in (
        "pie", "doughnut", "funnel", "treemap", "sunburst", "pareto", "histogram",
    )
    bg = c["content_background"]
    series2 = c["chart_series2"]
    if series2 == c["chart_series1"]:
        series2 = c["muted"]

    chart_props: dict[str, Any] = {
        "name": "MainChart",
        "chartType": chart_type,
        "series1.name": s1_name,
        "series1.values": s1,
        "series1.color": c["chart_series1"],
        "categories": cats,
        "x": _cm(b["margin"]),
        "y": "3.5cm",
        "width": "20cm",
        "height": "14cm",
    }
    if not single_series and s2:
        chart_props.update(
            {"series2.name": s2_name, "series2.values": s2, "series2.color": series2}
        )

    return [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": bg},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "ChartTitle",
                "text": title,
                "x": _cm(b["margin"]),
                "y": "1cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "1.8cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "chart",
            "props": chart_props,
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "InsightBg",
                "preset": b["preset"],
                "fill": c["surface"],
                "line": "none",
                "x": "22.5cm",
                "y": "3.5cm",
                "width": "9.8cm",
                "height": "14cm",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "InsightTitle",
                "text": insight_h,
                "x": "23cm",
                "y": "4cm",
                "width": "9cm",
                "height": "1.2cm",
                "font": t["heading_font"],
                "size": str(max(18, t["section_pt"])),
                "bold": "true",
                "color": c["text_on_surface"],
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "InsightBody",
                "text": insight_b,
                "x": "23cm",
                "y": "5.5cm",
                "width": "9cm",
                "height": "11cm",
                "font": t["body_font"],
                "size": str(t["body_pt"]),
                "color": c["muted"],
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "notes",
            "props": {
                "text": content.get("notes", "Lead with the insight card, then point to the bars.")
            },
        },
    ]


def recipe_timeline(tokens: dict, content: dict | None = None) -> list[dict]:
    """Horizontal timeline: 2–6 steps with labels."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Timeline")
    steps = content.get("steps") or [
        {"label": "Discover", "detail": ""},
        {"label": "Build", "detail": ""},
        {"label": "Ship", "detail": ""},
        {"label": "Learn", "detail": ""},
    ]
    if not isinstance(steps, list):
        steps = [{"label": str(steps)}]
    n = max(2, min(6, len(steps)))
    steps = steps[:n]
    col_w, xs = _grid_n(n, b["margin"], b["gap"], max_n=6)
    micro = str(_micro_pt(t))
    y_line = 9.0
    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "TlTitle",
                "text": title,
                "x": _cm(b["margin"]),
                "y": "1.2cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "1.8cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "TlAxis",
                "preset": "rect",
                "fill": c["hairline"],
                "line": "none",
                "x": _cm(b["margin"]),
                "y": _cm(y_line),
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "0.12cm",
            },
        },
    ]
    for i, step in enumerate(steps):
        if isinstance(step, str):
            label, detail = step, ""
        else:
            label = str(step.get("label", f"Step {i+1}"))
            detail = str(step.get("detail", ""))
        x = xs[i]
        cx = x + col_w / 2 - 0.45
        ops.extend(
            [
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"TlDot{i+1}",
                        "preset": "ellipse",
                        "fill": c["accent"],
                        "line": "none",
                        "x": _cm(cx),
                        "y": _cm(y_line - 0.35),
                        "width": "0.9cm",
                        "height": "0.9cm",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"TlLabel{i+1}",
                        "text": label,
                        "x": _cm(x),
                        "y": _cm(y_line + 1.2),
                        "width": _cm(col_w),
                        "height": "1.4cm",
                        "font": t["heading_font"],
                        "size": str(max(16, min(20, t["section_pt"]))),
                        "bold": "true",
                        "color": c["text_on_content"],
                        "align": "center",
                        "fill": "none",
                    },
                },
            ]
        )
        if detail:
            ops.append(
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"TlDetail{i+1}",
                        "text": detail,
                        "x": _cm(x),
                        "y": _cm(y_line + 2.7),
                        "width": _cm(col_w),
                        "height": "3cm",
                        "font": t["body_font"],
                        "size": micro if int(micro) >= 12 else "14",
                        "color": c["muted"],
                        "align": "center",
                        "fill": "none",
                    },
                }
            )
    if content.get("notes"):
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "notes",
                "props": {"text": content["notes"]},
            }
        )
    return ops


def recipe_process(
    tokens: dict,
    content: dict | None = None,
    *,
    slide_index: int | None = None,
) -> list[dict]:
    """Process boxes + glued officecli connectors (2–5 steps). Requires slide_index for connectors."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Process")
    steps = content.get("steps") or ["Input", "Transform", "Output"]
    if not isinstance(steps, list):
        steps = [str(steps)]
    n = max(2, min(5, len(steps)))
    steps = steps[:n]
    col_w, xs = _grid_n(n, b["margin"], b["gap"], max_n=5)
    box_h = 3.2
    y = 8.0
    parent = "/slide[last()]"
    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        },
        {
            "command": "add",
            "parent": parent,
            "type": "shape",
            "props": {
                "name": "ProcTitle",
                "text": title,
                "x": _cm(b["margin"]),
                "y": "1.2cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "1.8cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
    ]
    names: list[str] = []
    for i, step in enumerate(steps):
        if isinstance(step, dict):
            label = str(step.get("label", step.get("title", f"Step {i+1}")))
        else:
            label = str(step)
        name = f"Proc{i+1}"
        names.append(name)
        fill = c["accent"] if i == 0 or i == n - 1 else c["surface"]
        tc = c["on_accent"] if fill == c["accent"] else c["text_on_surface"]
        if fill == c["surface"]:
            tc = c["text_on_surface"]
        ops.append(
            {
                "command": "add",
                "parent": parent,
                "type": "shape",
                "props": {
                    "name": name,
                    "preset": b["preset"],
                    "fill": fill,
                    "line": "none",
                    "text": label,
                    "x": _cm(xs[i]),
                    "y": _cm(y),
                    "width": _cm(col_w),
                    "height": _cm(box_h),
                    "font": t["body_font"],
                    "size": str(max(16, min(20, t["body_pt"]))),
                    "bold": "true",
                    "color": tc,
                    "align": "center",
                    "valign": "middle",
                },
            }
        )
    # Glued connectors with absolute slide index (required — last() fails in from/to)
    if slide_index is not None:
        for i in range(len(names) - 1):
            a, bname = names[i], names[i + 1]
            ops.append(
                {
                    "command": "add",
                    "parent": parent,
                    "type": "connector",
                    "props": {
                        "from": f"/slide[{slide_index}]/shape[@name={a}]",
                        "to": f"/slide[{slide_index}]/shape[@name={bname}]",
                        "shape": "straight",
                        "color": c["muted"],
                        "tailEnd": "triangle",
                    },
                }
            )
    else:
        # catalog mode without index: decorative arrows (documented fallback)
        for i in range(len(names) - 1):
            gap_x = xs[i] + col_w
            next_x = xs[i + 1]
            aw = max(0.4, next_x - gap_x - 0.1)
            ops.append(
                {
                    "command": "add",
                    "parent": parent,
                    "type": "shape",
                    "props": {
                        "name": f"ProcArrow{i+1}",
                        "preset": "rightArrow",
                        "fill": c["muted"],
                        "line": "none",
                        "x": _cm(gap_x + 0.05),
                        "y": _cm(y + box_h / 2 - 0.35),
                        "width": _cm(aw),
                        "height": "0.7cm",
                    },
                }
            )
    if content.get("notes"):
        ops.append(
            {
                "command": "add",
                "parent": parent,
                "type": "notes",
                "props": {"text": content["notes"]},
            }
        )
    return ops


def recipe_table(tokens: dict, content: dict | None = None) -> list[dict]:
    """Shape-grid table (batch-safe; avoids set/last() path issues)."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Comparison")
    headers = content.get("headers") or ["Item", "Value", "Notes"]
    rows = content.get("rows") or [
        ["Alpha", "High", "Primary"],
        ["Beta", "Med", "Secondary"],
        ["Gamma", "Low", "Watch"],
    ]
    if not isinstance(headers, list):
        headers = ["Col1", "Col2"]
    if not isinstance(rows, list):
        rows = []
    cols = max(1, min(6, len(headers)))
    headers = [str(h) for h in headers[:cols]]
    norm_rows: list[list[str]] = []
    for r in rows[:8]:
        if isinstance(r, list):
            cells = [str(x) for x in r]
        else:
            cells = [str(r)]
        while len(cells) < cols:
            cells.append("")
        norm_rows.append(cells[:cols])
    if not norm_rows:
        norm_rows = [[""] * cols]

    table_w = 33.87 - 2 * b["margin"]
    gap = 0.08
    col_w = (table_w - gap * (cols - 1)) / cols
    row_h = 1.6
    start_y = 3.4

    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "TblTitle",
                "text": title,
                "x": _cm(b["margin"]),
                "y": "1.0cm",
                "width": _cm(table_w),
                "height": "1.8cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
    ]
    # header
    for ci, h in enumerate(headers):
        x = b["margin"] + ci * (col_w + gap)
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "shape",
                "props": {
                    "name": f"Th{ci+1}",
                    "preset": "rect",
                    "fill": c["accent"],
                    "line": "none",
                    "text": h,
                    "x": _cm(x),
                    "y": _cm(start_y),
                    "width": _cm(col_w),
                    "height": _cm(row_h),
                    "font": t["body_font"],
                    "size": str(max(14, min(18, t["body_pt"]))),
                    "bold": "true",
                    "color": c["on_accent"],
                    "align": "center",
                    "valign": "middle",
                },
            }
        )
    for ri, row in enumerate(norm_rows):
        for ci, cell in enumerate(row):
            x = b["margin"] + ci * (col_w + gap)
            y = start_y + (ri + 1) * (row_h + gap)
            fill = c["surface"] if ri % 2 == 0 else c.get("surface_elevated", c["surface"])
            ops.append(
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"Td{ri+1}_{ci+1}",
                        "preset": "rect",
                        "fill": fill,
                        "line": c["hairline"],
                        "text": cell,
                        "x": _cm(x),
                        "y": _cm(y),
                        "width": _cm(col_w),
                        "height": _cm(row_h),
                        "font": t["body_font"],
                        "size": str(max(14, min(18, t["body_pt"]))),
                        "color": c["text_on_surface"],
                        "align": "center",
                        "valign": "middle",
                    },
                }
            )
    if content.get("notes"):
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "notes",
                "props": {"text": content["notes"]},
            }
        )
    return ops


def recipe_image_full(tokens: dict, content: dict | None = None) -> list[dict]:
    """
    Image-forward slide. If src missing, draws a surface placeholder panel
    (so batch still succeeds without assets).
    """
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "")
    src = content.get("src")
    alt = content.get("alt", "Slide image")
    caption = content.get("caption", "")

    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        }
    ]
    if title:
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "shape",
                "props": {
                    "name": "ImgTitle",
                    "text": title,
                    "x": _cm(b["margin"]),
                    "y": "0.7cm",
                    "width": _cm(33.87 - 2 * b["margin"]),
                    "height": "1.9cm",
                    "font": t["heading_font"],
                    "size": str(t["title_pt"]),
                    "bold": "true",
                    "color": c["text_on_content"],
                    "fill": "none",
                },
            }
        )
        img_y, img_h = 2.9, 13.0
    else:
        img_y, img_h = 1.2, 15.5

    if src:
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "picture",
                "props": {
                    "name": "HeroImage",
                    "src": str(src),
                    "alt": alt,
                    "x": _cm(b["margin"]),
                    "y": _cm(img_y),
                    "width": _cm(33.87 - 2 * b["margin"]),
                    "height": _cm(img_h if not caption else img_h - 1.4),
                },
            }
        )
    else:
        ops.extend(
            [
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": "ImgPlaceholder",
                        "preset": b["preset"],
                        "fill": c["surface"],
                        "line": c["hairline"],
                        "x": _cm(b["margin"]),
                        "y": _cm(img_y),
                        "width": _cm(33.87 - 2 * b["margin"]),
                        "height": _cm(img_h if not caption else img_h - 1.4),
                        "text": "Image placeholder — set content.image_full.src",
                        "font": t["body_font"],
                        "size": str(t["body_pt"]),
                        "color": c["muted"],
                        "align": "center",
                        "valign": "middle",
                    },
                }
            ]
        )
    if caption:
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "shape",
                "props": {
                    "name": "ImgCaption",
                    "text": caption,
                    "x": _cm(b["margin"]),
                    "y": "17.2cm",
                    "width": _cm(33.87 - 2 * b["margin"]),
                    "height": "0.9cm",
                    "font": t["body_font"],
                    "size": str(t["caption_pt"]),
                    "color": c["muted"],
                    "fill": "none",
                },
            }
        )
    if content.get("notes"):
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "notes",
                "props": {"text": content["notes"]},
            }
        )
    return ops


def recipe_image_text_2col(
    tokens: dict,
    content: dict | None = None,
    *,
    slide_index: int | None = None,
) -> list[dict]:
    """Image + text two-column layout. alt required when src set."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Feature")
    body = content.get("body", "Supporting explanation beside the visual.")
    src = content.get("src")
    alt = content.get("alt", "")
    side = str(content.get("image_side", "left")).lower()
    if side not in ("left", "right"):
        side = "left"

    margin = b["margin"]
    gap = b["gap"]
    usable = 33.87 - 2 * margin - gap
    col_w = usable / 2
    img_x = margin if side == "left" else margin + col_w + gap
    text_x = margin + col_w + gap if side == "left" else margin

    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "It2Title",
                "text": title,
                "x": _cm(text_x),
                "y": "2.5cm",
                "width": _cm(col_w),
                "height": "2cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "It2Body",
                "text": body,
                "x": _cm(text_x),
                "y": "5cm",
                "width": _cm(col_w),
                "height": "11cm",
                "font": t["body_font"],
                "size": str(t["body_pt"]),
                "color": c["muted"],
                "fill": "none",
            },
        },
    ]
    if src:
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "picture",
                "props": {
                    "name": "It2Image",
                    "src": str(src),
                    "alt": alt or "Illustration",
                    "x": _cm(img_x),
                    "y": "2.5cm",
                    "width": _cm(col_w),
                    "height": "14cm",
                },
            }
        )
    else:
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "shape",
                "props": {
                    "name": "It2Placeholder",
                    "preset": b["preset"],
                    "fill": c["surface"],
                    "line": c["hairline"],
                    "text": "Image — set content.src",
                    "x": _cm(img_x),
                    "y": "2.5cm",
                    "width": _cm(col_w),
                    "height": "14cm",
                    "font": t["body_font"],
                    "size": str(t["body_pt"]),
                    "color": c["muted"],
                    "align": "center",
                    "valign": "middle",
                },
            }
        )
    if content.get("notes"):
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "notes",
                "props": {"text": content["notes"]},
            }
        )
    return ops


def recipe_close(tokens: dict, content: dict | None = None) -> list[dict]:
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Next step")
    body = content.get("body", "One clear ask. One owner. One date.")
    cta = content.get("cta", "Continue")

    return [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["background"]},
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "CloseTitle",
                "text": title,
                "x": _cm(b["margin"]),
                "y": "6cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "2.5cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text"],
                "align": "center",
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "CloseBody",
                "text": body,
                "x": _cm(b["margin"]),
                "y": "9cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "1.5cm",
                "font": t["body_font"],
                "size": str(t["body_pt"]),
                "color": c["muted"],
                "align": "center",
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "CloseCta",
                "preset": b["preset"],
                "fill": c["accent"],
                "line": "none",
                "text": cta,
                "x": "12.4cm",
                "y": "12cm",
                "width": "9cm",
                "height": "1.6cm",
                "font": t["body_font"],
                "size": str(max(18, t["body_pt"])),
                "bold": "true",
                "color": c["on_accent"],
                "align": "center",
                "valign": "middle",
            },
        },
    ]


def _title_op(tokens: dict, name: str, title: str, *, y: str = "1.0cm") -> dict:
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    return {
        "command": "add",
        "parent": "/slide[last()]",
        "type": "shape",
        "props": {
            "name": name,
            "text": title,
            "x": _cm(b["margin"]),
            "y": y,
            "width": _cm(33.87 - 2 * b["margin"]),
            "height": "1.8cm",
            "font": t["heading_font"],
            "size": str(t["title_pt"]),
            "bold": "true",
            "color": c["text_on_content"],
            "fill": "none",
        },
    }


def _slide_op(tokens: dict) -> dict:
    c = tokens["colors"]
    return {
        "command": "add",
        "parent": "/",
        "type": "slide",
        "props": {"layout": "blank", "background": c["content_background"]},
    }


def recipe_big_number(tokens: dict, content: dict | None = None) -> list[dict]:
    """One hero metric: huge value, label, context line."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    value = str(content.get("value", "—"))
    label = content.get("label", "Headline metric")
    context = content.get("context", "")
    mega = int(t.get("mega_pt", int(t.get("kpi_pt", 60) * 1.6)))
    color = c["risk"] if content.get("watch") else c["accent"]
    ops = [
        _slide_op(tokens),
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "BigValue",
                "text": value,
                "x": _cm(b["margin"]),
                "y": "4.6cm",
                "width": _cm(33.87 - 2 * b["margin"]),
                "height": "6cm",
                "font": t["heading_font"],
                "size": str(mega),
                "bold": "true",
                "color": color,
                "align": "center",
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "BigLabel",
                "text": str(label),
                "x": "3.94cm",
                "y": "11.2cm",
                "width": "26cm",
                "height": "1.6cm",
                "font": t["heading_font"],
                "size": str(t["section_pt"]),
                "bold": "true",
                "color": c["text_on_content"],
                "align": "center",
                "fill": "none",
            },
        },
    ]
    if context:
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "shape",
                "props": {
                    "name": "BigContext",
                    "text": str(context),
                    "x": "3.94cm",
                    "y": "13.2cm",
                    "width": "26cm",
                    "height": "2cm",
                    "font": t["body_font"],
                    "size": str(t["body_pt"]),
                    "color": c["muted"],
                    "align": "center",
                    "fill": "none",
                },
            }
        )
    ops.append(
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "notes",
            "props": {"text": content.get("notes", "Let the number land; one sentence of context.")},
        }
    )
    return ops


def recipe_matrix_2x2(tokens: dict, content: dict | None = None) -> list[dict]:
    """2×2 quadrant matrix with optional axis labels."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Where we play")
    quads = content.get("quadrants") or [
        {"title": f"Quadrant {i + 1}", "body": ""} for i in range(4)
    ]
    quads = (list(quads) + [{}] * 4)[:4]
    axes = content.get("axes") or {}
    usable = 33.87 - 2 * b["margin"]
    col_w = (usable - b["gap"]) / 2
    row_h, y0 = 6.4, 3.8
    ops = [_slide_op(tokens), _title_op(tokens, "MatrixTitle", title)]
    for i, q in enumerate(quads):
        x = b["margin"] + (i % 2) * (col_w + b["gap"])
        y = y0 + (i // 2) * (row_h + b["gap"])
        name = f"Quad{i + 1}"
        ops.extend(
            [
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Bg", "preset": b["preset"], "fill": c["surface"],
                        "line": "none", "x": _cm(x), "y": _cm(y),
                        "width": _cm(col_w), "height": _cm(row_h),
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Title", "text": str(q.get("title", "")),
                        "x": _cm(x + 0.5), "y": _cm(y + 0.4),
                        "width": _cm(col_w - 1), "height": "1.2cm",
                        "font": t["heading_font"], "size": str(max(18, t["section_pt"] - 4)),
                        "bold": "true", "color": c["text_on_surface"], "fill": "none",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Body", "text": str(q.get("body", "")),
                        "x": _cm(x + 0.5), "y": _cm(y + 1.8),
                        "width": _cm(col_w - 1), "height": _cm(row_h - 2.2),
                        "font": t["body_font"], "size": str(t["body_pt"]),
                        "color": c["muted"], "fill": "none",
                    },
                },
            ]
        )
    micro = str(_micro_pt(t))
    if axes.get("x"):
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "shape",
                "props": {
                    "name": "AxisX", "text": f"→ {axes['x']}",
                    "x": _cm(b["margin"]), "y": "17.5cm",
                    "width": _cm(usable), "height": "0.9cm",
                    "font": t["body_font"], "size": micro,
                    "color": c["muted"], "align": "center", "fill": "none",
                },
            }
        )
    if axes.get("y"):
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "shape",
                "props": {
                    "name": "AxisY", "text": f"↑ {axes['y']}",
                    "x": _cm(b["margin"]), "y": "3.0cm",
                    "width": "12cm", "height": "0.8cm",
                    "font": t["body_font"], "size": micro,
                    "color": c["muted"], "fill": "none",
                },
            }
        )
    ops.append(
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "notes",
            "props": {"text": content.get("notes", "Walk quadrants clockwise from top-left.")},
        }
    )
    return ops


def _initials(name: str) -> str:
    parts = [p for p in str(name).split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def recipe_team(tokens: dict, content: dict | None = None) -> list[dict]:
    """2–4 member cards: initials disc, name, role, blurb."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Team")
    members = content.get("members") or [
        {"name": "Member One", "role": "Role", "blurb": ""},
        {"name": "Member Two", "role": "Role", "blurb": ""},
    ]
    n = max(2, min(4, len(members)))
    members = members[:n]
    col_w, xs = _grid_n(n, b["margin"], b["gap"])
    micro = str(_micro_pt(t))
    y, h = 4.0, 12.0
    ops = [_slide_op(tokens), _title_op(tokens, "TeamTitle", title, y="1.2cm")]
    for i, m in enumerate(members):
        x = xs[i]
        name = f"Member{i + 1}"
        disc = min(3.4, col_w * 0.4)
        ops.extend(
            [
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Bg", "preset": b["preset"], "fill": c["surface"],
                        "line": "none", "x": _cm(x), "y": _cm(y),
                        "width": _cm(col_w), "height": _cm(h),
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Avatar", "preset": "ellipse", "fill": c["accent"],
                        "line": "none", "text": _initials(m.get("name", "")),
                        "x": _cm(x + (col_w - disc) / 2), "y": _cm(y + 1.0),
                        "width": _cm(disc), "height": _cm(disc),
                        "font": t["heading_font"], "size": str(max(18, t["section_pt"] - 4)),
                        "bold": "true", "color": c["on_accent"],
                        "align": "center", "valign": "middle",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Name", "text": str(m.get("name", "")),
                        "x": _cm(x + 0.4), "y": _cm(y + disc + 1.4),
                        "width": _cm(col_w - 0.8), "height": "1.1cm",
                        "font": t["heading_font"], "size": str(max(16, t["section_pt"] - 8)),
                        "bold": "true", "color": c["text_on_surface"],
                        "align": "center", "fill": "none",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Role", "text": str(m.get("role", "")),
                        "x": _cm(x + 0.4), "y": _cm(y + disc + 2.5),
                        "width": _cm(col_w - 0.8), "height": "0.9cm",
                        "font": t["body_font"], "size": micro,
                        "bold": "true", "color": c["accent"],
                        "align": "center", "fill": "none",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Blurb", "text": str(m.get("blurb", "")),
                        "x": _cm(x + 0.5), "y": _cm(y + disc + 3.5),
                        "width": _cm(col_w - 1.0), "height": _cm(h - disc - 4.0),
                        "font": t["body_font"], "size": str(max(12, t["body_pt"] - 4)),
                        "color": c["muted"], "align": "center", "fill": "none",
                    },
                },
            ]
        )
    ops.append(
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "notes",
            "props": {"text": content.get("notes", "One line each: name, why they matter here.")},
        }
    )
    return ops


def recipe_logo_strip(tokens: dict, content: dict | None = None) -> list[dict]:
    """Row of up to 6 partner/customer logos (image or text placeholder)."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Trusted by")
    logos = content.get("logos") or [{"label": f"Logo {i + 1}"} for i in range(4)]
    n = max(2, min(6, len(logos)))
    logos = logos[:n]
    col_w, xs = _grid_n(n, b["margin"], b["gap"], max_n=6)
    y, h = 7.0, 4.5
    ops = [_slide_op(tokens), _title_op(tokens, "LogoTitle", title, y="1.2cm")]
    for i, logo in enumerate(logos):
        if isinstance(logo, str):
            logo = {"label": logo}
        x = xs[i]
        src = logo.get("src")
        if src:
            ops.append(
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "picture",
                    "props": {
                        "name": f"Logo{i + 1}",
                        "src": str(src),
                        "alt": logo.get("alt") or logo.get("label") or f"Logo {i + 1}",
                        "x": _cm(x + 0.3), "y": _cm(y + 0.3),
                        "width": _cm(col_w - 0.6), "height": _cm(h - 0.6),
                    },
                }
            )
        else:
            ops.append(
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"Logo{i + 1}", "preset": b["preset"],
                        "fill": c["surface"], "line": c["hairline"],
                        "text": str(logo.get("label", "")),
                        "x": _cm(x), "y": _cm(y),
                        "width": _cm(col_w), "height": _cm(h),
                        "font": t["heading_font"], "size": str(max(14, t["body_pt"])),
                        "bold": "true", "color": c["muted"],
                        "align": "center", "valign": "middle",
                    },
                }
            )
    ops.append(
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "notes",
            "props": {"text": content.get("notes", "Name-drop two, move on.")},
        }
    )
    return ops


def recipe_pricing(tokens: dict, content: dict | None = None) -> list[dict]:
    """2–3 pricing tiers; highlight=true renders the accent tier."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Pricing")
    tiers = content.get("tiers") or [
        {"name": "Starter", "price": "$0", "features": ["Feature A"]},
        {"name": "Pro", "price": "$29", "features": ["Everything in Starter"], "highlight": True},
    ]
    n = max(2, min(3, len(tiers)))
    tiers = tiers[:n]
    col_w, xs = _grid_n(n, b["margin"], b["gap"], max_n=3)
    micro = str(_micro_pt(t))
    y, h = 3.8, 13.2
    ops = [_slide_op(tokens), _title_op(tokens, "PricingTitle", title)]
    for i, tier in enumerate(tiers):
        x = xs[i]
        hi = bool(tier.get("highlight"))
        fill = c["accent"] if hi else c["surface"]
        fg = c["on_accent"] if hi else c["text_on_surface"]
        sub = "FFFFFF" if hi else c["muted"]
        name = f"Tier{i + 1}"
        ops.extend(
            [
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Bg", "preset": b["preset"], "fill": fill,
                        "line": "none" if hi else c["hairline"],
                        "x": _cm(x), "y": _cm(y), "width": _cm(col_w), "height": _cm(h),
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Name", "text": str(tier.get("name", "")),
                        "x": _cm(x + 0.5), "y": _cm(y + 0.8),
                        "width": _cm(col_w - 1), "height": "1.2cm",
                        "font": t["heading_font"], "size": str(max(18, t["section_pt"] - 4)),
                        "bold": "true", "color": fg, "align": "center", "fill": "none",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Price", "text": str(tier.get("price", "")),
                        "x": _cm(x + 0.5), "y": _cm(y + 2.2),
                        "width": _cm(col_w - 1), "height": "2.6cm",
                        "font": t["heading_font"], "size": str(t["kpi_pt"]),
                        "bold": "true", "color": fg, "align": "center", "fill": "none",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Period", "text": str(tier.get("period", "")),
                        "x": _cm(x + 0.5), "y": _cm(y + 4.9),
                        "width": _cm(col_w - 1), "height": "0.9cm",
                        "font": t["body_font"], "size": micro,
                        "color": sub, "align": "center", "fill": "none",
                    },
                },
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"{name}Features",
                        "text": "\n".join(f"• {f}" for f in (tier.get("features") or [])[:5]),
                        "x": _cm(x + 0.7), "y": _cm(y + 6.2),
                        "width": _cm(col_w - 1.4), "height": _cm(h - 6.8),
                        "font": t["body_font"], "size": str(max(12, t["body_pt"] - 4)),
                        "color": sub, "fill": "none",
                    },
                },
            ]
        )
    ops.append(
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "notes",
            "props": {"text": content.get("notes", "Anchor on the highlighted tier.")},
        }
    )
    return ops


def recipe_appendix_table(tokens: dict, content: dict | None = None) -> list[dict]:
    """Dense reference table for appendices: up to 8 columns × 14 rows."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Appendix")
    headers = content.get("headers") or ["Item", "Value"]
    rows = content.get("rows") or []
    cols = max(1, min(8, len(headers)))
    headers = [str(h) for h in headers[:cols]]
    norm_rows: list[list[str]] = []
    for r in rows[:14]:
        cells = [str(x) for x in r] if isinstance(r, list) else [str(r)]
        while len(cells) < cols:
            cells.append("")
        norm_rows.append(cells[:cols])
    if not norm_rows:
        norm_rows = [[""] * cols]

    table_w = 33.87 - 2 * b["margin"]
    gap = 0.06
    col_w = (table_w - gap * (cols - 1)) / cols
    row_h, start_y = 0.98, 2.9
    fs = str(max(10, min(12, _micro_pt(t))))

    ops: list[dict] = [
        _slide_op(tokens),
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "AppTitle", "text": title,
                "x": _cm(b["margin"]), "y": "0.8cm",
                "width": _cm(table_w), "height": "1.4cm",
                "font": t["heading_font"], "size": str(t["section_pt"]),
                "bold": "true", "color": c["text_on_content"], "fill": "none",
            },
        },
    ]
    for ci, hcell in enumerate(headers):
        x = b["margin"] + ci * (col_w + gap)
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "shape",
                "props": {
                    "name": f"ATh{ci + 1}", "preset": "rect", "fill": c["accent"],
                    "line": "none", "text": hcell,
                    "x": _cm(x), "y": _cm(start_y),
                    "width": _cm(col_w), "height": _cm(row_h),
                    "font": t["body_font"], "size": fs, "bold": "true",
                    "color": c["on_accent"], "align": "center", "valign": "middle",
                },
            }
        )
    for ri, row in enumerate(norm_rows):
        for ci, cell in enumerate(row):
            x = b["margin"] + ci * (col_w + gap)
            y = start_y + (ri + 1) * (row_h + gap)
            fill = c["surface"] if ri % 2 == 0 else c.get("surface_elevated", c["surface"])
            ops.append(
                {
                    "command": "add",
                    "parent": "/slide[last()]",
                    "type": "shape",
                    "props": {
                        "name": f"ATd{ri + 1}_{ci + 1}", "preset": "rect",
                        "fill": fill, "line": c["hairline"], "text": cell,
                        "x": _cm(x), "y": _cm(y),
                        "width": _cm(col_w), "height": _cm(row_h),
                        "font": t["body_font"], "size": fs,
                        "color": c["text_on_surface"], "align": "center", "valign": "middle",
                    },
                }
            )
    if content.get("notes"):
        ops.append(
            {
                "command": "add",
                "parent": "/slide[last()]",
                "type": "notes",
                "props": {"text": content["notes"]},
            }
        )
    return ops


def _call_builder(builder, tokens, content, slide_index: int | None = None):
    """Call recipe builder with optional slide_index if supported."""
    try:
        return builder(tokens, content, slide_index=slide_index)
    except TypeError:
        return builder(tokens, content)


# Primary builders
RECIPE_BUILDERS = {
    "cover": recipe_cover,
    "section_divider": recipe_section_divider,
    "kpi_row": recipe_kpi_row,
    "feature_cards": recipe_feature_cards,
    "bullets": recipe_bullets,
    "quote": recipe_quote,
    "comparison_2col": recipe_comparison_2col,
    "timeline": recipe_timeline,
    "process": recipe_process,
    "table": recipe_table,
    "image_full": recipe_image_full,
    "image_text_2col": recipe_image_text_2col,
    "chart_insight": recipe_chart_insight,
    "close": recipe_close,
    "big_number": recipe_big_number,
    "matrix_2x2": recipe_matrix_2x2,
    "team": recipe_team,
    "logo_strip": recipe_logo_strip,
    "pricing": recipe_pricing,
    "appendix_table": recipe_appendix_table,
}

# Back-compat aliases used by older content.sample.json keys
RECIPE_ALIASES = {
    "kpi_3": "kpi_row",
    "feature_cards_3": "feature_cards",
}

DEFAULT_SEQUENCE = [
    "cover",
    "section_divider",
    "kpi_row",
    "big_number",
    "feature_cards",
    "pricing",
    "bullets",
    "timeline",
    "process",
    "table",
    "appendix_table",
    "chart_insight",
    "comparison_2col",
    "matrix_2x2",
    "quote",
    "team",
    "logo_strip",
    "image_full",
    "image_text_2col",
    "close",
]


def generate_all_recipes(
    tokens: dict,
    content_map: dict[str, dict] | None = None,
    *,
    validate: bool = True,
    catalog: bool = True,
) -> dict[str, list[dict]]:
    """
    Catalog mode: one JSON file per recipe (for inspection).
    Prefer generate_deck() / write_deck() for real presentations.
    """
    from .validate import validate_content_overlay

    content_map = content_map or {}
    if validate and content_map and not isinstance(content_map.get("slides"), list):
        errs = validate_content_overlay(content_map)
        if errs:
            raise ValueError("content overlay invalid:\n- " + "\n- ".join(errs))

    normalized: dict[str, dict] = {}
    if content_map and isinstance(content_map.get("slides"), list):
        for s in content_map["slides"]:
            if isinstance(s, dict) and s.get("recipe"):
                r = RECIPE_ALIASES.get(s["recipe"], s["recipe"])
                normalized[r] = s.get("content") or {}
    else:
        normalized = dict(content_map or {})
        for alias, canon in RECIPE_ALIASES.items():
            if alias in normalized and canon not in normalized:
                normalized[canon] = normalized[alias]

    out: dict[str, list[dict]] = {}
    if catalog:
        for name, builder in RECIPE_BUILDERS.items():
            # catalog: process gets slide_index=1 so connectors appear in JSON for inspection
            idx = 1 if name == "process" else None
            out[name] = _call_builder(builder, tokens, normalized.get(name), idx)
    return out


def write_recipes(recipes: dict[str, list[dict]], out_dir: str | Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name, ops in recipes.items():
        p = out_dir / f"{name}.json"
        p.write_text(json.dumps(ops, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths.append(p)
    return paths


def write_deck_sequence(ops: list[dict], out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    combo = out_dir / "deck.sequence.json"
    combo.write_text(json.dumps(ops, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return combo


def write_slide_design_md(tokens: dict, dest: str | Path) -> Path:
    """Emit a SLIDE-DESIGN.md summary for agents (medium-native)."""
    dest = Path(dest)
    c = tokens["colors"]
    t = tokens["type"]
    prov = tokens.get("color_provenance") or {}
    lines = [
        f"# SLIDE-DESIGN.md — {tokens.get('brand', 'Brand')}",
        "",
        f"> Compiled from `{tokens.get('source', 'DESIGN.md')}` by designmd-pptx "
        f"v{tokens.get('compiler', {}).get('version', '?')}.",
        "",
        "## Atmosphere",
        "",
        tokens.get("description", "")[:400],
        "",
        f"**Motif:** `{tokens.get('motif')}`  ",
        f"**Dark-first:** `{tokens.get('dark_first')}`  ",
        f"**Content BG policy:** `{tokens.get('content_bg_policy', 'match_canvas')}`",
        "",
        "## Tokens (officecli props)",
        "",
        "| Role | Hex | Provenance |",
        "|---|---|---|",
    ]
    for k, v in c.items():
        src = prov.get(k, prov.get(k.replace("chart_", ""), "—"))
        lines.append(f"| `{k}` | `{v}` | {src} |")
    lines += [
        "",
        "## Type",
        "",
        f"- Heading font: **{t['heading_font']}**",
        f"- Body font: **{t['body_font']}**",
        f"- Cover: {t['cover_pt']}pt · Title: {t['title_pt']}pt · Body: {t['body_pt']}pt",
        f"- KPI: {t['kpi_pt']}pt · Micro/chip: {t.get('micro_pt', 14)}pt · Caption: {t['caption_pt']}pt",
        "",
        "## Canvas",
        "",
        f"- {tokens['canvas_cm'][0]} × {tokens['canvas_cm'][1]} cm",
        f"- Margin ≥ {tokens['margin_cm']} cm · Gap ≥ {tokens['gap_cm']} cm",
        "",
        "## Patterns",
        "",
    ]
    for p in tokens.get("patterns", []):
        lines.append(f"- `{p}` → recipes/{p}.json")
    warns = tokens.get("warnings") or []
    if warns:
        lines += ["", "## Compiler warnings", ""]
        for w in warns:
            lines.append(f"- {w}")
    lines += [
        "",
        "## Dropped web concerns",
        "",
    ]
    for d in tokens.get("drop", []):
        lines.append(f"- {d}")
    lines += [
        "",
        "## Agent rules",
        "",
        "1. Use only hex tokens above for `background`, `fill`, `color`, chart series.",
        "2. Never go below body 18pt / title 36pt (micro chips may be 12–16pt).",
        "3. One idea per slide; use section_divider between arcs.",
        "4. Prefer `batch` with recipe JSON; then `validate` + `view issues`.",
        "5. Do not reintroduce hover, nav, or form components.",
        "6. If provenance is `fallback`, treat color as untrusted — prefer fixing DESIGN.md keys.",
        "",
    ]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest
