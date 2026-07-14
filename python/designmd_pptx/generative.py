"""Hybrid generative layout engine (Phase 5 / #21).

Patterns remain the default path. When a slide does not fit a known recipe
well, or the user issues a natural-language style directive ("Apple Keynote
style", "more whitespace", "consulting dense"), this module:

1. Parses the directive into a **style profile** (margins, density, recipe bias)
2. Optionally builds a **free-form layout tree** from content
3. Validates geometry via the constraint layout engine (``layout.solve_adaptive``)
   so text-fit floors still hold
4. Emits a deck-spec patch (recipe swaps + freeform placement metadata) that
   still materializes as editable native PPTX shapes through officecli ops

Vision findings (Gate 3 / refine) feed the same path: density/alignment codes
trigger re-layout with a roomier profile.

No live LLM is required for the deterministic offline path; optional
``DESIGNMD_LAYOUT_CMD`` / ``--layout-cmd`` can inject an external generator
that returns a freeform layout tree JSON (validated before acceptance).
"""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import layout as L
from . import refine as refine_mod
from . import vision_gate as VG

# ---------------------------------------------------------------------------
# Style profiles — pattern-first, freeform when needed
# ---------------------------------------------------------------------------

STYLE_PROFILES: dict[str, dict[str, Any]] = {
    "keynote": {
        "label": "Apple Keynote",
        "margin_cm": 2.2,
        "gap_cm": 1.1,
        "density": "comfortable",
        "title_bias": "large_center",
        "max_list_items": 4,
        "max_body_chars": 160,
        "recipe_map": {
            "bullets": "feature_cards",
            "process": "timeline",
            "table": "kpi_row",
        },
        "prefer_freeform_for": frozenset({"quote", "close", "cover"}),
        "freeform_preset": "hero_center",
    },
    "swiss": {
        "label": "Swiss / International",
        "margin_cm": 1.6,
        "gap_cm": 0.9,
        "density": "comfortable",
        "title_bias": "top_left",
        "max_list_items": 5,
        "max_body_chars": 200,
        "recipe_map": {
            "feature_cards": "bullets",
            "story_timeline": "timeline",
        },
        "prefer_freeform_for": frozenset({"section_divider", "quote"}),
        "freeform_preset": "asymmetric_band",
    },
    "consulting": {
        "label": "Consulting dense",
        "margin_cm": 1.27,
        "gap_cm": 0.6,
        "density": "compact",
        "title_bias": "top_left",
        "max_list_items": 6,
        "max_body_chars": 280,
        "recipe_map": {
            "feature_cards": "bullets",
            "quote": "bullets",
        },
        "prefer_freeform_for": frozenset(),
        "freeform_preset": "grid_cards",
    },
    "minimal": {
        "label": "Minimal whitespace",
        "margin_cm": 2.5,
        "gap_cm": 1.2,
        "density": "comfortable",
        "title_bias": "large_center",
        "max_list_items": 3,
        "max_body_chars": 120,
        "recipe_map": {
            "bullets": "feature_cards",
            "process": "kpi_row",
            "table": "kpi_row",
        },
        "prefer_freeform_for": frozenset({"cover", "close", "quote", "section_divider"}),
        "freeform_preset": "hero_center",
    },
    "editorial": {
        "label": "Editorial magazine",
        "margin_cm": 1.8,
        "gap_cm": 0.85,
        "density": "comfortable",
        "title_bias": "top_left",
        "max_list_items": 4,
        "max_body_chars": 220,
        "recipe_map": {
            "bullets": "image_text_2col",
            "feature_cards": "comparison_2col",
        },
        "prefer_freeform_for": frozenset({"quote"}),
        "freeform_preset": "asymmetric_band",
    },
    "default": {
        "label": "Pattern default",
        "margin_cm": 1.27,
        "gap_cm": 0.76,
        "density": "comfortable",
        "title_bias": "top_left",
        "max_list_items": 5,
        "max_body_chars": 220,
        "recipe_map": {},
        "prefer_freeform_for": frozenset(),
        "freeform_preset": "grid_cards",
    },
}

_NL_STYLES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(apple\s*)?keynote|키노트|hero\s*slide|big\s*type", re.I), "keynote"),
    (re.compile(r"swiss|international\s*typog|helvetica\s*grid|바우하우스", re.I), "swiss"),
    (re.compile(r"consult|mckinsey|dense\s*board|컨설팅|보드\s*덱", re.I), "consulting"),
    (re.compile(r"minimal|whitespace|airy|여백|미니멀|sparse", re.I), "minimal"),
    (re.compile(r"editorial|magazine|매거진|편집", re.I), "editorial"),
]

_NL_RELAYOUT = re.compile(
    r"(재구성|re-?layout|recompose|restyle|재배치|rearrange|rebalance|"
    r"visual\s*balance|여백\s*부족|too\s*tight|cramped)",
    re.I,
)


@dataclass
class LayoutValidation:
    ok: bool
    density: str | None = None
    placed_count: int = 0
    overflow: str | None = None
    placements: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Directive parsing
# ---------------------------------------------------------------------------

def parse_style_directive(text: str | None) -> dict[str, Any]:
    """Natural language → style profile (+ flags)."""
    text = (text or "").strip()
    profile_id = "default"
    if text:
        for pat, pid in _NL_STYLES:
            if pat.search(text):
                profile_id = pid
                break
    profile = copy.deepcopy(STYLE_PROFILES[profile_id])
    profile["id"] = profile_id
    profile["directive"] = text
    profile["force_relayout"] = bool(text and _NL_RELAYOUT.search(text))
    # Prefer freeform more aggressively when user asks to recompose
    if profile["force_relayout"] and profile_id == "default":
        profile = copy.deepcopy(STYLE_PROFILES["minimal"])
        profile["id"] = "minimal"
        profile["directive"] = text
        profile["force_relayout"] = True
    return profile


def list_style_profiles() -> list[dict[str, str]]:
    return [
        {"id": k, "label": str(v.get("label") or k)}
        for k, v in STYLE_PROFILES.items()
        if k != "default"
    ]


# ---------------------------------------------------------------------------
# Free-form layout trees (constraint-engine validated)
# ---------------------------------------------------------------------------

def _title_body_from_content(content: dict[str, Any]) -> tuple[str, str, list[str]]:
    title = str(content.get("title") or content.get("heading") or "Untitled")
    body = ""
    for k in ("body", "blurb", "subtitle", "quote", "insight_body", "meta"):
        if content.get(k):
            body = str(content[k])
            break
    items: list[str] = []
    for k in ("bullets", "items", "steps", "stages", "entries"):
        raw = content.get(k)
        if isinstance(raw, list) and raw:
            for it in raw:
                if isinstance(it, dict):
                    items.append(str(it.get("title") or it.get("label") or it.get("text") or ""))
                else:
                    items.append(str(it))
            break
    cards = content.get("cards")
    if isinstance(cards, list) and cards and not items:
        for c in cards:
            if isinstance(c, dict):
                items.append(str(c.get("title") or c.get("body") or ""))
            else:
                items.append(str(c))
    return title, body, [x for x in items if x]


def build_freeform_tree(
    content: dict[str, Any],
    profile: dict[str, Any],
    *,
    tokens: dict[str, Any] | None = None,
) -> L.Box:
    """Build a layout Box tree for free-form generation (still axis-aligned)."""
    title, body, items = _title_body_from_content(content)
    preset = str(profile.get("freeform_preset") or "hero_center")
    margin = float(profile.get("margin_cm") or 1.27)
    gap = float(profile.get("gap_cm") or 0.76)
    t = (tokens or {}).get("type") or {}
    title_pt = float(t.get("title_pt") or 36)
    body_pt = float(t.get("body_pt") or 18)
    # never below floors
    title_pt = max(36.0, title_pt)
    body_pt = max(18.0, body_pt)
    if profile.get("density") == "compact":
        title_pt = max(36.0, title_pt - 2)
        body_pt = max(18.0, body_pt)

    pad = (margin, margin, margin, margin)

    if preset == "hero_center":
        children: list[L.Box] = [
            L.Spacer(weight=1.0),
            L.Text(title, pt=title_pt + 8, name="FreeTitle",
                   min_cm=1.5, max_cm=5.0,
                   props={"_type": "shape", "bold": "true", "align": "center"}),
        ]
        if body:
            children.append(L.Fixed(0.4))
            children.append(L.Text(body, pt=body_pt, name="FreeBody",
                                   min_cm=0.8, max_cm=4.0,
                                   props={"_type": "shape", "align": "center"}))
        if items:
            children.append(L.Fixed(0.5))
            item_row = L.HStack(
                [
                    L.Text(it, pt=body_pt, name=f"FreeItem{i}", weight=1.0,
                           min_cm=0.6, max_cm=3.0,
                           props={"_type": "shape", "align": "center"})
                    for i, it in enumerate(items[:4])
                ],
                gap=gap,
                name="FreeItems",
            )
            children.append(item_row)
        children.append(L.Spacer(weight=1.0))
        return L.VStack(children, pad=pad, name="FreeRoot")

    if preset == "asymmetric_band":
        left = L.VStack(
            [
                L.Text(title, pt=title_pt, name="FreeTitle", min_cm=1.2, max_cm=6.0,
                       props={"_type": "shape", "bold": "true"}),
                L.Fixed(0.3),
                L.Text(body or " ", pt=body_pt, name="FreeBody", weight=1.0,
                       min_cm=1.0, max_cm=10.0,
                       props={"_type": "shape"}),
            ],
            gap=0.2,
            weight=1.4,
            name="FreeLeft",
        )
        right_kids: list[L.Box] = []
        for i, it in enumerate(items[:5] or ["—"]):
            right_kids.append(
                L.Text(it, pt=body_pt, name=f"FreeSide{i}", min_cm=0.6, max_cm=2.5,
                       props={"_type": "shape"})
            )
            if i < len(items[:5]) - 1:
                right_kids.append(L.Fixed(0.25))
        right = L.VStack(right_kids or [L.Spacer(weight=1.0)], weight=1.0, name="FreeRight")
        return L.VStack(
            [L.HStack([left, right], gap=gap, weight=1.0, name="FreeBand")],
            pad=pad,
            name="FreeRoot",
        )

    # grid_cards default
    header = L.Text(title, pt=title_pt, name="FreeTitle", min_cm=1.0, max_cm=3.5,
                    props={"_type": "shape", "bold": "true"})
    if not items and body:
        items = [body]
    cards = items[:6] or [" "]
    n = len(cards)
    cols = 3 if n >= 3 else max(1, n)
    rows: list[L.Box] = []
    for r in range(0, n, cols):
        chunk = cards[r : r + cols]
        rows.append(
            L.HStack(
                [
                    L.Text(c, pt=body_pt, name=f"FreeCard{r + i}", weight=1.0,
                           min_cm=1.5, max_cm=6.0,
                           props={"_type": "shape"})
                    for i, c in enumerate(chunk)
                ],
                gap=gap,
                weight=1.0,
                name=f"FreeRow{r}",
            )
        )
    return L.VStack(
        [header, L.Fixed(0.4), *rows],
        gap=gap * 0.5,
        pad=pad,
        name="FreeRoot",
    )


def validate_tree(
    tree: L.Box,
    *,
    density_hint: str = "comfortable",
) -> LayoutValidation:
    """Run constraint engine; never accept overflowing freeform.

    ``solve_adaptive`` expects ``build(density) -> Box``. For a pre-built tree
    we wrap it; density-aware freeform builders should pass a callable via
    ``validate_builder`` instead.
    """
    return validate_builder(lambda _d: tree, density_hint=density_hint)


def validate_builder(
    build,
    *,
    density_hint: str = "comfortable",
) -> LayoutValidation:
    """Validate a density-aware Box builder with the constraint engine."""
    try:
        if density_hint == "compact":
            # Only try compact
            placed = L.solve(build(L.COMPACT), 0, 0, L.CANVAS_W, L.CANVAS_H)
            dens = L.COMPACT
        else:
            placed, dens = L.solve_adaptive(build, 0, 0, L.CANVAS_W, L.CANVAS_H)
        placements = [
            {
                "name": p.name,
                "x": round(p.x, 3),
                "y": round(p.y, 3),
                "w": round(p.w, 3),
                "h": round(p.h, 3),
                "kind": p.box.kind,
                "text": p.box.text if p.box.kind == "text" else "",
                "pt": p.box.pt if p.box.kind == "text" else None,
            }
            for p in placed
            if p.name  # skip pure spacers without names
        ]
        dens_name = dens.name if hasattr(dens, "name") else str(dens)
        return LayoutValidation(
            ok=True,
            density=dens_name,
            placed_count=len(placements),
            placements=placements,
        )
    except L.LayoutOverflow as e:
        return LayoutValidation(ok=False, overflow=str(e), placed_count=0)


def freeform_to_ops(
    placements: list[dict[str, Any]],
    tokens: dict[str, Any],
) -> list[dict[str, Any]]:
    """Validated freeform placements → officecli add ops (editable shapes)."""
    c = tokens.get("colors") or {}
    t = tokens.get("type") or {}
    bg = tokens.get("background_gradient") or c.get("background") or "FFFFFF"
    ops: list[dict[str, Any]] = [
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "background": bg},
        }
    ]
    for p in placements:
        if not p.get("name"):
            continue
        text = p.get("text") or ""
        pt = p.get("pt") or t.get("body_pt") or 18
        props: dict[str, Any] = {
            "name": p["name"],
            "text": text,
            "x": f"{p['x']:.2f}".rstrip("0").rstrip(".") + "cm",
            "y": f"{p['y']:.2f}".rstrip("0").rstrip(".") + "cm",
            "width": f"{p['w']:.2f}".rstrip("0").rstrip(".") + "cm",
            "height": f"{p['h']:.2f}".rstrip("0").rstrip(".") + "cm",
            "font": t.get("heading_font") if "Title" in str(p["name"]) else t.get("body_font"),
            "size": str(int(pt)),
            "color": c.get("text") or "333333",
            "fill": "none",
        }
        if "Title" in str(p["name"]):
            props["bold"] = "true"
        ops.append({
            "command": "add",
            "parent": "/slide[last()]",
            "type": "shape",
            "props": props,
        })
    return ops


def recipe_freeform(tokens: dict, content: dict | None = None) -> list[dict]:
    """Recipe entry: freeform slide from content.layout / style directive."""
    content = content or {}
    profile = content.get("style_profile") or parse_style_directive(
        content.get("style_directive") or content.get("style")
    )
    if isinstance(profile, str):
        profile = parse_style_directive(profile)
    # Prefer pre-validated placements when present
    placements = content.get("placements")
    if isinstance(placements, list) and placements:
        return freeform_to_ops(placements, tokens)
    tree = build_freeform_tree(content, profile, tokens=tokens)
    val = validate_tree(tree, density_hint=str(profile.get("density") or "comfortable"))
    if not val.ok:
        # Fallback: shorten body and retry once
        short = copy.deepcopy(content)
        for k in ("body", "blurb", "subtitle", "quote"):
            if isinstance(short.get(k), str) and len(short[k]) > 80:
                short[k] = short[k][:79] + "…"
        tree = build_freeform_tree(short, profile, tokens=tokens)
        val = validate_tree(tree, density_hint="compact")
        if not val.ok:
            raise L.LayoutOverflow(
                f"freeform layout overflow: {val.overflow or 'unknown'} — shorten content"
            )
    return freeform_to_ops(val.placements, tokens)


# ---------------------------------------------------------------------------
# Deck-level generative restyle
# ---------------------------------------------------------------------------

def _apply_style_to_slide(
    slide: dict[str, Any],
    profile: dict[str, Any],
    *,
    tokens: dict[str, Any] | None = None,
    force_freeform: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (new_slide, patch_entry)."""
    out = copy.deepcopy(slide)
    content = out.setdefault("content", {})
    if not isinstance(content, dict):
        content = {}
        out["content"] = content
    recipe = str(out.get("recipe") or "bullets")
    patch: dict[str, Any] = {"slide_id": out.get("id"), "from_recipe": recipe}

    rmap: dict[str, str] = profile.get("recipe_map") or {}
    prefer_ff = profile.get("prefer_freeform_for") or frozenset()
    use_ff = force_freeform or recipe in prefer_ff or profile.get("force_relayout")

    # Cap list density per style
    max_items = int(profile.get("max_list_items") or 5)
    for key in ("bullets", "items", "steps", "stages", "cards", "entries"):
        raw = content.get(key)
        if isinstance(raw, list) and len(raw) > max_items:
            content[key] = raw[:max_items]
            content["notes"] = (
                (content.get("notes") or "")
                + f" [generative: trimmed {key} to {max_items} for {profile.get('id')} style]"
            ).strip()
            patch["trimmed"] = key

    max_body = int(profile.get("max_body_chars") or 220)
    for bk in ("body", "blurb", "subtitle", "quote", "insight_body"):
        if isinstance(content.get(bk), str) and len(content[bk]) > max_body:
            cut = content[bk][: max_body - 1].rsplit(" ", 1)[0]
            content[bk] = (cut or content[bk][: max_body - 1]) + "…"
            patch["shortened"] = bk

    if use_ff:
        tree = build_freeform_tree(content, profile, tokens=tokens)
        val = validate_tree(tree, density_hint=str(profile.get("density") or "comfortable"))
        if val.ok:
            out["recipe"] = "freeform"
            content["style_profile"] = {
                k: (list(v) if isinstance(v, frozenset) else v)
                for k, v in profile.items()
            }
            content["placements"] = val.placements
            content["style_directive"] = profile.get("directive") or profile.get("id")
            patch["to_recipe"] = "freeform"
            patch["action"] = "freeform_generate"
            patch["validation"] = val.to_dict()
            return out, patch
        patch["freeform_overflow"] = val.overflow

    # Pattern path with style-driven recipe map
    new_recipe = rmap.get(recipe, recipe)
    if new_recipe != recipe:
        # light content reshape when swapping bullets ↔ feature_cards
        if recipe == "bullets" and new_recipe == "feature_cards":
            bullets = content.get("bullets") or []
            content["cards"] = [
                {"title": str(b)[:48], "body": ""} for b in bullets[:4]
            ]
            content.pop("bullets", None)
        elif recipe == "feature_cards" and new_recipe == "bullets":
            cards = content.get("cards") or []
            content["bullets"] = [
                str(c.get("title") or c.get("body") or c) if isinstance(c, dict) else str(c)
                for c in cards
            ][:max_items]
            content.pop("cards", None)
        out["recipe"] = new_recipe
        patch["to_recipe"] = new_recipe
        patch["action"] = "recipe_map"
    else:
        patch["to_recipe"] = recipe
        patch["action"] = "style_annotate"
        content["notes"] = (
            (content.get("notes") or "")
            + f" [generative: style={profile.get('id')}]"
        ).strip()

    content["style_directive"] = profile.get("directive") or profile.get("id")
    return out, patch


def generate_deck_layout(
    deck: dict[str, Any],
    *,
    directive: str | None = None,
    profile_id: str | None = None,
    tokens: dict[str, Any] | None = None,
    findings: list[dict[str, Any]] | None = None,
    slide_indices: list[int] | None = None,
) -> dict[str, Any]:
    """Hybrid generative pass over a deck-spec.

    Returns report: {deck, profile, patches, validations, changed}.
    """
    if profile_id and profile_id in STYLE_PROFILES:
        profile = copy.deepcopy(STYLE_PROFILES[profile_id])
        profile["id"] = profile_id
        profile["directive"] = directive or profile_id
        profile["force_relayout"] = bool(directive and _NL_RELAYOUT.search(directive or ""))
    else:
        profile = parse_style_directive(directive)

    # Vision/density findings force roomier freeform on affected slides
    force_slides: set[int] = set()
    for f in findings or []:
        code = str(f.get("code") or "").lower()
        if code in refine_mod._DENSITY_CODES | refine_mod._ALIGNMENT_CODES | {
            "overflow", "balance", "margin", "whitespace",
        }:
            s = f.get("slide")
            if s is None:
                force_slides.update(range(len(deck.get("slides") or [])))
            else:
                try:
                    force_slides.add(int(s) - 1)
                except (TypeError, ValueError):
                    pass

    out = copy.deepcopy(deck)
    slides = out.get("slides") or []
    patches: list[dict[str, Any]] = []
    if not isinstance(slides, list):
        return {
            "version": 1,
            "deck": out,
            "profile": {k: (list(v) if isinstance(v, frozenset) else v) for k, v in profile.items()},
            "patches": [],
            "changed": False,
        }

    targets = set(slide_indices) if slide_indices is not None else set(range(len(slides)))
    new_slides: list[Any] = []
    for i, slide in enumerate(slides):
        if i not in targets or not isinstance(slide, dict):
            new_slides.append(slide)
            continue
        force_ff = i in force_slides or bool(profile.get("force_relayout"))
        ns, patch = _apply_style_to_slide(
            slide, profile, tokens=tokens, force_freeform=force_ff,
        )
        patch["slide"] = i + 1
        patches.append(patch)
        new_slides.append(ns)
    out["slides"] = new_slides
    # Persist generative provenance on deck
    out.setdefault("meta", {})
    if isinstance(out["meta"], dict):
        out["meta"]["generative"] = {
            "style": profile.get("id"),
            "directive": profile.get("directive"),
        }

    return {
        "version": 1,
        "deck": out,
        "profile": {
            k: (list(v) if isinstance(v, frozenset) else v)
            for k, v in profile.items()
        },
        "patches": patches,
        "changed": bool(patches),
    }


def generate_with_vision(
    deck: dict[str, Any],
    *,
    directive: str | None = None,
    contact_png: str | Path | None = None,
    vision_plan: str | Path | None = None,
    vision_cmd: str | None = None,
    tokens: dict[str, Any] | None = None,
    rounds: int = 2,
) -> dict[str, Any]:
    """Generate + optional vision re-layout loop (offline by default)."""
    findings: list[dict[str, Any]] = []
    if contact_png and Path(contact_png).exists():
        ev = VG.evaluate_contact_sheet(
            contact_png,
            vision_plan=vision_plan,
            vision_cmd=vision_cmd,
            use_subprocess=bool(vision_cmd) if vision_cmd else None,
            context={"task": "generative_layout"},
        )
        findings.extend(ev.get("findings") or [])

    report = generate_deck_layout(
        deck, directive=directive, tokens=tokens, findings=findings,
    )
    history = [report]
    current = report["deck"]
    for _ in range(max(0, rounds - 1)):
        # Second pass: refine density then re-generate if still cramped
        refined = refine_mod.refine_once(
            current, feedback=directive, findings=findings,
        )
        if not refined.get("changed"):
            break
        report = generate_deck_layout(
            refined["deck"], directive=directive, tokens=tokens, findings=findings,
        )
        history.append(report)
        current = report["deck"]
        if not report.get("changed"):
            break

    return {
        "version": 1,
        "deck": current,
        "profile": report.get("profile"),
        "patches": [p for h in history for p in (h.get("patches") or [])],
        "rounds": len(history),
        "findings": findings,
        "changed": any(h.get("changed") for h in history),
    }


def external_layout_tree(
    content: dict[str, Any],
    *,
    layout_cmd: str | None = None,
    timeout: float = 60.0,
) -> dict[str, Any] | None:
    """Optional external LLM layout generator.

    Command receives JSON on stdin ``{content, canvas:{w,h}}`` and must print
    a JSON object ``{placements:[...]}`` or ``{preset: hero_center|...}``.
    """
    cmd = layout_cmd or os.environ.get("DESIGNMD_LAYOUT_CMD")
    if not cmd:
        return None
    payload = {
        "content": content,
        "canvas": {"w": L.CANVAS_W, "h": L.CANVAS_H},
    }
    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            shell=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def write_report(report: dict[str, Any], out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    deck_path = out / "content.generated.deck.json"
    deck_path.write_text(
        json.dumps(report["deck"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    rep_path = out / "generative.report.json"
    slim = {k: v for k, v in report.items() if k != "deck"}
    slim["deck_path"] = str(deck_path.name)
    rep_path.write_text(
        json.dumps(slim, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return rep_path
