"""Generate officecli batch JSON recipes from tokens.slide.json."""

from __future__ import annotations

import json
import math
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


def recipe_kpi_dashboard_grid(tokens: dict, content: dict | None = None) -> list[dict]:
    """Premium multi-row KPI dashboard (Phase 2 / #58) — 4–8 metric tiles.

    Engine-solved 1–2 row grid inspired by consulting dashboard structure
    (card bands + large values), original geometry — not a vendor clone.
    """
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Performance dashboard")
    subtitle = content.get("subtitle", "")
    defaults = [
        {"value": "—", "label": f"Metric {i + 1}", "chip": ""}
        for i in range(6)
    ]
    kpis = content.get("kpis", defaults)
    if not isinstance(kpis, list) or not kpis:
        kpis = defaults
    n = max(4, min(8, len(kpis)))
    kpis = list(kpis[:n])
    # Pad short lists up to 4 so the grid never collapses to a single cell.
    while len(kpis) < 4:
        kpis.append({"value": "—", "label": "—", "chip": ""})
    n = len(kpis)
    bg = c["content_background"]
    mpt = _micro_pt(t)
    # Slightly smaller KPI type than kpi_row so 2×N grids stay readable.
    value_pt = max(28, int(t.get("kpi_pt", 60) * 0.55))

    def _tile(i: int, d: L.Density) -> L.Box:
        kpi = kpis[i] if isinstance(kpis[i], dict) else {}
        watch = bool(kpi.get("watch"))
        fill = c["risk"] if watch else c["surface"]
        tc = c["on_accent"] if watch else c["text_on_surface"]
        mc = "FFFFFF" if watch else c["muted"]
        chip_c = mc if watch else c["accent"]
        return L.VStack(
            weight=1,
            name=f"DashKpi{i + 1}Bg",
            pad=(0.55 * d.gap, 0.25, 0.45 * d.gap, 0.25),
            gap=0.2 * d.gap,
            props={"preset": b["preset"], "fill": fill, "line": c.get("hairline", "none")},
            children=[
                L.Spacer(weight=0.6),
                L.Text(
                    str(kpi.get("value", "—")),
                    pt=value_pt,
                    name=f"DashKpi{i + 1}Value",
                    min_cm=1.4,
                    max_cm=3.6,
                    props={
                        "font": t["heading_font"],
                        "size": str(value_pt),
                        "bold": "true",
                        "color": tc,
                        "align": "center",
                        "fill": "none",
                    },
                ),
                L.Text(
                    str(kpi.get("label", "")),
                    pt=mpt,
                    name=f"DashKpi{i + 1}Label",
                    min_cm=0.6,
                    props={
                        "font": t["body_font"],
                        "size": str(mpt),
                        "color": mc,
                        "align": "center",
                        "fill": "none",
                    },
                ),
                L.Text(
                    str(kpi.get("chip", "")),
                    pt=mpt,
                    name=f"DashKpi{i + 1}Chip",
                    min_cm=0.5,
                    props={
                        "font": t["body_font"],
                        "size": str(mpt),
                        "bold": "true",
                        "color": chip_c,
                        "align": "center",
                        "fill": "none",
                    },
                ),
                L.Spacer(weight=0.4),
            ],
        )

    def _row_slices(count: int) -> list[list[int]]:
        if count <= 4:
            return [list(range(count))]
        cols = 3 if count <= 6 else 4
        return [
            list(range(i, min(i + cols, count)))
            for i in range(0, count, cols)
        ]

    def build(d: L.Density) -> L.Box:
        header: list[L.Box] = [
            L.Text(
                title,
                pt=t["title_pt"],
                name="DashTitle",
                min_cm=1.4,
                max_cm=2.4,
                props={
                    "font": t["heading_font"],
                    "size": str(t["title_pt"]),
                    "bold": "true",
                    "color": c["text_on_content"],
                    "fill": "none",
                },
            ),
        ]
        if subtitle:
            header.append(
                L.Text(
                    str(subtitle),
                    pt=L.floored_pt(t["body_pt"], d),
                    name="DashSubtitle",
                    min_cm=0.7,
                    max_cm=1.6,
                    props={
                        "font": t["body_font"],
                        "size": str(L.floored_pt(t["body_pt"], d)),
                        "color": c["muted"],
                        "fill": "none",
                    },
                )
            )
        rows = []
        for ri, idxs in enumerate(_row_slices(n)):
            rows.append(
                L.HStack(
                    [_tile(i, d) for i in idxs],
                    gap=b["gap"] * d.gap,
                    weight=1,
                    name=f"DashRow{ri + 1}",
                )
            )
        return L.VStack(
            pad=(1.1, b["margin"], 0.9, b["margin"]),
            gap=0.55 * d.gap,
            name="kpi_dashboard_grid",
            children=header + rows,
        )

    placed, _d = L.solve_adaptive(build, 0, 0, L.CANVAS_W, L.CANVAS_H)
    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": bg},
        },
    ]
    ops.extend(_emit_shapes(placed))
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Read the dashboard left→right, top→bottom; call out watches.")},
    })
    return ops


def recipe_agenda_toc(tokens: dict, content: dict | None = None) -> list[dict]:
    """Numbered agenda / table-of-contents (Phase 2 / #58) — 5–12 items."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Agenda")
    raw = content.get("items") or content.get("entries")
    if not isinstance(raw, list) or not raw:
        raw = [
            {"label": "Context & goals"},
            {"label": "What changed"},
            {"label": "Options"},
            {"label": "Recommendation"},
            {"label": "Next steps"},
        ]
    items: list[dict] = []
    for i, it in enumerate(raw[:12]):
        if isinstance(it, str):
            items.append({"number": f"{i + 1:02d}", "label": it, "time": ""})
        elif isinstance(it, dict):
            items.append({
                "number": str(it.get("number") or f"{i + 1:02d}"),
                "label": str(it.get("label") or it.get("title") or f"Item {i + 1}"),
                "time": str(it.get("time") or it.get("duration") or ""),
            })
    if len(items) < 5:
        # Pad to the design floor so geometry stays stable in catalog mode.
        while len(items) < 5:
            items.append({"number": f"{len(items) + 1:02d}", "label": "—", "time": ""})
    bg = c["content_background"]
    body_base = t["body_pt"]

    def build(d: L.Density) -> L.Box:
        body_pt = L.floored_pt(body_base, d)
        num_pt = max(body_pt, min(28, t.get("section_pt", 28)))
        micro = max(12, _micro_pt(t))
        rows: list[L.Box] = []
        for i, it in enumerate(items):
            weighted: list[L.Box] = [
                L.VStack(
                    weight=0.18,
                    name=f"AgendaNumWrap{i + 1}",
                    children=[
                        L.Text(
                            str(it["number"]),
                            pt=num_pt,
                            name=f"AgendaNum{i + 1}",
                            min_cm=0.9,
                            max_cm=1.4,
                            props={
                                "font": t["heading_font"],
                                "size": str(num_pt),
                                "bold": "true",
                                "color": c["accent"],
                                "fill": "none",
                            },
                        ),
                    ],
                ),
                L.VStack(
                    weight=1,
                    name=f"AgendaLabelWrap{i + 1}",
                    children=[
                        L.Text(
                            str(it["label"]),
                            pt=body_pt,
                            name=f"AgendaLabel{i + 1}",
                            weight=1,
                            min_cm=0.9,
                            props={
                                "font": t["body_font"],
                                "size": str(body_pt),
                                "color": c["text_on_content"],
                                "fill": "none",
                            },
                        ),
                    ],
                ),
            ]
            if it.get("time"):
                weighted.append(
                    L.VStack(
                        weight=0.28,
                        name=f"AgendaTimeWrap{i + 1}",
                        children=[
                            L.Text(
                                str(it["time"]),
                                pt=micro,
                                name=f"AgendaTime{i + 1}",
                                min_cm=0.8,
                                max_cm=1.2,
                                props={
                                    "font": t["body_font"],
                                    "size": str(micro),
                                    "color": c["muted"],
                                    "align": "right",
                                    "fill": "none",
                                },
                            ),
                        ],
                    )
                )
            rows.append(
                L.HStack(
                    weighted,
                    gap=0.4 * d.gap,
                    weight=1,
                    name=f"AgendaRow{i + 1}",
                )
            )
            if i < len(items) - 1:
                rows.append(
                    L.Fixed(
                        0.04,
                        name=f"AgendaRule{i + 1}",
                        props={
                            "preset": "rect",
                            "fill": c.get("hairline", c["muted"]),
                            "line": "none",
                        },
                    )
                )
        return L.VStack(
            pad=(1.1, b["margin"], 1.0, b["margin"]),
            gap=0.35 * d.gap,
            name="agenda_toc",
            children=[
                L.Text(
                    title,
                    pt=t["title_pt"],
                    name="AgendaTitle",
                    min_cm=1.5,
                    max_cm=2.5,
                    props={
                        "font": t["heading_font"],
                        "size": str(t["title_pt"]),
                        "bold": "true",
                        "color": c["text_on_content"],
                        "fill": "none",
                    },
                ),
                L.VStack(rows, gap=0.28 * d.gap, weight=1, name="AgendaList"),
            ],
        )

    placed, _d = L.solve_adaptive(build, 0, 0, L.CANVAS_W, L.CANVAS_H)
    ops: list[dict] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": bg},
        },
    ]
    ops.extend(_emit_shapes(placed))
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get("notes", "Walk the agenda; mark time boxes.")},
    })
    return ops


def recipe_section_opener_numbered(tokens: dict, content: dict | None = None) -> list[dict]:
    """Premium section opener — solid large index + title (Phase 2 / #58).

    Fixed geometry (overlap / opacity centering is intentional chrome, not flex).
    Distinct from ``section_divider`` which uses a washed-out watermark number.
    """
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    number = str(content.get("number", "01"))
    title = content.get("title", "Section")
    blurb = content.get("blurb", "")
    bg = c["background"]

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
                "name": "OpenerAccentBar",
                "preset": "rect",
                "fill": c["accent"],
                "line": "none",
                "x": _cm(b["margin"]),
                "y": "6.4cm",
                "width": "1.1cm",
                "height": "6.2cm",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "OpenerNumber",
                "text": number,
                "x": _cm(b["margin"] + 1.6),
                "y": "5.8cm",
                "width": "8cm",
                "height": "2.4cm",
                "font": t["heading_font"],
                "size": "54",
                "bold": "true",
                "color": c["accent"],
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "OpenerTitle",
                "text": title,
                "x": _cm(b["margin"] + 1.6),
                "y": "8.4cm",
                "width": _cm(33.87 - 2 * b["margin"] - 1.6),
                "height": "2.6cm",
                "font": t["heading_font"],
                "size": str(t["title_pt"]),
                "bold": "true",
                "color": c["text"],
                "fill": "none",
            },
        },
    ]
    if blurb:
        ops.append({
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "OpenerBlurb",
                "text": blurb,
                "x": _cm(b["margin"] + 1.6),
                "y": "11.3cm",
                "width": "22cm",
                "height": "2.2cm",
                "font": t["body_font"],
                "size": str(t["body_pt"]),
                "color": c["muted"],
                "fill": "none",
            },
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


def recipe_story_timeline(tokens: dict, content: dict | None = None) -> list[dict]:
    """Premium story timeline (Phase 2 / #58) — era band + 2–6 milestone cards.

    Richer than ``timeline``: each step has date/era, title, and detail body.
    Engine-solved columns; axis + dots overlaid like timeline.
    """
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "The story so far")
    era = content.get("era", content.get("subtitle", ""))
    steps = content.get("steps") or [
        {"date": "Q1", "title": "Discover", "detail": "Frame the problem."},
        {"date": "Q2", "title": "Build", "detail": "Ship the thin slice."},
        {"date": "Q3", "title": "Scale", "detail": "Instrument and expand."},
        {"date": "Q4", "title": "Prove", "detail": "Measure outcomes."},
    ]
    if not isinstance(steps, list):
        steps = [{"title": str(steps)}]
    n = max(2, min(6, len(steps)))
    steps = steps[:n]
    mpt = _micro_pt(t)
    y_line = 8.6

    def _col(i: int, body_pt: int) -> L.Box:
        s = steps[i] if isinstance(steps[i], dict) else {"title": str(steps[i])}
        date = str(s.get("date") or s.get("era") or s.get("label") or f"{i + 1:02d}")
        head = str(s.get("title") or s.get("label") or f"Milestone {i + 1}")
        detail = str(s.get("detail") or s.get("body") or "")
        return L.VStack(
            weight=1,
            name=f"StoryCol{i + 1}",
            gap=0.3,
            pad=(0.45, 0.35, 0.45, 0.35),
            props={
                "preset": b["preset"],
                "fill": c["surface"],
                "line": c.get("hairline", "none"),
            },
            children=[
                L.Text(
                    date, pt=mpt, name=f"StoryDate{i + 1}", min_cm=0.55, max_cm=1.0,
                    props={
                        "font": t["body_font"], "size": str(mpt), "bold": "true",
                        "color": c["accent"], "align": "center", "fill": "none",
                    },
                ),
                L.Text(
                    head, pt=max(16, min(22, t["section_pt"] - 4)),
                    name=f"StoryTitle{i + 1}", min_cm=0.9, max_cm=2.2,
                    props={
                        "font": t["heading_font"],
                        "size": str(max(16, min(22, t["section_pt"] - 4))),
                        "bold": "true", "color": c["text_on_surface"],
                        "align": "center", "fill": "none",
                    },
                ),
                L.Text(
                    detail, pt=body_pt, name=f"StoryDetail{i + 1}", weight=1,
                    props={
                        "font": t["body_font"], "size": str(body_pt),
                        "color": c["muted"], "align": "center", "fill": "none",
                    },
                ),
            ],
        )

    def build(d: L.Density) -> L.Box:
        bpt = L.floored_pt(max(12, mpt + 2), d, floor=12)
        return L.HStack(
            [_col(i, bpt) for i in range(len(steps))],
            gap=b["gap"] * d.gap,
            weight=1,
        )

    placed, _d = L.solve_adaptive(
        build, b["margin"], y_line + 1.1, 33.87 - 2 * b["margin"],
        17.9 - (y_line + 1.1),
    )
    axis_w = 33.87 - 2 * b["margin"]
    ops: list[dict] = [
        _slide_op(tokens),
        _title_op(tokens, "StoryTlTitle", title),
    ]
    if era:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "StoryEra", "text": str(era),
                "x": _cm(b["margin"]), "y": "2.7cm",
                "width": _cm(axis_w), "height": "0.9cm",
                "font": t["body_font"], "size": str(t["body_pt"]),
                "color": c["muted"], "fill": "none",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "StoryAxis", "preset": "rect",
            "fill": c.get("hairline", c["muted"]), "line": "none",
            "x": _cm(b["margin"]), "y": _cm(y_line),
            "width": _cm(axis_w), "height": "0.12cm",
        },
    })
    ops.extend(_emit_shapes(placed))
    cards = {p.name: p for p in placed if p.name.startswith("StoryCol")}
    # Prefer centering dots under date labels when present.
    dates = {p.name: p for p in placed if p.name.startswith("StoryDate")}
    dot = 0.75
    for i in range(len(steps)):
        p = dates.get(f"StoryDate{i + 1}") or cards.get(f"StoryCol{i + 1}")
        if p is None:
            continue
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"StoryDot{i + 1}", "preset": "ellipse",
                "fill": c["accent"], "line": "none",
                "x": _cm(p.x + p.w / 2 - dot / 2),
                "y": _cm(y_line - dot / 2 + 0.06),
                "width": _cm(dot), "height": _cm(dot),
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Tell the arc left→right; pause on the turning point.")},
    })
    return ops


def recipe_funnel_stages(tokens: dict, content: dict | None = None) -> list[dict]:
    """Funnel / stage cascade (Phase 2 / #58) — 3–6 decreasing-width bands."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Conversion funnel")
    stages = content.get("stages") or content.get("steps") or [
        {"label": "Awareness", "value": "100%"},
        {"label": "Interest", "value": "48%"},
        {"label": "Decision", "value": "22%"},
        {"label": "Action", "value": "9%"},
    ]
    if not isinstance(stages, list):
        stages = [{"label": str(stages)}]
    n = max(3, min(6, len(stages)))
    stages = stages[:n]
    while len(stages) < 3:
        stages.append({"label": "—", "value": ""})
    n = len(stages)
    m = b["margin"]
    usable = 33.87 - 2 * m
    # Band heights share vertical space under the title.
    top = 3.4
    bottom = 18.0
    gap = 0.28
    band_h = (bottom - top - gap * (n - 1)) / n
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "FunnelTitle", title)]
    # Width fraction from top (widest) to bottom (narrowest): 1.0 → ~0.42
    for i, st in enumerate(stages):
        if isinstance(st, str):
            label, value = st, ""
        else:
            label = str(st.get("label") or st.get("title") or f"Stage {i + 1}")
            value = str(st.get("value") or st.get("metric") or "")
        frac = 1.0 - (i / max(1, n - 1)) * 0.55
        w = usable * frac
        x = m + (usable - w) / 2
        y = top + i * (band_h + gap)
        # Alternate surface / accent-tinted fill for depth without vendor art.
        fill = c["accent"] if i == n - 1 else c["surface"]
        tc = c["on_accent"] if i == n - 1 else c["text_on_surface"]
        mc = c["on_accent"] if i == n - 1 else c["muted"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"FunnelBand{i + 1}", "preset": b["preset"],
                "fill": fill, "line": "none",
                "x": _cm(x), "y": _cm(y), "width": _cm(w), "height": _cm(band_h),
            },
        })
        text = f"{label}  ·  {value}" if value else label
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"FunnelLabel{i + 1}", "text": text,
                "x": _cm(x + 0.4), "y": _cm(y + band_h * 0.28),
                "width": _cm(max(2.0, w - 0.8)), "height": _cm(band_h * 0.5),
                "font": t["heading_font"],
                "size": str(max(16, min(24, t["section_pt"] - 4))),
                "bold": "true", "color": tc, "align": "center", "fill": "none",
            },
        })
        # silence unused mc if value empty — use for secondary when value present
        if value and i != n - 1:
            ops[-1]["props"]["color"] = tc
        _ = mc
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Name the drop-off between the two biggest deltas.")},
    })
    return ops


def recipe_roadmap_swimlane(tokens: dict, content: dict | None = None) -> list[dict]:
    """Roadmap swimlanes (Phase 2 / #58) — rows × phase columns (structured grid)."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Roadmap")
    phases = content.get("phases") or content.get("columns") or ["Now", "Next", "Later"]
    if not isinstance(phases, list):
        phases = [str(phases)]
    phases = [str(p) for p in phases[:5]]
    if len(phases) < 2:
        phases = ["Now", "Next", "Later"]
    lanes = content.get("lanes") or content.get("rows") or [
        {"name": "Product", "cells": ["MVP", "Beta", "GA"]},
        {"name": "GTM", "cells": ["Design partners", "Launch", "Expand"]},
        {"name": "Platform", "cells": ["Core APIs", "Scale", "Self-serve"]},
    ]
    if not isinstance(lanes, list):
        lanes = [{"name": "Lane", "cells": []}]
    lanes = lanes[:5]
    m = b["margin"]
    usable = 33.87 - 2 * m
    label_w = 4.2
    grid_w = usable - label_w - 0.4
    n_ph = len(phases)
    col_w = (grid_w - 0.25 * (n_ph - 1)) / n_ph
    top = 3.5
    header_h = 1.1
    n_lanes = max(1, len(lanes))
    lane_h = min(3.2, (18.2 - top - header_h - 0.3 * n_lanes) / n_lanes)
    micro = str(_micro_pt(t))
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "RoadmapTitle", title)]
    # Phase headers
    for j, ph in enumerate(phases):
        x = m + label_w + 0.4 + j * (col_w + 0.25)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RoadPhase{j + 1}", "text": ph,
                "x": _cm(x), "y": _cm(top),
                "width": _cm(col_w), "height": _cm(header_h),
                "font": t["heading_font"], "size": str(max(14, t["body_pt"])),
                "bold": "true", "color": c["accent"], "align": "center", "fill": "none",
            },
        })
    for i, lane in enumerate(lanes):
        if isinstance(lane, str):
            name, cells = lane, []
        else:
            name = str(lane.get("name") or lane.get("label") or f"Lane {i + 1}")
            cells = lane.get("cells") or lane.get("items") or []
        if not isinstance(cells, list):
            cells = [str(cells)]
        cells = list(cells) + [""] * n_ph
        cells = cells[:n_ph]
        y = top + header_h + 0.25 + i * (lane_h + 0.3)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RoadLane{i + 1}", "text": name,
                "x": _cm(m), "y": _cm(y),
                "width": _cm(label_w), "height": _cm(lane_h),
                "font": t["heading_font"], "size": str(max(14, t["body_pt"])),
                "bold": "true", "color": c["text_on_content"], "fill": "none",
            },
        })
        for j, cell in enumerate(cells):
            x = m + label_w + 0.4 + j * (col_w + 0.25)
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"RoadCell{i + 1}_{j + 1}Bg", "preset": b["preset"],
                    "fill": c["surface"], "line": c.get("hairline", "none"),
                    "x": _cm(x), "y": _cm(y),
                    "width": _cm(col_w), "height": _cm(lane_h),
                },
            })
            if str(cell).strip():
                ops.append({
                    "command": "add", "parent": "/slide[last()]", "type": "shape",
                    "props": {
                        "name": f"RoadCell{i + 1}_{j + 1}", "text": str(cell),
                        "x": _cm(x + 0.2), "y": _cm(y + 0.25),
                        "width": _cm(col_w - 0.4), "height": _cm(lane_h - 0.5),
                        "font": t["body_font"], "size": micro,
                        "color": c["text_on_surface"], "fill": "none",
                    },
                })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Walk one lane at a time; call out dependencies across phases.")},
    })
    return ops


def recipe_quadrant_matrix_rich(tokens: dict, content: dict | None = None) -> list[dict]:
    """Labeled-axis 2×2 with denser cells (Phase 2 / #58) — engine grid + chrome."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Priority matrix")
    quads = content.get("quadrants") or [
        {"title": "Bet", "body": "High impact · invest", "tag": "Do"},
        {"title": "Shape", "body": "Promising · refine", "tag": "Design"},
        {"title": "Delegate", "body": "Low strategy · staff", "tag": "Own"},
        {"title": "Drop", "body": "Low leverage · cut", "tag": "Kill"},
    ]
    quads = (list(quads) + [{}] * 4)[:4]
    axes = content.get("axes") or {"x": "Effort →", "y": "Impact →"}
    qt_pt = max(16, t["section_pt"] - 6)
    micro = _micro_pt(t)

    def _quad(i: int, body_pt: int) -> L.Box:
        q = quads[i] if isinstance(quads[i], dict) else {}
        kids = [
            L.Text(
                str(q.get("tag") or q.get("chip") or ""),
                pt=micro, name=f"RichQuad{i + 1}Tag", min_cm=0.45, max_cm=0.9,
                props={
                    "font": t["body_font"], "size": str(micro), "bold": "true",
                    "color": c["accent"], "fill": "none",
                },
            ),
            L.Text(
                str(q.get("title", "")), pt=qt_pt, name=f"RichQuad{i + 1}Title",
                min_cm=0.8, max_cm=2.0,
                props={
                    "font": t["heading_font"], "size": str(qt_pt), "bold": "true",
                    "color": c["text_on_surface"], "fill": "none",
                },
            ),
            L.Text(
                str(q.get("body", "")), pt=body_pt, name=f"RichQuad{i + 1}Body",
                weight=1,
                props={
                    "font": t["body_font"], "size": str(body_pt),
                    "color": c["muted"], "fill": "none",
                },
            ),
        ]
        return L.VStack(
            weight=1, name=f"RichQuad{i + 1}Bg",
            pad=(0.45, 0.55, 0.5, 0.55), gap=0.28,
            props={"preset": b["preset"], "fill": c["surface"],
                   "line": c.get("hairline", "none")},
            children=kids,
        )

    def build(d: L.Density) -> L.Box:
        bpt = L.floored_pt(t["body_pt"], d)
        return L.VStack(gap=b["gap"] * d.gap, name="rich_matrix_grid", children=[
            L.HStack([_quad(0, bpt), _quad(1, bpt)], gap=b["gap"] * d.gap, weight=1),
            L.HStack([_quad(2, bpt), _quad(3, bpt)], gap=b["gap"] * d.gap, weight=1),
        ])

    grid_top = 3.9 if axes.get("y") else 3.4
    grid_bottom = 17.0 if axes.get("x") else 18.2
    placed, _d = L.solve_adaptive(
        build, b["margin"], grid_top, 33.87 - 2 * b["margin"], grid_bottom - grid_top)
    ops = [_slide_op(tokens), _title_op(tokens, "RichMatrixTitle", title),
           *_emit_shapes(placed)]
    usable = 33.87 - 2 * b["margin"]
    micro_s = str(micro)
    if axes.get("x"):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "RichAxisX", "text": str(axes["x"]),
                "x": _cm(b["margin"]), "y": "17.5cm",
                "width": _cm(usable), "height": "0.9cm",
                "font": t["body_font"], "size": micro_s,
                "color": c["muted"], "align": "center", "fill": "none",
            },
        })
    if axes.get("y"):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "RichAxisY", "text": str(axes["y"]),
                "x": _cm(b["margin"]), "y": "3.0cm",
                "width": "14cm", "height": "0.8cm",
                "font": t["body_font"], "size": micro_s,
                "color": c["muted"], "fill": "none",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Start top-left; contrast invest vs kill with one example each.")},
    })
    return ops


def recipe_pyramid_levels(tokens: dict, content: dict | None = None) -> list[dict]:
    """Hierarchy pyramid (Phase 2 / #58) — 3–5 centered levels, widest at base."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Capability stack")
    levels = content.get("levels") or content.get("steps") or [
        {"label": "Vision"},
        {"label": "Strategy"},
        {"label": "Programs"},
        {"label": "Execution"},
    ]
    if not isinstance(levels, list):
        levels = [{"label": str(levels)}]
    n = max(3, min(5, len(levels)))
    levels = levels[:n]
    while len(levels) < 3:
        levels.append({"label": "—"})
    n = len(levels)
    m = b["margin"]
    usable = 33.87 - 2 * m
    top = 3.5
    bottom = 18.0
    gap = 0.3
    band_h = (bottom - top - gap * (n - 1)) / n
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "PyramidTitle", title)]
    for i, lv in enumerate(levels):
        # Top of pyramid is narrowest (index 0); base is widest.
        if isinstance(lv, str):
            label, detail = lv, ""
        else:
            label = str(lv.get("label") or lv.get("title") or f"Level {i + 1}")
            detail = str(lv.get("detail") or lv.get("body") or "")
        frac = 0.42 + (i / max(1, n - 1)) * 0.58
        w = usable * frac
        x = m + (usable - w) / 2
        y = top + i * (band_h + gap)
        fill = c["accent"] if i == 0 else c["surface"]
        tc = c["on_accent"] if i == 0 else c["text_on_surface"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"PyramidBand{i + 1}", "preset": b["preset"],
                "fill": fill, "line": "none",
                "x": _cm(x), "y": _cm(y), "width": _cm(w), "height": _cm(band_h),
            },
        })
        text = f"{label} — {detail}" if detail else label
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"PyramidLabel{i + 1}", "text": text,
                "x": _cm(x + 0.35), "y": _cm(y + band_h * 0.28),
                "width": _cm(max(2.0, w - 0.7)), "height": _cm(band_h * 0.5),
                "font": t["heading_font"],
                "size": str(max(14, min(22, t["section_pt"] - 6))),
                "bold": "true", "color": tc, "align": "center", "fill": "none",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Read top→bottom; the apex is the single organizing idea.")},
    })
    return ops


def recipe_vs_scorecard(tokens: dict, content: dict | None = None) -> list[dict]:
    """Two-option scorecard (Phase 2 / #58) — criteria rows with A/B scores."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Option scorecard")
    left = content.get("left") or content.get("option_a") or {"title": "Option A"}
    right = content.get("right") or content.get("option_b") or {"title": "Option B"}
    if not isinstance(left, dict):
        left = {"title": str(left)}
    if not isinstance(right, dict):
        right = {"title": str(right)}
    criteria = content.get("criteria") or content.get("rows") or [
        {"name": "Impact", "left": "High", "right": "Med"},
        {"name": "Effort", "left": "Med", "right": "Low"},
        {"name": "Risk", "left": "Low", "right": "Med"},
        {"name": "Fit", "left": "Strong", "right": "Partial"},
    ]
    if not isinstance(criteria, list):
        criteria = []
    criteria = criteria[:8]
    if len(criteria) < 2:
        criteria = [
            {"name": "Impact", "left": "—", "right": "—"},
            {"name": "Effort", "left": "—", "right": "—"},
        ]
    mpt = _micro_pt(t)
    body_base = t["body_pt"]

    def build(d: L.Density) -> L.Box:
        bpt = L.floored_pt(body_base, d)
        header = L.HStack(
            [
                L.VStack(weight=1.1, name="VsCritHead", children=[
                    L.Text("Criteria", pt=mpt, name="VsCritHeadT", min_cm=0.7,
                           props={"font": t["body_font"], "size": str(mpt),
                                  "bold": "true", "color": c["muted"], "fill": "none"}),
                ]),
                L.VStack(weight=1, name="VsLeftHead", children=[
                    L.Text(str(left.get("title", "A")), pt=max(16, t["section_pt"] - 6),
                           name="VsLeftHeadT", min_cm=0.9,
                           props={"font": t["heading_font"],
                                  "size": str(max(16, t["section_pt"] - 6)),
                                  "bold": "true", "color": c["accent"],
                                  "align": "center", "fill": "none"}),
                ]),
                L.VStack(weight=1, name="VsRightHead", children=[
                    L.Text(str(right.get("title", "B")), pt=max(16, t["section_pt"] - 6),
                           name="VsRightHeadT", min_cm=0.9,
                           props={"font": t["heading_font"],
                                  "size": str(max(16, t["section_pt"] - 6)),
                                  "bold": "true", "color": c["accent"],
                                  "align": "center", "fill": "none"}),
                ]),
            ],
            gap=0.4 * d.gap,
            name="VsHeader",
        )
        rows: list[L.Box] = [header]
        for i, row in enumerate(criteria):
            if isinstance(row, str):
                name, lv, rv = row, "—", "—"
            else:
                name = str(row.get("name") or row.get("label") or f"C{i + 1}")
                lv = str(row.get("left") or row.get("a") or "—")
                rv = str(row.get("right") or row.get("b") or "—")
            rows.append(
                L.HStack(
                    [
                        L.VStack(
                            weight=1.1, name=f"VsCrit{i + 1}Bg",
                            pad=(0.35, 0.4, 0.35, 0.4),
                            props={"preset": b["preset"], "fill": c["surface"],
                                   "line": "none"},
                            children=[
                                L.Text(name, pt=bpt, name=f"VsCrit{i + 1}",
                                       min_cm=0.7, weight=1,
                                       props={"font": t["heading_font"],
                                              "size": str(bpt), "bold": "true",
                                              "color": c["text_on_surface"],
                                              "fill": "none"}),
                            ],
                        ),
                        L.VStack(
                            weight=1, name=f"VsLeft{i + 1}Bg",
                            pad=(0.35, 0.4, 0.35, 0.4),
                            props={"preset": b["preset"], "fill": c["surface"],
                                   "line": "none"},
                            children=[
                                L.Text(lv, pt=bpt, name=f"VsLeft{i + 1}",
                                       min_cm=0.7, weight=1,
                                       props={"font": t["body_font"], "size": str(bpt),
                                              "color": c["text_on_surface"],
                                              "align": "center", "fill": "none"}),
                            ],
                        ),
                        L.VStack(
                            weight=1, name=f"VsRight{i + 1}Bg",
                            pad=(0.35, 0.4, 0.35, 0.4),
                            props={"preset": b["preset"], "fill": c["surface"],
                                   "line": "none"},
                            children=[
                                L.Text(rv, pt=bpt, name=f"VsRight{i + 1}",
                                       min_cm=0.7, weight=1,
                                       props={"font": t["body_font"], "size": str(bpt),
                                              "color": c["text_on_surface"],
                                              "align": "center", "fill": "none"}),
                            ],
                        ),
                    ],
                    gap=0.35 * d.gap,
                    weight=1,
                    name=f"VsRow{i + 1}",
                )
            )
        return L.VStack(
            pad=(1.1, b["margin"], 0.9, b["margin"]),
            gap=0.4 * d.gap,
            name="vs_scorecard",
            children=[
                L.Text(
                    title, pt=t["title_pt"], name="VsTitle",
                    min_cm=1.4, max_cm=2.4,
                    props={
                        "font": t["heading_font"], "size": str(t["title_pt"]),
                        "bold": "true", "color": c["text_on_content"], "fill": "none",
                    },
                ),
                L.VStack(rows, gap=0.35 * d.gap, weight=1, name="VsGrid"),
            ],
        )

    placed, _d = L.solve_adaptive(build, 0, 0, L.CANVAS_W, L.CANVAS_H)
    ops: list[dict] = [_slide_op(tokens), *_emit_shapes(placed)]
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Score transparently; pick the option that wins where it matters.")},
    })
    return ops


def recipe_chart_callout_panel(tokens: dict, content: dict | None = None) -> list[dict]:
    """Chart + three numbered callouts (Phase 2 / #58) — structured storytelling."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "What the data says")
    cats = content.get("categories", "A,B,C,D")
    s1 = content.get("series1_values", "10,14,12,18")
    s2 = content.get("series2_values", "")
    s1_name = content.get("series1_name", "Series 1")
    s2_name = content.get("series2_name", "Series 2")
    chart_type = str(content.get("chart_type", "column"))
    callouts = content.get("callouts") or content.get("bullets") or [
        "Lead with the single most surprising bar.",
        "Name the driver behind the inflection.",
        "Close with the decision this enables.",
    ]
    if not isinstance(callouts, list):
        callouts = [str(callouts)]
    callouts = [str(x) for x in callouts[:3]]
    while len(callouts) < 3:
        callouts.append("—")
    single_series = chart_type.lower() in (
        "pie", "doughnut", "funnel", "treemap", "sunburst", "pareto", "histogram",
    )
    series2 = c.get("chart_series2", c["muted"])
    chart_props: dict[str, Any] = {
        "name": "CalloutChart",
        "chartType": chart_type,
        "series1.name": s1_name,
        "series1.values": s1,
        "series1.color": c.get("chart_series1", c["accent"]),
        "categories": cats,
        "x": _cm(b["margin"]),
        "y": "3.4cm",
        "width": "19.5cm",
        "height": "14cm",
    }
    if not single_series and s2:
        chart_props.update({
            "series2.name": s2_name,
            "series2.values": s2,
            "series2.color": series2,
        })
    ops: list[dict] = [
        _slide_op(tokens),
        _title_op(tokens, "CalloutTitle", title),
        {"command": "add", "parent": "/slide[last()]", "type": "chart",
         "props": chart_props},
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "CalloutPanelBg", "preset": b["preset"],
                "fill": c["surface"], "line": "none",
                "x": "22.2cm", "y": "3.4cm", "width": "10.2cm", "height": "14cm",
            },
        },
    ]
    y0 = 4.0
    slot_h = 4.0
    for i, text in enumerate(callouts):
        y = y0 + i * slot_h
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"CalloutNum{i + 1}", "text": f"{i + 1:02d}",
                "x": "22.7cm", "y": _cm(y),
                "width": "2.2cm", "height": "1.0cm",
                "font": t["heading_font"], "size": "22", "bold": "true",
                "color": c["accent"], "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"CalloutBody{i + 1}", "text": text,
                "x": "22.7cm", "y": _cm(y + 1.1),
                "width": "9.0cm", "height": "2.4cm",
                "font": t["body_font"], "size": str(t["body_pt"]),
                "color": c["text_on_surface"], "fill": "none",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Point to the chart only after the three callouts land.")},
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
    # Prefer studies[] when present so table-shaped HEAVY["rows"] cannot steal
    # the forest path in the geometry-contract suite.
    rows = content.get("studies") or content.get("rows") or [
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
    if d0 > d1:
        d0, d1 = d1, d0
    span = max(1e-6, d1 - d0)
    mpt = _micro_pt(t)
    forest_warnings: set[str] = set()

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
            if low > high:
                low, high = high, low
                forest_warnings.add(f"row {i + 1}: swapped inverted CI bounds")
            if effect < d0 or effect > d1 or low < d0 or high > d1:
                forest_warnings.add(
                    f"row {i + 1}: effect/CI clamped to domain [{d0}, {d1}]"
                )
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
    notes = content.get("notes", "Read left labels, then CI bars vs the null line.")
    if forest_warnings:
        notes = notes + " | " + "; ".join(sorted(forest_warnings)[:6])
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": notes},
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


# ---------------------------------------------------------------------------
# Wave 1 full-family coverage (docs/recipe-coverage-roadmap.md)
# ---------------------------------------------------------------------------

def _norm_steps(raw: Any, *, min_n: int = 3, max_n: int = 6,
                defaults: list | None = None) -> list[dict]:
    """Normalize steps/stages/items into list[{label, detail?, value?}]."""
    if raw is None:
        raw = defaults or [{"label": f"Step {i + 1}"} for i in range(min_n)]
    if not isinstance(raw, list):
        raw = [raw]
    out: list[dict] = []
    for i, item in enumerate(raw[:max_n]):
        if isinstance(item, dict):
            label = str(item.get("label") or item.get("title") or item.get("name")
                        or f"Item {i + 1}")
            detail = str(item.get("detail") or item.get("body") or item.get("desc") or "")
            value = str(item.get("value") or item.get("metric") or "")
            out.append({"label": label, "detail": detail, "value": value, **{
                k: item[k] for k in item if k not in ("label", "title", "name",
                                                       "detail", "body", "desc",
                                                       "value", "metric")
            }})
        else:
            out.append({"label": str(item), "detail": "", "value": ""})
    while len(out) < min_n:
        out.append({"label": "—", "detail": "", "value": ""})
    return out


def recipe_chevron_process(tokens: dict, content: dict | None = None) -> list[dict]:
    """Horizontal chevron / arrow process (Wave 1) — 3–6 stepped stages."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Process")
    steps = _norm_steps(content.get("steps") or content.get("stages"), min_n=3, max_n=6,
                        defaults=[{"label": s} for s in ("Discover", "Design", "Build", "Ship")])
    n = len(steps)
    m, gap = b["margin"], 0.2
    usable = 33.87 - 2 * m
    # Overlap chevrons slightly so the point reads as a chevron train.
    step_w = (usable + (n - 1) * 0.55) / n
    y, h = 7.2, 4.8
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "ChevronTitle", title)]
    for i, st in enumerate(steps):
        x = m + i * (step_w - 0.55)
        fill = c["accent"] if i == 0 or i == n - 1 else c["surface"]
        tc = c["on_accent"] if fill == c["accent"] else c["text_on_surface"]
        preset = "chevron" if i < n - 1 else b["preset"]
        # Some officecli builds lack chevron — rightArrow is the portable fallback.
        text = st["label"]
        if st.get("value"):
            text = f"{st['label']}\n{st['value']}"
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Chevron{i + 1}", "preset": preset,
                "fill": fill, "line": "none",
                "text": text,
                "x": _cm(x), "y": _cm(y), "width": _cm(step_w), "height": _cm(h),
                "font": t["heading_font"],
                "size": str(max(14, min(22, t["section_pt"] - 4))),
                "bold": "true", "color": tc, "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Walk left→right; the last chevron is the outcome.")},
    })
    return ops


def recipe_cycle_loop(tokens: dict, content: dict | None = None) -> list[dict]:
    """Circular process (Wave 1) — 3–6 nodes around a hub."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Cycle")
    hub = str(content.get("hub") or content.get("center") or "Loop")
    steps = _norm_steps(content.get("steps") or content.get("stages"), min_n=3, max_n=6,
                        defaults=[{"label": s} for s in ("Plan", "Do", "Check", "Act")])
    n = len(steps)
    cx, cy, r = 16.9, 11.0, 5.2
    node_w, node_h = 5.4, 2.4
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "CycleTitle", title)]
    # Hub
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "CycleHub", "preset": "ellipse",
            "fill": c["accent"], "line": "none", "text": hub,
            "x": _cm(cx - 2.2), "y": _cm(cy - 1.5),
            "width": "4.4cm", "height": "3.0cm",
            "font": t["heading_font"], "size": str(max(16, t["section_pt"] - 4)),
            "bold": "true", "color": c["on_accent"], "align": "center", "valign": "middle",
        },
    })
    for i, st in enumerate(steps):
        ang = -math.pi / 2 + (2 * math.pi * i / n)
        x = cx + r * math.cos(ang) - node_w / 2
        y = cy + r * math.sin(ang) * 0.72 - node_h / 2  # squash vertically for 16:9
        x = max(b["margin"], min(33.87 - b["margin"] - node_w, x))
        y = max(3.2, min(17.5 - node_h, y))
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"CycleNode{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none", "text": st["label"],
                "x": _cm(x), "y": _cm(y), "width": _cm(node_w), "height": _cm(node_h),
                "font": t["body_font"], "size": str(max(14, min(18, t["body_pt"]))),
                "bold": "true", "color": c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Name the handoff between two adjacent nodes.")},
    })
    return ops


def recipe_waterfall_insight(tokens: dict, content: dict | None = None) -> list[dict]:
    """Waterfall chart + insight rail (Wave 1) — chart_type defaults to waterfall."""
    content = dict(content or {})
    content.setdefault("chart_type", "waterfall")
    content.setdefault("title", content.get("title") or "Bridge to result")
    content.setdefault(
        "insight_title", content.get("insight_title") or "What moved the number")
    content.setdefault(
        "insight_body",
        content.get("insight_body")
        or "Call out the two largest positive and negative bridges.",
    )
    content.setdefault("categories", content.get("categories") or "Start,Price,Volume,Mix,End")
    content.setdefault("series1_values", content.get("series1_values") or "100,12,-5,8,115")
    content.setdefault("series1_name", content.get("series1_name") or "Bridge")
    content.setdefault(
        "notes",
        content.get("notes") or "Read left→right; the end bar is the result, not a delta.",
    )
    # Reuse chart_insight geometry with forced waterfall type.
    return recipe_chart_insight(tokens, content)


def recipe_venn_overlap(tokens: dict, content: dict | None = None) -> list[dict]:
    """2–3 set Venn (Wave 1) — overlapping ellipses + set labels + intersection."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Overlap")
    sets = content.get("sets") or content.get("circles") or [
        {"label": "Set A", "detail": ""},
        {"label": "Set B", "detail": ""},
        {"label": "Set C", "detail": ""},
    ]
    if not isinstance(sets, list):
        sets = [{"label": str(sets)}]
    sets = sets[:3]
    while len(sets) < 2:
        sets.append({"label": f"Set {len(sets) + 1}"})
    intersection = str(content.get("intersection") or content.get("overlap") or "Shared")
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "VennTitle", title)]
    # Two-set side-by-side overlap; three-set triangle of ellipses.
    if len(sets) == 2:
        positions = [(8.5, 6.5), (15.5, 6.5)]
        size = 11.0
    else:
        positions = [(9.0, 5.5), (15.0, 5.5), (12.0, 10.0)]
        size = 9.5
    fills = [c["accent"], c["surface"], c.get("chart_series2") or c["muted"]]
    for i, (st, (x, y)) in enumerate(zip(sets, positions)):
        label = st.get("label") if isinstance(st, dict) else str(st)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Venn{i + 1}", "preset": "ellipse",
                "fill": fills[i % len(fills)], "line": "none",
                # Soft overlap: no transparency API — use distinct fills + labels outside
                "x": _cm(x), "y": _cm(y), "width": _cm(size), "height": _cm(size * 0.85),
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"VennLabel{i + 1}", "text": str(label),
                "x": _cm(x + 0.8), "y": _cm(y + 0.6),
                "width": _cm(size - 1.6), "height": "1.2cm",
                "font": t["heading_font"], "size": str(max(16, t["section_pt"] - 6)),
                "bold": "true",
                "color": c["on_accent"] if i == 0 else c["text_on_surface"],
                "fill": "none", "align": "center",
            },
        })
    # Intersection callout at center
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "VennIntersection", "text": intersection,
            "x": "12.5cm", "y": "9.5cm", "width": "9cm", "height": "2.2cm",
            "font": t["heading_font"], "size": str(max(16, t["body_pt"] + 2)),
            "bold": "true", "color": c["text_on_content"],
            "fill": "none", "align": "center", "valign": "middle",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Define the intersection first; sets are context.")},
    })
    return ops


def recipe_swot_2x2(tokens: dict, content: dict | None = None) -> list[dict]:
    """SWOT 2×2 (Wave 1) — fixed S/W/O/T labels on a quadrant matrix."""
    content = dict(content or {})
    quads = content.get("quadrants")
    if not quads:
        s = content.get("strengths") or content.get("s") or ["Core strength"]
        w = content.get("weaknesses") or content.get("w") or ["Gap to close"]
        o = content.get("opportunities") or content.get("o") or ["Open door"]
        t_ = content.get("threats") or content.get("t") or ["External risk"]

        def _body(items: Any) -> str:
            if isinstance(items, list):
                return "\n".join(f"• {x}" for x in items[:6])
            return str(items)

        quads = [
            {"title": "Strengths", "body": _body(s)},
            {"title": "Weaknesses", "body": _body(w)},
            {"title": "Opportunities", "body": _body(o)},
            {"title": "Threats", "body": _body(t_)},
        ]
    content["quadrants"] = quads
    content.setdefault("title", content.get("title") or "SWOT")
    content.setdefault("axes", content.get("axes") or {
        "x": "Internal → External", "y": "Helpful → Harmful",
    })
    content.setdefault(
        "notes",
        content.get("notes") or "Pair each weakness with a strength that offsets it.",
    )
    return recipe_matrix_2x2(tokens, content)


def recipe_gantt_bars(tokens: dict, content: dict | None = None) -> list[dict]:
    """Simple Gantt (Wave 1) — rows with start/end bars across phases."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Schedule")
    phases = content.get("phases") or content.get("columns") or ["Q1", "Q2", "Q3", "Q4"]
    if not isinstance(phases, list):
        phases = [str(phases)]
    phases = [str(p) for p in phases[:8]]
    if len(phases) < 2:
        phases = ["Q1", "Q2", "Q3", "Q4"]
    tasks = content.get("tasks") or content.get("rows") or content.get("items") or [
        {"name": "Discovery", "start": 0, "end": 1},
        {"name": "Build", "start": 1, "end": 3},
        {"name": "Launch", "start": 3, "end": 4},
    ]
    if not isinstance(tasks, list):
        tasks = []
    tasks = tasks[:8]
    if not tasks:
        tasks = [{"name": "Task", "start": 0, "end": 1}]
    m = b["margin"]
    label_w = 6.5
    track_x = m + label_w + 0.3
    track_w = 33.87 - track_x - m
    nph = len(phases)
    col_w = track_w / nph
    top, header_h = 3.3, 1.0
    row_h = min(1.8, (17.8 - top - header_h) / max(1, len(tasks)))
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "GanttTitle", title)]
    for j, ph in enumerate(phases):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"GanttPhase{j + 1}", "text": ph,
                "x": _cm(track_x + j * col_w), "y": _cm(top),
                "width": _cm(col_w), "height": _cm(header_h),
                "font": t["body_font"], "size": str(_micro_pt(t) + 2),
                "bold": "true", "color": c["muted"], "align": "center", "fill": "none",
            },
        })
    for i, task in enumerate(tasks):
        if isinstance(task, dict):
            name = str(task.get("name") or task.get("label") or f"Task {i + 1}")
            start = int(task.get("start", 0))
            end = int(task.get("end", start + 1))
        else:
            name, start, end = str(task), 0, 1
        start = max(0, min(nph - 1, start))
        end = max(start + 1, min(nph, end))
        y = top + header_h + 0.15 + i * row_h
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"GanttLabel{i + 1}", "text": name,
                "x": _cm(m), "y": _cm(y), "width": _cm(label_w), "height": _cm(row_h - 0.15),
                "font": t["body_font"], "size": str(max(12, min(16, t["body_pt"] - 2))),
                "color": c["text_on_content"], "valign": "middle", "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"GanttBar{i + 1}", "preset": b["preset"],
                "fill": c["accent"] if i % 2 == 0 else c["surface"], "line": "none",
                "x": _cm(track_x + start * col_w + 0.1),
                "y": _cm(y + 0.25),
                "width": _cm(max(0.4, (end - start) * col_w - 0.2)),
                "height": _cm(max(0.5, row_h - 0.55)),
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Call out the critical path — the bar that cannot slip.")},
    })
    return ops


def recipe_org_tree(tokens: dict, content: dict | None = None) -> list[dict]:
    """Org tree (Wave 1) — root + up to 2 levels of reports."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Organization")
    root = content.get("root") or content.get("lead") or {
        "name": "Leader", "role": "Role",
    }
    if not isinstance(root, dict):
        root = {"name": str(root), "role": ""}
    reports = content.get("reports") or content.get("children") or content.get("members") or [
        {"name": "A", "role": "Role A"},
        {"name": "B", "role": "Role B"},
        {"name": "C", "role": "Role C"},
    ]
    if not isinstance(reports, list):
        reports = []
    reports = reports[:5]
    m = b["margin"]
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "OrgTitle", title)]
    # Root card
    rw, rh = 10.0, 2.8
    rx = (33.87 - rw) / 2
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "OrgRoot", "preset": b["preset"],
            "fill": c["accent"], "line": "none",
            "text": f"{root.get('name', 'Leader')}\n{root.get('role', '')}".strip(),
            "x": _cm(rx), "y": "3.6cm", "width": _cm(rw), "height": _cm(rh),
            "font": t["heading_font"], "size": str(max(16, t["section_pt"] - 4)),
            "bold": "true", "color": c["on_accent"],
            "align": "center", "valign": "middle",
        },
    })
    # Vertical spine
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "OrgSpine", "preset": "rect",
            "fill": c["muted"], "line": "none",
            "x": "16.75cm", "y": "6.5cm", "width": "0.12cm", "height": "1.2cm",
        },
    })
    n = max(1, len(reports))
    col_w, xs = _grid_n(n, m, b["gap"], max_n=5)
    y = 8.0
    for i, rep in enumerate(reports):
        if isinstance(rep, dict):
            text = f"{rep.get('name', '—')}\n{rep.get('role', '')}".strip()
        else:
            text = str(rep)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"OrgChild{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none", "text": text,
                "x": _cm(xs[i]), "y": _cm(y), "width": _cm(col_w), "height": "3.6cm",
                "font": t["body_font"], "size": str(max(14, min(18, t["body_pt"]))),
                "bold": "true", "color": c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "State the decision right of the root node.")},
    })
    return ops


def recipe_persona_card(tokens: dict, content: dict | None = None) -> list[dict]:
    """Buyer / user persona (Wave 1) — hero profile + attribute list."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Persona")
    name = str(content.get("name") or content.get("persona") or "Alex Rivera")
    role = str(content.get("role") or content.get("title_line") or "Role / segment")
    quote = str(content.get("quote") or content.get("goal")
                or "What success looks like in their words.")
    attrs = content.get("attrs") or content.get("traits") or content.get("bullets") or [
        "Goal: …", "Pain: …", "Channel: …", "Metric: …",
    ]
    if not isinstance(attrs, list):
        attrs = [str(attrs)]
    attrs = [str(a) for a in attrs[:8]]
    m = b["margin"]
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "PersonaTitle", title)]
    # Left profile panel
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "PersonaPanel", "preset": b["preset"],
            "fill": c["surface"], "line": "none",
            "x": _cm(m), "y": "3.4cm", "width": "14cm", "height": "14.2cm",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "PersonaAvatar", "preset": "ellipse",
            "fill": c["accent"], "line": "none", "text": _initials(name),
            "x": _cm(m + 4.2), "y": "4.2cm", "width": "5.5cm", "height": "5.5cm",
            "font": t["heading_font"], "size": "28",
            "bold": "true", "color": c["on_accent"],
            "align": "center", "valign": "middle",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "PersonaName", "text": name,
            "x": _cm(m + 0.6), "y": "10.2cm", "width": "12.8cm", "height": "1.4cm",
            "font": t["heading_font"], "size": str(t["title_pt"] - 8),
            "bold": "true", "color": c["text_on_surface"],
            "align": "center", "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "PersonaRole", "text": role,
            "x": _cm(m + 0.6), "y": "11.6cm", "width": "12.8cm", "height": "1.0cm",
            "font": t["body_font"], "size": str(t["body_pt"]),
            "color": c["muted"], "align": "center", "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "PersonaQuote", "text": f"“{quote}”",
            "x": _cm(m + 0.8), "y": "13.2cm", "width": "12.4cm", "height": "3.6cm",
            "font": t["body_font"], "size": str(max(14, t["body_pt"] - 2)),
            "color": c["text_on_surface"], "fill": "none",
        },
    })
    # Right attributes
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "PersonaAttrsBg", "preset": b["preset"],
            "fill": c["content_background"], "line": "none",
            "x": "16.5cm", "y": "3.4cm", "width": _cm(33.87 - m - 16.5), "height": "14.2cm",
        },
    })
    body = "\n".join(f"• {a}" for a in attrs)
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "PersonaAttrs", "text": body,
            "x": "17.2cm", "y": "4.2cm",
            "width": _cm(33.87 - m - 17.8), "height": "12.5cm",
            "font": t["body_font"], "size": str(t["body_pt"]),
            "color": c["text_on_content"], "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "One decision this persona forces on the product.")},
    })
    return ops


def recipe_business_canvas(tokens: dict, content: dict | None = None) -> list[dict]:
    """Business Model Canvas-style 9-block grid (Wave 1) — original layout."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Business model")
    # Standard BMC keys or free blocks list
    defaults = {
        "key_partners": "Key partners",
        "key_activities": "Key activities",
        "key_resources": "Key resources",
        "value_propositions": "Value propositions",
        "customer_relationships": "Customer relationships",
        "channels": "Channels",
        "customer_segments": "Customer segments",
        "cost_structure": "Cost structure",
        "revenue_streams": "Revenue streams",
    }
    blocks = content.get("blocks")
    if isinstance(blocks, list) and len(blocks) >= 9:
        labels = [str(x.get("label") if isinstance(x, dict) else x) for x in blocks[:9]]
        bodies = [
            str(x.get("body") if isinstance(x, dict) else "") for x in blocks[:9]
        ]
    else:
        labels, bodies = [], []
        for key, fallback in defaults.items():
            val = content.get(key)
            if isinstance(val, dict):
                labels.append(str(val.get("label") or fallback))
                bodies.append(str(val.get("body") or val.get("text") or ""))
            elif val:
                labels.append(fallback)
                bodies.append(str(val) if not isinstance(val, list)
                              else "\n".join(f"• {x}" for x in val[:5]))
            else:
                labels.append(fallback)
                bodies.append("")
    m = b["margin"]
    # Layout (approximate BMC):
    # Row1: KP | KA | VP | CR | CS
    #            KR |    | CH |
    # Row2: Cost structure     | Revenue streams
    usable = 33.87 - 2 * m
    col = usable / 5
    top, mid_h, bot_h = 3.2, 9.0, 4.5
    half = mid_h / 2
    # geometry: (i, x_cols, y, h) for each of 9 blocks in defaults order
    geos = [
        (0, 0, 1, top, mid_h),           # KP full height left
        (1, 1, 1, top, half),            # KA
        (2, 1, 1, top + half, half),     # KR
        (3, 2, 1, top, mid_h),           # VP full
        (4, 3, 1, top, half),            # CR
        (5, 3, 1, top + half, half),     # CH
        (6, 4, 1, top, mid_h),           # CS full
        (7, 0, 2, top + mid_h + 0.2, bot_h),  # Cost
        (8, 2, 3, top + mid_h + 0.2, bot_h),  # Revenue (cols 2-4)
    ]
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "BmcTitle", title)]
    micro = str(_micro_pt(t))
    for idx, x0, span, y, h in geos:
        x = m + x0 * col
        w = col * span - 0.15
        if idx == 8:
            w = col * 3 - 0.15
        fill = c["accent"] if idx == 3 else c["surface"]
        tc = c["on_accent"] if idx == 3 else c["text_on_surface"]
        mc = c["on_accent"] if idx == 3 else c["muted"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"BmcBlock{idx + 1}", "preset": b["preset"],
                "fill": fill, "line": "none",
                "x": _cm(x), "y": _cm(y), "width": _cm(w), "height": _cm(h - 0.12),
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"BmcLabel{idx + 1}", "text": labels[idx],
                "x": _cm(x + 0.2), "y": _cm(y + 0.15),
                "width": _cm(w - 0.4), "height": "0.7cm",
                "font": t["heading_font"], "size": micro,
                "bold": "true", "color": mc, "fill": "none",
            },
        })
        if bodies[idx]:
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"BmcBody{idx + 1}", "text": bodies[idx][:280],
                    "x": _cm(x + 0.2), "y": _cm(y + 0.9),
                    "width": _cm(w - 0.4), "height": _cm(max(0.8, h - 1.2)),
                    "font": t["body_font"], "size": str(max(11, t["body_pt"] - 6)),
                    "color": tc, "fill": "none",
                },
            })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Start at value proposition; test cost vs revenue last.")},
    })
    return ops


def recipe_fishbone_causes(tokens: dict, content: dict | None = None) -> list[dict]:
    """Ishikawa / fishbone (Wave 1) — spine + cause branches."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Root causes")
    effect = str(content.get("effect") or content.get("head") or "Effect")
    causes = content.get("causes") or content.get("bones") or content.get("branches") or [
        {"label": "People", "items": ["Skill gap"]},
        {"label": "Process", "items": ["Handoff delay"]},
        {"label": "Tools", "items": ["Legacy stack"]},
        {"label": "Data", "items": ["No single source"]},
    ]
    if not isinstance(causes, list):
        causes = [{"label": str(causes), "items": []}]
    causes = causes[:6]
    m = b["margin"]
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "FishTitle", title)]
    # Spine
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "FishSpine", "preset": "rect",
            "fill": c["muted"], "line": "none",
            "x": _cm(m + 1), "y": "10.5cm",
            "width": _cm(33.87 - 2 * m - 8), "height": "0.18cm",
        },
    })
    # Head (effect)
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "FishHead", "preset": b["preset"],
            "fill": c["accent"], "line": "none", "text": effect,
            "x": _cm(33.87 - m - 6.5), "y": "8.8cm",
            "width": "6.2cm", "height": "3.6cm",
            "font": t["heading_font"], "size": str(max(16, t["section_pt"] - 4)),
            "bold": "true", "color": c["on_accent"],
            "align": "center", "valign": "middle",
        },
    })
    # Alternate bones above / below spine
    n = len(causes)
    span = 33.87 - 2 * m - 9
    for i, bone in enumerate(causes):
        if isinstance(bone, dict):
            label = str(bone.get("label") or bone.get("name") or f"Cause {i + 1}")
            items = bone.get("items") or bone.get("bullets") or []
            if not isinstance(items, list):
                items = [str(items)]
            detail = "\n".join(f"• {x}" for x in items[:4])
        else:
            label, detail = str(bone), ""
        x = m + 1.2 + (i + 0.5) * (span / max(1, n)) - 2.8
        above = i % 2 == 0
        y = 4.0 if above else 12.0
        h = 5.8 if above else 5.5
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"FishBone{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none",
                "text": f"{label}\n{detail}".strip(),
                "x": _cm(max(m, x)), "y": _cm(y),
                "width": "5.6cm", "height": _cm(h),
                "font": t["body_font"], "size": str(max(12, t["body_pt"] - 4)),
                "bold": "true", "color": c["text_on_surface"],
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Pick the one bone you will act on this quarter.")},
    })
    return ops


def recipe_iceberg_levels(tokens: dict, content: dict | None = None) -> list[dict]:
    """Iceberg model (Wave 1) — waterline + levels above/below."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Iceberg")
    above = content.get("above") or content.get("events") or [
        {"label": "Events", "detail": "What we see"},
    ]
    below = content.get("below") or content.get("levels") or [
        {"label": "Patterns", "detail": "Recurring trends"},
        {"label": "Structure", "detail": "System design"},
        {"label": "Mental models", "detail": "Beliefs"},
    ]
    if not isinstance(above, list):
        above = [above]
    if not isinstance(below, list):
        below = [below]
    above = _norm_steps(above, min_n=1, max_n=2)
    below = _norm_steps(below, min_n=2, max_n=4)
    m = b["margin"]
    usable = 33.87 - 2 * m
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "IceTitle", title)]
    # Waterline
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "Waterline", "preset": "rect",
            "fill": c.get("chart_series2") or c["muted"], "line": "none",
            "x": _cm(m), "y": "8.3cm", "width": _cm(usable), "height": "0.12cm",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "WaterlineLabel", "text": "waterline — visible above / hidden below",
            "x": _cm(m), "y": "7.5cm", "width": _cm(usable), "height": "0.7cm",
            "font": t["body_font"], "size": str(_micro_pt(t)),
            "color": c["muted"], "align": "center", "fill": "none",
        },
    })
    # Above bands (narrower tip)
    for i, lv in enumerate(above):
        frac = 0.45 + i * 0.1
        w = usable * frac
        x = m + (usable - w) / 2
        y = 3.5 + i * 1.8
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"IceAbove{i + 1}", "preset": b["preset"],
                "fill": c["accent"], "line": "none",
                "text": f"{lv['label']}" + (f" — {lv['detail']}" if lv.get("detail") else ""),
                "x": _cm(x), "y": _cm(y), "width": _cm(w), "height": "1.6cm",
                "font": t["heading_font"], "size": str(max(14, t["section_pt"] - 8)),
                "bold": "true", "color": c["on_accent"],
                "align": "center", "valign": "middle",
            },
        })
    # Below bands (widening)
    for i, lv in enumerate(below):
        frac = 0.55 + (i / max(1, len(below) - 1)) * 0.4 if len(below) > 1 else 0.75
        w = usable * frac
        x = m + (usable - w) / 2
        y = 8.7 + i * 2.2
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"IceBelow{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none",
                "text": f"{lv['label']}" + (f" — {lv['detail']}" if lv.get("detail") else ""),
                "x": _cm(x), "y": _cm(y), "width": _cm(w), "height": "2.0cm",
                "font": t["heading_font"], "size": str(max(14, t["section_pt"] - 8)),
                "bold": "true", "color": c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Interventions below the waterline change what appears above.")},
    })
    return ops


def recipe_framework_row(tokens: dict, content: dict | None = None) -> list[dict]:
    """Named framework stages (Wave 1) — ADKAR / AIDA / value-chain style row."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Framework")
    framework = str(content.get("framework") or content.get("name") or "")
    steps = _norm_steps(
        content.get("steps") or content.get("stages") or content.get("items"),
        min_n=3, max_n=7,
        defaults=[{"label": s} for s in ("A", "D", "K", "A", "R")],
    )
    n = len(steps)
    m = b["margin"]
    col_w, xs = _grid_n(n, m, b["gap"] * 0.6, max_n=7)
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "FwTitle", title)]
    if framework:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "FwName", "text": framework,
                "x": _cm(m), "y": "2.7cm",
                "width": _cm(33.87 - 2 * m), "height": "0.8cm",
                "font": t["body_font"], "size": str(_micro_pt(t) + 2),
                "color": c["muted"], "fill": "none",
            },
        })
    y, h = 4.2, 12.5
    for i, st in enumerate(steps):
        fill = c["accent"] if i == 0 else c["surface"]
        tc = c["on_accent"] if i == 0 else c["text_on_surface"]
        letter = st["label"][:1].upper() if len(st["label"]) <= 3 else f"{i + 1}"
        # Index disc
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"FwDisc{i + 1}", "preset": "ellipse",
                "fill": fill, "line": "none", "text": letter,
                "x": _cm(xs[i] + col_w / 2 - 0.9), "y": _cm(y),
                "width": "1.8cm", "height": "1.8cm",
                "font": t["heading_font"], "size": "18",
                "bold": "true", "color": tc if i == 0 else c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
        body = st["label"]
        if st.get("detail"):
            body = f"{st['label']}\n{st['detail']}"
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"FwCard{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none", "text": body,
                "x": _cm(xs[i]), "y": _cm(y + 2.3),
                "width": _cm(col_w), "height": _cm(h - 2.3),
                "font": t["body_font"], "size": str(max(13, min(18, t["body_pt"] - 2))),
                "bold": "true", "color": c["text_on_surface"],
                "align": "center",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Name the stage that is currently underinvested.")},
    })
    return ops


# ---------------------------------------------------------------------------
# Wave 2 long-tail roles (docs/recipe-coverage-roadmap.md)
# ---------------------------------------------------------------------------

def recipe_icon_stat_row(tokens: dict, content: dict | None = None) -> list[dict]:
    """Icon + stat row (Wave 2) — letter/chip stand-ins, not vendor icons."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "At a glance")
    stats = content.get("stats") or content.get("items") or content.get("kpis") or [
        {"value": "84%", "label": "Adoption", "icon": "A"},
        {"value": "3.2×", "label": "ROI", "icon": "R"},
        {"value": "12d", "label": "Cycle time", "icon": "T"},
        {"value": "NPS 62", "label": "Loyalty", "icon": "N"},
    ]
    if not isinstance(stats, list):
        stats = []
    stats = stats[:6] or [{"value": "—", "label": "Metric", "icon": "M"}]
    n = len(stats)
    col_w, xs = _grid_n(n, b["margin"], b["gap"], max_n=6)
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "IconStatTitle", title)]
    for i, st in enumerate(stats):
        if isinstance(st, dict):
            val = str(st.get("value") or st.get("metric") or "—")
            label = str(st.get("label") or st.get("name") or f"Metric {i + 1}")
            icon = str(st.get("icon") or st.get("chip") or label[:1]).upper()[:2]
        else:
            val, label, icon = str(st), f"Metric {i + 1}", str(i + 1)
        x = xs[i]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"IconStatChip{i + 1}", "preset": "ellipse",
                "fill": c["accent"], "line": "none", "text": icon,
                "x": _cm(x + col_w / 2 - 1.0), "y": "4.2cm",
                "width": "2.0cm", "height": "2.0cm",
                "font": t["heading_font"], "size": "16",
                "bold": "true", "color": c["on_accent"],
                "align": "center", "valign": "middle",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"IconStatVal{i + 1}", "text": val,
                "x": _cm(x), "y": "6.8cm", "width": _cm(col_w), "height": "2.4cm",
                "font": t["heading_font"],
                "size": str(max(28, min(44, t.get("kpi_pt", 48) - 12))),
                "bold": "true", "color": c["text_on_content"],
                "align": "center", "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"IconStatLabel{i + 1}", "text": label,
                "x": _cm(x), "y": "9.4cm", "width": _cm(col_w), "height": "2.2cm",
                "font": t["body_font"], "size": str(t["body_pt"]),
                "color": c["muted"], "align": "center", "fill": "none",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Lead with the metric that decides the meeting.")},
    })
    return ops


def recipe_scale_rating(tokens: dict, content: dict | None = None) -> list[dict]:
    """Likert / smile-scale rating (Wave 2) — 3–7 points, optional selection."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Rating")
    prompt = str(content.get("prompt") or content.get("question")
                 or "How would you rate the experience?")
    points = content.get("points") or content.get("scale") or [
        "1", "2", "3", "4", "5",
    ]
    if not isinstance(points, list):
        points = [str(points)]
    points = [str(p) for p in points[:7]]
    if len(points) < 3:
        points = ["1", "2", "3", "4", "5"]
    selected = content.get("selected") or content.get("value")
    labels = content.get("labels") or {}
    n = len(points)
    col_w, xs = _grid_n(n, b["margin"], b["gap"] * 0.5, max_n=7)
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "ScaleTitle", title)]
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "ScalePrompt", "text": prompt,
            "x": _cm(b["margin"]), "y": "3.2cm",
            "width": _cm(33.87 - 2 * b["margin"]), "height": "1.6cm",
            "font": t["body_font"], "size": str(t["body_pt"] + 2),
            "color": c["text_on_content"], "fill": "none",
        },
    })
    for i, p in enumerate(points):
        is_sel = selected is not None and str(selected) == p
        fill = c["accent"] if is_sel else c["surface"]
        tc = c["on_accent"] if is_sel else c["text_on_surface"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"ScalePt{i + 1}", "preset": "ellipse",
                "fill": fill, "line": "none", "text": p,
                "x": _cm(xs[i] + col_w / 2 - 1.3), "y": "7.5cm",
                "width": "2.6cm", "height": "2.6cm",
                "font": t["heading_font"], "size": "20",
                "bold": "true", "color": tc,
                "align": "center", "valign": "middle",
            },
        })
        lab = labels.get(p) or labels.get(str(i + 1)) or ""
        if lab:
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"ScaleLab{i + 1}", "text": str(lab),
                    "x": _cm(xs[i]), "y": "10.5cm",
                    "width": _cm(col_w), "height": "1.4cm",
                    "font": t["body_font"], "size": str(_micro_pt(t) + 2),
                    "color": c["muted"], "align": "center", "fill": "none",
                },
            })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "State the action if the score stays below the target.")},
    })
    return ops


def recipe_hub_spoke(tokens: dict, content: dict | None = None) -> list[dict]:
    """Hub-and-spoke / bullseye (Wave 2) — center + 3–6 spokes."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Hub")
    hub = str(content.get("hub") or content.get("center") or "Core")
    spokes = _norm_steps(
        content.get("spokes") or content.get("items") or content.get("steps"),
        min_n=3, max_n=6,
        defaults=[{"label": s} for s in ("North", "East", "South", "West")],
    )
    # Reuse cycle geometry with hub label from content
    return recipe_cycle_loop(tokens, {
        "title": title, "hub": hub, "steps": spokes,
        "notes": content.get("notes", "Name the spoke that is under-resourced."),
    })


def recipe_before_after_slider(tokens: dict, content: dict | None = None) -> list[dict]:
    """Before / after comparison (Wave 2) — two equal panels + divider."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Before → After")
    left = content.get("before") or content.get("left") or {
        "title": "Before", "body": "Current state pain points.",
    }
    right = content.get("after") or content.get("right") or {
        "title": "After", "body": "Target state outcomes.",
    }
    if not isinstance(left, dict):
        left = {"title": "Before", "body": str(left)}
    if not isinstance(right, dict):
        right = {"title": "After", "body": str(right)}
    m = b["margin"]
    usable = 33.87 - 2 * m
    gap = 0.5
    col = (usable - gap) / 2
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "BaTitle", title)]
    for i, (side, data) in enumerate((("Before", left), ("After", right))):
        x = m + i * (col + gap)
        fill = c["surface"] if i == 0 else c["accent"]
        tc = c["text_on_surface"] if i == 0 else c["on_accent"]
        mc = c["muted"] if i == 0 else c["on_accent"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"BaPanel{i + 1}", "preset": b["preset"],
                "fill": fill, "line": "none",
                "x": _cm(x), "y": "3.5cm", "width": _cm(col), "height": "13.8cm",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"BaHead{i + 1}",
                "text": str(data.get("title") or side),
                "x": _cm(x + 0.5), "y": "4.0cm", "width": _cm(col - 1.0), "height": "1.4cm",
                "font": t["heading_font"], "size": str(t["section_pt"]),
                "bold": "true", "color": tc, "fill": "none",
            },
        })
        body = data.get("body") or data.get("text") or ""
        if isinstance(body, list):
            body = "\n".join(f"• {x}" for x in body[:8])
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"BaBody{i + 1}", "text": str(body),
                "x": _cm(x + 0.5), "y": "5.8cm",
                "width": _cm(col - 1.0), "height": "10.5cm",
                "font": t["body_font"], "size": str(t["body_pt"]),
                "color": mc if i == 1 else c["muted"], "fill": "none",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Call the single metric that proves the after state.")},
    })
    return ops


def recipe_calendar_heatmap(tokens: dict, content: dict | None = None) -> list[dict]:
    """Month / week intensity grid (Wave 2) — structured cells, no real calendar API."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Activity calendar")
    subtitle = str(content.get("subtitle") or content.get("month") or "")
    # cells: list of 0-3 intensity or flat list of values
    cells = content.get("cells") or content.get("values") or content.get("days")
    if not isinstance(cells, list) or not cells:
        # 5 weeks × 7 days sample intensities
        cells = [((i * 3 + j) % 4) for i in range(5) for j in range(7)]
    cells = [int(x) if str(x).isdigit() else 0 for x in cells[:42]]
    while len(cells) < 28:
        cells.append(0)
    cols, rows = 7, min(6, max(4, (len(cells) + 6) // 7))
    cells = cells[: cols * rows]
    m = b["margin"]
    usable = 33.87 - 2 * m
    top = 3.6 if not subtitle else 4.2
    cell_gap = 0.12
    cell_w = (usable - cell_gap * (cols - 1)) / cols
    cell_h = min(2.2, (17.8 - top - cell_gap * (rows - 1)) / rows)
    fills = [c["surface"], c.get("chart_series2") or c["muted"], c["accent"], c["accent"]]
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "CalTitle", title)]
    if subtitle:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "CalSub", "text": subtitle,
                "x": _cm(m), "y": "2.8cm", "width": _cm(usable), "height": "0.7cm",
                "font": t["body_font"], "size": str(_micro_pt(t) + 2),
                "color": c["muted"], "fill": "none",
            },
        })
    for i, val in enumerate(cells):
        r, col = divmod(i, cols)
        x = m + col * (cell_w + cell_gap)
        y = top + r * (cell_h + cell_gap)
        level = max(0, min(3, val))
        fill = fills[level]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"CalCell{i + 1}", "preset": b["preset"],
                "fill": fill, "line": "none",
                "text": str(i + 1) if level == 0 else "",
                "x": _cm(x), "y": _cm(y),
                "width": _cm(cell_w), "height": _cm(cell_h),
                "font": t["body_font"], "size": str(_micro_pt(t)),
                "color": c["muted"], "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Point at the densest week and what drove it.")},
    })
    return ops


def recipe_case_study_band(tokens: dict, content: dict | None = None) -> list[dict]:
    """Case study narrative + KPI strip (Wave 2)."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Case study")
    customer = str(content.get("customer") or content.get("client") or "Customer")
    body = str(content.get("body") or content.get("story")
               or "Context → intervention → outcome in three beats.")
    kpis = content.get("kpis") or content.get("results") or [
        {"value": "2.4×", "label": "Pipeline"},
        {"value": "−31%", "label": "Churn"},
        {"value": "NPS +18", "label": "Loyalty"},
    ]
    if not isinstance(kpis, list):
        kpis = []
    kpis = kpis[:4] or [{"value": "—", "label": "Result"}]
    m = b["margin"]
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "CaseTitle", title)]
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "CaseCustomer", "text": customer,
            "x": _cm(m), "y": "2.9cm",
            "width": _cm(33.87 - 2 * m), "height": "0.9cm",
            "font": t["heading_font"], "size": str(max(16, t["section_pt"] - 6)),
            "bold": "true", "color": c["accent"], "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "CaseBody", "text": body,
            "x": _cm(m), "y": "4.0cm",
            "width": _cm(33.87 - 2 * m), "height": "7.5cm",
            "font": t["body_font"], "size": str(t["body_pt"]),
            "color": c["text_on_content"], "fill": "none",
        },
    })
    n = len(kpis)
    col_w, xs = _grid_n(n, m, b["gap"], max_n=4)
    for i, k in enumerate(kpis):
        if isinstance(k, dict):
            val, lab = str(k.get("value", "—")), str(k.get("label", ""))
        else:
            val, lab = str(k), ""
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"CaseKpi{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none",
                "text": f"{val}\n{lab}".strip(),
                "x": _cm(xs[i]), "y": "12.2cm",
                "width": _cm(col_w), "height": "5.0cm",
                "font": t["heading_font"],
                "size": str(max(20, min(32, t.get("kpi_pt", 48) - 20))),
                "bold": "true", "color": c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "One quote from the customer beats three feature bullets.")},
    })
    return ops


def recipe_okrs_tree(tokens: dict, content: dict | None = None) -> list[dict]:
    """OKR tree (Wave 2) — objective + key results."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "OKRs")
    objective = str(content.get("objective") or content.get("o")
                    or "Ship a memorable customer moment this quarter")
    krs = content.get("key_results") or content.get("krs") or content.get("results") or [
        {"label": "KR1", "detail": "Metric target A"},
        {"label": "KR2", "detail": "Metric target B"},
        {"label": "KR3", "detail": "Metric target C"},
    ]
    if not isinstance(krs, list):
        krs = [{"label": str(krs)}]
    krs = _norm_steps(krs, min_n=2, max_n=5)
    m = b["margin"]
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "OkrTitle", title)]
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "OkrObjective", "preset": b["preset"],
            "fill": c["accent"], "line": "none", "text": f"O — {objective}",
            "x": _cm(m), "y": "3.4cm",
            "width": _cm(33.87 - 2 * m), "height": "3.2cm",
            "font": t["heading_font"], "size": str(max(18, t["section_pt"] - 2)),
            "bold": "true", "color": c["on_accent"], "valign": "middle",
        },
    })
    n = len(krs)
    col_w, xs = _grid_n(n, m, b["gap"], max_n=5)
    for i, kr in enumerate(krs):
        text = kr["label"]
        if kr.get("detail"):
            text = f"{kr['label']}\n{kr['detail']}"
        if kr.get("value"):
            text = f"{text}\n{kr['value']}"
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"OkrKr{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none", "text": text,
                "x": _cm(xs[i]), "y": "7.4cm",
                "width": _cm(col_w), "height": "9.8cm",
                "font": t["body_font"], "size": str(max(14, t["body_pt"] - 2)),
                "bold": "true", "color": c["text_on_surface"],
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Kill or rewrite any KR that is not measurable this quarter.")},
    })
    return ops


def recipe_project_status_rag(tokens: dict, content: dict | None = None) -> list[dict]:
    """RAG project status table (Wave 2)."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Project status")
    rows = content.get("rows") or content.get("projects") or content.get("items") or [
        {"name": "Platform", "status": "green", "note": "On track"},
        {"name": "Mobile", "status": "amber", "note": "Hire lag"},
        {"name": "Data", "status": "red", "note": "Schema freeze"},
    ]
    if not isinstance(rows, list):
        rows = []
    rows = rows[:10] or [{"name": "—", "status": "green", "note": ""}]
    rag_fill = {
        "green": c.get("success") or "2F9E44",
        "g": c.get("success") or "2F9E44",
        "amber": c.get("warning") or "D97706",
        "yellow": c.get("warning") or "D97706",
        "a": c.get("warning") or "D97706",
        "red": c.get("risk") or c.get("danger") or "C92A2A",
        "r": c.get("risk") or "C92A2A",
    }
    m = b["margin"]
    usable = 33.87 - 2 * m
    row_h = min(1.7, (14.5) / max(1, len(rows)))
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "RagTitle", title)]
    # header
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "RagHead", "text": "Project          Status          Note",
            "x": _cm(m), "y": "3.3cm", "width": _cm(usable), "height": "0.9cm",
            "font": t["body_font"], "size": str(_micro_pt(t) + 2),
            "bold": "true", "color": c["muted"], "fill": "none",
        },
    })
    for i, row in enumerate(rows):
        if isinstance(row, dict):
            name = str(row.get("name") or row.get("project") or f"Item {i + 1}")
            status = str(row.get("status") or row.get("rag") or "green").lower()
            note = str(row.get("note") or row.get("detail") or "")
        else:
            name, status, note = str(row), "green", ""
        y = 4.4 + i * row_h
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RagRow{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none",
                "x": _cm(m), "y": _cm(y), "width": _cm(usable), "height": _cm(row_h - 0.15),
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RagName{i + 1}", "text": name,
                "x": _cm(m + 0.4), "y": _cm(y + 0.25),
                "width": "10cm", "height": _cm(row_h - 0.5),
                "font": t["body_font"], "size": str(t["body_pt"]),
                "bold": "true", "color": c["text_on_surface"],
                "valign": "middle", "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RagDot{i + 1}", "preset": "ellipse",
                "fill": rag_fill.get(status, rag_fill["green"]), "line": "none",
                "x": _cm(m + 12.0), "y": _cm(y + (row_h - 0.9) / 2),
                "width": "0.9cm", "height": "0.9cm",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RagNote{i + 1}", "text": note,
                "x": _cm(m + 13.5), "y": _cm(y + 0.25),
                "width": _cm(usable - 14.2), "height": _cm(row_h - 0.5),
                "font": t["body_font"], "size": str(max(12, t["body_pt"] - 2)),
                "color": c["muted"], "valign": "middle", "fill": "none",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Red items need an owner and a date before the next review.")},
    })
    return ops


def recipe_finance_statement(tokens: dict, content: dict | None = None) -> list[dict]:
    """Finance statement table + insight rail (Wave 2)."""
    content = dict(content or {})
    content.setdefault("title", content.get("title") or "Financial summary")
    content.setdefault("headers", content.get("headers") or ["Line", "Actual", "Plan", "Δ"])
    content.setdefault("rows", content.get("rows") or [
        ["Revenue", "42.1", "40.0", "+5%"],
        ["COGS", "12.4", "12.0", "+3%"],
        ["Gross profit", "29.7", "28.0", "+6%"],
        ["Opex", "18.2", "17.5", "+4%"],
        ["Op. income", "11.5", "10.5", "+10%"],
    ])
    content.setdefault(
        "insight",
        content.get("insight") or content.get("insight_body")
        or "Operating leverage improved as revenue outgrew opex.",
    )
    content.setdefault("insight_title", content.get("insight_title") or "Takeaway")
    # Build table ops then add insight panel on the right via results_table_insight style
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    title = content["title"]
    headers = content["headers"]
    rows = content["rows"]
    if not isinstance(headers, list):
        headers = ["Item", "Value"]
    if not isinstance(rows, list):
        rows = []
    rows = rows[:10]
    m = b["margin"]
    table_w = 20.5
    n_cols = max(1, len(headers))
    col_w = (table_w - 0.2 * (n_cols - 1)) / n_cols
    start_y, row_h = 3.5, 1.25
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "FinTitle", title)]
    for j, h in enumerate(headers):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"FinHead{j + 1}", "preset": b["preset"],
                "fill": c["accent"], "line": "none", "text": str(h),
                "x": _cm(m + j * (col_w + 0.2)), "y": _cm(start_y),
                "width": _cm(col_w), "height": _cm(row_h),
                "font": t["body_font"], "size": str(max(12, t["body_pt"] - 4)),
                "bold": "true", "color": c["on_accent"],
                "align": "center", "valign": "middle",
            },
        })
    for i, row in enumerate(rows):
        cells = row if isinstance(row, list) else [row]
        for j in range(n_cols):
            val = cells[j] if j < len(cells) else ""
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"FinCell{i + 1}_{j + 1}", "preset": b["preset"],
                    "fill": c["surface"], "line": "none", "text": str(val),
                    "x": _cm(m + j * (col_w + 0.2)),
                    "y": _cm(start_y + (i + 1) * row_h),
                    "width": _cm(col_w), "height": _cm(row_h),
                    "font": t["body_font"], "size": str(max(12, t["body_pt"] - 4)),
                    "color": c["text_on_surface"],
                    "align": "center", "valign": "middle",
                },
            })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "FinInsightBg", "preset": b["preset"],
            "fill": c["surface"], "line": "none",
            "x": "22.8cm", "y": "3.5cm", "width": "9.5cm", "height": "14.0cm",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "FinInsightTitle", "text": str(content["insight_title"]),
            "x": "23.3cm", "y": "4.0cm", "width": "8.5cm", "height": "1.2cm",
            "font": t["heading_font"], "size": str(max(16, t["section_pt"] - 6)),
            "bold": "true", "color": c["text_on_surface"], "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "FinInsightBody", "text": str(content["insight"]),
            "x": "23.3cm", "y": "5.5cm", "width": "8.5cm", "height": "11.0cm",
            "font": t["body_font"], "size": str(t["body_pt"]),
            "color": c["muted"], "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "One line of narrative beats reading every cell aloud.")},
    })
    return ops


def recipe_pipeline_stages(tokens: dict, content: dict | None = None) -> list[dict]:
    """Sales / delivery pipeline (Wave 2) — equal stages with counts."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Pipeline")
    stages = _norm_steps(
        content.get("stages") or content.get("steps") or content.get("items"),
        min_n=3, max_n=6,
        defaults=[
            {"label": "Lead", "value": "120"},
            {"label": "SQL", "value": "48"},
            {"label": "Opp", "value": "22"},
            {"label": "Won", "value": "9"},
        ],
    )
    n = len(stages)
    col_w, xs = _grid_n(n, b["margin"], 0.25, max_n=6)
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "PipeTitle", title)]
    y, h = 5.5, 9.5
    for i, st in enumerate(stages):
        fill = c["accent"] if i == n - 1 else c["surface"]
        tc = c["on_accent"] if i == n - 1 else c["text_on_surface"]
        text = st["label"]
        if st.get("value"):
            text = f"{st['value']}\n{st['label']}"
        if st.get("detail"):
            text = f"{text}\n{st['detail']}"
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"PipeStage{i + 1}", "preset": b["preset"],
                "fill": fill, "line": "none", "text": text,
                "x": _cm(xs[i]), "y": _cm(y),
                "width": _cm(col_w), "height": _cm(h),
                "font": t["heading_font"],
                "size": str(max(16, min(28, t["section_pt"]))),
                "bold": "true", "color": tc,
                "align": "center", "valign": "middle",
            },
        })
        if i < n - 1:
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"PipeArrow{i + 1}", "preset": "rightArrow",
                    "fill": c["muted"], "line": "none",
                    "x": _cm(xs[i] + col_w - 0.15), "y": _cm(y + h / 2 - 0.35),
                    "width": "0.55cm", "height": "0.7cm",
                },
            })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Name the biggest conversion drop between adjacent stages.")},
    })
    return ops


def recipe_geo_callout(tokens: dict, content: dict | None = None) -> list[dict]:
    """Map placeholder + callout cards (Wave 2) — user supplies map image; no basemap."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Regions")
    src = str(content.get("src") or content.get("map") or "")
    alt = str(content.get("alt") or "Geographic overview map")
    callouts = content.get("callouts") or content.get("regions") or [
        {"label": "Americas", "detail": "42%"},
        {"label": "EMEA", "detail": "35%"},
        {"label": "APAC", "detail": "23%"},
    ]
    if not isinstance(callouts, list):
        callouts = []
    callouts = callouts[:5] or [{"label": "Region", "detail": ""}]
    m = b["margin"]
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "GeoTitle", title)]
    # Map area (picture if src, else placeholder)
    if src:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "picture",
            "props": {
                "name": "GeoMap", "src": src, "alt": alt,
                "x": _cm(m), "y": "3.4cm",
                "width": "20cm", "height": "14.2cm",
            },
        })
    else:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "GeoMapPlaceholder", "preset": b["preset"],
                "fill": c["surface"], "line": "none",
                "text": alt + "\n(set content.src to your map image)",
                "x": _cm(m), "y": "3.4cm",
                "width": "20cm", "height": "14.2cm",
                "font": t["body_font"], "size": str(t["body_pt"]),
                "color": c["muted"], "align": "center", "valign": "middle",
            },
        })
    cy = 3.4
    for i, co in enumerate(callouts):
        if isinstance(co, dict):
            text = f"{co.get('label', 'Region')}\n{co.get('detail') or co.get('value') or ''}".strip()
        else:
            text = str(co)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"GeoCallout{i + 1}", "preset": b["preset"],
                "fill": c["accent"] if i == 0 else c["surface"], "line": "none",
                "text": text,
                "x": "22.3cm", "y": _cm(cy),
                "width": "9.8cm", "height": "2.5cm",
                "font": t["body_font"], "size": str(max(14, t["body_pt"] - 2)),
                "bold": "true",
                "color": c["on_accent"] if i == 0 else c["text_on_surface"],
                "valign": "middle",
            },
        })
        cy += 2.7
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Never ship vendor basemap art — only user-owned map assets.")},
    })
    return ops


def recipe_device_frame(tokens: dict, content: dict | None = None) -> list[dict]:
    """Device frame slot (Wave 2) — chrome frame; user supplies screen image."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Product surface")
    body = str(content.get("body") or content.get("caption")
               or "Describe the UI moment. Provide src for the screenshot.")
    src = str(content.get("src") or "")
    alt = str(content.get("alt") or "Product screenshot")
    device = str(content.get("device") or "phone").lower()
    m = b["margin"]
    # Frame dimensions
    if device in ("laptop", "desktop", "browser"):
        fx, fy, fw, fh = m + 0.5, 3.6, 18.5, 13.5
        pad = 0.45
    else:
        fx, fy, fw, fh = m + 4.5, 3.5, 10.5, 14.0
        pad = 0.55
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "DevTitle", title)]
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "DeviceChrome", "preset": b["preset"],
            "fill": c["surface"], "line": "none",
            "x": _cm(fx), "y": _cm(fy), "width": _cm(fw), "height": _cm(fh),
        },
    })
    if src:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "picture",
            "props": {
                "name": "DeviceScreen", "src": src, "alt": alt,
                "x": _cm(fx + pad), "y": _cm(fy + pad),
                "width": _cm(fw - 2 * pad), "height": _cm(fh - 2 * pad),
            },
        })
    else:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "DeviceScreenPh", "preset": "rect",
                "fill": c["content_background"], "line": "none",
                "text": alt + "\n(set content.src)",
                "x": _cm(fx + pad), "y": _cm(fy + pad),
                "width": _cm(fw - 2 * pad), "height": _cm(fh - 2 * pad),
                "font": t["body_font"], "size": str(_micro_pt(t) + 2),
                "color": c["muted"], "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "DeviceBody", "text": body,
            "x": "21.5cm", "y": "4.0cm", "width": "10.8cm", "height": "12.5cm",
            "font": t["body_font"], "size": str(t["body_pt"]),
            "color": c["text_on_content"], "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Only user-owned screenshots — never vendor mockup photo packs.")},
    })
    return ops


# ---------------------------------------------------------------------------
# Wave 4 — Infograpify long-tail structural roles (filename + geometry analysis)
# Mind maps, journey, PESTLE, RACI, scorecard, hex, puzzle, pillars, stairs,
# checklist, empathy map, risk matrix, circle segments, mission/vision.
# Original geometry only — never vendor bytes.
# ---------------------------------------------------------------------------

def recipe_mindmap_branches(tokens: dict, content: dict | None = None) -> list[dict]:
    """Mind map (Wave 4) — center hub + 4–8 radial branches."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Mind map")
    hub = str(content.get("hub") or content.get("center") or content.get("topic") or "Core idea")
    branches = _norm_steps(
        content.get("branches") or content.get("nodes") or content.get("items")
        or content.get("steps"),
        min_n=4, max_n=8,
        defaults=[{"label": s} for s in ("Theme A", "Theme B", "Theme C", "Theme D", "Theme E", "Theme F")],
    )
    n = len(branches)
    cx, cy, r = 16.9, 11.2, 6.4
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "MindTitle", title)]
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "MindHub", "preset": "ellipse",
            "fill": c["accent"], "line": "none", "text": hub,
            "x": _cm(cx - 3.0), "y": _cm(cy - 1.8),
            "width": "6.0cm", "height": "3.6cm",
            "font": t["heading_font"], "size": str(max(16, t["section_pt"] - 2)),
            "bold": "true", "color": c["on_accent"],
            "align": "center", "valign": "middle",
        },
    })
    nw, nh = 5.6, 2.2
    for i, br in enumerate(branches):
        ang = -math.pi / 2 + (2 * math.pi * i / n)
        x = cx + r * math.cos(ang) - nw / 2
        y = cy + r * math.sin(ang) * 0.68 - nh / 2
        x = max(b["margin"], min(33.87 - b["margin"] - nw, x))
        y = max(3.2, min(17.6 - nh, y))
        label = br["label"]
        if br.get("detail"):
            label = f"{label}\n{br['detail']}"
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"MindBranch{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none", "text": label,
                "x": _cm(x), "y": _cm(y), "width": _cm(nw), "height": _cm(nh),
                "font": t["body_font"], "size": str(max(14, min(18, t["body_pt"]))),
                "bold": "true", "color": c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "One branch = one discussion thread; prune to ≤8.")},
    })
    return ops


def recipe_journey_stages(tokens: dict, content: dict | None = None) -> list[dict]:
    """Customer / user journey (Wave 4) — staged swim of moments + emotion."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Journey")
    stages = _norm_steps(
        content.get("stages") or content.get("steps") or content.get("moments"),
        min_n=3, max_n=6,
        defaults=[
            {"label": "Aware", "detail": "Discover"},
            {"label": "Consider", "detail": "Compare"},
            {"label": "Decide", "detail": "Choose"},
            {"label": "Use", "detail": "Adopt"},
            {"label": "Advocate", "detail": "Share"},
        ],
    )
    n = len(stages)
    # Leave a left gutter for Action/Emotion lane labels so they are not
    # covered by the first stage column (airier DESIGN.md margins).
    lane_w = 2.6
    col_w, xs = _grid_n(n, b["margin"] + lane_w + 0.25, 0.3, max_n=6)
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "JourneyTitle", title)]
    # Lane labels
    for lane_i, lane in enumerate(("Action", "Emotion")):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"JourneyLane{lane_i}", "text": lane,
                "x": _cm(b["margin"]), "y": _cm(7.5 + lane_i * 5.5),
                "width": _cm(lane_w), "height": "1.2cm",
                "font": t["body_font"], "size": str(_micro_pt(t) + 2),
                "bold": "true", "color": c["muted"], "fill": "none",
            },
        })
    for i, st in enumerate(stages):
        emo = st.get("emotion") or st.get("feeling") or ("🙂" if i < n - 1 else "🤩")
        # Stage header
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"JourneyHead{i + 1}", "preset": b["preset"],
                "fill": c["accent"] if i == 0 else c["surface"], "line": "none",
                "text": st["label"],
                "x": _cm(xs[i]), "y": "3.6cm",
                "width": _cm(col_w), "height": "2.0cm",
                "font": t["heading_font"], "size": str(max(14, t["body_pt"])),
                "bold": "true",
                "color": c["on_accent"] if i == 0 else c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"JourneyAct{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none",
                "text": st.get("detail") or st.get("action") or "—",
                "x": _cm(xs[i]), "y": "6.0cm",
                "width": _cm(col_w), "height": "5.2cm",
                "font": t["body_font"], "size": str(max(14, t["body_pt"] - 2)),
                "color": c["text_on_surface"], "align": "center", "valign": "middle",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"JourneyEmo{i + 1}", "preset": b["preset"],
                "fill": c["content_background"], "line": "none",
                "text": str(emo),
                "x": _cm(xs[i]), "y": "11.6cm",
                "width": _cm(col_w), "height": "4.5cm",
                "font": t["body_font"], "size": "28",
                "color": c["text_on_content"], "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Call the biggest emotion drop — that is the intervention.")},
    })
    return ops


def recipe_pestle_grid(tokens: dict, content: dict | None = None) -> list[dict]:
    """PESTLE / PESTEL 6-cell strategy scan (Wave 4)."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "PESTLE scan")
    labels = ["Political", "Economic", "Social", "Technological", "Legal", "Environmental"]
    keys = ["political", "economic", "social", "technological", "legal", "environmental"]
    cells: list[tuple[str, str]] = []
    raw = content.get("cells") or content.get("factors")
    if isinstance(raw, list) and raw:
        for i, item in enumerate(raw[:6]):
            if isinstance(item, dict):
                cells.append((
                    str(item.get("label") or labels[i]),
                    str(item.get("body") or item.get("text") or ""),
                ))
            else:
                cells.append((labels[i], str(item)))
    else:
        for i, k in enumerate(keys):
            val = content.get(k) or content.get(k[:4])
            body = ""
            if isinstance(val, list):
                body = "\n".join(f"• {x}" for x in val[:4])
            elif isinstance(val, dict):
                body = str(val.get("body") or val.get("text") or "")
            elif val:
                body = str(val)
            cells.append((labels[i], body or "• …"))
    while len(cells) < 6:
        cells.append((labels[len(cells)], "• …"))
    m = b["margin"]
    gap = 0.35
    usable_w = 33.87 - 2 * m
    usable_h = 14.5
    cw, ch = (usable_w - 2 * gap) / 3, (usable_h - gap) / 2
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "PestleTitle", title)]
    for i, (lab, body) in enumerate(cells[:6]):
        col, row = i % 3, i // 3
        x = m + col * (cw + gap)
        y = 3.5 + row * (ch + gap)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Pestle{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none",
                "x": _cm(x), "y": _cm(y), "width": _cm(cw), "height": _cm(ch),
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"PestleLab{i + 1}", "text": lab,
                "x": _cm(x + 0.35), "y": _cm(y + 0.3),
                "width": _cm(cw - 0.7), "height": "1.1cm",
                "font": t["heading_font"], "size": str(max(16, t["body_pt"])),
                "bold": "true", "color": c["accent"], "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"PestleBody{i + 1}", "text": body,
                "x": _cm(x + 0.35), "y": _cm(y + 1.5),
                "width": _cm(cw - 0.7), "height": _cm(ch - 2.0),
                "font": t["body_font"], "size": str(max(14, t["body_pt"] - 2)),
                "color": c["text_on_surface"], "fill": "none",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Mark the two factors that change the plan this quarter.")},
    })
    return ops


def recipe_raci_matrix(tokens: dict, content: dict | None = None) -> list[dict]:
    """RACI responsibility matrix (Wave 4) — activities × roles."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "RACI")
    roles = content.get("roles") or ["Exec", "PM", "Eng", "Design", "Ops"]
    if not isinstance(roles, list):
        roles = [str(roles)]
    roles = [str(r) for r in roles[:6]]
    activities = content.get("activities") or content.get("rows") or [
        {"name": "Scope", "raci": ["A", "R", "C", "C", "I"]},
        {"name": "Build", "raci": ["I", "A", "R", "C", "C"]},
        {"name": "Launch", "raci": ["A", "R", "C", "C", "R"]},
    ]
    m = b["margin"]
    n_roles = len(roles)
    name_w = 6.5
    usable = 33.87 - 2 * m - name_w
    col_w = usable / max(1, n_roles)
    row_h = 2.0
    start_y = 4.0
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "RaciTitle", title)]
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "RaciCorner", "preset": b["preset"],
            "fill": c["accent"], "line": "none", "text": "Activity",
            "x": _cm(m), "y": _cm(start_y), "width": _cm(name_w), "height": _cm(row_h),
            "font": t["body_font"], "size": str(max(12, t["body_pt"] - 4)),
            "bold": "true", "color": c["on_accent"],
            "align": "center", "valign": "middle",
        },
    })
    for j, role in enumerate(roles):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RaciRole{j + 1}", "preset": b["preset"],
                "fill": c["accent"], "line": "none", "text": role,
                "x": _cm(m + name_w + j * col_w), "y": _cm(start_y),
                "width": _cm(col_w - 0.1), "height": _cm(row_h),
                "font": t["body_font"], "size": str(max(12, t["body_pt"] - 4)),
                "bold": "true", "color": c["on_accent"],
                "align": "center", "valign": "middle",
            },
        })
    # Cap rows so header + rows stay within 16:9 canvas under contract load.
    max_rows = 5
    act_list = list(activities)[:max_rows]
    row_h = min(2.0, (14.5) / (len(act_list) + 1))
    for i, act in enumerate(act_list):
        if isinstance(act, dict):
            name = str(act.get("name") or act.get("label") or f"Task {i + 1}")
            cells = act.get("raci") or act.get("cells") or []
        elif isinstance(act, list):
            name, cells = str(act[0]), act[1:]
        else:
            name, cells = str(act), []
        y = start_y + (i + 1) * row_h
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RaciAct{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none", "text": name,
                "x": _cm(m), "y": _cm(y), "width": _cm(name_w), "height": _cm(row_h),
                "font": t["body_font"], "size": str(max(12, t["body_pt"] - 4)),
                "bold": "true", "color": c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
        for j in range(n_roles):
            letter = str(cells[j] if j < len(cells) else "—")[:2]
            fill = c["accent"] if letter.upper() in ("R", "A") else c["surface"]
            tc = c["on_accent"] if letter.upper() in ("R", "A") else c["text_on_surface"]
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"RaciCell{i + 1}_{j + 1}", "preset": b["preset"],
                    "fill": fill, "line": "none", "text": letter.upper(),
                    "x": _cm(m + name_w + j * col_w), "y": _cm(y),
                    "width": _cm(col_w - 0.1), "height": _cm(row_h),
                    "font": t["heading_font"], "size": str(max(14, t["body_pt"] - 2)),
                    "bold": "true", "color": tc,
                    "align": "center", "valign": "middle",
                },
            })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Exactly one A per row; R does the work.")},
    })
    return ops


def recipe_scorecard_balanced(tokens: dict, content: dict | None = None) -> list[dict]:
    """Balanced scorecard (Wave 4) — 4 perspective cards with metrics."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Balanced scorecard")
    defaults = [
        ("Financial", "Revenue, margin, cash"),
        ("Customer", "NPS, retention, win rate"),
        ("Internal", "Cycle time, quality"),
        ("Learning", "Skills, experiments"),
    ]
    perspectives = content.get("perspectives") or content.get("cards") or content.get("quadrants")
    cards: list[dict] = []
    if isinstance(perspectives, list) and perspectives:
        for i, p in enumerate(perspectives[:4]):
            if isinstance(p, dict):
                cards.append({
                    "label": str(p.get("label") or p.get("title") or defaults[i][0]),
                    "body": str(p.get("body") or p.get("metrics") or p.get("text") or defaults[i][1]),
                })
            else:
                cards.append({"label": defaults[i][0], "body": str(p)})
    else:
        cards = [{"label": a, "body": b_} for a, b_ in defaults]
    while len(cards) < 4:
        cards.append({"label": defaults[len(cards)][0], "body": defaults[len(cards)][1]})
    m = b["margin"]
    gap = 0.4
    cw = (33.87 - 2 * m - gap) / 2
    ch = 6.4
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "BscTitle", title)]
    for i, card in enumerate(cards[:4]):
        col, row = i % 2, i // 2
        x = m + col * (cw + gap)
        y = 3.6 + row * (ch + gap)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"BscCard{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none",
                "x": _cm(x), "y": _cm(y), "width": _cm(cw), "height": _cm(ch),
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"BscLab{i + 1}", "text": card["label"],
                "x": _cm(x + 0.5), "y": _cm(y + 0.4),
                "width": _cm(cw - 1.0), "height": "1.2cm",
                "font": t["heading_font"], "size": str(t["section_pt"]),
                "bold": "true", "color": c["accent"], "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"BscBody{i + 1}", "text": card["body"],
                "x": _cm(x + 0.5), "y": _cm(y + 1.8),
                "width": _cm(cw - 1.0), "height": _cm(ch - 2.4),
                "font": t["body_font"], "size": str(t["body_pt"]),
                "color": c["text_on_surface"], "fill": "none",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Tie each metric to one owner and one review cadence.")},
    })
    return ops


def recipe_hex_cluster(tokens: dict, content: dict | None = None) -> list[dict]:
    """Honeycomb / hex cluster (Wave 4) — 5–7 tiles around a center."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Cluster")
    items = _norm_steps(
        content.get("items") or content.get("tiles") or content.get("cells"),
        min_n=5, max_n=7,
        defaults=[{"label": s} for s in ("Core", "A", "B", "C", "D", "E", "F")],
    )
    # Approximate hex with roundRect tiles in honeycomb packing
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "HexTitle", title)]
    # positions relative (cx, cy) for 7 hex: center + 6 ring
    cx, cy = 16.9, 11.0
    s = 3.4  # tile half-span
    coords = [(0.0, 0.0)]
    for i in range(6):
        ang = math.pi / 6 + i * math.pi / 3
        coords.append((math.cos(ang) * 2.1 * s, math.sin(ang) * 1.55 * s))
    for i, (item, (dx, dy)) in enumerate(zip(items, coords)):
        fill = c["accent"] if i == 0 else c["surface"]
        tc = c["on_accent"] if i == 0 else c["text_on_surface"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Hex{i + 1}", "preset": b["preset"],
                "fill": fill, "line": "none", "text": item["label"],
                "x": _cm(cx + dx - s), "y": _cm(cy + dy - s * 0.7),
                "width": _cm(2 * s), "height": _cm(1.5 * s),
                "font": t["body_font"],
                "size": str(max(14, t["body_pt"] if i else t["section_pt"] - 4)),
                "bold": "true", "color": tc,
                "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Center is the organising idea; ring tiles are facets.")},
    })
    return ops


def recipe_puzzle_pieces(tokens: dict, content: dict | None = None) -> list[dict]:
    """Puzzle / interlocking pieces (Wave 4) — 3–6 complementary parts."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Fit")
    pieces = _norm_steps(
        content.get("pieces") or content.get("parts") or content.get("items"),
        min_n=3, max_n=6,
        defaults=[{"label": s} for s in ("Product", "GTM", "Ops", "People")],
    )
    n = len(pieces)
    col_w, xs = _grid_n(n, b["margin"], 0.35, max_n=6)
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "PuzzleTitle", title)]
    for i, pc in enumerate(pieces):
        text = pc["label"]
        if pc.get("detail"):
            text = f"{text}\n{pc['detail']}"
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Puzzle{i + 1}", "preset": b["preset"],
                "fill": c["accent"] if i % 2 == 0 else c["surface"],
                "line": "none", "text": text,
                "x": _cm(xs[i]), "y": "5.0cm",
                "width": _cm(col_w), "height": "10.5cm",
                "font": t["heading_font"],
                "size": str(max(16, min(24, t["section_pt"]))),
                "bold": "true",
                "color": c["on_accent"] if i % 2 == 0 else c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Name what breaks if any single piece is missing.")},
    })
    return ops


def recipe_pillar_columns(tokens: dict, content: dict | None = None) -> list[dict]:
    """Pillars / foundational columns (Wave 4) — 3–5 vertical pillars."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Pillars")
    pillars = _norm_steps(
        content.get("pillars") or content.get("columns") or content.get("items"),
        min_n=3, max_n=5,
        defaults=[{"label": s, "detail": "Foundation"} for s in ("Trust", "Speed", "Craft")],
    )
    n = len(pillars)
    col_w, xs = _grid_n(n, b["margin"], 0.5, max_n=5)
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "PillarTitle", title)]
    base_y, max_h = 16.5, 11.5
    for i, p in enumerate(pillars):
        h = max_h - i * 0.4  # slight variation
        y = base_y - h
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Pillar{i + 1}", "preset": b["preset"],
                "fill": c["accent"] if i == 0 else c["surface"],
                "line": "none",
                "text": f"{p['label']}\n\n{p.get('detail') or ''}",
                "x": _cm(xs[i]), "y": _cm(y),
                "width": _cm(col_w), "height": _cm(h),
                "font": t["heading_font"],
                "size": str(max(16, t["section_pt"] - 4)),
                "bold": "true",
                "color": c["on_accent"] if i == 0 else c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Pillars are non-negotiable investments, not initiatives.")},
    })
    return ops


def recipe_stairs_ascent(tokens: dict, content: dict | None = None) -> list[dict]:
    """Ascending stairs / maturity steps (Wave 4)."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Ascent")
    steps = _norm_steps(
        content.get("steps") or content.get("levels") or content.get("stages"),
        min_n=3, max_n=6,
        defaults=[{"label": s} for s in ("Aware", "Repeatable", "Defined", "Managed", "Optimising")],
    )
    n = len(steps)
    m = b["margin"]
    usable = 33.87 - 2 * m
    step_w = usable / n
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "StairsTitle", title)]
    base_y = 16.8
    for i, st in enumerate(steps):
        h = 3.5 + i * (9.5 / max(1, n - 1))
        y = base_y - h
        x = m + i * step_w
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Stair{i + 1}", "preset": b["preset"],
                "fill": c["accent"] if i == n - 1 else c["surface"],
                "line": "none",
                "text": f"{i + 1}. {st['label']}",
                "x": _cm(x + 0.1), "y": _cm(y),
                "width": _cm(step_w - 0.2), "height": _cm(h),
                "font": t["body_font"],
                "size": str(max(14, min(20, t["body_pt"]))),
                "bold": "true",
                "color": c["on_accent"] if i == n - 1 else c["text_on_surface"],
                "align": "center", "valign": "top",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "You cannot skip a stair — name the exit criteria per step.")},
    })
    return ops


def recipe_checklist_board(tokens: dict, content: dict | None = None) -> list[dict]:
    """Checklist / launch readiness board (Wave 4)."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Checklist")
    items = content.get("items") or content.get("checks") or content.get("bullets") or [
        {"label": "Scope locked", "done": True},
        {"label": "Legal review", "done": True},
        {"label": "Support ready", "done": False},
        {"label": "Comms sent", "done": False},
        {"label": "Metrics live", "done": False},
    ]
    if not isinstance(items, list):
        items = [{"label": str(items)}]
    norm: list[dict] = []
    for it in items[:10]:
        if isinstance(it, dict):
            norm.append({
                "label": str(it.get("label") or it.get("text") or it.get("title") or "Item"),
                "done": bool(it.get("done") or it.get("checked") or it.get("status") in ("done", "ok", "yes")),
            })
        else:
            s = str(it)
            done = s.startswith("[x]") or s.startswith("✓")
            norm.append({"label": s.lstrip("[x]✓ ").strip(), "done": done})
    m = b["margin"]
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "CheckTitle", title)]
    row_h = min(1.9, 14.0 / max(1, len(norm)))
    for i, it in enumerate(norm):
        y = 3.6 + i * row_h
        mark = "✓" if it["done"] else "○"
        fill = c["surface"] if it["done"] else c["content_background"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"CheckRow{i + 1}", "preset": b["preset"],
                "fill": fill, "line": "none",
                "text": f"{mark}  {it['label']}",
                "x": _cm(m), "y": _cm(y),
                "width": _cm(33.87 - 2 * m), "height": _cm(row_h - 0.15),
                "font": t["body_font"], "size": str(t["body_pt"]),
                "bold": "true" if not it["done"] else "false",
                "color": c["text_on_surface"], "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Open items need an owner before the meeting ends.")},
    })
    return ops


def recipe_empathy_map_quad(tokens: dict, content: dict | None = None) -> list[dict]:
    """Empathy map (Wave 4) — Says / Thinks / Does / Feels around a user."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Empathy map")
    user = str(content.get("user") or content.get("persona") or content.get("name") or "User")
    quads = [
        ("Says", content.get("says") or content.get("say") or "• Quotes from interviews"),
        ("Thinks", content.get("thinks") or content.get("think") or "• Private worries / hopes"),
        ("Does", content.get("does") or content.get("do") or "• Observable behaviours"),
        ("Feels", content.get("feels") or content.get("feel") or "• Emotional state"),
    ]
    # Allow quads list override
    if isinstance(content.get("quadrants"), list) and len(content["quadrants"]) >= 4:
        q = content["quadrants"]
        quads = []
        for i, lab in enumerate(("Says", "Thinks", "Does", "Feels")):
            item = q[i]
            if isinstance(item, dict):
                quads.append((str(item.get("label") or lab),
                              str(item.get("body") or item.get("text") or "")))
            else:
                quads.append((lab, str(item)))
    m = b["margin"]
    gap = 0.35
    cw = (33.87 - 2 * m - gap) / 2
    # Keep quads clear of the center user chip (chip sits in the cross).
    ch = 5.6
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "EmpTitle", title)]
    # Short user label — long names overflow the ellipse and trip issues gate.
    user_label = user if len(user) <= 18 else (user[:16] + "…")
    lab_pt = min(20, max(14, int(t.get("body_pt", 18))))
    positions = [
        (m, 3.5), (m + cw + gap, 3.5),
        (m, 3.5 + ch + gap), (m + cw + gap, 3.5 + ch + gap),
    ]
    for i, ((lab, body), (x, y)) in enumerate(zip(quads, positions)):
        if isinstance(body, list):
            body = "\n".join(f"• {x}" for x in body[:5])
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"EmpQ{i + 1}", "preset": b["preset"],
                "fill": c["surface"], "line": "none",
                "x": _cm(x), "y": _cm(y), "width": _cm(cw), "height": _cm(ch),
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"EmpLab{i + 1}", "text": lab,
                "x": _cm(x + 0.4), "y": _cm(y + 0.3),
                "width": _cm(cw - 0.8), "height": "1.2cm",
                "font": t["heading_font"], "size": str(lab_pt),
                "bold": "true", "color": c["accent"], "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"EmpBody{i + 1}", "text": str(body),
                "x": _cm(x + 0.4), "y": _cm(y + 1.5),
                "width": _cm(cw - 0.8), "height": _cm(ch - 2.0),
                "font": t["body_font"], "size": str(max(14, t["body_pt"] - 2)),
                "color": c["text_on_surface"], "fill": "none",
            },
        })
    # User chip last so it stays on top of the four panels without hiding labels.
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "EmpUser", "preset": "ellipse",
            "fill": c["accent"], "line": "none", "text": user_label,
            "x": "14.4cm", "y": "8.6cm", "width": "5.0cm", "height": "3.0cm",
            "font": t["heading_font"], "size": str(max(14, t["body_pt"] - 2)),
            "bold": "true", "color": c["on_accent"],
            "align": "center", "valign": "middle",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Prefer evidence over stereotypes in every quadrant.")},
    })
    return ops


def recipe_risk_heat_matrix(tokens: dict, content: dict | None = None) -> list[dict]:
    """Risk heat matrix (Wave 4) — likelihood × impact grid with items."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Risk matrix")
    # 3×3 cells; items place by likelihood/impact 1–3
    items = content.get("risks") or content.get("items") or [
        {"label": "Vendor delay", "likelihood": 2, "impact": 3},
        {"label": "Scope creep", "likelihood": 3, "impact": 2},
        {"label": "Key person", "likelihood": 1, "impact": 3},
        {"label": "Reg change", "likelihood": 1, "impact": 2},
    ]
    m = b["margin"]
    # Left labels + bottom labels
    grid_x, grid_y = m + 3.2, 4.0
    grid_w, grid_h = 22.0, 12.5
    cell_w, cell_h = grid_w / 3, grid_h / 3
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "RiskTitle", title)]
    # axis labels
    for i, lab in enumerate(("Low", "Med", "High")):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RiskX{i}", "text": lab,
                "x": _cm(grid_x + i * cell_w), "y": _cm(grid_y + grid_h + 0.15),
                "width": _cm(cell_w), "height": "0.9cm",
                "font": t["body_font"], "size": str(_micro_pt(t) + 2),
                "color": c["muted"], "align": "center", "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RiskY{i}", "text": lab,
                "x": _cm(m), "y": _cm(grid_y + (2 - i) * cell_h + cell_h / 2 - 0.4),
                "width": "3.0cm", "height": "0.9cm",
                "font": t["body_font"], "size": str(_micro_pt(t) + 2),
                "color": c["muted"], "align": "right", "fill": "none",
            },
        })
    # heat cells (background)
    heat = [
        [c["surface"], c["surface"], c.get("chart_series2") or c["muted"]],
        [c["surface"], c.get("chart_series2") or c["muted"], c["accent"]],
        [c.get("chart_series2") or c["muted"], c["accent"], c["accent"]],
    ]
    for iy in range(3):
        for ix in range(3):
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"RiskCell{iy}{ix}", "preset": "rect",
                    "fill": heat[iy][ix], "line": "none",
                    "x": _cm(grid_x + ix * cell_w + 0.05),
                    "y": _cm(grid_y + (2 - iy) * cell_h + 0.05),
                    "width": _cm(cell_w - 0.1), "height": _cm(cell_h - 0.1),
                },
            })
    # place risk labels (clamp 1–3)
    buckets: dict[tuple[int, int], list[str]] = {}
    for it in items[:12]:
        if not isinstance(it, dict):
            continue
        L = max(1, min(3, int(it.get("likelihood") or it.get("x") or 2)))
        I = max(1, min(3, int(it.get("impact") or it.get("y") or 2)))
        buckets.setdefault((L, I), []).append(str(it.get("label") or it.get("name") or "Risk"))
    for (L, I), labels in buckets.items():
        text = "\n".join(labels[:3])
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RiskItem{L}{I}", "text": text,
                "x": _cm(grid_x + (L - 1) * cell_w + 0.25),
                "y": _cm(grid_y + (3 - I) * cell_h + 0.3),
                "width": _cm(cell_w - 0.5), "height": _cm(cell_h - 0.5),
                "font": t["body_font"], "size": str(max(12, t["body_pt"] - 4)),
                "bold": "true", "color": c["text"], "fill": "none",
                "align": "center", "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "RiskAxisX", "text": "Likelihood →",
            "x": _cm(grid_x), "y": "18.0cm", "width": _cm(grid_w), "height": "0.7cm",
            "font": t["body_font"], "size": str(_micro_pt(t)),
            "color": c["muted"], "align": "center", "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Top-right cells need owners this week.")},
    })
    return ops


def recipe_circle_segments(tokens: dict, content: dict | None = None) -> list[dict]:
    """Segmented circle / ring legend (Wave 4) — 3–6 segments as legend cards."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Segments")
    segs = _norm_steps(
        content.get("segments") or content.get("parts") or content.get("items"),
        min_n=3, max_n=6,
        defaults=[
            {"label": "Acquire", "value": "32%"},
            {"label": "Activate", "value": "28%"},
            {"label": "Retain", "value": "24%"},
            {"label": "Refer", "value": "16%"},
        ],
    )
    n = len(segs)
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "CircTitle", title)]
    center = str(content.get("center") or content.get("hub") or "100%")
    # Center disc (placeholder for donut — officecli has no pie slice API in shapes).
    # Put the hub label on the inner hole so it is not covered by a second ellipse.
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "CircDisc", "preset": "ellipse",
            "fill": c["surface"], "line": "none",
            "x": "3.5cm", "y": "5.0cm", "width": "12.0cm", "height": "12.0cm",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "CircHole", "preset": "ellipse",
            "fill": c["content_background"], "line": "none",
            "text": center,
            "x": "6.5cm", "y": "8.0cm", "width": "6.0cm", "height": "6.0cm",
            "font": t["heading_font"], "size": str(t["title_pt"] - 8),
            "bold": "true", "color": c["text_on_content"],
            "align": "center", "valign": "middle",
        },
    })
    # Legend list on the right
    row_h = min(2.4, 13.0 / n)
    for i, sg in enumerate(segs):
        y = 4.0 + i * row_h
        text = sg["label"]
        if sg.get("value"):
            text = f"{sg['value']}  {text}"
        if sg.get("detail"):
            text = f"{text}\n{sg['detail']}"
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"CircLeg{i + 1}", "preset": b["preset"],
                "fill": c["accent"] if i == 0 else c["surface"],
                "line": "none", "text": text,
                "x": "18.0cm", "y": _cm(y),
                "width": "13.5cm", "height": _cm(row_h - 0.2),
                "font": t["body_font"], "size": str(t["body_pt"]),
                "bold": "true",
                "color": c["on_accent"] if i == 0 else c["text_on_surface"],
                "valign": "middle",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Legend carries the insight; the disc is orientation only.")},
    })
    return ops


def recipe_mission_vision_split(tokens: dict, content: dict | None = None) -> list[dict]:
    """Mission / vision two-panel (Wave 4) — narrative chrome."""
    b = _base_props(tokens)
    c, t = b["c"], b["t"]
    content = content or {}
    title = content.get("title", "Direction")
    mission = str(content.get("mission") or content.get("left")
                  or "Why we exist — the problem we refuse to ignore.")
    vision = str(content.get("vision") or content.get("right")
                 or "Where we are going — the future state in concrete terms.")
    m = b["margin"]
    gap = 0.5
    cw = (33.87 - 2 * m - gap) / 2
    ops: list[dict] = [_slide_op(tokens), _title_op(tokens, "MVTitle", title)]
    for i, (lab, body, fill) in enumerate((
        ("Mission", mission, c["surface"]),
        ("Vision", vision, c["accent"]),
    )):
        x = m + i * (cw + gap)
        tc = c["text_on_surface"] if i == 0 else c["on_accent"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"MVPanel{i + 1}", "preset": b["preset"],
                "fill": fill, "line": "none",
                "x": _cm(x), "y": "3.8cm", "width": _cm(cw), "height": "13.5cm",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"MVLab{i + 1}", "text": lab,
                "x": _cm(x + 0.8), "y": "4.6cm",
                "width": _cm(cw - 1.6), "height": "1.2cm",
                "font": t["heading_font"], "size": str(t["section_pt"]),
                "bold": "true", "color": tc, "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"MVBody{i + 1}", "text": body,
                "x": _cm(x + 0.8), "y": "6.4cm",
                "width": _cm(cw - 1.6), "height": "10.0cm",
                "font": t["body_font"], "size": str(t["body_pt"] + 2),
                "color": tc, "fill": "none",
            },
        })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "notes",
        "props": {"text": content.get(
            "notes", "Mission is timeless; vision is dated and measurable.")},
    })
    return ops


def _call_builder(builder, tokens, content, slide_index: int | None = None):
    """Call recipe builder with optional slide_index if supported."""
    try:
        return builder(tokens, content, slide_index=slide_index)
    except TypeError:
        return builder(tokens, content)


def recipe_freeform(tokens: dict, content: dict | None = None) -> list[dict]:
    """Hybrid generative free-form slide (#21) — constraint-validated placements."""
    from .generative import recipe_freeform as _gen_freeform
    return _gen_freeform(tokens, content)


# Primary builders
RECIPE_BUILDERS = {
    "cover": recipe_cover,
    "section_divider": recipe_section_divider,
    "section_opener_numbered": recipe_section_opener_numbered,
    "kpi_row": recipe_kpi_row,
    "kpi_dashboard_grid": recipe_kpi_dashboard_grid,
    "feature_cards": recipe_feature_cards,
    "bullets": recipe_bullets,
    "quote": recipe_quote,
    "comparison_2col": recipe_comparison_2col,
    "timeline": recipe_timeline,
    "story_timeline": recipe_story_timeline,
    "process": recipe_process,
    "funnel_stages": recipe_funnel_stages,
    "roadmap_swimlane": recipe_roadmap_swimlane,
    "table": recipe_table,
    "image_full": recipe_image_full,
    "image_text_2col": recipe_image_text_2col,
    "chart_insight": recipe_chart_insight,
    "chart_callout_panel": recipe_chart_callout_panel,
    "close": recipe_close,
    "big_number": recipe_big_number,
    "matrix_2x2": recipe_matrix_2x2,
    "quadrant_matrix_rich": recipe_quadrant_matrix_rich,
    "pyramid_levels": recipe_pyramid_levels,
    "vs_scorecard": recipe_vs_scorecard,
    "team": recipe_team,
    "logo_strip": recipe_logo_strip,
    "pricing": recipe_pricing,
    "appendix_table": recipe_appendix_table,
    "agenda_toc": recipe_agenda_toc,
    # Phase 2 / #10 academic · medical · research
    "consort_flow": recipe_consort_flow,
    "kaplan_meier": recipe_kaplan_meier,
    "forest_plot": recipe_forest_plot,
    "study_design": recipe_study_design,
    "results_table_insight": recipe_results_table_insight,
    "multi_panel_figure": recipe_multi_panel_figure,
    # Wave 1 full-family coverage
    "chevron_process": recipe_chevron_process,
    "cycle_loop": recipe_cycle_loop,
    "waterfall_insight": recipe_waterfall_insight,
    "venn_overlap": recipe_venn_overlap,
    "swot_2x2": recipe_swot_2x2,
    "gantt_bars": recipe_gantt_bars,
    "org_tree": recipe_org_tree,
    "persona_card": recipe_persona_card,
    "business_canvas": recipe_business_canvas,
    "fishbone_causes": recipe_fishbone_causes,
    "iceberg_levels": recipe_iceberg_levels,
    "framework_row": recipe_framework_row,
    # Wave 2 long-tail roles
    "icon_stat_row": recipe_icon_stat_row,
    "scale_rating": recipe_scale_rating,
    "hub_spoke": recipe_hub_spoke,
    "before_after_slider": recipe_before_after_slider,
    "calendar_heatmap": recipe_calendar_heatmap,
    "case_study_band": recipe_case_study_band,
    "okrs_tree": recipe_okrs_tree,
    "project_status_rag": recipe_project_status_rag,
    "finance_statement": recipe_finance_statement,
    "pipeline_stages": recipe_pipeline_stages,
    "geo_callout": recipe_geo_callout,
    "device_frame": recipe_device_frame,
    # Wave 4 Infograpify long-tail roles
    "mindmap_branches": recipe_mindmap_branches,
    "journey_stages": recipe_journey_stages,
    "pestle_grid": recipe_pestle_grid,
    "raci_matrix": recipe_raci_matrix,
    "scorecard_balanced": recipe_scorecard_balanced,
    "hex_cluster": recipe_hex_cluster,
    "puzzle_pieces": recipe_puzzle_pieces,
    "pillar_columns": recipe_pillar_columns,
    "stairs_ascent": recipe_stairs_ascent,
    "checklist_board": recipe_checklist_board,
    "empathy_map_quad": recipe_empathy_map_quad,
    "risk_heat_matrix": recipe_risk_heat_matrix,
    "circle_segments": recipe_circle_segments,
    "mission_vision_split": recipe_mission_vision_split,
    "freeform": recipe_freeform,
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
# Geometry strategy per pattern. Every registered recipe is in exactly one
# bucket (test_pattern_layout_covers_registry). Buckets:
#   "engine"     — content grid solved by layout.py for adaptive text-fit;
#                  chrome may still be fixed.
#   "hybrid"     — fixed frame + engine-solved region and/or post-solve markers
#                  (timeline dots, forest CI bars, consort spine, matrix axes).
#   "structured" — chart/table/connector/picture-cell composition or pure
#                  hand-cm band stacks (funnel/pyramid/roadmap).
#   "fixed"      — intentional hero/divider compositions (overlap / opacity).
# Geometry-contract harness asserts on-canvas + readability for all; it does
# not enforce single-system purity inside hybrid/structured recipes.
PATTERN_LAYOUT: dict[str, tuple[str, ...]] = {
    "engine": (
        "bullets", "feature_cards", "comparison_2col", "image_text_2col",
        "kpi_row", "kpi_dashboard_grid", "pricing", "team", "agenda_toc",
        "vs_scorecard", "study_design",
        # Phase 5 / #21 generative freeform (constraint-validated Box tree)
        "freeform",
        # Wave 2
        "icon_stat_row", "scale_rating", "before_after_slider",
        "okrs_tree", "project_status_rag", "pipeline_stages",
    ),
    "hybrid": (
        "timeline", "story_timeline", "matrix_2x2", "quadrant_matrix_rich",
        "consort_flow", "forest_plot", "swot_2x2",
        "case_study_band",
    ),
    "structured": (
        "process", "funnel_stages", "roadmap_swimlane", "pyramid_levels",
        "chart_insight", "chart_callout_panel", "table", "appendix_table",
        "logo_strip", "kaplan_meier", "results_table_insight",
        "multi_panel_figure",
        # Wave 1 full-family coverage
        "chevron_process", "cycle_loop", "waterfall_insight", "venn_overlap",
        "gantt_bars", "org_tree", "persona_card", "business_canvas",
        "fishbone_causes", "iceberg_levels", "framework_row",
        # Wave 2
        "hub_spoke", "calendar_heatmap", "finance_statement",
        "geo_callout", "device_frame",
        # Wave 4 Infograpify long-tail
        "mindmap_branches", "journey_stages", "pestle_grid", "raci_matrix",
        "scorecard_balanced", "hex_cluster", "puzzle_pieces", "pillar_columns",
        "stairs_ascent", "checklist_board", "empathy_map_quad",
        "risk_heat_matrix", "circle_segments", "mission_vision_split",
    ),
    "fixed": (
        "cover", "section_divider", "section_opener_numbered",
        "big_number", "quote", "close", "image_full",
    ),
}

# Back-compat aliases used by older content.sample.json keys
RECIPE_ALIASES = {
    "kpi_3": "kpi_row",
    "feature_cards_3": "feature_cards",
}

# Catalog partitions (Phase 2 review: avoid kitchen-sink empty scaffolds).
CORE_SEQUENCE = [
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

PREMIUM_SEQUENCE = [
    "agenda_toc",
    "section_opener_numbered",
    "kpi_dashboard_grid",
    "story_timeline",
    "funnel_stages",
    "roadmap_swimlane",
    "pyramid_levels",
    "chart_callout_panel",
    "vs_scorecard",
    "quadrant_matrix_rich",
]

DOMAIN_SEQUENCE = [
    "consort_flow",
    "study_design",
    "kaplan_meier",
    "forest_plot",
    "results_table_insight",
    "multi_panel_figure",
]

# Wave 1 full-family coverage (docs/recipe-coverage-roadmap.md)
WAVE1_SEQUENCE = [
    "chevron_process",
    "cycle_loop",
    "waterfall_insight",
    "venn_overlap",
    "swot_2x2",
    "gantt_bars",
    "org_tree",
    "persona_card",
    "business_canvas",
    "fishbone_causes",
    "iceberg_levels",
    "framework_row",
]

# Wave 2 long-tail roles
WAVE2_SEQUENCE = [
    "icon_stat_row",
    "scale_rating",
    "hub_spoke",
    "before_after_slider",
    "calendar_heatmap",
    "case_study_band",
    "okrs_tree",
    "project_status_rag",
    "finance_statement",
    "pipeline_stages",
    "geo_callout",
    "device_frame",
]

# Wave 4 — Infograpify remaining structural roles (post W1–W3)
WAVE4_SEQUENCE = [
    "mindmap_branches",
    "journey_stages",
    "pestle_grid",
    "raci_matrix",
    "scorecard_balanced",
    "hex_cluster",
    "puzzle_pieces",
    "pillar_columns",
    "stairs_ascent",
    "checklist_board",
    "empathy_map_quad",
    "risk_heat_matrix",
    "circle_segments",
    "mission_vision_split",
]

# Empty-deck / flat-overlay default: consulting core only (no medical tax).
DEFAULT_SEQUENCE = list(CORE_SEQUENCE)

# Phase 5 / #21 — hybrid generative free-form (not in empty-scaffold defaults)
GENERATIVE_SEQUENCE = [
    "freeform",
]

# Full catalog for inspection / generate_all_recipes ordering helpers.
CATALOG_SEQUENCE = list(CORE_SEQUENCE) + [
    n for n in (
        PREMIUM_SEQUENCE + DOMAIN_SEQUENCE + WAVE1_SEQUENCE + WAVE2_SEQUENCE
        + WAVE4_SEQUENCE + GENERATIVE_SEQUENCE
    )
    if n not in CORE_SEQUENCE
]


def sequence_for(catalog: str = "core") -> list[str]:
    """Return ordered recipe list: core | premium | domain | wave1 | wave2 | wave4 | generative | all."""
    key = (catalog or "core").strip().lower()
    if key in ("core", "default", ""):
        return list(CORE_SEQUENCE)
    if key in ("premium", "consulting-premium"):
        return list(CORE_SEQUENCE) + [n for n in PREMIUM_SEQUENCE if n not in CORE_SEQUENCE]
    if key in ("domain", "medical", "academic"):
        return list(CORE_SEQUENCE) + [n for n in DOMAIN_SEQUENCE if n not in CORE_SEQUENCE]
    if key in ("wave1", "family", "full-family"):
        return list(CORE_SEQUENCE) + [n for n in WAVE1_SEQUENCE if n not in CORE_SEQUENCE]
    if key in ("wave2", "long-tail"):
        return list(CORE_SEQUENCE) + [n for n in WAVE2_SEQUENCE if n not in CORE_SEQUENCE]
    if key in ("wave4", "infograpify", "strategy-extra"):
        return list(CORE_SEQUENCE) + [n for n in WAVE4_SEQUENCE if n not in CORE_SEQUENCE]
    if key in ("generative", "freeform", "hybrid"):
        return list(CORE_SEQUENCE) + [n for n in GENERATIVE_SEQUENCE if n not in CORE_SEQUENCE]
    if key in ("all", "catalog", "full"):
        return list(CATALOG_SEQUENCE)
    raise ValueError(f"unknown catalog sequence: {catalog!r}")


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
