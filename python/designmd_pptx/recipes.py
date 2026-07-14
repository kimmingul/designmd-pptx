"""Generate officecli batch JSON recipes from tokens.slide.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import layout as L


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


def _emit_shapes(placed: list[L.Placed]) -> list[dict]:
    """Solved layout leaves → officecli add ops (geometry from the engine)."""
    ops: list[dict] = []
    for p in placed:
        props = dict(p.box.props)
        op_type = props.pop("_type", "shape")
        # Drop private engine metadata (e.g. forest-plot CI geometry).
        for k in list(props):
            if k.startswith("_"):
                props.pop(k, None)
        props.setdefault("name", p.name)
        if p.box.kind == "text" and "text" not in props:
            props["text"] = p.box.text
        props.update(
            {"x": _cm(p.x), "y": _cm(p.y), "width": _cm(p.w), "height": _cm(p.h)}
        )
        ops.append(
            {"command": "add", "parent": "/slide[last()]", "type": op_type, "props": props}
        )
    return ops


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
    """Adaptive 2–4 KPI cards (default 3) — engine-solved card row (#9)."""
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
    bg = c["content_background"]
    mpt = _micro_pt(t)
    micro = str(mpt)

    def _kpi_card(i: int) -> L.Box:
        kpi = kpis[i] if isinstance(kpis[i], dict) else {}
        watch = bool(kpi.get("watch"))
        fill = c["risk"] if watch else c["surface"]
        tc = c["on_accent"] if watch else c["text_on_surface"]
        mc = "FFFFFF" if watch else c["muted"]
        chip_c = mc if watch else c["accent"]
        # Narrow side padding: the big KPI value needs near-full column width so
        # it stays on one line (officecli wraps a wide value in a padded box).
        return L.VStack(
            weight=1, name=f"Kpi{i + 1}Bg", pad=(0.9, 0.2, 0.7, 0.2), gap=0.3,
            props={"preset": b["preset"], "fill": fill, "line": "none"},
            children=[
                L.Spacer(weight=1),
                L.Text(str(kpi.get("value", "—")), pt=t["kpi_pt"],
                       name=f"Kpi{i + 1}Value", min_cm=2.0, max_cm=5.0, props={
                           "font": t["heading_font"], "size": str(t["kpi_pt"]),
                           "bold": "true", "color": tc, "align": "center", "fill": "none"}),
                L.Text(str(kpi.get("label", "")), pt=mpt, name=f"Kpi{i + 1}Label",
                       min_cm=0.8, props={
                           "font": t["body_font"], "size": micro, "color": mc,
                           "align": "center", "fill": "none"}),
                L.Text(str(kpi.get("chip", "")), pt=mpt, name=f"Kpi{i + 1}Chip",
                       min_cm=0.7, props={
                           "font": t["body_font"], "size": micro, "bold": "true",
                           "color": chip_c, "align": "center", "fill": "none"}),
                L.Spacer(weight=1),
            ])

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

    def build(d: L.Density) -> L.Box:
        # iterate the ACTUAL kpis (n is only the display clamp) — range(n) would
        # index past a 1-item list and crash.
        return L.HStack([_kpi_card(i) for i in range(len(kpis))],
                        gap=b["gap"] * d.gap, weight=1)

    placed, _d = L.solve_adaptive(
        build, b["margin"], 4.2, 33.87 - 2 * b["margin"], 11.0)
    ops.extend(_emit_shapes(placed))
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Walk KPIs left to right; pause on any watch metric.")},
    })
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
    bg = c["content_background"]

    # v1.6: engine-solved geometry — equal-width card columns, card heights
    # share the space below the title; body text height is validated.
    def build(d: L.Density) -> L.Box:
        body_pt = L.floored_pt(t["body_pt"], d)
        card_boxes = []
        for i, card in enumerate(cards):
            card_boxes.append(
                L.VStack(
                    weight=1,
                    name=f"Card{i + 1}Bg",
                    children=[
                        L.Fixed(0.18, name=f"Card{i + 1}Accent", props={
                            "preset": "rect", "fill": c["accent"], "line": "none",
                        }),
                        L.VStack(
                            weight=1,
                            pad=(1.0 * d.gap, 0.6, 0.6, 0.6),
                            gap=0.5 * d.gap,
                            children=[
                                L.Text(str(card.get("title", "")),
                                       pt=max(20, t["section_pt"]),
                                       name=f"Card{i + 1}Title",
                                       min_cm=1.2, max_cm=3.0, props={
                                           "font": t["heading_font"],
                                           "size": str(max(20, t["section_pt"])),
                                           "bold": "true",
                                           "color": c["text_on_surface"],
                                           "fill": "none",
                                       }),
                                L.Text(str(card.get("body", "")), pt=body_pt,
                                       name=f"Card{i + 1}Body", weight=1, props={
                                           "font": t["body_font"],
                                           "size": str(body_pt),
                                           "color": c["muted"], "fill": "none",
                                       }),
                            ],
                        ),
                    ],
                    props={
                        "preset": b["preset"], "fill": c["surface"],
                        "line": c["hairline"],
                    },
                )
            )
        return L.VStack(
            pad=(1.2, b["margin"], 1.0, b["margin"]),
            gap=0.9 * d.gap,
            name="feature_cards",
            children=[
                L.Text(title, pt=t["title_pt"], name="FeatTitle",
                       min_cm=1.6, max_cm=2.8, props={
                           "font": t["heading_font"], "size": str(t["title_pt"]),
                           "bold": "true", "color": c["text_on_content"],
                           "fill": "none",
                       }),
                L.HStack(card_boxes, gap=b["gap"] * d.gap, weight=1),
            ],
        )

    placed, _d = L.solve_adaptive(build, 0, 0, L.CANVAS_W, L.CANVAS_H)
    return [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": bg},
        },
        *_emit_shapes(placed),
    ]


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

    # v1.6: engine-solved geometry — title height from its text, body fills
    # the rest; density backs off spacing/pt before failing loudly.
    def build(d: L.Density) -> L.Box:
        body_pt = L.floored_pt(t["body_pt"], d)
        return L.VStack(
            pad=(1.2, b["margin"], 1.0, b["margin"]),
            gap=0.8 * d.gap,
            name="bullets",
            children=[
                L.Text(title, pt=t["title_pt"], name="BulletTitle",
                       min_cm=1.6, max_cm=2.8, props={
                           "font": t["heading_font"], "size": str(t["title_pt"]),
                           "bold": "true", "color": c["text_on_content"],
                           "fill": "none",
                       }),
                L.Text(body, pt=body_pt, name="BulletBody", weight=1, props={
                    "font": t["body_font"], "size": str(body_pt),
                    "color": c["text_on_content"], "fill": "none",
                }),
            ],
        )

    placed, _d = L.solve_adaptive(build, 0, 0, L.CANVAS_W, L.CANVAS_H)
    return [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        },
        *_emit_shapes(placed),
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

    # v1.6: engine-solved geometry — two equal panels, body heights validated.
    def build(d: L.Density) -> L.Box:
        body_pt = L.floored_pt(t["body_pt"], d)
        panels = []
        for i, side in enumerate((left, right)):
            panels.append(
                L.VStack(
                    weight=1,
                    name=f"Cmp{i + 1}Bg",
                    pad=(0.8 * d.gap, 0.8, 0.8, 0.8),
                    gap=0.5 * d.gap,
                    children=[
                        L.Text(str(side.get("title", "")),
                               pt=max(20, t["section_pt"]),
                               name=f"Cmp{i + 1}Title",
                               min_cm=1.2, max_cm=3.0, props={
                                   "font": t["heading_font"],
                                   "size": str(max(20, t["section_pt"])),
                                   "bold": "true",
                                   "color": c["text_on_surface"],
                                   "fill": "none",
                               }),
                        L.Text(str(side.get("body", "")), pt=body_pt,
                               name=f"Cmp{i + 1}Body", weight=1, props={
                                   "font": t["body_font"], "size": str(body_pt),
                                   "color": c["muted"], "fill": "none",
                               }),
                    ],
                    props={
                        "preset": b["preset"], "fill": c["surface"],
                        "line": c["hairline"],
                    },
                )
            )
        return L.VStack(
            pad=(1.2, b["margin"], 1.0, b["margin"]),
            gap=0.9 * d.gap,
            name="comparison_2col",
            children=[
                L.Text(title, pt=t["title_pt"], name="CmpTitle",
                       min_cm=1.6, max_cm=2.8, props={
                           "font": t["heading_font"], "size": str(t["title_pt"]),
                           "bold": "true", "color": c["text_on_content"],
                           "fill": "none",
                       }),
                L.HStack(panels, gap=b["gap"] * d.gap, weight=1),
            ],
        )

    placed, _d = L.solve_adaptive(build, 0, 0, L.CANVAS_W, L.CANVAS_H)
    return [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        },
        *_emit_shapes(placed),
    ]


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
    """Horizontal timeline: 2–6 steps. The label/detail columns are engine-solved
    (#9) for adaptive text-fit; the axis line and step dots are overlaid on the
    fixed track from the solved column geometry."""
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
    mpt = _micro_pt(t)
    label_pt = max(16, min(20, t["section_pt"]))
    y_line = 9.0

    def _step_col(i: int, detail_pt: int) -> L.Box:
        step = steps[i] if isinstance(steps[i], dict) else {"label": str(steps[i])}
        # `or` (not a default arg) so an explicit null renders the fallback, not "None".
        label = str(step.get("label") or f"Step {i + 1}")
        detail = str(step.get("detail") or "")
        return L.VStack(
            weight=1, name=f"TlCol{i + 1}", gap=0.35,
            children=[
                L.Text(label, pt=label_pt, name=f"TlLabel{i + 1}",
                       min_cm=1.0, max_cm=2.4, props={
                           "font": t["heading_font"], "size": str(label_pt),
                           "bold": "true", "color": c["text_on_content"],
                           "align": "center", "fill": "none"}),
                L.Text(detail, pt=detail_pt, name=f"TlDetail{i + 1}", weight=1, props={
                    "font": t["body_font"], "size": str(detail_pt),
                    "color": c["muted"], "align": "center", "fill": "none"}),
            ])

    def build(d: L.Density) -> L.Box:
        dpt = L.floored_pt(max(12, mpt), d, floor=12)
        return L.HStack([_step_col(i, dpt) for i in range(len(steps))],
                        gap=b["gap"] * d.gap, weight=1)

    placed = L.solve_adaptive(
        build, b["margin"], y_line + 1.3, 33.87 - 2 * b["margin"],
        17.8 - (y_line + 1.3))[0]

    axis_w = 33.87 - 2 * b["margin"]
    ops: list[dict] = [
        {"command": "add", "parent": "/", "type": "slide",
         "props": {"layout": "blank", "background": c["content_background"]}},
        {"command": "add", "parent": "/slide[last()]", "type": "shape",
         "props": {
             "name": "TlTitle", "text": title, "x": _cm(b["margin"]), "y": "1.2cm",
             "width": _cm(axis_w), "height": "1.8cm", "font": t["heading_font"],
             "size": str(t["title_pt"]), "bold": "true",
             "color": c["text_on_content"], "fill": "none"}},
        {"command": "add", "parent": "/slide[last()]", "type": "shape",
         "props": {
             "name": "TlAxis", "preset": "rect", "fill": c["hairline"], "line": "none",
             "x": _cm(b["margin"]), "y": _cm(y_line), "width": _cm(axis_w),
             "height": "0.12cm"}},
        *_emit_shapes(placed),
    ]

    # Overlay a dot on the axis, centered under each solved label column.
    labels = {p.name: p for p in placed if p.name.startswith("TlLabel")}
    dot = 0.9
    for i in range(len(steps)):
        p = labels.get(f"TlLabel{i + 1}")
        if p is None:
            continue
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"TlDot{i + 1}", "preset": "ellipse", "fill": c["accent"],
                "line": "none",
                "x": _cm(p.x + p.w / 2 - dot / 2), "y": _cm(y_line - dot / 2 + 0.06),
                "width": _cm(dot), "height": _cm(dot)},
        })

    if content.get("notes"):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "notes",
            "props": {"text": content["notes"]},
        })
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

    # v1.6: engine-solved geometry — image column fills its half, text column
    # gets a content-sized title and a validated, space-filling body.
    if src:
        visual = L.Box(kind="fixed", weight=1, name="It2Image", props={
            "_type": "picture", "src": str(src), "alt": alt or "Illustration",
        })
    else:
        visual = L.Box(kind="fixed", weight=1, name="It2Placeholder", props={
            "preset": b["preset"], "fill": c["surface"], "line": c["hairline"],
            "text": "Image — set content.src", "font": t["body_font"],
            "size": str(t["body_pt"]), "color": c["muted"],
            "align": "center", "valign": "middle",
        })

    def build(d: L.Density) -> L.Box:
        body_pt = L.floored_pt(t["body_pt"], d)
        text_col = L.VStack(
            weight=1,
            gap=0.7 * d.gap,
            children=[
                L.Text(title, pt=t["title_pt"], name="It2Title",
                       min_cm=1.6, max_cm=4.0, props={
                           "font": t["heading_font"], "size": str(t["title_pt"]),
                           "bold": "true", "color": c["text_on_content"],
                           "fill": "none",
                       }),
                L.Text(body, pt=body_pt, name="It2Body", weight=1, props={
                    "font": t["body_font"], "size": str(body_pt),
                    "color": c["muted"], "fill": "none",
                }),
            ],
        )
        cols = [visual, text_col] if side == "left" else [text_col, visual]
        return L.HStack(cols, gap=b["gap"] * d.gap,
                        pad=(2.5 * d.gap, b["margin"], 2.0 * d.gap, b["margin"]),
                        name="image_text_2col")

    placed, _d = L.solve_adaptive(build, 0, 0, L.CANVAS_W, L.CANVAS_H)
    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        },
        *_emit_shapes(placed),
    ]
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
    """2×2 quadrant matrix with optional axis labels. The quadrant grid is
    engine-solved (#9) — card heights and text-fit adapt to content; the title
    and axis annotations stay fixed as chrome."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Where we play")
    quads = content.get("quadrants") or [
        {"title": f"Quadrant {i + 1}", "body": ""} for i in range(4)
    ]
    quads = (list(quads) + [{}] * 4)[:4]
    axes = content.get("axes") or {}

    qt_pt = max(18, t["section_pt"] - 4)

    def _quad(i: int, body_pt: int) -> L.Box:
        q = quads[i] if isinstance(quads[i], dict) else {}
        return L.VStack(
            weight=1, name=f"Quad{i + 1}Bg", pad=(0.5, 0.6, 0.6, 0.6), gap=0.4,
            props={"preset": b["preset"], "fill": c["surface"], "line": "none"},
            children=[
                L.Text(str(q.get("title", "")), pt=qt_pt, name=f"Quad{i + 1}Title",
                       min_cm=0.9, max_cm=2.4, props={
                           "font": t["heading_font"], "size": str(qt_pt),
                           "bold": "true", "color": c["text_on_surface"], "fill": "none"}),
                L.Text(str(q.get("body", "")), pt=body_pt, name=f"Quad{i + 1}Body",
                       weight=1, props={
                           "font": t["body_font"], "size": str(body_pt),
                           "color": c["muted"], "fill": "none"}),
            ])

    def build(d: L.Density) -> L.Box:
        # body font shrinks with density (compact) so dense quadrants compact
        # instead of overflowing.
        bpt = L.floored_pt(t["body_pt"], d)
        return L.VStack(gap=b["gap"] * d.gap, name="matrix_grid", children=[
            L.HStack([_quad(0, bpt), _quad(1, bpt)], gap=b["gap"] * d.gap, weight=1),
            L.HStack([_quad(2, bpt), _quad(3, bpt)], gap=b["gap"] * d.gap, weight=1),
        ])

    # grid clears the fixed AxisY band (3.0–3.8cm) when present, and the AxisX
    # band at the bottom — the overlap codex flagged (#9 review).
    grid_top = 3.9 if axes.get("y") else 3.4
    grid_bottom = 17.0 if axes.get("x") else 18.2
    placed, _d = L.solve_adaptive(
        build, b["margin"], grid_top, 33.87 - 2 * b["margin"], grid_bottom - grid_top)
    ops = [_slide_op(tokens), _title_op(tokens, "MatrixTitle", title),
           *_emit_shapes(placed)]

    usable = 33.87 - 2 * b["margin"]
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
    """2–4 member cards: initials disc, name, role, blurb. Card text is
    engine-solved (#9); the avatar disc is overlaid centered in each solved
    card's reserved top band (a fixed square disc isn't a flex child)."""
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
    mpt = _micro_pt(t)
    micro = str(mpt)
    name_pt = max(16, t["section_pt"] - 8)
    avatar_pt = max(18, t["section_pt"] - 4)
    AVATAR_BAND = 4.4  # top padding reserved for the overlaid disc

    def _card(i: int, blurb_pt: int) -> L.Box:
        m = members[i] if isinstance(members[i], dict) else {}
        return L.VStack(
            weight=1, name=f"Member{i + 1}Bg", pad=(AVATAR_BAND, 0.4, 0.6, 0.4), gap=0.3,
            props={"preset": b["preset"], "fill": c["surface"], "line": "none"},
            children=[
                # names can wrap to 2 lines; reserve the height officecli needs
                # after text-frame insets (a 1-line box overflows a long name).
                L.Text(str(m.get("name", "")), pt=name_pt, name=f"Member{i + 1}Name",
                       min_cm=1.75, max_cm=2.4, props={
                           "font": t["heading_font"], "size": str(name_pt), "bold": "true",
                           "color": c["text_on_surface"], "align": "center", "fill": "none"}),
                L.Text(str(m.get("role", "")), pt=mpt, name=f"Member{i + 1}Role",
                       min_cm=0.6, props={
                           "font": t["body_font"], "size": micro, "bold": "true",
                           "color": c["accent"], "align": "center", "fill": "none"}),
                L.Text(str(m.get("blurb", "")), pt=blurb_pt, name=f"Member{i + 1}Blurb",
                       weight=1, props={
                           "font": t["body_font"], "size": str(blurb_pt),
                           "color": c["muted"], "align": "center", "fill": "none"}),
            ])

    def build(d: L.Density) -> L.Box:
        bpt = L.floored_pt(max(12, t["body_pt"] - 4), d, floor=12)
        return L.HStack([_card(i, bpt) for i in range(len(members))],
                        gap=b["gap"] * d.gap, weight=1)

    placed = L.solve_adaptive(
        build, b["margin"], 3.4, 33.87 - 2 * b["margin"], 14.4)[0]
    ops = [_slide_op(tokens), _title_op(tokens, "TeamTitle", title, y="1.2cm"),
           *_emit_shapes(placed)]

    # Overlay the avatar disc, centered in each solved card's reserved top band.
    bg = {p.name: p for p in placed if p.name.endswith("Bg")}
    for i in range(len(members)):
        m = members[i] if isinstance(members[i], dict) else {}
        p = bg.get(f"Member{i + 1}Bg")
        if p is None:
            continue
        disc = min(3.4, p.w * 0.42)
        # font scaled to the disc so initials never overflow it (narrow cards /
        # large brand type scale) — the disc is outside solve_adaptive.
        av_pt = min(avatar_pt, max(14, int(disc * 12)))
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Member{i + 1}Avatar", "preset": "ellipse", "fill": c["accent"],
                "line": "none", "text": _initials(m.get("name", "")),
                "x": _cm(p.x + (p.w - disc) / 2), "y": _cm(p.y + 0.6),
                "width": _cm(disc), "height": _cm(disc),
                "font": t["heading_font"], "size": str(av_pt), "bold": "true",
                "color": c["on_accent"], "align": "center", "valign": "middle"},
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get("notes", "One line each: name, why they matter here.")},
    })
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
    """2–3 pricing tiers; highlight=true renders the accent tier — engine-solved
    card row (#9): tier heights and feature-list fit adapt to content."""
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
    mpt = _micro_pt(t)
    micro = str(mpt)
    name_pt = max(18, t["section_pt"] - 4)

    def _tier(i: int, feat_pt: int) -> L.Box:
        tier = tiers[i] if isinstance(tiers[i], dict) else {}
        hi = bool(tier.get("highlight"))
        fill = c["accent"] if hi else c["surface"]
        fg = c["on_accent"] if hi else c["text_on_surface"]
        sub = "FFFFFF" if hi else c["muted"]
        feats = "\n".join(f"• {f}" for f in (tier.get("features") or [])[:5])
        # Narrow side padding: the big price needs near-full column width to
        # stay on one line (see kpi_row).
        return L.VStack(
            weight=1, name=f"Tier{i + 1}Bg", pad=(0.8, 0.35, 0.8, 0.35), gap=0.35,
            props={"preset": b["preset"], "fill": fill,
                   "line": "none" if hi else c["hairline"]},
            children=[
                L.Text(str(tier.get("name", "")), pt=name_pt, name=f"Tier{i + 1}Name",
                       min_cm=0.9, max_cm=1.8, props={
                           "font": t["heading_font"], "size": str(name_pt),
                           "bold": "true", "color": fg, "align": "center", "fill": "none"}),
                L.Text(str(tier.get("price", "")), pt=t["kpi_pt"], name=f"Tier{i + 1}Price",
                       min_cm=1.8, max_cm=3.4, props={
                           "font": t["heading_font"], "size": str(t["kpi_pt"]),
                           "bold": "true", "color": fg, "align": "center", "fill": "none"}),
                L.Text(str(tier.get("period", "")), pt=mpt, name=f"Tier{i + 1}Period",
                       min_cm=0.6, props={
                           "font": t["body_font"], "size": micro,
                           "color": sub, "align": "center", "fill": "none"}),
                L.Text(feats, pt=feat_pt, name=f"Tier{i + 1}Features", weight=1, props={
                    "font": t["body_font"], "size": str(feat_pt),
                    "color": sub, "fill": "none"}),
            ])

    def build(d: L.Density) -> L.Box:
        feat_pt = L.floored_pt(max(12, t["body_pt"] - 2), d, floor=12)
        return L.HStack([_tier(i, feat_pt) for i in range(len(tiers))],
                        gap=b["gap"] * d.gap, weight=1)

    placed, _d = L.solve_adaptive(
        build, b["margin"], 3.6, 33.87 - 2 * b["margin"], 14.6)
    ops = [_slide_op(tokens), _title_op(tokens, "PricingTitle", title),
           *_emit_shapes(placed)]
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get("notes", "Anchor on the highlighted tier.")},
    })
    return ops


# One appendix slide fits ~14 rows below the title/header band.
APPENDIX_ROWS_PER_SLIDE = 14


def _appendix_page_ops(tokens: dict, b: dict, c: dict, t: dict, page_title: str,
                       headers: list[str], chunk: list[list[str]], cols: int,
                       col_w: float, gap: float, row_h: float, start_y: float,
                       fs: str, page: int) -> list[dict]:
    """Ops for a single appendix-table slide (title + header band + rows)."""
    table_w = 33.87 - 2 * b["margin"]
    ops: list[dict] = [
        _slide_op(tokens),
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "AppTitle", "text": page_title,
                "x": _cm(b["margin"]), "y": "0.8cm",
                "width": _cm(table_w), "height": "1.4cm",
                "font": t["heading_font"], "size": str(t["section_pt"]),
                "bold": "true", "color": c["text_on_content"], "fill": "none",
            },
        },
    ]
    for ci, hcell in enumerate(headers):
        x = b["margin"] + ci * (col_w + gap)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"ATh{page}_{ci + 1}", "preset": "rect", "fill": c["accent"],
                "line": "none", "text": hcell,
                "x": _cm(x), "y": _cm(start_y),
                "width": _cm(col_w), "height": _cm(row_h),
                "font": t["body_font"], "size": fs, "bold": "true",
                "color": c["on_accent"], "align": "center", "valign": "middle",
            },
        })
    for ri, row in enumerate(chunk):
        for ci, cell in enumerate(row):
            x = b["margin"] + ci * (col_w + gap)
            y = start_y + (ri + 1) * (row_h + gap)
            fill = c["surface"] if ri % 2 == 0 else c.get("surface_elevated", c["surface"])
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"ATd{page}_{ri + 1}_{ci + 1}", "preset": "rect",
                    "fill": fill, "line": c["hairline"], "text": cell,
                    "x": _cm(x), "y": _cm(y),
                    "width": _cm(col_w), "height": _cm(row_h),
                    "font": t["body_font"], "size": fs,
                    "color": c["text_on_surface"], "align": "center", "valign": "middle",
                },
            })
    return ops


def recipe_appendix_table(tokens: dict, content: dict | None = None) -> list[dict]:
    """Dense reference table for appendices: up to 8 columns. Rows beyond one
    slide's capacity (14) auto-split into continuation slides (#17) — the table
    is never silently truncated. Continuation slides repeat the header band and
    tag the title `(cont. k/n)`."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Appendix")
    headers = content.get("headers") or ["Item", "Value"]
    rows = content.get("rows") or []
    cols = max(1, min(8, len(headers)))
    headers = [str(h) for h in headers[:cols]]
    norm_rows: list[list[str]] = []
    for r in rows:
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

    per = APPENDIX_ROWS_PER_SLIDE
    pages = max(1, (len(norm_rows) + per - 1) // per)
    ops: list[dict] = []
    for page in range(pages):
        chunk = norm_rows[page * per:(page + 1) * per]
        if pages == 1:
            page_title = title
        elif page == 0:
            page_title = f"{title} (1/{pages})"
        else:
            page_title = f"{title} (cont. {page + 1}/{pages})"
        ops.extend(_appendix_page_ops(
            tokens, b, c, t, page_title, headers, chunk, cols,
            col_w, gap, row_h, start_y, fs, page + 1))

    if content.get("notes"):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "notes",
            "props": {"text": content["notes"]},
        })
    return ops


def recipe_consort_flow(tokens: dict, content: dict | None = None) -> list[dict]:
    """CONSORT-style enrollment flow (Phase 2 / #10) — vertical boxes 3–7 stages.

    Engine-solved stack of stage cards (label + n= count + optional reason).
    Original geometry for research decks; not a medical-template clone.
    """
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "CONSORT flow")
    stages = content.get("stages") or content.get("steps") or [
        {"label": "Assessed for eligibility", "n": "N=420"},
        {"label": "Randomized", "n": "N=300"},
        {"label": "Allocated to intervention", "n": "N=150"},
        {"label": "Analyzed", "n": "N=148", "note": "2 lost to follow-up"},
    ]
    if not isinstance(stages, list):
        stages = [{"label": str(stages)}]
    stages = stages[:7]
    while len(stages) < 3:
        stages.append({"label": "—", "n": ""})
    mpt = _micro_pt(t)

    def build(d: L.Density) -> L.Box:
        # Tighter type as stage count grows so 5–7 CONSORT boxes still fit.
        n_stages = len(stages)
        body_pt = L.floored_pt(max(12, t["body_pt"] - (0 if n_stages <= 4 else 4)), d, floor=12)
        label_min = 0.45 if n_stages >= 5 else 0.65
        rows: list[L.Box] = []
        for i, st in enumerate(stages):
            if isinstance(st, str):
                label, n, note = st, "", ""
            else:
                label = str(st.get("label") or st.get("title") or f"Stage {i + 1}")
                n = str(st.get("n") or st.get("count") or "")
                note = str(st.get("note") or st.get("reason") or "")
            kids: list[L.Box] = [
                L.Text(
                    label, pt=body_pt, name=f"ConsortLabel{i + 1}",
                    min_cm=label_min, max_cm=1.4, weight=1,
                    props={
                        "font": t["heading_font"], "size": str(body_pt),
                        "bold": "true", "color": c["text_on_surface"], "fill": "none",
                    },
                ),
            ]
            if n:
                kids.append(
                    L.Text(
                        n, pt=mpt, name=f"ConsortN{i + 1}",
                        min_cm=0.35, max_cm=0.7,
                        props={
                            "font": t["body_font"], "size": str(mpt), "bold": "true",
                            "color": c["accent"], "fill": "none",
                        },
                    )
                )
            if note:
                kids.append(
                    L.Text(
                        note, pt=mpt, name=f"ConsortNote{i + 1}",
                        min_cm=0.3, max_cm=0.7,
                        props={
                            "font": t["body_font"], "size": str(mpt),
                            "color": c["muted"], "fill": "none",
                        },
                    )
                )
            rows.append(
                L.VStack(
                    weight=1, name=f"ConsortBox{i + 1}",
                    pad=(0.2 * d.gap, 0.45, 0.2 * d.gap, 0.45),
                    gap=0.08 * d.gap,
                    props={
                        "preset": b["preset"], "fill": c["surface"],
                        "line": c.get("hairline", "none"),
                    },
                    children=kids,
                )
            )
        side = b["margin"] + (3.0 if n_stages <= 4 else 5.0)
        return L.VStack(
            pad=(1.0, side, 0.7, side),
            gap=0.25 * d.gap,
            name="consort_flow",
            children=[
                L.Text(
                    title, pt=t["title_pt"], name="ConsortTitle",
                    min_cm=1.2, max_cm=2.0,
                    props={
                        "font": t["heading_font"], "size": str(t["title_pt"]),
                        "bold": "true", "color": c["text_on_content"], "fill": "none",
                    },
                ),
                L.VStack(rows, gap=0.18 * d.gap, weight=1, name="ConsortStack"),
            ],
        )

    placed, _d = L.solve_adaptive(build, 0, 0, L.CANVAS_W, L.CANVAS_H)
    ops: list[dict] = [_slide_op(tokens), *_emit_shapes(placed)]
    # Connectors between consecutive boxes (visual CONSORT spine).
    boxes = {p.name: p for p in placed if p.name.startswith("ConsortBox")}
    for i in range(1, len(stages)):
        a, b_ = boxes.get(f"ConsortBox{i}"), boxes.get(f"ConsortBox{i + 1}")
        if not a or not b_:
            continue
        x = a.x + a.w / 2 - 0.06
        y = a.y + a.h
        h = max(0.15, b_.y - y)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"ConsortLink{i}", "preset": "rect",
                "fill": c["accent"], "line": "none",
                "x": _cm(x), "y": _cm(y), "width": "0.12cm", "height": _cm(h),
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Walk top→bottom; call out each attrition reason.")},
    })
    return ops


def recipe_kaplan_meier(tokens: dict, content: dict | None = None) -> list[dict]:
    """Kaplan–Meier curve + risk table (Phase 2 / #10) — structured.

    Uses a line chart for survival estimates and a compact risk table under it.
    Provide categories as time points and series as arm survival percentages.
    """
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Kaplan–Meier survival")
    cats = content.get("categories", "0,6,12,18,24")
    s1 = content.get("series1_values", "100,92,85,78,72")
    s2 = content.get("series2_values", "100,88,79,70,61")
    s1_name = content.get("series1_name", "Intervention")
    s2_name = content.get("series2_name", "Control")
    insight = content.get("insight", content.get("insight_body", ""))
    # Risk table: list of {time, arm_a, arm_b} or rows [[time, a, b], ...]
    risk = content.get("risk_table") or content.get("rows") or [
        ["0", "150", "150"],
        ["12", "128", "119"],
        ["24", "96", "84"],
    ]
    if risk and isinstance(risk[0], dict):
        risk = [
            [str(r.get("time", "")), str(r.get("arm_a", r.get("n1", ""))),
             str(r.get("arm_b", r.get("n2", "")))]
            for r in risk
        ]
    risk = risk[:6]
    headers = content.get("risk_headers") or ["Month", s1_name, s2_name]
    m = b["margin"]
    micro = str(_micro_pt(t))
    series2 = c.get("chart_series2", c["muted"])
    ops: list[dict] = [
        _slide_op(tokens),
        _title_op(tokens, "KmTitle", title),
        {
            "command": "add", "parent": "/slide[last()]", "type": "chart",
            "props": {
                "name": "KmChart",
                "chartType": "line",
                "series1.name": s1_name,
                "series1.values": s1,
                "series1.color": c.get("chart_series1", c["accent"]),
                "series2.name": s2_name,
                "series2.values": s2,
                "series2.color": series2,
                "categories": cats,
                "x": _cm(m), "y": "3.2cm",
                "width": "22.5cm", "height": "10.5cm",
            },
        },
    ]
    # Risk table under chart
    table_y = 14.0
    col_w = (22.5 - 0.3 * (len(headers) - 1)) / max(1, len(headers))
    for j, h in enumerate(headers[:4]):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"KmRiskH{j + 1}", "text": str(h),
                "x": _cm(m + j * (col_w + 0.3)), "y": _cm(table_y),
                "width": _cm(col_w), "height": "0.7cm",
                "font": t["body_font"], "size": micro, "bold": "true",
                "color": c["muted"], "fill": "none",
            },
        })
    for i, row in enumerate(risk):
        if not isinstance(row, (list, tuple)):
            continue
        for j, cell in enumerate(list(row)[:4]):
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"KmRisk{i + 1}_{j + 1}", "text": str(cell),
                    "x": _cm(m + j * (col_w + 0.3)),
                    "y": _cm(table_y + 0.75 + i * 0.65),
                    "width": _cm(col_w), "height": "0.6cm",
                    "font": t["body_font"], "size": micro,
                    "color": c["text_on_content"], "fill": "none",
                },
            })
    # Insight panel
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "KmInsightBg", "preset": b["preset"],
            "fill": c["surface"], "line": "none",
            "x": "24.5cm", "y": "3.2cm", "width": "7.8cm", "height": "14.5cm",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "KmInsightTitle", "text": content.get("insight_title", "Takeaway"),
            "x": "25cm", "y": "3.7cm", "width": "6.8cm", "height": "1.1cm",
            "font": t["heading_font"], "size": str(max(16, t["section_pt"] - 8)),
            "bold": "true", "color": c["text_on_surface"], "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "KmInsightBody",
            "text": insight or "State HR, median survival, and clinical relevance.",
            "x": "25cm", "y": "5.1cm", "width": "6.8cm", "height": "11.5cm",
            "font": t["body_font"], "size": str(t["body_pt"]),
            "color": c["muted"], "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Point to separation of curves, then the numbers at risk.")},
    })
    return ops


def recipe_forest_plot(tokens: dict, content: dict | None = None) -> list[dict]:
    """Forest plot rows (Phase 2 / #10) — study / effect / CI as engine rows.

    Each row: label | effect text | visual CI bar (normalized 0–1 domain).
    ``effect`` is the point estimate (float); ``low``/``high`` are CI bounds
    on the same scale (default domain -1..1 mapped to a bar track).
    """
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Forest plot")
    rows = content.get("rows") or content.get("studies") or [
        {"label": "Study A", "effect": -0.2, "low": -0.5, "high": 0.1, "text": "0.82 (0.60–1.10)"},
        {"label": "Study B", "effect": -0.35, "low": -0.6, "high": -0.1, "text": "0.70 (0.55–0.90)"},
        {"label": "Study C", "effect": 0.05, "low": -0.2, "high": 0.3, "text": "1.05 (0.82–1.35)"},
        {"label": "Pooled", "effect": -0.22, "low": -0.4, "high": -0.05, "text": "0.80 (0.67–0.95)"},
    ]
    if not isinstance(rows, list):
        rows = []
    rows = rows[:8]
    while len(rows) < 2:
        rows.append({"label": "—", "effect": 0, "low": -0.2, "high": 0.2, "text": "—"})
    domain = content.get("domain") or [-1.0, 1.0]
    d0, d1 = float(domain[0]), float(domain[1])
    span = max(1e-6, d1 - d0)
    mpt = _micro_pt(t)

    def _norm(v: float) -> float:
        return max(0.0, min(1.0, (float(v) - d0) / span))

    def build(d: L.Density) -> L.Box:
        body_pt = L.floored_pt(max(14, t["body_pt"] - 2), d, floor=12)
        line_boxes: list[L.Box] = []
        for i, row in enumerate(rows):
            if isinstance(row, str):
                label, text = row, ""
                effect = low = high = 0.0
            elif isinstance(row, (list, tuple)):
                label = str(row[0]) if row else f"Row {i + 1}"
                text = str(row[1]) if len(row) > 1 else ""
                effect = low = high = 0.0
            elif isinstance(row, dict):
                label = str(row.get("label") or row.get("study") or f"Row {i + 1}")
                text = str(row.get("text") or row.get("ci") or "")
                effect = float(row.get("effect", row.get("or", row.get("hr", 0)) or 0))
                low = float(row.get("low", row.get("ci_low", effect - 0.2)) or 0)
                high = float(row.get("high", row.get("ci_high", effect + 0.2)) or 0)
            else:
                label, text, effect, low, high = f"Row {i + 1}", "", 0.0, -0.2, 0.2
            # Store normalized geometry in props for post-solve bar overlay.
            line_boxes.append(
                L.HStack(
                    [
                        L.VStack(
                            weight=1.1, name=f"ForestLabelWrap{i + 1}",
                            children=[
                                L.Text(
                                    label, pt=body_pt, name=f"ForestLabel{i + 1}",
                                    min_cm=0.7, weight=1,
                                    props={
                                        "font": t["heading_font"], "size": str(body_pt),
                                        "bold": "true", "color": c["text_on_content"],
                                        "fill": "none",
                                    },
                                ),
                            ],
                        ),
                        L.VStack(
                            weight=1.6, name=f"ForestTrack{i + 1}",
                            pad=(0.35, 0.2, 0.35, 0.2),
                            props={
                                "preset": "rect",
                                "fill": c["surface"],
                                "line": "none",
                                "_forest": {
                                    "low": _norm(low),
                                    "high": _norm(high),
                                    "effect": _norm(effect),
                                },
                            },
                            children=[L.Spacer(weight=1)],
                        ),
                        L.VStack(
                            weight=1.0, name=f"ForestTextWrap{i + 1}",
                            children=[
                                L.Text(
                                    text or f"{effect:.2f}",
                                    pt=mpt, name=f"ForestText{i + 1}",
                                    min_cm=0.6, weight=1,
                                    props={
                                        "font": t["body_font"], "size": str(mpt),
                                        "color": c["muted"], "align": "right",
                                        "fill": "none",
                                    },
                                ),
                            ],
                        ),
                    ],
                    gap=0.35 * d.gap,
                    weight=1,
                    name=f"ForestRow{i + 1}",
                )
            )
        return L.VStack(
            pad=(1.1, b["margin"], 0.9, b["margin"]),
            gap=0.35 * d.gap,
            name="forest_plot",
            children=[
                L.Text(
                    title, pt=t["title_pt"], name="ForestTitle",
                    min_cm=1.4, max_cm=2.4,
                    props={
                        "font": t["heading_font"], "size": str(t["title_pt"]),
                        "bold": "true", "color": c["text_on_content"], "fill": "none",
                    },
                ),
                L.VStack(line_boxes, gap=0.28 * d.gap, weight=1, name="ForestRows"),
            ],
        )

    placed, _d = L.solve_adaptive(build, 0, 0, L.CANVAS_W, L.CANVAS_H)
    ops: list[dict] = [_slide_op(tokens), *_emit_shapes(placed)]
    # Overlay CI bars + effect markers on solved track boxes.
    tracks = {p.name: p for p in placed if p.name.startswith("ForestTrack")}
    for i in range(len(rows)):
        tr = tracks.get(f"ForestTrack{i + 1}")
        if tr is None:
            continue
        meta = (tr.box.props or {}).get("_forest") or {}
        lo = float(meta.get("low", 0.3))
        hi = float(meta.get("high", 0.7))
        ef = float(meta.get("effect", 0.5))
        pad = 0.25
        track_w = max(0.5, tr.w - 2 * pad)
        bar_x = tr.x + pad + lo * track_w
        bar_w = max(0.12, (hi - lo) * track_w)
        mid_y = tr.y + tr.h / 2
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"ForestBar{i + 1}", "preset": "rect",
                "fill": c["accent"], "line": "none",
                "x": _cm(bar_x), "y": _cm(mid_y - 0.08),
                "width": _cm(bar_w), "height": "0.16cm",
            },
        })
        dot = 0.35
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"ForestDot{i + 1}", "preset": "ellipse",
                "fill": c["accent"], "line": "none",
                "x": _cm(tr.x + pad + ef * track_w - dot / 2),
                "y": _cm(mid_y - dot / 2),
                "width": _cm(dot), "height": _cm(dot),
            },
        })
        # Null line at effect=0 if in domain
        if d0 < 0 < d1:
            zx = tr.x + pad + _norm(0.0) * track_w
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"ForestNull{i + 1}", "preset": "rect",
                    "fill": c.get("hairline", c["muted"]), "line": "none",
                    "x": _cm(zx - 0.03), "y": _cm(tr.y + 0.15),
                    "width": "0.06cm", "height": _cm(max(0.3, tr.h - 0.3)),
                },
            })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Read left labels, then CI bars vs the null line.")},
    })
    return ops


def recipe_study_design(tokens: dict, content: dict | None = None) -> list[dict]:
    """Study design schematic (Phase 2 / #10) — phases × optional arms.

    Engine-solved phase columns with arm cards underneath.
    """
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Study design")
    phases = content.get("phases") or [
        {"label": "Screen", "detail": "D-28 to D0"},
        {"label": "Randomize", "detail": "1:1"},
        {"label": "Treat", "detail": "12 weeks"},
        {"label": "Follow-up", "detail": "Week 24"},
    ]
    if not isinstance(phases, list):
        phases = [{"label": str(phases)}]
    phases = phases[:5]
    while len(phases) < 2:
        phases.append({"label": "—", "detail": ""})
    arms = content.get("arms") or content.get("groups") or [
        {"label": "Intervention", "detail": "Drug X + SOC"},
        {"label": "Control", "detail": "Placebo + SOC"},
    ]
    if not isinstance(arms, list):
        arms = []
    arms = arms[:4]
    mpt = _micro_pt(t)

    def build(d: L.Density) -> L.Box:
        body_pt = L.floored_pt(t["body_pt"], d)
        phase_boxes = []
        for i, ph in enumerate(phases):
            if isinstance(ph, str):
                label, detail = ph, ""
            else:
                label = str(ph.get("label") or ph.get("title") or f"Phase {i + 1}")
                detail = str(ph.get("detail") or ph.get("body") or "")
            phase_boxes.append(
                L.VStack(
                    weight=1, name=f"StudyPhase{i + 1}",
                    pad=(0.45, 0.4, 0.45, 0.4), gap=0.2 * d.gap,
                    props={
                        "preset": b["preset"], "fill": c["surface"],
                        "line": c.get("hairline", "none"),
                    },
                    children=[
                        L.Text(
                            f"{i + 1:02d}", pt=mpt, name=f"StudyPhaseNum{i + 1}",
                            min_cm=0.45,
                            props={
                                "font": t["body_font"], "size": str(mpt), "bold": "true",
                                "color": c["accent"], "fill": "none",
                            },
                        ),
                        L.Text(
                            label, pt=body_pt, name=f"StudyPhaseLabel{i + 1}",
                            min_cm=0.7, weight=1,
                            props={
                                "font": t["heading_font"], "size": str(body_pt),
                                "bold": "true", "color": c["text_on_surface"],
                                "fill": "none",
                            },
                        ),
                        L.Text(
                            detail, pt=mpt, name=f"StudyPhaseDetail{i + 1}",
                            min_cm=0.5,
                            props={
                                "font": t["body_font"], "size": str(mpt),
                                "color": c["muted"], "fill": "none",
                            },
                        ),
                    ],
                )
            )
        kids: list[L.Box] = [
            L.Text(
                title, pt=t["title_pt"], name="StudyTitle",
                min_cm=1.4, max_cm=2.4,
                props={
                    "font": t["heading_font"], "size": str(t["title_pt"]),
                    "bold": "true", "color": c["text_on_content"], "fill": "none",
                },
            ),
            L.HStack(phase_boxes, gap=b["gap"] * d.gap, weight=1.2, name="StudyPhases"),
        ]
        if arms:
            arm_boxes = []
            for i, arm in enumerate(arms):
                if isinstance(arm, str):
                    label, detail = arm, ""
                else:
                    label = str(arm.get("label") or arm.get("name") or f"Arm {i + 1}")
                    detail = str(arm.get("detail") or arm.get("body") or "")
                arm_boxes.append(
                    L.VStack(
                        weight=1, name=f"StudyArm{i + 1}",
                        pad=(0.4, 0.45, 0.4, 0.45), gap=0.15 * d.gap,
                        props={
                            "preset": b["preset"],
                            "fill": c["accent"] if i == 0 else c["surface"],
                            "line": "none",
                        },
                        children=[
                            L.Text(
                                label, pt=body_pt, name=f"StudyArmLabel{i + 1}",
                                min_cm=0.7, weight=1,
                                props={
                                    "font": t["heading_font"], "size": str(body_pt),
                                    "bold": "true",
                                    "color": c["on_accent"] if i == 0 else c["text_on_surface"],
                                    "fill": "none",
                                },
                            ),
                            L.Text(
                                detail, pt=mpt, name=f"StudyArmDetail{i + 1}",
                                min_cm=0.5,
                                props={
                                    "font": t["body_font"], "size": str(mpt),
                                    "color": c["on_accent"] if i == 0 else c["muted"],
                                    "fill": "none",
                                },
                            ),
                        ],
                    )
                )
            kids.append(
                L.HStack(arm_boxes, gap=b["gap"] * d.gap, weight=0.9, name="StudyArms")
            )
        return L.VStack(
            pad=(1.1, b["margin"], 0.9, b["margin"]),
            gap=0.55 * d.gap,
            name="study_design",
            children=kids,
        )

    placed, _d = L.solve_adaptive(build, 0, 0, L.CANVAS_W, L.CANVAS_H)
    ops: list[dict] = [_slide_op(tokens), *_emit_shapes(placed)]
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Narrate phases left→right, then contrast the arms.")},
    })
    return ops


def recipe_results_table_insight(tokens: dict, content: dict | None = None) -> list[dict]:
    """Results table + interpretation panel (Phase 2 / #10) — structured."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Primary results")
    headers = content.get("headers") or ["Endpoint", "Intervention", "Control", "p"]
    rows = content.get("rows") or [
        ["ORR", "42%", "28%", "0.03"],
        ["PFS median", "11.2 mo", "7.8 mo", "0.01"],
        ["Grade ≥3 AE", "18%", "14%", "0.22"],
    ]
    if not isinstance(headers, list):
        headers = ["Col"]
    if not isinstance(rows, list):
        rows = []
    headers = [str(h) for h in headers[:6]]
    rows = rows[:8]
    insight_h = content.get("insight_title", "Interpretation")
    insight_b = content.get(
        "insight_body",
        content.get("insight", "State clinical meaning, not just statistical significance."),
    )
    m = b["margin"]
    micro = str(_micro_pt(t))
    n_cols = max(1, len(headers))
    table_w = 21.0
    col_w = (table_w - 0.2 * (n_cols - 1)) / n_cols
    row_h = 0.95
    start_y = 3.5
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "ResTitle", title)]
    for j, h in enumerate(headers):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"ResH{j + 1}", "text": h,
                "x": _cm(m + j * (col_w + 0.2)), "y": _cm(start_y),
                "width": _cm(col_w), "height": _cm(row_h),
                "font": t["heading_font"], "size": str(max(12, t["body_pt"] - 4)),
                "bold": "true", "color": c["on_accent"],
                "fill": c["accent"], "align": "center",
            },
        })
    for i, row in enumerate(rows):
        if not isinstance(row, (list, tuple)):
            row = [str(row)]
        cells = list(row) + [""] * n_cols
        for j in range(n_cols):
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"ResR{i + 1}C{j + 1}", "text": str(cells[j]),
                    "x": _cm(m + j * (col_w + 0.2)),
                    "y": _cm(start_y + (i + 1) * row_h),
                    "width": _cm(col_w), "height": _cm(row_h),
                    "font": t["body_font"], "size": micro,
                    "color": c["text_on_surface"],
                    "fill": c["surface"] if i % 2 == 0 else c["content_background"],
                    "align": "center",
                },
            })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "ResInsightBg", "preset": b["preset"],
            "fill": c["surface"], "line": "none",
            "x": "24.0cm", "y": "3.5cm", "width": "8.3cm", "height": "13.8cm",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "ResInsightTitle", "text": insight_h,
            "x": "24.5cm", "y": "4.0cm", "width": "7.3cm", "height": "1.2cm",
            "font": t["heading_font"], "size": str(max(16, t["section_pt"] - 8)),
            "bold": "true", "color": c["text_on_surface"], "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "ResInsightBody", "text": insight_b,
            "x": "24.5cm", "y": "5.5cm", "width": "7.3cm", "height": "11.0cm",
            "font": t["body_font"], "size": str(t["body_pt"]),
            "color": c["muted"], "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Lead with the interpretation, then walk the table.")},
    })
    return ops


def recipe_multi_panel_figure(tokens: dict, content: dict | None = None) -> list[dict]:
    """Multi-panel figure grid (Phase 2 / #10) — 2–4 panels with captions.

    Structured picture cells; missing src leaves a labeled placeholder surface.
    """
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Multi-panel figure")
    panels = content.get("panels") or content.get("figures") or [
        {"label": "A", "caption": "Primary endpoint", "src": "", "alt": "Panel A"},
        {"label": "B", "caption": "Subgroup", "src": "", "alt": "Panel B"},
        {"label": "C", "caption": "Safety", "src": "", "alt": "Panel C"},
        {"label": "D", "caption": "Exploratory", "src": "", "alt": "Panel D"},
    ]
    if not isinstance(panels, list):
        panels = []
    n = max(2, min(4, len(panels) or 2))
    panels = (list(panels) + [
        {"label": chr(65 + i), "caption": "", "src": "", "alt": f"Panel {chr(65 + i)}"}
        for i in range(4)
    ])[:n]
    # Layout: 2 cols if 2–4 panels
    cols = 2 if n > 1 else 1
    rows = (n + cols - 1) // cols
    m = b["margin"]
    usable_w = 33.87 - 2 * m
    gap = 0.5
    cell_w = (usable_w - gap * (cols - 1)) / cols
    top = 3.3
    usable_h = 18.3 - top
    cell_h = (usable_h - gap * (rows - 1)) / rows
    micro = str(_micro_pt(t))
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "FigTitle", title)]
    for i, panel in enumerate(panels):
        if isinstance(panel, str):
            label, caption, src, alt = chr(65 + i), panel, "", f"Panel {chr(65 + i)}"
        else:
            label = str(panel.get("label") or chr(65 + i))
            caption = str(panel.get("caption") or panel.get("title") or "")
            src = str(panel.get("src") or "")
            alt = str(panel.get("alt") or caption or f"Panel {label}")
        r, col = divmod(i, cols)
        x = m + col * (cell_w + gap)
        y = top + r * (cell_h + gap)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"FigPanel{i + 1}Bg", "preset": b["preset"],
                "fill": c["surface"], "line": c.get("hairline", "none"),
                "x": _cm(x), "y": _cm(y),
                "width": _cm(cell_w), "height": _cm(cell_h),
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"FigPanel{i + 1}Label", "text": label,
                "x": _cm(x + 0.25), "y": _cm(y + 0.2),
                "width": "1.5cm", "height": "0.8cm",
                "font": t["heading_font"], "size": "18", "bold": "true",
                "color": c["accent"], "fill": "none",
            },
        })
        if src:
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "picture",
                "props": {
                    "name": f"FigPanel{i + 1}Img",
                    "src": src, "alt": alt,
                    "x": _cm(x + 0.4), "y": _cm(y + 1.1),
                    "width": _cm(cell_w - 0.8), "height": _cm(cell_h - 2.4),
                },
            })
        else:
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"FigPanel{i + 1}Placeholder",
                    "text": alt or f"[{label}]",
                    "x": _cm(x + 0.4), "y": _cm(y + 1.3),
                    "width": _cm(cell_w - 0.8), "height": _cm(cell_h - 2.6),
                    "font": t["body_font"], "size": micro,
                    "color": c["muted"], "align": "center", "fill": "none",
                },
            })
        if caption:
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"FigPanel{i + 1}Cap", "text": caption,
                    "x": _cm(x + 0.3), "y": _cm(y + cell_h - 0.95),
                    "width": _cm(cell_w - 0.6), "height": "0.8cm",
                    "font": t["body_font"], "size": micro,
                    "color": c["muted"], "fill": "none",
                },
            })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Walk panels A→D; set src/alt for each figure asset.")},
    })
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
    # Phase 2 / #10 academic · medical · research
    "consort_flow": recipe_consort_flow,
    "kaplan_meier": recipe_kaplan_meier,
    "forest_plot": recipe_forest_plot,
    "study_design": recipe_study_design,
    "results_table_insight": recipe_results_table_insight,
    "multi_panel_figure": recipe_multi_panel_figure,
}

# Layout strategy per pattern (#9). Every pattern is one of:
#   "engine"     — content grid/columns solved by the constraint layout engine
#                  (layout.py) for adaptive card heights + CJK-aware text-fit;
#                  non-flex markers (avatar discs, timeline dots) are overlaid
#                  from the solved geometry, chrome (title/axes) stays fixed.
#   "structured" — geometry is an embedded officecli object (chart, table) or a
#                  glued-connector / picture-cell composition, not a flex-text
#                  stack; these keep fixed geometry by design (tables paginate
#                  via #17). No v2 flex-quality claim.
#   "fixed"      — intentional hero/divider compositions whose design depends on
#                  overlap / opacity / precise centering that a top-down flex
#                  engine cannot express (e.g. the 0.25-opacity section number).
# Geometry-contract harness covers every registered pattern.
# test_pattern_layout_covers_registry keeps this in sync with RECIPE_BUILDERS.
PATTERN_LAYOUT: dict[str, tuple[str, ...]] = {
    "engine": (
        "bullets", "feature_cards", "comparison_2col", "image_text_2col",
        "matrix_2x2", "kpi_row", "pricing", "team", "timeline",
        "consort_flow", "forest_plot", "study_design",
    ),
    "structured": (
        "process", "chart_insight", "table", "appendix_table", "logo_strip",
        "kaplan_meier", "results_table_insight", "multi_panel_figure",
    ),
    "fixed": (
        "cover", "section_divider", "big_number", "quote", "close", "image_full",
    ),
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
    "consort_flow",
    "study_design",
    "kaplan_meier",
    "forest_plot",
    "results_table_insight",
    "multi_panel_figure",
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
