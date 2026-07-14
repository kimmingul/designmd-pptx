"""Constraint-based layout engine (v1.6) — one-pass axis-aligned flex.

Replaces hard-coded cm coordinates in text-heavy recipes: a recipe declares a
tree of stacks once, and the engine solves absolute cm geometry from content —
text boxes get their height from estimated line counts (fit.text_units), free
space is distributed by weight, and min/max clamps keep the design floor.

Two density presets (comfortable → compact) adapt spacing first, fonts second,
never below the hard floors (title ≥36pt, body ≥18pt). When even compact
overflows, the engine raises LayoutOverflow with a shorten-or-split message —
the same no-silent-truncation contract as fit.py.

Deliberately NOT a constraint solver: one top-down pass. Widths are decided
by the container (weights / equal split); text height is then a pure function
of width. That covers slide layouts; true 2D reflow is out of scope.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .fit import text_units

PT_TO_CM = 0.0353
LINE_SPACING = 1.25
CANVAS_W = 33.87
CANVAS_H = 19.05


class Overflow:
    """Typed overflow outcomes (issue #9) — the vocabulary recipes use to decide
    what to do when content does not fit, instead of silently shrinking or
    dropping it. `solve_adaptive` fits (FIT/USE_COMPACT) or raises
    `LayoutOverflow`; a recipe that can split its content (e.g. tables, #17)
    catches that and PAGINATEs rather than failing."""

    FIT = "fit"                 # fits at comfortable density
    USE_COMPACT = "use_compact"  # fits only at the compact density
    PAGINATE = "paginate"       # caller should split across slides
    SHORTEN = "shorten"         # content must be shortened to fit
    FAIL = "fail"               # unrecoverable


class LayoutOverflow(ValueError):
    """Content cannot fit even at the compact density — shorten or split.

    Carries `.policy` (default `Overflow.SHORTEN`) so callers can branch: a
    paginating recipe treats it as `Overflow.PAGINATE`, others surface it."""

    def __init__(self, *args, policy: str = Overflow.SHORTEN):
        super().__init__(*args)
        self.policy = policy


@dataclass
class Box:
    kind: str = "fixed"  # vstack | hstack | text | fixed | spacer
    name: str = ""
    children: list["Box"] = field(default_factory=list)
    weight: float = 0.0
    size_cm: float = 0.0            # intrinsic main-axis size for fixed/spacer
    min_cm: float = 0.0
    max_cm: float = 1e9
    gap_cm: float = 0.0             # between children (containers only)
    pad: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # T R B L
    text: str = ""
    pt: float = 18.0
    props: dict[str, Any] = field(default_factory=dict)  # style passthrough


def VStack(children: list[Box], *, gap: float = 0.0,
           pad: tuple[float, float, float, float] = (0, 0, 0, 0),
           weight: float = 0.0, name: str = "",
           props: dict[str, Any] | None = None) -> Box:
    return Box(kind="vstack", children=children, gap_cm=gap, pad=pad,
               weight=weight, name=name, props=props or {})


def HStack(children: list[Box], *, gap: float = 0.0,
           pad: tuple[float, float, float, float] = (0, 0, 0, 0),
           weight: float = 0.0, name: str = "",
           props: dict[str, Any] | None = None) -> Box:
    return Box(kind="hstack", children=children, gap_cm=gap, pad=pad,
               weight=weight, name=name, props=props or {})


def Text(text: str, *, pt: float, name: str, weight: float = 0.0,
         min_cm: float = 0.0, max_cm: float = 1e9,
         props: dict[str, Any] | None = None) -> Box:
    return Box(kind="text", text=str(text), pt=pt, name=name, weight=weight,
               min_cm=min_cm, max_cm=max_cm, props=props or {})


def Fixed(size_cm: float, *, name: str = "",
          props: dict[str, Any] | None = None) -> Box:
    return Box(kind="fixed", size_cm=size_cm, name=name, props=props or {})


def Spacer(size_cm: float = 0.0, *, weight: float = 0.0) -> Box:
    return Box(kind="spacer", size_cm=size_cm, weight=weight)


def text_height_cm(text: str, width_cm: float, pt: float) -> float:
    """Estimated rendered height: wrapped line count per paragraph (\\n)."""
    line_h = pt * PT_TO_CM * LINE_SPACING
    if width_cm <= 0:
        return line_h
    units_per_line = max(1.0, width_cm / (pt * PT_TO_CM))
    lines = sum(
        max(1, math.ceil(text_units(para) / units_per_line))
        for para in str(text).split("\n")
    )
    return max(1, lines) * line_h + 0.25  # breathing room for box padding


@dataclass
class Placed:
    """A leaf box with solved absolute geometry (cm)."""
    name: str
    x: float
    y: float
    w: float
    h: float
    box: Box


def _intrinsic_main(box: Box, cross_cm: float, vertical: bool) -> float:
    """Main-axis size of a weight-0 child given the container's cross size."""
    if box.kind == "spacer" or box.kind == "fixed":
        return max(box.size_cm, box.min_cm)
    if box.kind == "text":
        if vertical:  # main axis is height; text wraps at the cross width
            h = text_height_cm(box.text, cross_cm, box.pt)
            return min(max(h, box.min_cm), box.max_cm)
        return max(box.min_cm, box.size_cm)  # width must be weighted/fixed
    # nested container: sum of its children along ITS main axis when that
    # matches ours; otherwise its cross extent is our children's max — for
    # slide layouts a weight-0 nested stack sizes to its content vertically.
    t, _r, b, _l = box.pad[0], box.pad[1], box.pad[2], box.pad[3]
    if vertical and box.kind == "vstack":
        inner_cross = cross_cm - box.pad[1] - box.pad[3]
        total = sum(_intrinsic_main(c, inner_cross, True) for c in box.children
                    if c.weight == 0)
        if any(c.weight > 0 for c in box.children):
            total += sum(c.min_cm for c in box.children if c.weight > 0)
        total += box.gap_cm * max(0, len(box.children) - 1) + t + b
        return min(max(total, box.min_cm), box.max_cm)
    if vertical and box.kind == "hstack":
        inner_cross = cross_cm - box.pad[1] - box.pad[3]
        n = max(1, len(box.children))
        # approximate: children split the width equally for measurement
        child_w = (inner_cross - box.gap_cm * (n - 1)) / n
        total = max(
            (_intrinsic_main(c, child_w, True) for c in box.children),
            default=0.0,
        ) + t + b
        return min(max(total, box.min_cm), box.max_cm)
    return max(box.min_cm, box.size_cm)


def solve(root: Box, x: float, y: float, w: float, h: float) -> list[Placed]:
    """Solve the tree into absolutely-positioned leaves. Raises LayoutOverflow.

    Containers that carry props are emitted too (before their children), so a
    card stack renders its own background rect. After placement, every text
    leaf — including weighted ones that were sized by free space, not by
    content — is re-checked against its estimated height, closing the
    weighted-text overflow hole.
    """
    placed: list[Placed] = []
    _solve_into(root, x, y, w, h, placed)
    for p in placed:
        if p.box.kind == "text" and p.box.text:
            need = text_height_cm(p.box.text, p.w, p.box.pt)
            if need > p.h + 0.3:
                raise LayoutOverflow(
                    f"{p.name}: text needs ~{need:.1f}cm but has {p.h:.1f}cm "
                    "at this density — shorten the text or split the slide"
                )
    return placed


def _solve_into(box: Box, x: float, y: float, w: float, h: float,
                out: list[Placed]) -> None:
    if box.kind in ("text", "fixed"):
        out.append(Placed(box.name, x, y, w, h, box))
        return
    if box.kind == "spacer":
        return
    if box.props:  # container with visual chrome (e.g. card background)
        out.append(Placed(box.name, x, y, w, h, box))
    t, r, b, l = box.pad
    ix, iy, iw, ih = x + l, y + t, w - l - r, h - t - b
    vertical = box.kind == "vstack"
    main_total = ih if vertical else iw
    cross = iw if vertical else ih
    gaps = box.gap_cm * max(0, len(box.children) - 1)

    sizes: list[float] = []
    for c in box.children:
        if c.weight > 0:
            sizes.append(-1.0)  # resolved below
        else:
            sizes.append(_intrinsic_main(c, cross, vertical))

    fixed_sum = sum(s for s in sizes if s >= 0)
    free = main_total - gaps - fixed_sum
    weights = sum(c.weight for c in box.children if c.weight > 0)
    if weights > 0:
        if free < -0.01:
            raise LayoutOverflow(
                f"{box.name or box.kind}: content needs {fixed_sum + gaps:.1f}cm "
                f"of {main_total:.1f}cm — shorten the text or split the slide"
            )
        share = free / weights
        # clamp pass: weighted children respect min/max, remainder rebalances once
        clamped = 0.0
        flex = 0.0
        for c in box.children:
            if c.weight > 0:
                want = share * c.weight
                got = min(max(want, c.min_cm), c.max_cm)
                if abs(got - want) > 1e-9:
                    clamped += got
                else:
                    flex += c.weight
        if flex > 0:
            share2 = (free - clamped) / flex
        else:
            share2 = 0.0
        for i, c in enumerate(box.children):
            if c.weight > 0:
                want = share * c.weight
                got = min(max(want, c.min_cm), c.max_cm)
                if abs(got - want) <= 1e-9:
                    got = min(max(share2 * c.weight, c.min_cm), c.max_cm)
                sizes[i] = got
    else:
        overflow = fixed_sum + gaps - main_total
        if overflow > 0.05:
            raise LayoutOverflow(
                f"{box.name or box.kind}: content needs "
                f"{fixed_sum + gaps:.1f}cm of {main_total:.1f}cm — "
                "shorten the text or split the slide"
            )

    cursor = iy if vertical else ix
    for c, size in zip(box.children, sizes):
        if vertical:
            _solve_into(c, ix, cursor, cross, size, out)
        else:
            _solve_into(c, cursor, iy, size, cross, out)
        cursor += size + box.gap_cm


@dataclass(frozen=True)
class Density:
    name: str
    gap: float      # multiplier for gaps/padding
    body_delta: int  # applied to body-ish pt, floored by caller


COMFORTABLE = Density("comfortable", 1.0, 0)
COMPACT = Density("compact", 0.7, -2)


def floored_pt(base: float, density: Density, floor: int = 18) -> int:
    """Density-adjusted font size that never crosses the hard floor
    (title ≥36, body ≥18 are skill hard rules)."""
    return max(floor, int(base) + density.body_delta)


def solve_adaptive(build, x: float, y: float, w: float, h: float):
    """Try comfortable, then compact. build(density) → Box tree.

    Returns (placed_leaves, density). Raises LayoutOverflow when even the
    compact variant cannot fit — the content must be shortened or split.
    """
    last: LayoutOverflow | None = None
    for density in (COMFORTABLE, COMPACT):
        try:
            return solve(build(density), x, y, w, h), density
        except LayoutOverflow as e:
            last = e
    raise LayoutOverflow(str(last))
