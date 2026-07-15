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


MOTIF_BUILDERS: dict[str, MotifBuilder] = {
    "split_hero": build_split_hero,
    "card_row": build_card_row,
    "step_rail": build_step_rail,
    "kpi_hero": build_kpi_hero,
    "stair_ascent": build_stair_ascent,
    "check_stack": build_check_stack,
    "tile_row": build_tile_row,
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
