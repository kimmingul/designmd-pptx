"""Structural motif builders — Infograpify family coverage (original geometry).

Owned shapes only. Spacing from ``ui_kit.StageMetrics``. Compact fixed-cm
grammars for hierarchy / process / strategy patterns that dominate the local
400-deck structural catalog.
"""

from __future__ import annotations

import math
from typing import Any

from .. import layout as L  # noqa: F401 — reserved for engine motifs
from .. import ui_kit as UI


def _notes(slots: dict[str, Any], default: str) -> list[dict[str, Any]]:
    return [UI.notes_op(str(slots.get("notes") or default))]


def _bg(c: dict[str, str]) -> str:
    return c.get("content_background") or c["background"]


def _title_ops(st: UI.StageMetrics, title: str, name: str = "SlideTitle") -> list[dict[str, Any]]:
    c = st.c
    return [
        {
            "command": "add", "parent": "/", "type": "slide",
            "props": {"layout": "blank", "background": _bg(c)},
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": name, "text": title,
                "x": UI.cm(st.margin),
                "y": UI.cm(max(1.15, st.margin * 0.55)),
                "width": UI.cm(st.usable_w),
                "height": UI.cm(st.title_band),
                "font": st.heading_font, "size": str(st.title_pt),
                "bold": "true",
                "color": c.get("text_on_content") or c["text"],
                "fill": "none",
            },
        },
    ]


def _items(raw: Any, *, n_min: int = 3, n_max: int = 6, defaults: list[str] | None = None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if isinstance(raw, list):
        for it in raw[:n_max]:
            if isinstance(it, dict):
                label = str(
                    it.get("label") or it.get("title") or it.get("name")
                    or it.get("text") or "Item"
                )
                detail = str(
                    it.get("detail") or it.get("body") or it.get("role")
                    or it.get("value") or it.get("desc") or ""
                )
                out.append({"label": label, "detail": detail})
            else:
                out.append({"label": str(it), "detail": ""})
    defaults = defaults or [f"Item {i + 1}" for i in range(n_min)]
    while len(out) < n_min:
        out.append({"label": defaults[len(out) % len(defaults)], "detail": ""})
    return out[:n_max]


def _equal_row(
    st: UI.StageMetrics,
    *,
    title: str,
    title_name: str,
    items: list[dict[str, str]],
    name_prefix: str,
    accent_ends: bool = False,
    accent_every: int = 0,
) -> list[dict[str, Any]]:
    n = max(1, len(items))
    gap = st.gap * 0.9
    col = (st.usable_w - gap * (n - 1)) / n
    xs = [st.margin + i * (col + gap) for i in range(n)]
    y, h = UI.content_band_y_h(st, fraction=0.7, min_h=5.5, max_h=10.0)
    ops = _title_ops(st, title, title_name)
    c = st.c
    pt = max(14, min(20, st.section_pt - 4))
    for i, it in enumerate(items):
        if accent_ends and (i == 0 or i == n - 1):
            fill, tc = c["accent"], c["on_accent"]
        elif accent_every and (i % accent_every == 0):
            fill, tc = c["accent"], c["on_accent"]
        else:
            fill, tc = c["surface"], c["text_on_surface"]
        text = it["label"]
        if it.get("detail"):
            text = f"{it['label']}\n{it['detail']}"
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"{name_prefix}{i + 1}", "preset": st.preset,
                "fill": fill, "line": "none", "text": text,
                "x": UI.cm(xs[i]), "y": UI.cm(y),
                "width": UI.cm(col), "height": UI.cm(h),
                "font": st.heading_font, "size": str(pt),
                "bold": "true", "color": tc,
                "align": "center", "valign": "middle",
            },
        })
    return ops


# ---------------------------------------------------------------------------
# Process / hub
# ---------------------------------------------------------------------------

def build_hub_orbit(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Cycle")
    hub = str(slots.get("hub") or slots.get("center") or "Core")
    steps = _items(slots.get("steps") or slots.get("spokes") or slots.get("items"),
                   defaults=["Plan", "Do", "Check", "Act"])
    n = len(steps)
    cx, cy = 16.93, 11.0
    r = 5.0
    node_w, node_h = 5.2, 2.2
    ops = _title_ops(st, title, "CycleTitle")
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "HubCore", "preset": "ellipse",
            "fill": c["accent"], "line": "none", "text": hub,
            "x": UI.cm(cx - 2.1), "y": UI.cm(cy - 1.4),
            "width": "4.2cm", "height": "2.8cm",
            "font": st.heading_font, "size": str(max(16, st.section_pt - 4)),
            "bold": "true", "color": c["on_accent"],
            "align": "center", "valign": "middle",
        },
    })
    for i, step in enumerate(steps):
        ang = -math.pi / 2 + (2 * math.pi * i / n)
        x = cx + r * math.cos(ang) - node_w / 2
        y = cy + r * math.sin(ang) * 0.72 - node_h / 2
        x = max(st.margin, min(UI.CANVAS_W - st.margin - node_w, x))
        y = max(st.content_top, min(17.2 - node_h, y))
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"HubNode{i + 1}", "preset": st.preset,
                "fill": c["surface"], "line": "none", "text": step["label"],
                "x": UI.cm(x), "y": UI.cm(y),
                "width": UI.cm(node_w), "height": UI.cm(node_h),
                "font": st.body_font, "size": str(max(14, min(18, st.body_pt))),
                "bold": "true", "color": c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "Name the handoff between two adjacent nodes."))
    return ops


def build_pipeline_rail(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    items = _items(slots.get("stages") or slots.get("steps") or slots.get("items"),
                   defaults=["Lead", "Qualify", "Propose", "Close"])
    ops = _equal_row(
        st, title=str(slots.get("title") or "Pipeline"),
        title_name="PipeTitle", items=items, name_prefix="Pipe",
        accent_ends=True,
    )
    ops.extend(_notes(slots, "Call the stage with the biggest drop-off."))
    return ops


def build_journey_path(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    items = _items(slots.get("stages") or slots.get("steps"),
                   n_max=7, defaults=["Aware", "Consider", "Trial", "Adopt", "Expand"])
    ops = _equal_row(
        st, title=str(slots.get("title") or "Journey"),
        title_name="JourneyTitle", items=items, name_prefix="Journey",
        accent_every=0,
    )
    # accent last stage
    for op in ops:
        p = op.get("props") or {}
        if str(p.get("name") or "").startswith(f"Journey{len(items)}"):
            p["fill"] = st.c["accent"]
            p["color"] = st.c["on_accent"]
    ops.extend(_notes(slots, "Name the friction between two adjacent stages."))
    return ops


def build_framework_bar(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    items = _items(slots.get("items") or slots.get("pillars") or slots.get("steps"),
                   defaults=["People", "Process", "Tech", "Data"])
    ops = _equal_row(
        st, title=str(slots.get("title") or "Framework"),
        title_name="FwTitle", items=items, name_prefix="Fw",
    )
    ops.extend(_notes(slots, "Pick the under-invested bar."))
    return ops


def build_fishbone_spine(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Causes")
    effect = str(slots.get("effect") or slots.get("head") or "Effect")
    causes = _items(slots.get("causes") or slots.get("bones") or slots.get("items"),
                    n_min=4, n_max=6, defaults=["Method", "Machine", "Material", "Manpower"])
    ops = _title_ops(st, title, "FishTitle")
    m = st.margin
    # horizontal spine
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "FishSpine", "preset": "rect",
            "fill": c["muted"], "line": "none",
            "x": UI.cm(m + 1), "y": "10.8cm",
            "width": UI.cm(st.usable_w - 6), "height": "0.18cm",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "FishHead", "preset": st.preset,
            "fill": c["accent"], "line": "none", "text": effect,
            "x": UI.cm(m + st.usable_w - 5.5), "y": "9.4cm",
            "width": "5.2cm", "height": "3.0cm",
            "font": st.heading_font, "size": str(max(14, st.section_pt - 6)),
            "bold": "true", "color": c["on_accent"],
            "align": "center", "valign": "middle",
        },
    })
    half = (len(causes) + 1) // 2
    for i, cause in enumerate(causes):
        top = i < half
        col = i if top else i - half
        n_side = half if top else len(causes) - half
        x = m + 1.5 + col * ((st.usable_w - 8) / max(1, n_side))
        y = 5.2 if top else 12.6
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"FishBone{i + 1}", "preset": st.preset,
                "fill": c["surface"], "line": "none", "text": cause["label"],
                "x": UI.cm(x), "y": UI.cm(y),
                "width": "5.5cm", "height": "2.4cm",
                "font": st.body_font, "size": str(max(13, st.body_pt - 2)),
                "bold": "true", "color": c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "Mark the single root cause you will act on."))
    return ops


# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------

def build_pyramid_stack(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Pyramid")
    levels = _items(slots.get("levels") or slots.get("steps") or slots.get("items"),
                    n_min=3, n_max=5, defaults=["Base", "Middle", "Peak"])
    n = len(levels)
    ops = _title_ops(st, title, "PyrTitle")
    band_y, band_h = UI.content_band_y_h(st, fraction=0.8, min_h=8.0, max_h=12.0, settle=0.15)
    row_h = band_h / n
    usable = st.usable_w
    for i, lv in enumerate(levels):
        # wider at bottom
        frac = 0.45 + 0.55 * ((n - 1 - i) / max(1, n - 1))
        w = usable * frac
        x = st.margin + (usable - w) / 2
        y = band_y + i * row_h
        fill = c["accent"] if i == 0 else c["surface"]
        tc = c["on_accent"] if fill == c["accent"] else c["text_on_surface"]
        text = lv["label"]
        if lv.get("detail"):
            text = f"{lv['label']}  ·  {lv['detail']}"
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Pyr{i + 1}", "preset": st.preset,
                "fill": fill, "line": "none", "text": text,
                "x": UI.cm(x), "y": UI.cm(y + 0.08),
                "width": UI.cm(w), "height": UI.cm(max(1.6, row_h - 0.2)),
                "font": st.heading_font,
                "size": str(max(14, min(20, st.section_pt - 4))),
                "bold": "true", "color": tc,
                "align": "center", "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "Top layer is the decision; base is the enabler."))
    return ops


def build_iceberg_depth(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Iceberg")
    levels = _items(slots.get("levels") or slots.get("layers") or slots.get("items"),
                    n_min=3, n_max=4,
                    defaults=["Visible", "Patterns", "Structure", "Mental models"])
    ops = _title_ops(st, title, "IceTitle")
    m = st.margin
    # waterline
    water_y = 8.2
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "IceWater", "preset": "rect",
            "fill": c["surface"], "line": "none",
            "x": UI.cm(m), "y": UI.cm(water_y),
            "width": UI.cm(st.usable_w), "height": UI.cm(UI.CANVAS_H - water_y - m),
        },
    })
    n = len(levels)
    for i, lv in enumerate(levels):
        if i == 0:
            y, h, fill, tc = 4.0, 3.6, c["accent"], c["on_accent"]
        else:
            y = water_y + 0.4 + (i - 1) * 2.4
            h, fill, tc = 2.1, c.get("content_background") or c["background"], c["text_on_surface"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"IceLayer{i + 1}", "preset": st.preset,
                "fill": fill, "line": "none", "text": lv["label"],
                "x": UI.cm(m + st.usable_w * 0.2), "y": UI.cm(y),
                "width": UI.cm(st.usable_w * 0.6), "height": UI.cm(h),
                "font": st.heading_font, "size": str(max(14, st.section_pt - 6)),
                "bold": "true", "color": tc,
                "align": "center", "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "Name what sits below the waterline."))
    return ops


def build_pillar_band(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    items = _items(slots.get("pillars") or slots.get("columns") or slots.get("items"),
                   n_min=3, n_max=5, defaults=["Legacy", "Official", "Offline"])
    # rising heights
    c = st.c
    title = str(slots.get("title") or "Pillars")
    ops = _title_ops(st, title, "PillarTitle")
    n = len(items)
    gap = st.gap
    col = (st.usable_w - gap * (n - 1)) / n
    xs = [st.margin + i * (col + gap) for i in range(n)]
    band_y, band_h = UI.content_band_y_h(st, fraction=0.78, min_h=7.5, max_h=11.5)
    for i, it in enumerate(items):
        h = band_h * (0.55 + 0.45 * (i / max(1, n - 1)))
        y = band_y + band_h - h
        fill = c["accent"] if i == n - 1 else c["surface"]
        tc = c["on_accent"] if fill == c["accent"] else c["text_on_surface"]
        text = it["label"]
        if it.get("detail"):
            text = f"{it['label']}\n{it['detail']}"
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Pillar{i + 1}", "preset": st.preset,
                "fill": fill, "line": "none", "text": text,
                "x": UI.cm(xs[i]), "y": UI.cm(y),
                "width": UI.cm(col), "height": UI.cm(h),
                "font": st.heading_font, "size": str(max(14, st.section_pt - 6)),
                "bold": "true", "color": tc,
                "align": "center", "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "The tallest pillar is the strategic bet."))
    return ops


def build_okr_tree(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    # reuse org cascade geometry with OKR labels (lazy import avoids cycle)
    from ..motif import build_org_cascade

    root = slots.get("objective") or slots.get("root") or {
        "name": str(slots.get("title") or "Objective"),
        "role": "O",
    }
    if isinstance(root, str):
        root = {"name": root, "role": "O"}
    krs = slots.get("key_results") or slots.get("reports") or slots.get("items") or [
        {"name": "KR1", "role": "Metric"},
        {"name": "KR2", "role": "Metric"},
        {"name": "KR3", "role": "Metric"},
    ]
    return build_org_cascade(tokens, {
        "title": str(slots.get("title") or "OKRs"),
        "root": root,
        "reports": krs,
        "notes": slots.get("notes") or "Each KR needs an owner and a date.",
    })


# ---------------------------------------------------------------------------
# Timeline / roadmap
# ---------------------------------------------------------------------------

def build_timeline_rail(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Timeline")
    steps = _items(slots.get("steps") or slots.get("milestones") or slots.get("items"),
                   n_min=3, n_max=6, defaults=["Q1", "Q2", "Q3", "Q4"])
    n = len(steps)
    ops = _title_ops(st, title, "TlTitle")
    m = st.margin
    y_line = 10.2
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "TlAxis", "preset": "rect",
            "fill": c["muted"], "line": "none",
            "x": UI.cm(m), "y": UI.cm(y_line),
            "width": UI.cm(st.usable_w), "height": "0.12cm",
        },
    })
    for i, step in enumerate(steps):
        x = m + (i + 0.5) * (st.usable_w / n) - 0.35
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"TlDot{i + 1}", "preset": "ellipse",
                "fill": c["accent"] if i == 0 or i == n - 1 else c["surface"],
                "line": "none",
                "x": UI.cm(x), "y": UI.cm(y_line - 0.3),
                "width": "0.7cm", "height": "0.7cm",
            },
        })
        label_w = st.usable_w / n - 0.3
        lx = m + i * (st.usable_w / n) + 0.15
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"TlLabel{i + 1}", "text": step["label"],
                "x": UI.cm(lx), "y": UI.cm(y_line + 1.0),
                "width": UI.cm(label_w), "height": "2.2cm",
                "font": st.heading_font, "size": str(max(14, st.body_pt)),
                "bold": "true", "color": c.get("text_on_content") or c["text"],
                "align": "center", "fill": "none",
            },
        })
        if step.get("detail"):
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"TlDetail{i + 1}", "text": step["detail"],
                    "x": UI.cm(lx), "y": UI.cm(y_line - 3.2),
                    "width": UI.cm(label_w), "height": "2.4cm",
                    "font": st.body_font, "size": str(max(12, st.caption_pt + 2)),
                    "color": c["muted"], "align": "center", "fill": "none",
                },
            })
    ops.extend(_notes(slots, "Name the milestone that unlocks the rest."))
    return ops


def build_swimlane_roadmap(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Roadmap")
    lanes = slots.get("lanes") or slots.get("rows") or [
        {"label": "Product", "items": ["A", "B", "C"]},
        {"label": "GTM", "items": ["A", "B", "C"]},
        {"label": "Ops", "items": ["A", "B", "C"]},
    ]
    if not isinstance(lanes, list):
        lanes = []
    lanes = lanes[:5] or [{"label": "Lane", "items": ["1", "2", "3"]}]
    ops = _title_ops(st, title, "RoadTitle")
    band_y, band_h = UI.content_band_y_h(st, fraction=0.82, min_h=9.0, max_h=12.5, settle=0.1)
    row_h = band_h / len(lanes)
    label_w = 4.2
    for i, lane in enumerate(lanes):
        if not isinstance(lane, dict):
            lane = {"label": str(lane), "items": []}
        y = band_y + i * row_h
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"LaneLabel{i + 1}", "preset": st.preset,
                "fill": c["accent"] if i == 0 else c["surface"],
                "line": "none", "text": str(lane.get("label") or f"Lane {i + 1}"),
                "x": UI.cm(st.margin), "y": UI.cm(y + 0.1),
                "width": UI.cm(label_w), "height": UI.cm(row_h - 0.2),
                "font": st.heading_font, "size": str(max(13, st.body_pt - 2)),
                "bold": "true",
                "color": c["on_accent"] if i == 0 else c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
        items = lane.get("items") or lane.get("cells") or ["", "", ""]
        if not isinstance(items, list):
            items = [items]
        items = (list(items) + ["", "", ""])[:4]
        cell_w = (st.usable_w - label_w - st.gap) / len(items)
        for j, cell in enumerate(items):
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"Lane{i + 1}Cell{j + 1}", "preset": st.preset,
                    "fill": c["surface"], "line": "none",
                    "text": str(cell) if cell else "·",
                    "x": UI.cm(st.margin + label_w + st.gap + j * cell_w),
                    "y": UI.cm(y + 0.15),
                    "width": UI.cm(cell_w - 0.15),
                    "height": UI.cm(row_h - 0.3),
                    "font": st.body_font, "size": str(max(12, st.caption_pt + 2)),
                    "color": c["text_on_surface"],
                    "align": "center", "valign": "middle",
                },
            })
    ops.extend(_notes(slots, "Call the cross-lane dependency."))
    return ops


def build_gantt_track(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Plan")
    bars = slots.get("bars") or slots.get("items") or slots.get("tasks") or [
        {"label": "Discover", "start": 0, "span": 2},
        {"label": "Build", "start": 1, "span": 3},
        {"label": "Ship", "start": 3, "span": 2},
    ]
    if not isinstance(bars, list):
        bars = []
    bars = bars[:6]
    ops = _title_ops(st, title, "GanttTitle")
    band_y, band_h = UI.content_band_y_h(st, fraction=0.75, min_h=8.0, max_h=11.5)
    row_h = band_h / max(1, len(bars))
    label_w = 5.5
    track_w = st.usable_w - label_w - st.gap
    units = 6
    for i, bar in enumerate(bars):
        if not isinstance(bar, dict):
            bar = {"label": str(bar), "start": i, "span": 2}
        y = band_y + i * row_h
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"GanttLabel{i + 1}", "text": str(bar.get("label") or f"Task {i + 1}"),
                "x": UI.cm(st.margin), "y": UI.cm(y + 0.15),
                "width": UI.cm(label_w), "height": UI.cm(row_h - 0.3),
                "font": st.body_font, "size": str(st.body_pt),
                "bold": "true", "color": c.get("text_on_content") or c["text"],
                "valign": "middle", "fill": "none",
            },
        })
        start = float(bar.get("start") or 0)
        span = float(bar.get("span") or bar.get("duration") or 2)
        x = st.margin + label_w + st.gap + (start / units) * track_w
        w = max(1.2, (span / units) * track_w)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"GanttBar{i + 1}", "preset": st.preset,
                "fill": c["accent"] if i == 0 else c["surface"],
                "line": "none",
                "x": UI.cm(x), "y": UI.cm(y + row_h * 0.22),
                "width": UI.cm(w), "height": UI.cm(row_h * 0.55),
            },
        })
    ops.extend(_notes(slots, "Highlight the critical path bar."))
    return ops


# ---------------------------------------------------------------------------
# Org / team / persona
# ---------------------------------------------------------------------------

def build_team_cards(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    members = slots.get("members") or slots.get("items") or [
        {"name": "Alex", "role": "Eng", "blurb": ""},
        {"name": "Sam", "role": "Design", "blurb": ""},
        {"name": "Riley", "role": "GTM", "blurb": ""},
    ]
    if not isinstance(members, list):
        members = []
    members = members[:4]
    items = []
    for m in members:
        if isinstance(m, dict):
            items.append({
                "label": str(m.get("name") or "Member"),
                "detail": str(m.get("role") or m.get("title") or ""),
            })
        else:
            items.append({"label": str(m), "detail": ""})
    ops = _equal_row(
        st, title=str(slots.get("title") or "Team"),
        title_name="TeamTitle", items=items or [{"label": "Member", "detail": ""}],
        name_prefix="Member",
    )
    ops.extend(_notes(slots, "One line each: name, why they matter here."))
    return ops


def build_persona_split(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Persona")
    name = str(slots.get("name") or slots.get("persona") or "Alex Rivera")
    role = str(slots.get("role") or "Role / segment")
    quote = str(slots.get("quote") or slots.get("goal") or "What success looks like.")
    attrs = slots.get("attrs") or slots.get("traits") or slots.get("bullets") or [
        "Goal", "Pain", "Channel", "Metric",
    ]
    if not isinstance(attrs, list):
        attrs = [str(attrs)]
    attrs = [str(a) for a in attrs[:6]]
    ops = _title_ops(st, title, "PersonaTitle")
    m = st.margin
    left_w = st.usable_w * 0.42
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "PersonaPanel", "preset": st.preset,
            "fill": c["surface"], "line": "none",
            "x": UI.cm(m), "y": UI.cm(st.content_top),
            "width": UI.cm(left_w), "height": UI.cm(UI.CANVAS_H - st.content_top - m),
        },
    })
    # initials
    parts = [p for p in name.split() if p]
    initials = "".join(p[0].upper() for p in parts[:2]) or "?"
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "PersonaAvatar", "preset": "ellipse",
            "fill": c["accent"], "line": "none", "text": initials,
            "x": UI.cm(m + left_w / 2 - 2.4), "y": UI.cm(st.content_top + 1.2),
            "width": "4.8cm", "height": "4.8cm",
            "font": st.heading_font, "size": "28",
            "bold": "true", "color": c["on_accent"],
            "align": "center", "valign": "middle",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "PersonaName", "text": f"{name}\n{role}",
            "x": UI.cm(m + 0.5), "y": UI.cm(st.content_top + 6.5),
            "width": UI.cm(left_w - 1), "height": "2.8cm",
            "font": st.heading_font, "size": str(max(16, st.section_pt - 4)),
            "bold": "true", "color": c["text_on_surface"],
            "align": "center", "fill": "none",
        },
    })
    right_x = m + left_w + st.gap
    right_w = st.usable_w - left_w - st.gap
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "PersonaQuote", "text": f"“{quote}”",
            "x": UI.cm(right_x), "y": UI.cm(st.content_top),
            "width": UI.cm(right_w), "height": "3.5cm",
            "font": st.heading_font, "size": str(max(16, st.section_pt - 4)),
            "color": c.get("text_on_content") or c["text"], "fill": "none",
        },
    })
    for i, a in enumerate(attrs):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"PersonaAttr{i + 1}", "preset": st.preset,
                "fill": c["surface"], "line": "none", "text": a,
                "x": UI.cm(right_x),
                "y": UI.cm(st.content_top + 3.8 + i * 1.7),
                "width": UI.cm(right_w), "height": "1.5cm",
                "font": st.body_font, "size": str(st.body_pt),
                "color": c["text_on_surface"], "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "One decision this persona forces on the product."))
    return ops


# ---------------------------------------------------------------------------
# KPI / pricing / stats
# ---------------------------------------------------------------------------

def build_kpi_grid(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Dashboard")
    kpis = slots.get("kpis") or slots.get("metrics") or [
        {"value": "12", "label": "A"}, {"value": "48%", "label": "B"},
        {"value": "3.1", "label": "C"}, {"value": "9", "label": "D"},
        {"value": "2.4x", "label": "E"}, {"value": "18", "label": "F"},
    ]
    if not isinstance(kpis, list):
        kpis = []
    kpis = kpis[:8]
    n = max(4, len(kpis))
    cols = 4 if n > 4 else max(2, n)
    rows = (len(kpis) + cols - 1) // cols
    ops = _title_ops(st, title, "DashTitle")
    band_y, band_h = UI.content_band_y_h(st, fraction=0.8, min_h=8.5, max_h=12.0)
    gap = st.gap * 0.8
    cell_w = (st.usable_w - gap * (cols - 1)) / cols
    cell_h = (band_h - gap * (rows - 1)) / rows
    for i, k in enumerate(kpis):
        if not isinstance(k, dict):
            k = {"value": str(k), "label": ""}
        r, col = divmod(i, cols)
        x = st.margin + col * (cell_w + gap)
        y = band_y + r * (cell_h + gap)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"DashCard{i + 1}", "preset": st.preset,
                "fill": c["surface"], "line": "none",
                "x": UI.cm(x), "y": UI.cm(y),
                "width": UI.cm(cell_w), "height": UI.cm(cell_h),
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"DashValue{i + 1}",
                "text": str(k.get("value") or "—"),
                "x": UI.cm(x + st.pad * 0.5), "y": UI.cm(y + cell_h * 0.18),
                "width": UI.cm(cell_w - st.pad), "height": UI.cm(cell_h * 0.45),
                "font": st.heading_font,
                "size": str(max(22, min(36, st.title_pt - 4))),
                "bold": "true", "color": c["accent"],
                "align": "center", "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"DashLabel{i + 1}",
                "text": str(k.get("label") or ""),
                "x": UI.cm(x + st.pad * 0.5), "y": UI.cm(y + cell_h * 0.62),
                "width": UI.cm(cell_w - st.pad), "height": UI.cm(cell_h * 0.28),
                "font": st.body_font, "size": str(max(12, st.caption_pt + 2)),
                "color": c["muted"], "align": "center", "fill": "none",
            },
        })
    ops.extend(_notes(slots, "Lead with the metric that forces a decision."))
    return ops


def build_stat_row(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    raw = slots.get("stats") or slots.get("items") or slots.get("kpis") or [
        {"value": "01", "label": "A"}, {"value": "02", "label": "B"},
        {"value": "03", "label": "C"}, {"value": "04", "label": "D"},
    ]
    items = []
    if isinstance(raw, list):
        for it in raw[:6]:
            if isinstance(it, dict):
                items.append({
                    "label": str(it.get("value") or it.get("label") or "—"),
                    "detail": str(it.get("label") if it.get("value") else it.get("detail") or ""),
                })
            else:
                items.append({"label": str(it), "detail": ""})
    ops = _equal_row(
        st, title=str(slots.get("title") or "Stats"),
        title_name="StatTitle", items=items or [{"label": "—", "detail": ""}],
        name_prefix="Stat", accent_every=2,
    )
    ops.extend(_notes(slots, "One stat, one implication."))
    return ops


def build_scale_meter(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Scale")
    value = int(slots.get("value") or slots.get("score") or 3)
    max_v = int(slots.get("max") or 5)
    value = max(1, min(max_v, value))
    labels = slots.get("labels") or [str(i + 1) for i in range(max_v)]
    if not isinstance(labels, list):
        labels = [str(i + 1) for i in range(max_v)]
    ops = _title_ops(st, title, "ScaleTitle")
    band_y, band_h = UI.content_band_y_h(st, fraction=0.45, min_h=4.0, max_h=6.5, settle=0.4)
    gap = st.gap * 0.7
    col = (st.usable_w - gap * (max_v - 1)) / max_v
    for i in range(max_v):
        fill = c["accent"] if i < value else c["surface"]
        tc = c["on_accent"] if i < value else c["muted"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"ScaleCell{i + 1}", "preset": st.preset,
                "fill": fill, "line": "none",
                "text": str(labels[i] if i < len(labels) else i + 1),
                "x": UI.cm(st.margin + i * (col + gap)), "y": UI.cm(band_y),
                "width": UI.cm(col), "height": UI.cm(band_h),
                "font": st.heading_font, "size": str(max(16, st.section_pt - 4)),
                "bold": "true", "color": tc,
                "align": "center", "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "State what would move the score one notch."))
    return ops


def build_pricing_tiers(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Pricing")
    tiers = slots.get("tiers") or [
        {"name": "Starter", "price": "$9", "blurb": "Solo"},
        {"name": "Team", "price": "$29", "blurb": "Squad"},
        {"name": "Enterprise", "price": "Talk", "blurb": "Scale"},
    ]
    if not isinstance(tiers, list):
        tiers = []
    tiers = tiers[:4]
    n = max(1, len(tiers))
    gap = st.gap
    col = (st.usable_w - gap * (n - 1)) / n
    ops = _title_ops(st, title, "PriceTitle")
    y, h = UI.content_band_y_h(st, fraction=0.78, min_h=8.0, max_h=12.0)
    for i, tier in enumerate(tiers):
        if not isinstance(tier, dict):
            tier = {"name": str(tier), "price": "—"}
        x = st.margin + i * (col + gap)
        featured = bool(tier.get("featured") or i == n // 2)
        fill = c["accent"] if featured else c["surface"]
        tc = c["on_accent"] if featured else c["text_on_surface"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Tier{i + 1}Bg", "preset": st.preset,
                "fill": fill, "line": "none",
                "x": UI.cm(x), "y": UI.cm(y),
                "width": UI.cm(col), "height": UI.cm(h),
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Tier{i + 1}Name", "text": str(tier.get("name") or "Tier"),
                "x": UI.cm(x + 0.4), "y": UI.cm(y + 0.8),
                "width": UI.cm(col - 0.8), "height": "1.4cm",
                "font": st.heading_font, "size": str(max(16, st.section_pt - 4)),
                "bold": "true", "color": tc, "align": "center", "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Tier{i + 1}Price", "text": str(tier.get("price") or "—"),
                "x": UI.cm(x + 0.4), "y": UI.cm(y + h * 0.35),
                "width": UI.cm(col - 0.8), "height": "2.4cm",
                "font": st.heading_font, "size": str(max(28, st.title_pt)),
                "bold": "true", "color": tc, "align": "center", "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Tier{i + 1}Blurb",
                "text": str(tier.get("blurb") or tier.get("detail") or ""),
                "x": UI.cm(x + 0.4), "y": UI.cm(y + h * 0.7),
                "width": UI.cm(col - 0.8), "height": "2.0cm",
                "font": st.body_font, "size": str(st.body_pt),
                "color": tc if featured else c["muted"],
                "align": "center", "fill": "none",
            },
        })
    ops.extend(_notes(slots, "Recommend one tier; don't present a menu."))
    return ops


# ---------------------------------------------------------------------------
# Narrative chrome
# ---------------------------------------------------------------------------

def build_section_wash(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    number = str(slots.get("number") or "01")
    title = str(slots.get("title") or "Section")
    blurb = str(slots.get("blurb") or "")
    ops: list[dict[str, Any]] = [
        {
            "command": "add", "parent": "/", "type": "slide",
            "props": {"layout": "blank", "background": c["background"]},
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "SectionNumber", "text": number,
                "x": UI.cm(st.margin), "y": "4.2cm",
                "width": "14cm", "height": "4.8cm",
                "font": st.heading_font, "size": "96",
                "bold": "true", "color": c["accent"], "fill": "none",
            },
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "SectionTitle", "text": title,
                "x": UI.cm(st.margin), "y": "10.0cm",
                "width": UI.cm(st.usable_w), "height": "2.6cm",
                "font": st.heading_font, "size": str(st.title_pt),
                "bold": "true", "color": c["text"], "fill": "none",
            },
        },
    ]
    if blurb:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "SectionBlurb", "text": blurb,
                "x": UI.cm(st.margin), "y": "13.0cm",
                "width": "24cm", "height": "2.0cm",
                "font": st.body_font, "size": str(st.body_pt),
                "color": c["muted"], "fill": "none",
            },
        })
    ops.extend(_notes(slots, "Hold the number; then the title."))
    return ops


def build_agenda_list(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Agenda")
    items = _items(slots.get("items") or slots.get("agenda") or slots.get("sections"),
                   n_min=3, n_max=8, defaults=["Context", "Insight", "Plan", "Ask"])
    ops = _title_ops(st, title, "AgendaTitle")
    band_y, band_h = UI.content_band_y_h(st, fraction=0.78, min_h=8.0, max_h=12.0)
    row_h = band_h / len(items)
    for i, it in enumerate(items):
        y = band_y + i * row_h
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"AgendaNum{i + 1}", "text": f"{i + 1:02d}",
                "x": UI.cm(st.margin), "y": UI.cm(y),
                "width": "2.4cm", "height": UI.cm(max(1.4, row_h - 0.15)),
                "font": st.heading_font, "size": str(max(18, st.section_pt - 2)),
                "bold": "true", "color": c["accent"], "fill": "none", "valign": "middle",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"AgendaItem{i + 1}", "text": it["label"],
                "x": UI.cm(st.margin + 2.8), "y": UI.cm(y),
                "width": UI.cm(st.usable_w - 2.8),
                "height": UI.cm(max(1.4, row_h - 0.15)),
                "font": st.heading_font, "size": str(max(16, st.section_pt - 4)),
                "bold": "true",
                "color": c.get("text_on_content") or c["text"],
                "fill": "none", "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "Skip the menu — point at the one decision."))
    return ops


def build_quote_mark(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    quote = str(slots.get("quote") or slots.get("text") or slots.get("title") or "Quote")
    attr = str(slots.get("attribution") or slots.get("author") or slots.get("meta") or "")
    ops: list[dict[str, Any]] = [
        {
            "command": "add", "parent": "/", "type": "slide",
            "props": {"layout": "blank", "background": _bg(c)},
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "QuoteMark", "text": "“",
                "x": UI.cm(st.margin), "y": "3.5cm",
                "width": "4cm", "height": "3cm",
                "font": st.heading_font, "size": "96",
                "bold": "true", "color": c["accent"], "fill": "none",
            },
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "QuoteText", "text": quote,
                "x": UI.cm(st.margin + 1), "y": "7.0cm",
                "width": UI.cm(st.usable_w - 2), "height": "5.5cm",
                "font": st.heading_font, "size": str(max(22, st.title_pt - 4)),
                "bold": "true",
                "color": c.get("text_on_content") or c["text"], "fill": "none",
            },
        },
    ]
    if attr:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "QuoteAttr", "text": attr,
                "x": UI.cm(st.margin + 1), "y": "13.2cm",
                "width": UI.cm(st.usable_w - 2), "height": "1.4cm",
                "font": st.body_font, "size": str(st.body_pt),
                "color": c["muted"], "fill": "none",
            },
        })
    ops.extend(_notes(slots, "Let the quote land; no bullet restatement."))
    return ops


def build_bullet_stack(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Key points")
    bullets = slots.get("bullets") or slots.get("items") or ["Point one", "Point two", "Point three"]
    if not isinstance(bullets, list):
        bullets = [str(bullets)]
    bullets = [str(b) for b in bullets[:7]]
    ops = _title_ops(st, title, "BulletTitle")
    band_y, band_h = UI.content_band_y_h(st, fraction=0.75, min_h=7.5, max_h=11.5)
    row_h = band_h / max(1, len(bullets))
    for i, b in enumerate(bullets):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Bullet{i + 1}", "preset": st.preset,
                "fill": c["surface"], "line": "none",
                "text": f"  ·  {b}",
                "x": UI.cm(st.margin), "y": UI.cm(band_y + i * row_h),
                "width": UI.cm(st.usable_w),
                "height": UI.cm(max(1.4, row_h - 0.18)),
                "font": st.body_font, "size": str(st.body_pt),
                "bold": "true", "color": c["text_on_surface"], "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "Three bullets max when the decision is binary."))
    return ops


def build_close_mark(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or slots.get("cta") or "Next step")
    body = str(slots.get("body") or slots.get("subtitle") or "doctor --ensure")
    meta = str(slots.get("meta") or "")
    ops: list[dict[str, Any]] = [
        {
            "command": "add", "parent": "/", "type": "slide",
            "props": {"layout": "blank", "background": c["background"]},
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "CloseTitle", "text": title,
                "x": UI.cm(st.margin), "y": "6.5cm",
                "width": UI.cm(st.usable_w), "height": "3.2cm",
                "font": st.heading_font, "size": str(max(32, st.title_pt)),
                "bold": "true", "color": c["text"], "fill": "none",
            },
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "CloseBody", "text": body,
                "x": UI.cm(st.margin), "y": "10.2cm",
                "width": UI.cm(st.usable_w), "height": "2.2cm",
                "font": st.body_font, "size": str(st.body_pt + 2),
                "color": c["muted"], "fill": "none",
            },
        },
    ]
    if meta:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "CloseMeta", "text": meta,
                "x": UI.cm(st.margin), "y": "16.2cm",
                "width": UI.cm(st.usable_w), "height": "1.2cm",
                "font": st.body_font, "size": str(st.caption_pt + 2),
                "color": c["muted"], "fill": "none",
            },
        })
    ops.extend(_notes(slots, "One ask. Stop."))
    return ops


# ---------------------------------------------------------------------------
# Strategy / matrix-like
# ---------------------------------------------------------------------------

def build_canvas_bmc(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Business model")
    cells = slots.get("cells") or slots.get("blocks") or [
        "Partners", "Activities", "Value", "Relationships", "Segments",
        "Resources", "Channels", "Costs", "Revenue",
    ]
    if isinstance(cells, dict):
        cells = list(cells.values())
    if not isinstance(cells, list):
        cells = [str(cells)]
    cells = [str(x) if not isinstance(x, dict) else str(x.get("label") or x.get("title") or "")
             for x in cells][:9]
    while len(cells) < 9:
        cells.append(f"Block {len(cells) + 1}")
    ops = _title_ops(st, title, "BmcTitle")
    # 3x3-ish BMC-like grid (original layout, not vendor)
    band_y, band_h = UI.content_band_y_h(st, fraction=0.82, min_h=9.0, max_h=12.5, settle=0.08)
    cols, rows = 3, 3
    gap = 0.25
    cw = (st.usable_w - gap * (cols - 1)) / cols
    ch = (band_h - gap * (rows - 1)) / rows
    for i, label in enumerate(cells):
        r, col = divmod(i, cols)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Bmc{i + 1}", "preset": st.preset,
                "fill": c["accent"] if i == 2 else c["surface"],
                "line": "none", "text": label,
                "x": UI.cm(st.margin + col * (cw + gap)),
                "y": UI.cm(band_y + r * (ch + gap)),
                "width": UI.cm(cw), "height": UI.cm(ch),
                "font": st.body_font, "size": str(max(13, st.body_pt - 2)),
                "bold": "true",
                "color": c["on_accent"] if i == 2 else c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "Value proposition is the only required block today."))
    return ops


def build_pestle_cells(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    labels = slots.get("items") or slots.get("factors") or list("PESTLE")
    # expand letters
    if labels == list("PESTLE") or labels == ["P", "E", "S", "T", "L", "E"]:
        labels = [
            {"label": "Political"}, {"label": "Economic"}, {"label": "Social"},
            {"label": "Tech"}, {"label": "Legal"}, {"label": "Environment"},
        ]
    items = _items(labels, n_min=6, n_max=6)
    ops = _equal_row(
        st, title=str(slots.get("title") or "PESTLE"),
        title_name="PestleTitle", items=items, name_prefix="Pestle",
    )
    ops.extend(_notes(slots, "Pick the factor that changes the plan."))
    return ops


def build_scorecard_grid(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    items = _items(
        slots.get("perspectives") or slots.get("items") or slots.get("cards"),
        n_min=4, n_max=4,
        defaults=["Financial", "Customer", "Process", "Learning"],
    )
    ops = _equal_row(
        st, title=str(slots.get("title") or "Scorecard"),
        title_name="ScoreTitle", items=items, name_prefix="Score",
        accent_every=0,
    )
    ops.extend(_notes(slots, "One metric per perspective is enough."))
    return ops


def build_risk_heat(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Risk matrix")
    ops = _title_ops(st, title, "RiskTitle")
    # 3x3 heat
    band_y, band_h = UI.content_band_y_h(st, fraction=0.75, min_h=8.0, max_h=11.5)
    n = 3
    gap = 0.25
    cw = (st.usable_w - gap * (n - 1)) / n
    ch = (band_h - gap * (n - 1)) / n
    fills = [
        c["surface"], c["surface"], c.get("chart_series2") or c["muted"],
        c["surface"], c.get("chart_series2") or c["muted"], c["accent"],
        c.get("chart_series2") or c["muted"], c["accent"], c["accent"],
    ]
    labels = slots.get("cells") or [
        "Low", "Watch", "Plan",
        "Watch", "Plan", "Act",
        "Plan", "Act", "Stop",
    ]
    if not isinstance(labels, list):
        labels = ["·"] * 9
    for i in range(9):
        r, col = divmod(i, 3)
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RiskCell{i + 1}", "preset": st.preset,
                "fill": fills[i], "line": "none",
                "text": str(labels[i] if i < len(labels) else "·"),
                "x": UI.cm(st.margin + col * (cw + gap)),
                "y": UI.cm(band_y + r * (ch + gap)),
                "width": UI.cm(cw), "height": UI.cm(ch),
                "font": st.body_font, "size": str(st.body_pt),
                "bold": "true",
                "color": c["on_accent"] if fills[i] == c["accent"] else c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "Move one risk out of the red zone this quarter."))
    return ops


def build_raci_grid(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "RACI")
    roles = slots.get("roles") or ["Exec", "PM", "Eng", "Design"]
    activities = slots.get("activities") or ["Decide", "Build", "Review", "Ship"]
    if not isinstance(roles, list):
        roles = ["A", "B", "C"]
    if not isinstance(activities, list):
        activities = ["1", "2", "3"]
    roles = [str(r) for r in roles[:5]]
    activities = [str(a) for a in activities[:5]]
    ops = _title_ops(st, title, "RaciTitle")
    band_y, band_h = UI.content_band_y_h(st, fraction=0.8, min_h=8.5, max_h=12.0)
    cols = len(roles) + 1
    rows = len(activities) + 1
    gap = 0.12
    cw = (st.usable_w - gap * (cols - 1)) / cols
    ch = (band_h - gap * (rows - 1)) / rows
    # header row
    for j, role in enumerate([""] + roles):
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RaciH{j}", "preset": st.preset,
                "fill": c["accent"] if j else c["surface"],
                "line": "none", "text": role,
                "x": UI.cm(st.margin + j * (cw + gap)), "y": UI.cm(band_y),
                "width": UI.cm(cw), "height": UI.cm(ch),
                "font": st.body_font, "size": str(max(12, st.caption_pt + 2)),
                "bold": "true",
                "color": c["on_accent"] if j else c["text_on_surface"],
                "align": "center", "valign": "middle",
            },
        })
    letters = ["R", "A", "C", "I"]
    for i, act in enumerate(activities):
        for j in range(cols):
            text = act if j == 0 else letters[(i + j) % 4]
            ops.append({
                "command": "add", "parent": "/slide[last()]", "type": "shape",
                "props": {
                    "name": f"Raci{i}_{j}", "preset": st.preset,
                    "fill": c["surface"], "line": "none", "text": text,
                    "x": UI.cm(st.margin + j * (cw + gap)),
                    "y": UI.cm(band_y + (i + 1) * (ch + gap)),
                    "width": UI.cm(cw), "height": UI.cm(ch),
                    "font": st.body_font, "size": str(max(12, st.caption_pt + 2)),
                    "bold": "true", "color": c["text_on_surface"],
                    "align": "center", "valign": "middle",
                },
            })
    ops.extend(_notes(slots, "Only one A per row."))
    return ops


def build_empathy_quad(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    quads = slots.get("quadrants") or [
        {"title": "Says", "body": ""},
        {"title": "Thinks", "body": ""},
        {"title": "Does", "body": ""},
        {"title": "Feels", "body": ""},
    ]
    from ..motif import build_matrix_quad

    return build_matrix_quad(tokens, {
        "title": str(slots.get("title") or "Empathy map"),
        "quadrants": quads,
        "notes": slots.get("notes") or "One insight that changes the design.",
    })


def build_rich_matrix(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    from ..motif import build_matrix_quad

    return build_matrix_quad(tokens, {
        "title": str(slots.get("title") or "Priority matrix"),
        "quadrants": slots.get("quadrants"),
        "axes": slots.get("axes") or {"x": "Effort →", "y": "Impact ↑"},
        "notes": slots.get("notes"),
    })


def build_vs_columns(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    left = slots.get("left") or slots.get("a") or {"title": "Us", "body": "Option A"}
    right = slots.get("right") or slots.get("b") or {"title": "B", "body": "Option B"}
    if not isinstance(left, dict):
        left = {"title": "A", "body": str(left)}
    if not isinstance(right, dict):
        right = {"title": "B", "body": str(right)}
    return UI.comparison_panels(
        st,
        title=str(slots.get("title") or "Compare"),
        left_title=str(left.get("title") or "A"),
        left_body=str(left.get("body") or ""),
        right_title=str(right.get("title") or "B"),
        right_body=str(right.get("body") or ""),
        title_name="VsTitle",
        left_fill=st.c["surface"],
        right_fill=st.c["accent"],
    ) + _notes(slots, "Pick a winner; don't average.")


# ---------------------------------------------------------------------------
# Long-tail visuals
# ---------------------------------------------------------------------------

def build_hex_honey(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    items = _items(slots.get("items") or slots.get("nodes"),
                   n_min=5, n_max=7, defaults=["A", "B", "C", "D", "E", "F", "G"])
    # approximate hex cluster as tile row + center accent
    ops = _equal_row(
        st, title=str(slots.get("title") or "Cluster"),
        title_name="HexTitle", items=items[:5], name_prefix="Hex",
        accent_every=3,
    )
    ops.extend(_notes(slots, "Name the node that connects the most edges."))
    return ops


def build_mindmap_radial(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    return build_hub_orbit(tokens, {
        "title": slots.get("title") or "Mind map",
        "hub": slots.get("hub") or slots.get("center") or "Topic",
        "steps": slots.get("branches") or slots.get("nodes") or slots.get("items"),
        "notes": slots.get("notes") or "Collapse branches that don't serve the thesis.",
    })


def build_venn_duo(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Overlap")
    left = str(
        slots.get("left")
        or ((slots.get("sets") or ["A", "B"])[0] if isinstance(slots.get("sets"), list) else "A")
    )
    right = str(
        slots.get("right")
        or (
            (slots.get("sets") or ["A", "B"])[1]
            if isinstance(slots.get("sets"), list) and len(slots.get("sets") or []) > 1
            else "B"
        )
    )
    mid = str(slots.get("overlap") or "Both")
    ops = _title_ops(st, title, "VennTitle")
    # Two overlapping ellipses — labels sit in the outer lobes / gap so
    # officecli issues do not flag intentional circle overlap as text-hidden.
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "VennL", "preset": "ellipse",
            "fill": c["surface"], "line": "none",
            "x": "6.5cm", "y": "5.5cm", "width": "12cm", "height": "10cm",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "VennR", "preset": "ellipse",
            "fill": c["accent"], "line": "none",
            "x": "15.5cm", "y": "5.5cm", "width": "12cm", "height": "10cm",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "VennLLabel", "text": left,
            "x": "7.2cm", "y": "9.0cm", "width": "5.5cm", "height": "2.2cm",
            "font": st.heading_font, "size": "22", "bold": "true",
            "color": c["text_on_surface"], "align": "center", "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "VennRLabel", "text": right,
            "x": "21.5cm", "y": "9.0cm", "width": "5.5cm", "height": "2.2cm",
            "font": st.heading_font, "size": "22", "bold": "true",
            "color": c["on_accent"], "align": "center", "fill": "none",
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "VennMid", "text": mid,
            "x": "13.5cm", "y": "9.2cm", "width": "7cm", "height": "2cm",
            "font": st.body_font, "size": str(st.body_pt),
            "bold": "true", "color": c.get("text_on_content") or c["text"],
            "align": "center", "fill": "none",
        },
    })
    ops.extend(_notes(slots, "The intersection is the only story."))
    return ops


def build_ring_segments(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    items = _items(slots.get("segments") or slots.get("items"),
                   n_min=3, n_max=6, defaults=["A", "B", "C", "D"])
    ops = _equal_row(
        st, title=str(slots.get("title") or "Segments"),
        title_name="RingTitle", items=items, name_prefix="Seg",
        accent_every=2,
    )
    ops.extend(_notes(slots, "Label the largest segment first."))
    return ops


def build_case_band(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    items = _items(
        slots.get("bands") or slots.get("items") or [
            {"label": "Challenge", "detail": ""},
            {"label": "Approach", "detail": ""},
            {"label": "Result", "detail": ""},
        ],
        n_min=3, n_max=4,
    )
    ops = _equal_row(
        st, title=str(slots.get("title") or "Case study"),
        title_name="CaseTitle", items=items, name_prefix="Case",
        accent_ends=True,
    )
    ops.extend(_notes(slots, "Result needs a number."))
    return ops


def build_rag_status(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Status")
    rows = slots.get("rows") or slots.get("items") or [
        {"label": "Scope", "status": "G"},
        {"label": "Schedule", "status": "A"},
        {"label": "Risk", "status": "R"},
    ]
    if not isinstance(rows, list):
        rows = []
    rows = rows[:8]
    ops = _title_ops(st, title, "RagTitle")
    band_y, band_h = UI.content_band_y_h(st, fraction=0.75, min_h=7.5, max_h=11.5)
    row_h = band_h / max(1, len(rows))
    status_fill = {
        "G": c.get("semantic_success") or c["accent"],
        "green": c.get("semantic_success") or c["accent"],
        "A": c.get("chart_series2") or c["muted"],
        "amber": c.get("chart_series2") or c["muted"],
        "R": c.get("risk") or c["accent"],
        "red": c.get("risk") or c["accent"],
    }
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            row = {"label": str(row), "status": "G"}
        y = band_y + i * row_h
        st_code = str(row.get("status") or "G")
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RagRow{i + 1}", "preset": st.preset,
                "fill": c["surface"], "line": "none",
                "text": f"  {row.get('label') or 'Item'}",
                "x": UI.cm(st.margin), "y": UI.cm(y),
                "width": UI.cm(st.usable_w - 3.2),
                "height": UI.cm(max(1.3, row_h - 0.15)),
                "font": st.body_font, "size": str(st.body_pt),
                "bold": "true", "color": c["text_on_surface"], "valign": "middle",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"RagDot{i + 1}", "preset": "ellipse",
                "fill": status_fill.get(st_code, c["muted"]), "line": "none",
                "text": st_code[:1].upper(),
                "x": UI.cm(st.margin + st.usable_w - 2.6), "y": UI.cm(y + 0.25),
                "width": "2.2cm", "height": UI.cm(max(1.0, row_h - 0.5)),
                "font": st.heading_font, "size": "16", "bold": "true",
                "color": c["on_accent"], "align": "center", "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "Red needs an owner before the meeting ends."))
    return ops


def build_calendar_grid(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Calendar")
    cells = slots.get("cells") or [((i * 3 + j) % 4) for i in range(4) for j in range(7)]
    if not isinstance(cells, list):
        cells = [0] * 28
    cells = [int(x) if str(x).isdigit() else 0 for x in cells[:35]]
    cols, rows = 7, min(5, max(4, (len(cells) + 6) // 7))
    cells = (cells + [0] * 35)[: cols * rows]
    ops = _title_ops(st, title, "CalTitle")
    band_y, band_h = UI.content_band_y_h(st, fraction=0.75, min_h=8.0, max_h=11.5)
    gap = 0.12
    cw = (st.usable_w - gap * (cols - 1)) / cols
    ch = (band_h - gap * (rows - 1)) / rows
    fills = [c["surface"], c.get("chart_series2") or c["muted"], c["accent"], c["accent"]]
    for i, val in enumerate(cells):
        r, col = divmod(i, cols)
        level = max(0, min(3, int(val)))
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"Cal{i + 1}", "preset": st.preset,
                "fill": fills[level], "line": "none",
                "x": UI.cm(st.margin + col * (cw + gap)),
                "y": UI.cm(band_y + r * (ch + gap)),
                "width": UI.cm(cw), "height": UI.cm(ch),
            },
        })
    ops.extend(_notes(slots, "Point at the densest week."))
    return ops


def build_logo_band(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    logos = slots.get("logos") or slots.get("items") or ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
    if not isinstance(logos, list):
        logos = [str(logos)]
    items = [{"label": str(x if not isinstance(x, dict) else x.get("label") or x.get("name") or "Logo"),
              "detail": ""} for x in logos[:6]]
    ops = _equal_row(
        st, title=str(slots.get("title") or "Partners"),
        title_name="LogoTitle", items=items, name_prefix="Logo",
    )
    ops.extend(_notes(slots, "Logos are social proof — keep the row quiet."))
    return ops


def build_geo_pins(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    items = _items(slots.get("regions") or slots.get("pins") or slots.get("items"),
                   n_min=3, n_max=6, defaults=["AMER", "EMEA", "APAC"])
    ops = _equal_row(
        st, title=str(slots.get("title") or "Regions"),
        title_name="GeoTitle", items=items, name_prefix="Geo",
        accent_ends=True,
    )
    ops.extend(_notes(slots, "User basemap only — no vendor map art."))
    return ops


def build_device_chrome(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Product")
    caption = str(slots.get("caption") or slots.get("body") or "Screenshot placeholder")
    ops = _title_ops(st, title, "DeviceTitle")
    # phone-ish frame centered
    fw, fh = 9.0, 12.0
    fx = (UI.CANVAS_W - fw) / 2
    fy = st.content_top + 0.3
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "DeviceFrame", "preset": st.preset,
            "fill": c["surface"], "line": "none",
            "x": UI.cm(fx), "y": UI.cm(fy),
            "width": UI.cm(fw), "height": UI.cm(fh),
        },
    })
    ops.append({
        "command": "add", "parent": "/slide[last()]", "type": "shape",
        "props": {
            "name": "DeviceScreen", "preset": "rect",
            "fill": c.get("content_background") or c["background"], "line": "none",
            "text": caption,
            "x": UI.cm(fx + 0.45), "y": UI.cm(fy + 0.8),
            "width": UI.cm(fw - 0.9), "height": UI.cm(fh - 1.5),
            "font": st.body_font, "size": str(st.body_pt),
            "color": c["muted"], "align": "center", "valign": "middle",
        },
    })
    ops.extend(_notes(slots, "Swap in a real screenshot via image ops."))
    return ops


STRUCTURAL_BUILDERS: dict[str, Any] = {
    "hub_orbit": build_hub_orbit,
    "pipeline_rail": build_pipeline_rail,
    "journey_path": build_journey_path,
    "framework_bar": build_framework_bar,
    "fishbone_spine": build_fishbone_spine,
    "pyramid_stack": build_pyramid_stack,
    "iceberg_depth": build_iceberg_depth,
    "pillar_band": build_pillar_band,
    "okr_tree": build_okr_tree,
    "timeline_rail": build_timeline_rail,
    "swimlane_roadmap": build_swimlane_roadmap,
    "gantt_track": build_gantt_track,
    "team_cards": build_team_cards,
    "persona_split": build_persona_split,
    "kpi_grid": build_kpi_grid,
    "stat_row": build_stat_row,
    "scale_meter": build_scale_meter,
    "pricing_tiers": build_pricing_tiers,
    "section_wash": build_section_wash,
    "agenda_list": build_agenda_list,
    "quote_mark": build_quote_mark,
    "bullet_stack": build_bullet_stack,
    "close_mark": build_close_mark,
    "canvas_bmc": build_canvas_bmc,
    "pestle_cells": build_pestle_cells,
    "scorecard_grid": build_scorecard_grid,
    "risk_heat": build_risk_heat,
    "raci_grid": build_raci_grid,
    "empathy_quad": build_empathy_quad,
    "rich_matrix": build_rich_matrix,
    "vs_columns": build_vs_columns,
    "hex_honey": build_hex_honey,
    "mindmap_radial": build_mindmap_radial,
    "venn_duo": build_venn_duo,
    "ring_segments": build_ring_segments,
    "case_band": build_case_band,
    "rag_status": build_rag_status,
    "calendar_grid": build_calendar_grid,
    "logo_band": build_logo_band,
    "geo_pins": build_geo_pins,
    "device_chrome": build_device_chrome,
}
