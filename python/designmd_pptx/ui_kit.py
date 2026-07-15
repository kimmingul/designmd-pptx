"""Shared UI contract for recipe chrome (React-like spacing system).

Recipes MUST derive stage geometry from ``StageMetrics`` instead of inventing
one-off cm constants. The contract mirrors a simple design system:

* **margin** — outer stage inset (from tokens / whitespace density)
* **gap** — between siblings (cards, columns)
* **pad** — inset inside a card/surface (≈ 0.5× margin, clamped)
* **title_band** — fixed height for slide titles so columns share a baseline
* **body text is content-height** — never ``weight=1`` on Text leaves
* **free space goes to Spacer** — empty surface, not a hollow text frame

Layout trees use ``layout.py`` (flex stacks). Fixed-cm recipes use the same
metrics via helpers so both geometry systems stay in rhythm.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from . import layout as L

CANVAS_W = L.CANVAS_W  # 33.87
CANVAS_H = L.CANVAS_H  # 19.05


@dataclass(frozen=True)
class StageMetrics:
    """Resolved spacing + type scale for one deck (one DESIGN.md compile)."""

    margin: float
    gap: float
    pad: float
    title_to_body: float
    title_band: float
    card_title_band: float
    usable_w: float
    content_top: float
    content_bottom: float
    content_h: float
    # type
    title_pt: int
    section_pt: int
    body_pt: int
    caption_pt: int
    cover_pt: int
    heading_font: str
    body_font: str
    # chrome
    preset: str
    colors: dict[str, str]
    title_placement: str
    density_name: str

    @property
    def c(self) -> dict[str, str]:
        return self.colors


def stage_metrics(tokens: dict[str, Any]) -> StageMetrics:
    """Single source of spacing truth for recipes."""
    c = tokens["colors"]
    t = tokens["type"]
    m = float(tokens.get("margin_cm", 1.27))
    g = float(tokens.get("gap_cm", 0.76))
    # Inner pad tracks margin (spacious decks get roomier cards).
    pad = max(0.85, min(1.4, m * 0.5))
    title_to_body = max(0.45, min(0.75, m * 0.28))
    title_band = 1.55
    card_title_band = 2.15  # two-line section titles at ~24–26pt
    usable = CANVAS_W - 2 * m
    # Top content starts after a title band + gap (when a slide has a title).
    content_top = max(1.15, m * 0.55) + title_band + max(0.7, m * 0.38)
    content_bottom = m
    content_h = max(4.0, CANVAS_H - content_top - content_bottom)
    comp = tokens.get("composition") or {}
    return StageMetrics(
        margin=m,
        gap=max(0.55, g),
        pad=pad,
        title_to_body=title_to_body,
        title_band=title_band,
        card_title_band=card_title_band,
        usable_w=usable,
        content_top=content_top,
        content_bottom=content_bottom,
        content_h=content_h,
        title_pt=int(t.get("title_pt", 36)),
        section_pt=int(t.get("section_pt", 24)),
        body_pt=int(t.get("body_pt", 18)),
        caption_pt=int(t.get("caption_pt", 12)),
        cover_pt=int(t.get("cover_pt", 44)),
        heading_font=str(t.get("heading_font", "Arial")),
        body_font=str(t.get("body_font", "Arial")),
        preset=str(tokens.get("shape", {}).get("card_preset", "roundRect")),
        colors=c,
        title_placement=str(comp.get("title_placement") or "top"),
        density_name=str(comp.get("whitespace_density") or "comfortable"),
    )


def cm(n: float) -> str:
    s = f"{n:.2f}".rstrip("0").rstrip(".")
    return f"{s}cm"


def body_height_cm(
    text: str,
    *,
    body_pt: int,
    width_cm: float | None = None,
    min_cm: float = 1.4,
    max_cm: float = 8.0,
) -> float:
    """Content-height estimate for body copy (OfficeCLI-friendly padding).

    When ``width_cm`` is set, wraps with the same estimator as ``layout.py``.
    """
    if width_cm is not None and width_cm > 0:
        h = L.text_height_cm(str(text), width_cm, float(body_pt))
        # OfficeCLI line metrics run slightly taller than our estimator.
        return max(min_cm, min(max_cm, h + 0.65))
    line_h = body_pt * L.PT_TO_CM * 1.55
    n = max(1, str(text).count("\n") + 1)
    return max(min_cm, min(max_cm, n * line_h + 0.7))


def bullets_text(items: Sequence[Any], *, limit: int = 6) -> str:
    lines: list[str] = []
    for x in list(items)[:limit]:
        s = str(x).strip()
        if not s:
            continue
        if not s.startswith(("•", "-", "–")):
            s = f"• {s}"
        lines.append(s)
    return "\n".join(lines) if lines else "• —"


# ---------------------------------------------------------------------------
# Layout-tree primitives (use with L.solve_adaptive)
# ---------------------------------------------------------------------------

def slide_title_node(st: StageMetrics, title: str, *, name: str = "SlideTitle",
                     density: L.Density | None = None) -> L.Box:
    d = density or L.COMFORTABLE
    band = st.title_band * (0.85 + 0.15 * d.gap)
    return L.Text(
        title,
        pt=st.title_pt,
        name=name,
        min_cm=band,
        max_cm=band + 0.4,
        props={
            "font": st.heading_font,
            "size": str(st.title_pt),
            "bold": "true",
            "color": st.c["text_on_content"],
            "fill": "none",
        },
    )


def content_text(st: StageMetrics, text: str, *, name: str,
                 pt: int | None = None, color: str | None = None,
                 weight: float = 0.0, min_cm: float = 1.2,
                 max_cm: float = 5.5, bold: bool = False) -> L.Box:
    """Body/title leaf — default weight=0 (content height). Never stretch copy."""
    use_pt = int(pt if pt is not None else st.body_pt)
    return L.Text(
        text,
        pt=use_pt,
        name=name,
        weight=weight,
        min_cm=min_cm,
        max_cm=max_cm,
        props={
            "font": st.heading_font if bold else st.body_font,
            "size": str(use_pt),
            "bold": "true" if bold else "false",
            "color": color or st.c["muted"],
            "fill": "none",
        },
    )


def card(
    st: StageMetrics,
    *,
    name: str,
    children: list[L.Box],
    fill: str | None = None,
    weight: float = 1.0,
    density: L.Density | None = None,
    absorb_free: bool = True,
) -> L.Box:
    """Surface card: pad from StageMetrics; optional bottom Spacer for free height."""
    d = density or L.COMFORTABLE
    pad_y = st.pad * (0.85 + 0.15 * d.gap)
    pad_x = st.pad
    kids = list(children)
    if absorb_free:
        kids.append(L.Spacer(weight=1))
    return L.VStack(
        kids,
        weight=weight,
        name=name,
        pad=(pad_y, pad_x, pad_y, pad_x),
        gap=st.title_to_body * d.gap,
        props={
            "preset": st.preset,
            "fill": fill if fill is not None else st.c["surface"],
            "line": "none",
        },
    )


def feature_card(
    st: StageMetrics,
    *,
    index: int,
    title: str,
    body: str,
    density: L.Density | None = None,
) -> L.Box:
    """Numbered product card (01 / title / body / spacer)."""
    d = density or L.COMFORTABLE
    body_pt = L.floored_pt(st.body_pt, d)
    title_pt = max(20, min(26, st.section_pt))
    num_pt = max(28, min(36, title_pt + 8))
    return card(
        st,
        name=f"Card{index}Bg",
        density=d,
        children=[
            content_text(
                st, f"{index:02d}", name=f"Card{index}Num",
                pt=num_pt, color=st.c["accent"], bold=True,
                min_cm=1.85, max_cm=2.1,
            ),
            content_text(
                st, title, name=f"Card{index}Title",
                pt=title_pt, color=st.c["text_on_surface"], bold=True,
                min_cm=st.card_title_band, max_cm=st.card_title_band + 0.25,
            ),
            content_text(
                st, body, name=f"Card{index}Body",
                pt=body_pt, color=st.c["muted"],
                min_cm=2.2, max_cm=5.5,
            ),
        ],
    )


def titled_stage(
    st: StageMetrics,
    title: str,
    body: L.Box,
    *,
    title_name: str = "SlideTitle",
    density: L.Density | None = None,
) -> L.Box:
    """Full-slide VStack: margin pad, title band, then body region (weight=1)."""
    d = density or L.COMFORTABLE
    return L.VStack(
        [
            slide_title_node(st, title, name=title_name, density=d),
            body,
        ],
        pad=(max(1.2, st.margin * 0.55), st.margin, st.margin, st.margin),
        gap=max(0.75, st.margin * 0.4) * d.gap,
        name="titled_stage",
    )


def equal_columns(
    children: list[L.Box],
    st: StageMetrics,
    *,
    density: L.Density | None = None,
    weight: float = 1.0,
) -> L.Box:
    d = density or L.COMFORTABLE
    return L.HStack(children, gap=st.gap * d.gap, weight=weight, name="columns")


def solve_stage(
    build: Callable[[L.Density], L.Box],
    *,
    bg: str,
) -> list[dict[str, Any]]:
    """Solve adaptive tree → officecli slide + shape ops."""
    placed, _d = L.solve_adaptive(build, 0, 0, CANVAS_W, CANVAS_H)
    ops: list[dict[str, Any]] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": bg},
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
            {"x": cm(p.x), "y": cm(p.y), "width": cm(p.w), "height": cm(p.h)}
        )
        # Skip pure spacers (no props / no name) — already filtered by layout
        if p.box.kind == "spacer":
            continue
        ops.append(
            {"command": "add", "parent": "/slide[last()]", "type": op_type, "props": props}
        )
    return ops


# ---------------------------------------------------------------------------
# Fixed-cm comparison panels (before/after, vs) — same metrics, no weight stretch
# ---------------------------------------------------------------------------

def comparison_panels(
    st: StageMetrics,
    *,
    title: str,
    left_title: str,
    left_body: str,
    right_title: str,
    right_body: str,
    title_name: str = "CmpTitle",
    left_fill: str | None = None,
    right_fill: str | None = None,
) -> list[dict[str, Any]]:
    """Two equal columns; panel height from content; stage air preserved."""
    c = st.c
    left_fill = left_fill if left_fill is not None else c["surface"]
    right_fill = right_fill if right_fill is not None else c["accent"]
    m, gap, pad = st.margin, st.gap, st.pad
    usable = st.usable_w
    col = (usable - gap) / 2

    title_y = max(1.15, m * 0.55)
    title_h = st.title_band
    title_to_panel = max(0.8, m * 0.42)
    band_top = title_y + title_h + title_to_panel
    bottom_m = m

    head_pt = max(22, min(28, st.section_pt))
    head_h = 1.5
    head_to_body = st.title_to_body
    inner_w = col - 2 * pad
    body_h = max(
        body_height_cm(left_body, body_pt=st.body_pt, width_cm=inner_w),
        body_height_cm(right_body, body_pt=st.body_pt, width_cm=inner_w),
    )
    # Shorten long vision/mission lines if they still exceed a sane panel.
    body_h = min(body_h, 7.5)
    panel_h = pad + head_h + head_to_body + body_h + pad
    max_panel_h = CANVAS_H - band_top - bottom_m
    panel_h = min(panel_h, max_panel_h)
    free = max(0.0, max_panel_h - panel_h)
    panel_y = band_top + free * 0.38

    bg = c.get("content_background") or c["background"]
    ops: list[dict[str, Any]] = [
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
                "name": title_name,
                "text": title,
                "x": cm(m),
                "y": cm(title_y),
                "width": cm(usable),
                "height": cm(title_h),
                "font": st.heading_font,
                "size": str(st.title_pt),
                "bold": "true",
                "color": c["text_on_content"],
                "fill": "none",
            },
        },
    ]
    for i, (head, body, fill) in enumerate((
        (left_title, left_body, left_fill),
        (right_title, right_body, right_fill),
    )):
        x = m + i * (col + gap)
        on_accent = fill == c["accent"]
        tc = c["on_accent"] if on_accent else c["text_on_surface"]
        bc = c["on_accent"] if on_accent else c["muted"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"CmpPanel{i + 1}",
                "preset": st.preset,
                "fill": fill,
                "line": "none",
                "x": cm(x), "y": cm(panel_y),
                "width": cm(col), "height": cm(panel_h),
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"CmpHead{i + 1}",
                "text": head,
                "x": cm(x + pad), "y": cm(panel_y + pad),
                "width": cm(col - 2 * pad), "height": cm(head_h),
                "font": st.heading_font, "size": str(head_pt),
                "bold": "true", "color": tc, "fill": "none",
            },
        })
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"CmpBody{i + 1}",
                "text": body,
                "x": cm(x + pad),
                "y": cm(panel_y + pad + head_h + head_to_body),
                "width": cm(col - 2 * pad),
                "height": cm(body_h),
                "font": st.body_font, "size": str(st.body_pt),
                "color": bc, "fill": "none",
            },
        })
    return ops


def notes_op(text: str) -> dict[str, Any]:
    return {
        "command": "add",
        "parent": "/slide[last()]",
        "type": "notes",
        "props": {"text": text},
    }


def content_band_y_h(
    st: StageMetrics,
    *,
    fraction: float = 0.72,
    min_h: float = 5.5,
    max_h: float = 10.5,
    settle: float = 0.38,
) -> tuple[float, float]:
    """(y, height) for a content band under the title with stage bottom air.

    ``fraction`` of available height is used for the band; the rest is stage
    air above/below via ``settle`` (0 = top-align, 0.5 = center).
    """
    band_top = st.content_top
    avail = max(min_h, CANVAS_H - band_top - st.content_bottom)
    h = min(max_h, max(min_h, avail * fraction))
    free = max(0.0, avail - h)
    y = band_top + free * settle
    return y, h


def equal_tile_row_ops(
    st: StageMetrics,
    *,
    title: str,
    title_name: str,
    items: Sequence[dict[str, str]],
    name_prefix: str,
    accent_every: int = 2,
) -> list[dict[str, Any]]:
    """Equal-width tiles (puzzle / chips) with content-band height."""
    n = max(1, len(items))
    # local grid (avoid circular import of recipes._grid_n)
    usable = st.usable_w
    gap = st.gap
    col = (usable - gap * (n - 1)) / n
    xs = [st.margin + i * (col + gap) for i in range(n)]
    y, h = content_band_y_h(st, fraction=0.68, min_h=5.8, max_h=9.5)
    bg = st.c.get("content_background") or st.c["background"]
    ops: list[dict[str, Any]] = [
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
                "name": title_name,
                "text": title,
                "x": cm(st.margin),
                "y": cm(max(1.15, st.margin * 0.55)),
                "width": cm(st.usable_w),
                "height": cm(st.title_band),
                "font": st.heading_font,
                "size": str(st.title_pt),
                "bold": "true",
                "color": st.c["text_on_content"],
                "fill": "none",
            },
        },
    ]
    for i, it in enumerate(items):
        text = str(it.get("label") or it.get("title") or "")
        detail = str(it.get("detail") or it.get("body") or "").strip()
        if detail:
            text = f"{text}\n{detail}" if text else detail
        accent = (i % accent_every == 0)
        fill = st.c["accent"] if accent else st.c["surface"]
        tc = st.c["on_accent"] if accent else st.c["text_on_surface"]
        ops.append({
            "command": "add", "parent": "/slide[last()]", "type": "shape",
            "props": {
                "name": f"{name_prefix}{i + 1}",
                "preset": st.preset,
                "fill": fill,
                "line": "none",
                "text": text,
                "x": cm(xs[i]),
                "y": cm(y),
                "width": cm(col),
                "height": cm(h),
                "font": st.heading_font,
                "size": str(max(16, min(22, st.section_pt))),
                "bold": "true",
                "color": tc,
                "align": "center",
                "valign": "middle",
            },
        })
    return ops


__all__ = [
    "CANVAS_W",
    "CANVAS_H",
    "StageMetrics",
    "stage_metrics",
    "cm",
    "body_height_cm",
    "bullets_text",
    "slide_title_node",
    "content_text",
    "card",
    "feature_card",
    "titled_stage",
    "equal_columns",
    "solve_stage",
    "comparison_panels",
    "notes_op",
]
