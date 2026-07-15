"""Visual motif library — SmartArt-like originals for designmd-pptx.

Motifs are **owned geometry** derived from license-safe structural analysis of
premium packs (Infograpify local only). They are not PowerPoint SmartArt
(``dgm:``) and never embed vendor shapes, icons, or media.

Recipes thin-wrap ``render_motif`` so chrome stays consistent. Spacing always
comes from ``ui_kit.StageMetrics``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from . import layout as L
from . import ui_kit as UI

_CATALOG_PATH = Path(__file__).resolve().parent / "motifs" / "catalog.json"

MotifBuilder = Callable[[dict[str, Any], dict[str, Any]], list[dict[str, Any]]]


def catalog() -> dict[str, Any]:
    if not _CATALOG_PATH.is_file():
        return {"schema": 1, "motifs": []}
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def list_motifs() -> list[str]:
    return [str(m.get("id")) for m in catalog().get("motifs") or [] if m.get("id")]


def motif_info(motif_id: str) -> dict[str, Any] | None:
    for m in catalog().get("motifs") or []:
        if m.get("id") == motif_id:
            return dict(m)
    return None


def _notes(slots: dict[str, Any], default: str) -> list[dict[str, Any]]:
    text = slots.get("notes") or default
    return [UI.notes_op(str(text))]


def _rename_prefix(ops: list[dict[str, Any]], mapping: list[tuple[str, str]]) -> None:
    for op in ops:
        props = op.get("props") or {}
        name = str(props.get("name") or "")
        for old, new in mapping:
            if name.startswith(old):
                props["name"] = name.replace(old, new, 1)
                break


# ---------------------------------------------------------------------------
# Motif builders (original geometry)
# ---------------------------------------------------------------------------

def build_split_hero(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    """Two equal panels — comparison / mission-vision / before-after."""
    st = UI.stage_metrics(tokens)
    left = slots.get("left") or {}
    right = slots.get("right") or {}
    if not isinstance(left, dict):
        left = {"title": "Left", "body": str(left)}
    if not isinstance(right, dict):
        right = {"title": "Right", "body": str(right)}

    def body_of(side: dict) -> str:
        b = side.get("body") or side.get("text") or ""
        if isinstance(b, list):
            return UI.bullets_text(b, limit=5)
        return str(b).strip()

    accent_right = slots.get("accent_right", True)
    ops = UI.comparison_panels(
        st,
        title=str(slots.get("title") or "Compare"),
        left_title=str(left.get("title") or "Before"),
        left_body=body_of(left),
        right_title=str(right.get("title") or "After"),
        right_body=body_of(right),
        title_name=str(slots.get("title_name") or "SplitTitle"),
        left_fill=st.c["surface"],
        right_fill=st.c["accent"] if accent_right else st.c["surface"],
    )
    prefix = slots.get("name_prefix")
    if prefix:
        _rename_prefix(ops, [
            ("CmpPanel", f"{prefix}Panel"),
            ("CmpHead", f"{prefix}Head"),
            ("CmpBody", f"{prefix}Body"),
        ])
    ops.extend(_notes(slots, "State the single change that matters."))
    return ops


def build_card_row(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    """N equal feature cards with index discs (card-row rhythm)."""
    st = UI.stage_metrics(tokens)
    title = str(slots.get("title") or "Capabilities")
    cards = slots.get("cards") or []
    if not isinstance(cards, list) or not cards:
        cards = [{"title": "One", "body": "Detail."}]
    cards = cards[: max(2, min(4, len(cards)))]
    bg = st.c["content_background"]
    title_name = str(slots.get("title_name") or "FeatTitle")

    def build(d: L.Density) -> L.Box:
        cols = [
            UI.feature_card(
                st,
                index=i + 1,
                title=str(c.get("title", "")),
                body=str(c.get("body", "")),
                density=d,
            )
            for i, c in enumerate(cards)
        ]
        return UI.titled_stage(
            st, title, UI.equal_columns(cols, st, density=d),
            title_name=title_name, density=d,
        )

    ops = UI.solve_stage(build, bg=bg)
    ops.extend(_notes(slots, "Three cards max on a hero slide; cut copy first."))
    return ops


def build_step_rail(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    """Horizontal numbered steps + optional glued connectors."""
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Process")
    steps = slots.get("steps") or ["Input", "Transform", "Output"]
    if not isinstance(steps, list):
        steps = [str(steps)]
    n = max(2, min(5, len(steps)))
    steps = steps[:n]

    usable = st.usable_w
    gap = st.gap
    col = (usable - gap * (n - 1)) / n
    xs = [st.margin + i * (col + gap) for i in range(n)]
    box_h = min(5.0, max(3.8, st.content_h * 0.42))
    free = max(0.0, UI.CANVAS_H - st.content_top - st.content_bottom - box_h)
    y = st.content_top + free * 0.35
    slide_index = slots.get("slide_index")

    ops: list[dict[str, Any]] = [
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
                "name": "ProcTitle",
                "text": title,
                "x": UI.cm(st.margin),
                "y": UI.cm(max(1.15, st.margin * 0.55)),
                "width": UI.cm(st.usable_w),
                "height": UI.cm(st.title_band),
                "font": st.heading_font,
                "size": str(st.title_pt),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
    ]
    names: list[str] = []
    for i, step in enumerate(steps):
        if isinstance(step, dict):
            label = str(step.get("label", step.get("title", f"Step {i + 1}")))
            detail = str(step.get("detail") or step.get("body") or "").strip()
            text = f"{i + 1}\n{label}" + (f"\n{detail}" if detail else "")
        else:
            text = f"{i + 1}\n{step}"
        name = f"Proc{i + 1}"
        names.append(name)
        fill = c["accent"] if i == 0 or i == n - 1 else c["surface"]
        tc = c["on_accent"] if fill == c["accent"] else c["text_on_surface"]
        ops.append({
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": name,
                "preset": st.preset,
                "fill": fill,
                "line": "none",
                "text": text,
                "x": UI.cm(xs[i]),
                "y": UI.cm(y),
                "width": UI.cm(col),
                "height": UI.cm(box_h),
                "font": st.heading_font,
                "size": str(max(16, min(20, st.body_pt))),
                "bold": "true",
                "color": tc,
                "align": "center",
                "valign": "middle",
            },
        })
    if slide_index is not None:
        for i in range(len(names) - 1):
            a, bname = names[i], names[i + 1]
            ops.append({
                "command": "add",
                "parent": "/slide[last()]",
                "type": "connector",
                "props": {
                    "from": f"/slide[{int(slide_index)}]/shape[@name={a}]",
                    "to": f"/slide[{int(slide_index)}]/shape[@name={bname}]",
                    "shape": "straight",
                    "color": c["muted"],
                    "tailEnd": "triangle",
                },
            })
    ops.extend(_notes(slots, "Walk left to right; stop on the bottleneck."))
    return ops


def build_kpi_hero(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    """Single mega metric — centered stack."""
    st = UI.stage_metrics(tokens)
    c = st.c
    t = tokens.get("type") or {}
    value = str(slots.get("value", "—"))
    label = str(slots.get("label", "Headline metric"))
    context = str(slots.get("context") or "")
    mega = int(t.get("mega_pt", max(72, int(t.get("kpi_pt", 60) * 1.35))))
    mega = min(96, max(56, mega))
    color = c["risk"] if slots.get("watch") else c["accent"]
    m, usable = st.margin, st.usable_w
    value_h, label_h, ctx_h = 6.4, 1.7, 2.2
    stack = value_h + st.title_to_body + label_h
    if context:
        stack += st.gap * 0.6 + ctx_h
    free = max(0.0, UI.CANVAS_H - 2 * m - stack)
    y0 = m + free * 0.35
    ops: list[dict[str, Any]] = [
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
                "name": "BigValue",
                "text": value,
                "x": UI.cm(m),
                "y": UI.cm(y0),
                "width": UI.cm(usable),
                "height": UI.cm(value_h),
                "font": st.heading_font,
                "size": str(mega),
                "bold": "true",
                "color": color,
                "align": "center",
                "valign": "middle",
                "fill": "none",
            },
        },
        {
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "BigLabel",
                "text": label,
                "x": UI.cm(m),
                "y": UI.cm(y0 + value_h + st.title_to_body),
                "width": UI.cm(usable),
                "height": UI.cm(label_h),
                "font": st.heading_font,
                "size": str(max(22, st.section_pt)),
                "bold": "true",
                "color": c["text_on_content"],
                "align": "center",
                "fill": "none",
            },
        },
    ]
    if context:
        ops.append({
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": "BigContext",
                "text": context,
                "x": UI.cm(m + st.pad),
                "y": UI.cm(y0 + value_h + st.title_to_body + label_h + st.gap * 0.5),
                "width": UI.cm(usable - 2 * st.pad),
                "height": UI.cm(ctx_h),
                "font": st.body_font,
                "size": str(st.body_pt),
                "color": c["muted"],
                "align": "center",
                "fill": "none",
            },
        })
    ops.extend(_notes(slots, "Let the number land; one sentence of context."))
    return ops


def build_stair_ascent(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Ascent")
    raw = slots.get("steps") or slots.get("levels") or []
    steps: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for s in raw:
            if isinstance(s, dict):
                steps.append(s)
            else:
                steps.append({"label": str(s)})
    if len(steps) < 3:
        steps = [{"label": s} for s in (
            "Aware", "Repeatable", "Defined", "Managed", "Optimising")]
    steps = steps[:6]
    n = len(steps)
    m = st.margin
    step_w = st.usable_w / n
    band_y, band_h = UI.content_band_y_h(
        st, fraction=0.8, min_h=7.5, max_h=11.5, settle=0.15)
    base_y = band_y + band_h
    ops: list[dict[str, Any]] = [
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
                "name": "StairsTitle",
                "text": title,
                "x": UI.cm(m),
                "y": UI.cm(max(1.15, m * 0.55)),
                "width": UI.cm(st.usable_w),
                "height": UI.cm(st.title_band),
                "font": st.heading_font,
                "size": str(st.title_pt),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
    ]
    for i, step in enumerate(steps):
        h = band_h * (0.45 + 0.55 * (i / max(1, n - 1)))
        y = base_y - h
        x = m + i * step_w
        detail = str(step.get("detail") or step.get("body") or "").strip()
        label = f"{i + 1}\n{step.get('label', '')}" + (f"\n{detail}" if detail else "")
        ops.append({
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": f"Stair{i + 1}",
                "preset": st.preset,
                "fill": c["accent"] if i == n - 1 else c["surface"],
                "line": "none",
                "text": label,
                "x": UI.cm(x + 0.1),
                "y": UI.cm(y),
                "width": UI.cm(step_w - 0.2),
                "height": UI.cm(h),
                "font": st.heading_font,
                "size": str(max(14, min(18, st.body_pt))),
                "bold": "true",
                "color": c["on_accent"] if i == n - 1 else c["text_on_surface"],
                "align": "center",
                "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "You cannot skip a stair — name the exit criteria."))
    return ops


def build_check_stack(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Checklist")
    raw = slots.get("items") or slots.get("checks") or []
    norm: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for it in raw[:8]:
            if isinstance(it, dict):
                norm.append({
                    "label": str(it.get("label") or it.get("text") or ""),
                    "done": bool(it.get("done", it.get("checked", True))),
                })
            else:
                s = str(it)
                done = s.startswith("[x]") or s.startswith("✓")
                norm.append({"label": s.lstrip("[x]✓ ").strip(), "done": done})
    if not norm:
        norm = [{"label": "Item", "done": False}]
    band_y, band_h = UI.content_band_y_h(
        st, fraction=0.75, min_h=6.0, max_h=11.0, settle=0.2)
    row_h = min(2.0, band_h / max(1, len(norm)))
    ops: list[dict[str, Any]] = [
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
                "name": "CheckTitle",
                "text": title,
                "x": UI.cm(st.margin),
                "y": UI.cm(max(1.15, st.margin * 0.55)),
                "width": UI.cm(st.usable_w),
                "height": UI.cm(st.title_band),
                "font": st.heading_font,
                "size": str(st.title_pt),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
    ]
    for i, it in enumerate(norm):
        y = band_y + i * row_h
        mark = "✓" if it["done"] else "○"
        fill = c["surface"] if it["done"] else c["content_background"]
        ops.append({
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": {
                "name": f"CheckRow{i + 1}",
                "preset": st.preset,
                "fill": fill,
                "line": "none",
                "text": f"{mark}  {it['label']}",
                "x": UI.cm(st.margin),
                "y": UI.cm(y),
                "width": UI.cm(st.usable_w),
                "height": UI.cm(max(1.3, row_h - 0.18)),
                "font": st.body_font,
                "size": str(st.body_pt),
                "bold": "true" if not it["done"] else "false",
                "color": c["text_on_surface"],
                "valign": "middle",
            },
        })
    ops.extend(_notes(slots, "Open items need an owner before the meeting ends."))
    return ops


def build_tile_row(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    st = UI.stage_metrics(tokens)
    items = slots.get("items") or slots.get("pieces") or []
    norm: list[dict[str, str]] = []
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                norm.append({
                    "label": str(it.get("label") or it.get("title") or ""),
                    "detail": str(it.get("detail") or it.get("body") or ""),
                })
            else:
                norm.append({"label": str(it), "detail": ""})
    if len(norm) < 3:
        norm = [{"label": s, "detail": ""} for s in ("A", "B", "C", "D")]
    ops = UI.equal_tile_row_ops(
        st,
        title=str(slots.get("title") or "Parts"),
        title_name=str(slots.get("title_name") or "TileTitle"),
        items=norm[:6],
        name_prefix=str(slots.get("name_prefix") or "Tile"),
        accent_every=int(slots.get("accent_every") or 2),
    )
    ops.extend(_notes(slots, "Name the piece that is under-invested."))
    return ops


def build_sparse_hero(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    """Cover / sparse hero — large type, accent bar, optional left edge (ref: sparse_hero)."""
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Title")
    subtitle = str(slots.get("subtitle") or "")
    meta = str(slots.get("meta") or "")
    bg = tokens.get("background_gradient") or c["background"]
    placement = str(slots.get("placement") or st.title_placement or "top")
    left = placement == "left"
    m, usable = st.margin, st.usable_w
    align = "left" if left else "center"
    title_y = 5.0 if left else 5.8
    title_h = 4.0 if left else 3.2
    sub_y = title_y + title_h + 0.3
    bar_w = 4.8 if left else 5.2
    bar_x = m if left else (UI.CANVAS_W - bar_w) / 2
    ops: list[dict[str, Any]] = [
        {
            "command": "add", "parent": "/", "type": "slide",
            "props": {"layout": "blank", "background": bg},
        },
    ]
    if left:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "CoverEdge", "preset": "rect",
                "fill": c["accent"], "line": "none",
                "x": "0cm", "y": "0cm", "width": "0.35cm", "height": "19.05cm",
            },
        })
    ops.extend([
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "CoverTitle", "text": title,
                "x": UI.cm(m), "y": UI.cm(title_y),
                "width": UI.cm(usable), "height": UI.cm(title_h),
                "font": st.heading_font, "size": str(st.cover_pt),
                "bold": "true", "color": c["text"], "align": align,
                "valign": "bottom" if left else "middle", "fill": "none",
            },
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "CoverAccent", "preset": "rect",
                "fill": c["accent"], "line": "none",
                "x": UI.cm(bar_x), "y": UI.cm(sub_y - 0.2),
                "width": UI.cm(bar_w), "height": "0.14cm",
            },
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "CoverSubtitle", "text": subtitle,
                "x": UI.cm(m), "y": UI.cm(sub_y + 0.2),
                "width": UI.cm(min(usable, 26.0) if left else usable),
                "height": "1.6cm",
                "font": st.body_font, "size": str(max(18, st.body_pt)),
                "color": c["muted"], "align": align, "fill": "none",
            },
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "CoverMeta", "text": meta,
                "x": UI.cm(m), "y": UI.cm(UI.CANVAS_H - m - 0.9),
                "width": UI.cm(usable), "height": "0.9cm",
                "font": st.body_font, "size": str(max(12, st.caption_pt)),
                "color": c["muted"], "align": align, "fill": "none",
            },
        },
    ])
    ops.extend(_notes(slots, "Hold the product name, then the promise."))
    return ops


def build_kpi_band(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    """2–4 KPI cards in a band (ref: kpi_band / kpi_band_3|4)."""
    st = UI.stage_metrics(tokens)
    c = st.c
    t = tokens.get("type") or {}
    title = str(slots.get("title") or "Key metrics")
    kpis = slots.get("kpis") or []
    if not isinstance(kpis, list) or not kpis:
        kpis = [
            {"value": "—", "label": "Metric A"},
            {"value": "—", "label": "Metric B"},
            {"value": "—", "label": "Metric C"},
        ]
    n = max(2, min(4, len(kpis)))
    kpis = kpis[:n]
    kpi_pt = int(t.get("kpi_pt", 60))
    micro = max(12, st.caption_pt)

    def _kpi_card(i: int) -> L.Box:
        kpi = kpis[i] if isinstance(kpis[i], dict) else {}
        watch = bool(kpi.get("watch"))
        fill = c["risk"] if watch else c["surface"]
        tc = c["on_accent"] if watch else c["text_on_surface"]
        mc = "FFFFFF" if watch else c["muted"]
        chip = str(kpi.get("chip") or "")
        return L.VStack(
            weight=1,
            name=f"Kpi{i + 1}Bg",
            pad=(st.pad * 0.85, 0.35, st.pad * 0.7, 0.35),
            gap=0.35,
            props={"preset": st.preset, "fill": fill, "line": "none"},
            children=[
                L.Spacer(weight=1),
                L.Text(
                    str(kpi.get("value", "—")), pt=kpi_pt, name=f"Kpi{i + 1}Value",
                    min_cm=2.0, max_cm=4.5,
                    props={
                        "font": st.heading_font, "size": str(kpi_pt),
                        "bold": "true", "color": tc, "align": "center", "fill": "none",
                    },
                ),
                L.Text(
                    str(kpi.get("label", "")), pt=micro, name=f"Kpi{i + 1}Label",
                    min_cm=0.85, max_cm=1.4,
                    props={
                        "font": st.body_font, "size": str(micro),
                        "color": mc, "align": "center", "fill": "none",
                    },
                ),
                L.Text(
                    chip, pt=micro, name=f"Kpi{i + 1}Chip",
                    min_cm=0.55, max_cm=1.0,
                    props={
                        "font": st.body_font, "size": str(micro), "bold": "true",
                        "color": c["accent"] if not watch else mc,
                        "align": "center", "fill": "none",
                    },
                ),
                L.Spacer(weight=1),
            ],
        )

    def build(d: L.Density) -> L.Box:
        return UI.titled_stage(
            st, title,
            L.HStack(
                [_kpi_card(i) for i in range(len(kpis))],
                gap=st.gap * d.gap, weight=1, name="KpiBand",
            ),
            title_name="KpiTitle", density=d,
        )

    ops = UI.solve_stage(build, bg=c["content_background"])
    ops.extend(_notes(slots, "Walk KPIs left to right; pause on any watch metric."))
    return ops


def build_funnel_cascade(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    """Decreasing-width funnel bands (ref: process_flow / funnel packs)."""
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Funnel")
    stages = slots.get("stages") or slots.get("steps") or [
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
    band_y, band_h = UI.content_band_y_h(
        st, fraction=0.82, min_h=8.0, max_h=12.0, settle=0.12)
    gap = max(0.22, st.gap * 0.25)
    row_h = (band_h - gap * (n - 1)) / n
    m, usable = st.margin, st.usable_w
    ops: list[dict[str, Any]] = [
        {
            "command": "add", "parent": "/", "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "FunnelTitle", "text": title,
                "x": UI.cm(m), "y": UI.cm(max(1.15, m * 0.55)),
                "width": UI.cm(usable), "height": UI.cm(st.title_band),
                "font": st.heading_font, "size": str(st.title_pt),
                "bold": "true", "color": c["text_on_content"], "fill": "none",
            },
        },
    ]
    for i, stage in enumerate(stages):
        if isinstance(stage, str):
            label, value = stage, ""
        else:
            label = str(stage.get("label") or stage.get("title") or f"Stage {i + 1}")
            value = str(stage.get("value") or stage.get("metric") or "")
        frac = 1.0 - (i / max(1, n - 1)) * 0.55
        w = usable * frac
        x = m + (usable - w) / 2
        y = band_y + i * (row_h + gap)
        fill = c["accent"] if i == n - 1 else c["surface"]
        tc = c["on_accent"] if i == n - 1 else c["text_on_surface"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"FunnelBand{i + 1}", "preset": st.preset,
                "fill": fill, "line": "none",
                "x": UI.cm(x), "y": UI.cm(y),
                "width": UI.cm(w), "height": UI.cm(row_h),
            },
        })
        text = f"{label}  ·  {value}" if value else label
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"FunnelLabel{i + 1}", "text": text,
                "x": UI.cm(x + st.pad * 0.5),
                "y": UI.cm(y + row_h * 0.22),
                "width": UI.cm(max(2.0, w - st.pad)),
                "height": UI.cm(row_h * 0.55),
                "font": st.heading_font,
                "size": str(max(16, min(22, st.section_pt - 4))),
                "bold": "true", "color": tc, "align": "center", "fill": "none",
            },
        })
    ops.extend(_notes(slots, "Name the drop-off between the two biggest deltas."))
    return ops


def build_matrix_quad(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    """2×2 matrix cells (ref: matrix_like) — content-height titles, optional axes.

    Axis chrome is fixed outside the solved grid so labels never overlap
    quadrant surfaces (regression: AxisX/AxisY vs Quad*Bg).
    """
    st = UI.stage_metrics(tokens)
    c = st.c
    title = str(slots.get("title") or "Matrix")
    quads = slots.get("quadrants") or [
        {"title": f"Q{i + 1}", "body": ""} for i in range(4)
    ]
    if not isinstance(quads, list):
        quads = []
    quads = (list(quads) + [{"title": "", "body": ""}] * 4)[:4]
    axes = slots.get("axes") or {}
    if not isinstance(axes, dict):
        axes = {}
    title_pt = max(16, st.section_pt - 4)
    has_y = bool(axes.get("y"))
    has_x = bool(axes.get("x"))
    # Reserve bands for axis labels (same contract as pre-motif matrix_2x2).
    grid_top = 3.9 if has_y else st.content_top
    grid_bottom = 17.0 if has_x else (UI.CANVAS_H - st.margin)
    grid_h = max(4.0, grid_bottom - grid_top)

    def _quad(i: int, body_pt: int) -> L.Box:
        q = quads[i] if isinstance(quads[i], dict) else {}
        return L.VStack(
            weight=1,
            name=f"Quad{i + 1}Bg",
            pad=(st.pad * 0.7, st.pad * 0.75, st.pad * 0.7, st.pad * 0.75),
            gap=0.35,
            props={"preset": st.preset, "fill": c["surface"], "line": "none"},
            children=[
                L.Text(
                    str(q.get("title", "")), pt=title_pt, name=f"Quad{i + 1}Title",
                    min_cm=1.0, max_cm=2.2,
                    props={
                        "font": st.heading_font, "size": str(title_pt),
                        "bold": "true", "color": c["text_on_surface"], "fill": "none",
                    },
                ),
                L.Text(
                    str(q.get("body", "")), pt=body_pt, name=f"Quad{i + 1}Body",
                    min_cm=1.2, max_cm=5.0,
                    props={
                        "font": st.body_font, "size": str(body_pt),
                        "color": c["muted"], "fill": "none",
                    },
                ),
                L.Spacer(weight=1),
            ],
        )

    def build(d: L.Density) -> L.Box:
        bpt = L.floored_pt(st.body_pt, d)
        return L.VStack(
            gap=st.gap * d.gap, weight=1, name="matrix_grid",
            children=[
                L.HStack(
                    [_quad(0, bpt), _quad(1, bpt)],
                    gap=st.gap * d.gap, weight=1,
                ),
                L.HStack(
                    [_quad(2, bpt), _quad(3, bpt)],
                    gap=st.gap * d.gap, weight=1,
                ),
            ],
        )

    placed, _d = L.solve_adaptive(
        build, st.margin, grid_top, st.usable_w, grid_h,
    )
    ops: list[dict[str, Any]] = [
        {
            "command": "add", "parent": "/", "type": "slide",
            "props": {"layout": "blank", "background": c["content_background"]},
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "MatrixTitle", "text": title,
                "x": UI.cm(st.margin),
                "y": UI.cm(max(1.15, st.margin * 0.55)),
                "width": UI.cm(st.usable_w),
                "height": UI.cm(st.title_band),
                "font": st.heading_font, "size": str(st.title_pt),
                "bold": "true", "color": c["text"], "fill": "none",
            },
        },
    ]
    for p in placed:
        props = dict(p.box.props)
        op_type = props.pop("_type", "shape")
        for k in list(props):
            if k.startswith("_"):
                props.pop(k, None)
        props.setdefault("name", p.name)
        if p.box.kind == "text" and "text" not in props:
            props["text"] = p.box.text
        props.update(
            {"x": UI.cm(p.x), "y": UI.cm(p.y), "width": UI.cm(p.w), "height": UI.cm(p.h)}
        )
        if p.box.kind == "spacer":
            continue
        ops.append(
            {"command": "add", "parent": "/slide[last()]", "type": op_type, "props": props}
        )

    micro = str(max(12, st.caption_pt))
    if has_x:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "AxisX", "text": f"→ {axes['x']}",
                "x": UI.cm(st.margin), "y": "17.5cm",
                "width": UI.cm(st.usable_w), "height": "0.9cm",
                "font": st.body_font, "size": micro,
                "color": c["muted"], "align": "center", "fill": "none",
            },
        })
    if has_y:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "AxisY", "text": f"↑ {axes['y']}",
                "x": UI.cm(st.margin), "y": "3.0cm",
                "width": "12cm", "height": "0.8cm",
                "font": st.body_font, "size": micro,
                "color": c["muted"], "fill": "none",
            },
        })
    ops.extend(_notes(slots, "Name the quadrant that needs a decision this quarter."))
    return ops


def build_section_mark(tokens: dict[str, Any], slots: dict[str, Any]) -> list[dict[str, Any]]:
    """Numbered section opener (ref: narrative_chrome)."""
    st = UI.stage_metrics(tokens)
    c = st.c
    number = str(slots.get("number") or "01")
    title = str(slots.get("title") or "Section")
    blurb = str(slots.get("blurb") or slots.get("body") or "")
    m = st.margin
    ops: list[dict[str, Any]] = [
        {
            "command": "add", "parent": "/", "type": "slide",
            "props": {"layout": "blank", "background": c["background"]},
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "OpenerAccentBar", "preset": "rect",
                "fill": c["accent"], "line": "none",
                "x": UI.cm(m), "y": "6.2cm", "width": "1.1cm", "height": "6.2cm",
            },
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "OpenerNumber", "text": number,
                "x": UI.cm(m + 1.6), "y": "5.6cm",
                "width": "8cm", "height": "2.4cm",
                "font": st.heading_font, "size": "54",
                "bold": "true", "color": c["accent"], "fill": "none",
            },
        },
        {
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "OpenerTitle", "text": title,
                "x": UI.cm(m + 1.6), "y": "8.2cm",
                "width": UI.cm(st.usable_w - 1.6), "height": "2.6cm",
                "font": st.heading_font, "size": str(st.title_pt),
                "bold": "true", "color": c["text"], "fill": "none",
            },
        },
    ]
    if blurb:
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": "OpenerBlurb", "text": blurb,
                "x": UI.cm(m + 1.6), "y": "11.0cm",
                "width": "22cm", "height": "2.2cm",
                "font": st.body_font, "size": str(st.body_pt),
                "color": c["muted"], "fill": "none",
            },
        })
    ops.extend(_notes(slots, "Pause on the section number before the title."))
    return ops


MOTIF_BUILDERS: dict[str, MotifBuilder] = {
    "split_hero": build_split_hero,
    "card_row": build_card_row,
    "step_rail": build_step_rail,
    "kpi_hero": build_kpi_hero,
    "kpi_band": build_kpi_band,
    "stair_ascent": build_stair_ascent,
    "check_stack": build_check_stack,
    "tile_row": build_tile_row,
    "sparse_hero": build_sparse_hero,
    "funnel_cascade": build_funnel_cascade,
    "matrix_quad": build_matrix_quad,
    "section_mark": build_section_mark,
}


def render_motif(
    motif_id: str,
    tokens: dict[str, Any],
    slots: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Render a named motif into officecli batch ops."""
    builder = MOTIF_BUILDERS.get(motif_id)
    if not builder:
        known = ", ".join(sorted(MOTIF_BUILDERS))
        raise KeyError(f"unknown motif {motif_id!r}; known: {known}")
    return builder(tokens, slots or {})


__all__ = [
    "catalog",
    "list_motifs",
    "motif_info",
    "render_motif",
    "MOTIF_BUILDERS",
]
