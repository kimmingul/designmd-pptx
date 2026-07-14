"""Animation & transition support (Phase 5 / #40).

DESIGN.md (and compiled tokens) may declare animation presets. Defaults apply
entrance effects on key pattern shapes (cover title, bullets, feature cards,
KPI values). Emission is **namespace-safe OOXML** via ``opc`` (lxml, URI-matched
tags) — never regex on raw slide XML.

Presets are conservative: fade / appear / wipe entrance + simple slide
transitions. Emphasis is limited to a mild pulse on accent shapes when
requested. PowerPoint and LibreOffice both accept the standard DrawingML /
PresentationML timing trees we emit.

Typical flow
------------
1. DESIGN.md frontmatter ``animation:`` → compile → tokens[\"animation\"]
2. scaffold / apply produces a .pptx
3. ``designmd-pptx animate deck.pptx --tokens tokens.slide.json -o out.pptx``
   (or ``scaffold --animate``) injects timing + transitions in place of staging
"""

from __future__ import annotations

import copy
import re
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from lxml import etree

from . import opc

# ---------------------------------------------------------------------------
# Preset catalog
# ---------------------------------------------------------------------------

# OOXML presetID values (entrance): 1=appear, 10=fade, 22=wipe
ENTRANCE_PRESETS: dict[str, dict[str, Any]] = {
    "none": {"preset_id": 0, "preset_class": None, "dur_ms": 0},
    "appear": {"preset_id": 1, "preset_class": "entr", "dur_ms": 1, "filter": None},
    "fade": {"preset_id": 10, "preset_class": "entr", "dur_ms": 500, "filter": "fade"},
    "wipe": {"preset_id": 22, "preset_class": "entr", "dur_ms": 400, "filter": "wipe(down)"},
    "fly_in": {"preset_id": 2, "preset_class": "entr", "dur_ms": 500, "filter": None},
}

EMPHASIS_PRESETS: dict[str, dict[str, Any]] = {
    "none": {"preset_id": 0, "preset_class": None},
    "pulse": {"preset_id": 24, "preset_class": "emph", "dur_ms": 500},  # flashbulb-ish
}

# Slide transitions (child element local name under p:transition)
TRANSITION_PRESETS: dict[str, str | None] = {
    "none": None,
    "fade": "fade",
    "push": "push",
    "wipe": "wipe",
    "cut": "cut",
    "cover": "cover",
}

# Default: which shape name prefixes get entrance on which recipes
DEFAULT_SHAPE_TARGETS: dict[str, list[str]] = {
    "cover": ["CoverTitle", "CoverSubtitle"],
    "section_divider": ["SectionTitle", "SectionLabel", "FreeTitle"],
    "bullets": ["BulletTitle", "Bullet", "Title", "FreeTitle"],
    "feature_cards": ["CardTitle", "Card", "Feature", "FreeCard", "FreeTitle"],
    "kpi_row": ["KpiValue", "Kpi", "KPI", "FreeTitle"],
    "process": ["Step", "Process", "FreeTitle"],
    "timeline": ["Timeline", "FreeTitle"],
    "quote": ["Quote", "FreeTitle", "FreeBody"],
    "close": ["CloseTitle", "Close", "FreeTitle"],
    "freeform": ["FreeTitle", "FreeBody", "FreeCard", "FreeItem", "FreeSide"],
}

DEFAULT_ANIMATION: dict[str, Any] = {
    "enabled": True,
    "entrance": "fade",
    "emphasis": "none",
    "transition": "fade",
    "transition_speed": "med",  # slow | med | fast
    "stagger_ms": 150,
    "on": "click",  # click | with_previous | after_previous
    "recipes": {
        # per-recipe overrides (optional)
        "cover": {"entrance": "fade", "transition": "fade"},
        "bullets": {"entrance": "fade"},
        "feature_cards": {"entrance": "fade"},
        "kpi_row": {"entrance": "appear"},
        "process": {"entrance": "wipe"},
        "freeform": {"entrance": "fade"},
    },
}


@dataclass
class AnimationReport:
    ok: bool
    slides_touched: int = 0
    effects_added: int = 0
    transitions_added: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# DESIGN.md / tokens extraction
# ---------------------------------------------------------------------------

_SPEED = frozenset({"slow", "med", "fast"})
_ON = frozenset({"click", "with_previous", "after_previous"})


def extract_animation(fm: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    """Parse optional ``animation:`` frontmatter block into tokens.animation."""
    warnings: list[str] = []
    raw = (fm or {}).get("animation")
    if raw is None:
        # Default off in tokens so existing decks stay animation-free unless asked
        cfg = copy.deepcopy(DEFAULT_ANIMATION)
        cfg["enabled"] = False
        return cfg, warnings
    if raw is False:
        cfg = copy.deepcopy(DEFAULT_ANIMATION)
        cfg["enabled"] = False
        return cfg, warnings
    if raw is True:
        return copy.deepcopy(DEFAULT_ANIMATION), warnings
    if not isinstance(raw, dict):
        warnings.append("animation: expected mapping — using defaults disabled")
        cfg = copy.deepcopy(DEFAULT_ANIMATION)
        cfg["enabled"] = False
        return cfg, warnings

    cfg = copy.deepcopy(DEFAULT_ANIMATION)
    cfg["enabled"] = bool(raw.get("enabled", True))

    ent = str(raw.get("entrance") or cfg["entrance"]).lower()
    if ent not in ENTRANCE_PRESETS:
        warnings.append(f"animation.entrance: unknown {ent!r} — using fade")
        ent = "fade"
    cfg["entrance"] = ent

    emph = str(raw.get("emphasis") or cfg["emphasis"]).lower()
    if emph not in EMPHASIS_PRESETS:
        warnings.append(f"animation.emphasis: unknown {emph!r} — using none")
        emph = "none"
    cfg["emphasis"] = emph

    tr = str(raw.get("transition") or cfg["transition"]).lower()
    if tr not in TRANSITION_PRESETS:
        warnings.append(f"animation.transition: unknown {tr!r} — using fade")
        tr = "fade"
    cfg["transition"] = tr

    spd = str(raw.get("transition_speed") or cfg["transition_speed"]).lower()
    if spd not in _SPEED:
        warnings.append(f"animation.transition_speed: unknown {spd!r} — using med")
        spd = "med"
    cfg["transition_speed"] = spd

    on = str(raw.get("on") or cfg["on"]).lower()
    if on not in _ON:
        on = "click"
    cfg["on"] = on

    try:
        cfg["stagger_ms"] = max(0, min(2000, int(raw.get("stagger_ms", cfg["stagger_ms"]))))
    except (TypeError, ValueError):
        warnings.append("animation.stagger_ms: invalid — using 150")

    recipes = raw.get("recipes")
    if isinstance(recipes, dict):
        merged = dict(cfg["recipes"])
        for k, v in recipes.items():
            if isinstance(v, dict):
                merged[str(k)] = {**merged.get(str(k), {}), **v}
            elif isinstance(v, str):
                merged[str(k)] = {"entrance": v}
        cfg["recipes"] = merged

    return cfg, warnings


def resolve_animation(tokens: dict[str, Any] | None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge tokens.animation with CLI overrides."""
    base = copy.deepcopy(DEFAULT_ANIMATION)
    src = (tokens or {}).get("animation")
    if isinstance(src, dict):
        base.update({k: v for k, v in src.items() if k != "recipes"})
        if isinstance(src.get("recipes"), dict):
            recipes = dict(base.get("recipes") or {})
            recipes.update(src["recipes"])
            base["recipes"] = recipes
    if overrides:
        for k, v in overrides.items():
            if v is not None and k != "recipes":
                base[k] = v
        if isinstance(overrides.get("recipes"), dict):
            recipes = dict(base.get("recipes") or {})
            recipes.update(overrides["recipes"])
            base["recipes"] = recipes
    # normalize
    if base.get("entrance") not in ENTRANCE_PRESETS:
        base["entrance"] = "fade"
    if base.get("transition") not in TRANSITION_PRESETS:
        base["transition"] = "fade"
    base["enabled"] = bool(base.get("enabled", True))
    return base


# ---------------------------------------------------------------------------
# OOXML helpers (namespace-safe)
# ---------------------------------------------------------------------------

def _shape_targets(slide_el: etree._Element) -> list[tuple[str, str]]:
    """Return [(spid, name), ...] for shapes that have cNvPr id+name."""
    out: list[tuple[str, str]] = []
    for cnv in slide_el.iter(opc.qn("p:cNvPr")):
        spid = cnv.get("id")
        name = cnv.get("name") or ""
        if spid and name:
            out.append((spid, name))
    return out


def _match_targets(
    shapes: list[tuple[str, str]],
    prefixes: list[str],
) -> list[tuple[str, str]]:
    if not prefixes:
        return shapes
    matched: list[tuple[str, str]] = []
    for spid, name in shapes:
        for pref in prefixes:
            if name == pref or name.startswith(pref):
                matched.append((spid, name))
                break
    return matched or shapes[:3]  # fall back to first few shapes


def _node_type_for_on(on: str) -> str:
    if on == "with_previous":
        return "withEffect"
    if on == "after_previous":
        return "afterEffect"
    return "clickEffect"


def _build_timing(
    targets: list[tuple[str, str]],
    *,
    entrance: str,
    stagger_ms: int,
    on: str,
    start_id: int = 1,
) -> etree._Element | None:
    """Build a p:timing element for entrance effects on targets."""
    ent = ENTRANCE_PRESETS.get(entrance) or ENTRANCE_PRESETS["fade"]
    if not ent.get("preset_class") or not targets:
        return None

    P = opc.NS["p"]
    A = opc.NS["a"]  # noqa: F841 — kept for future emphasis paths

    def el(tag: str, **attrs: str) -> etree._Element:
        # tag like p:timing
        e = etree.Element(opc.qn(tag))
        for k, v in attrs.items():
            e.set(k, v)
        return e

    timing = el("p:timing")
    tn_lst = el("p:tnLst")
    timing.append(tn_lst)

    root_par = el("p:par")
    tn_lst.append(root_par)
    cid = start_id
    root_ctn = el(
        "p:cTn",
        id=str(cid),
        dur="indefinite",
        restart="never",
        nodeType="tmRoot",
    )
    cid += 1
    root_par.append(root_ctn)
    root_children = el("p:childTnLst")
    root_ctn.append(root_children)

    seq = el("p:seq", concurrent="1", nextAc="seek")
    root_children.append(seq)
    main_ctn = el("p:cTn", id=str(cid), dur="indefinite", nodeType="mainSeq")
    cid += 1
    seq.append(main_ctn)
    main_children = el("p:childTnLst")
    main_ctn.append(main_children)

    # click container
    click_par = el("p:par")
    main_children.append(click_par)
    click_ctn = el("p:cTn", id=str(cid), fill="hold")
    cid += 1
    click_par.append(click_ctn)
    st = el("p:stCondLst")
    st.append(el("p:cond", delay="indefinite"))
    click_ctn.append(st)
    click_kids = el("p:childTnLst")
    click_ctn.append(click_kids)

    # group container
    grp_par = el("p:par")
    click_kids.append(grp_par)
    grp_ctn = el("p:cTn", id=str(cid), fill="hold")
    cid += 1
    grp_par.append(grp_ctn)
    gst = el("p:stCondLst")
    gst.append(el("p:cond", delay="0"))
    grp_ctn.append(gst)
    grp_kids = el("p:childTnLst")
    grp_ctn.append(grp_kids)

    node_type = _node_type_for_on(on)
    for i, (spid, _name) in enumerate(targets):
        delay = str(i * max(0, stagger_ms)) if on != "click" else ("0" if i == 0 else str(i * max(0, stagger_ms)))
        # For click: first is clickEffect; subsequent after previous with stagger
        this_node = node_type if i == 0 or on != "click" else "afterEffect"
        this_delay = "0" if i == 0 else str(i * max(0, stagger_ms))

        effect_par = el("p:par")
        grp_kids.append(effect_par)
        effect_ctn = el(
            "p:cTn",
            id=str(cid),
            presetID=str(ent["preset_id"]),
            presetClass=str(ent["preset_class"]),
            presetSubtype="0",
            fill="hold",
            grpId="0",
            nodeType=this_node,
        )
        cid += 1
        effect_par.append(effect_ctn)
        est = el("p:stCondLst")
        est.append(el("p:cond", delay=this_delay if on != "click" else ("0" if i == 0 else delay)))
        effect_ctn.append(est)
        effect_kids = el("p:childTnLst")
        effect_ctn.append(effect_kids)

        if ent.get("filter"):
            anim = el("p:animEffect", transition="in", filter=str(ent["filter"]))
        else:
            # appear / fly_in without filter: use set visibility
            anim = el("p:set")
            to_el = el("p:to")
            str_val = etree.Element(opc.qn("p:strVal"))
            # use a: namespace for strVal in some producers; p:strVal is accepted
            str_val = etree.Element("{http://schemas.openxmlformats.org/drawingml/2006/main}strVal")
            str_val.set("val", "visible")
            # Prefer p:strVal if present in schema; DrawingML strVal works in PPT
            to_el.append(str_val)
            anim.append(to_el)

        effect_kids.append(anim)
        cbhvr = el("p:cBhvr")
        anim.append(cbhvr)
        cbhvr.append(el("p:cTn", id=str(cid), dur=str(int(ent.get("dur_ms") or 500))))
        cid += 1
        tgt = el("p:tgtEl")
        cbhvr.append(tgt)
        tgt.append(el("p:spTgt", spid=str(spid)))

        if not ent.get("filter"):
            # For set-based appear, need attrNameLst
            attr = el("p:attrNameLst")
            an = el("p:attrName")
            an.text = "style.visibility"
            attr.append(an)
            cbhvr.append(attr)

    # prev/next conditions for sequence
    prev = el("p:prevCondLst")
    pc = el("p:cond", evt="onPrev", delay="0")
    pt = el("p:tgtEl")
    pt.append(el("p:sldTgt"))
    pc.append(pt)
    prev.append(pc)
    seq.append(prev)
    nxt = el("p:nextCondLst")
    nc = el("p:cond", evt="onNext", delay="0")
    nt = el("p:tgtEl")
    nt.append(el("p:sldTgt"))
    nc.append(nt)
    nxt.append(nc)
    seq.append(nxt)

    return timing


def _build_transition(name: str, speed: str) -> etree._Element | None:
    local = TRANSITION_PRESETS.get(name)
    if not local:
        return None
    tr = etree.Element(opc.qn("p:transition"))
    tr.set("spd", speed if speed in _SPEED else "med")
    child = etree.SubElement(tr, opc.qn(f"p:{local}"))
    if local == "push":
        child.set("dir", "l")
    elif local == "wipe":
        child.set("dir", "d")
    return tr


def inject_slide_animation(
    slide_xml: bytes,
    *,
    entrance: str = "fade",
    transition: str = "fade",
    transition_speed: str = "med",
    stagger_ms: int = 150,
    on: str = "click",
    name_prefixes: list[str] | None = None,
) -> tuple[bytes, int, int]:
    """Inject timing + transition into a slide part. Returns (xml, effects, transitions)."""
    decl = opc.xml_declaration(slide_xml)
    try:
        root = opc.parse(slide_xml)
    except etree.XMLSyntaxError:
        return slide_xml, 0, 0

    shapes = _shape_targets(root)
    targets = _match_targets(shapes, name_prefixes or [])
    effects = 0
    transitions = 0

    # Remove existing timing / transition (we own animation when --animate runs)
    for tag in ("p:timing", "p:transition"):
        for old in list(root.iter(opc.qn(tag))):
            parent = old.getparent()
            if parent is not None:
                parent.remove(old)

    timing = _build_timing(
        targets,
        entrance=entrance,
        stagger_ms=stagger_ms,
        on=on,
    )
    if timing is not None:
        root.append(timing)
        effects = len(targets)

    tr_el = _build_transition(transition, transition_speed)
    if tr_el is not None:
        # transition should appear before timing in many writers; append is OK for PPT
        # Insert after cSld if possible
        csld = root.find(opc.qn("p:cSld"))
        if csld is not None:
            idx = list(root).index(csld) + 1
            root.insert(idx, tr_el)
        else:
            root.insert(0, tr_el)
        transitions = 1

    return opc.serialize(root, declaration=decl), effects, transitions


def _guess_recipe_from_shapes(shapes: list[tuple[str, str]]) -> str:
    names = " ".join(n for _, n in shapes).lower()
    for recipe, prefixes in DEFAULT_SHAPE_TARGETS.items():
        for p in prefixes:
            if p.lower() in names:
                return recipe
    return "bullets"


def animate_pptx(
    pptx: str | Path,
    *,
    out: str | Path | None = None,
    animation: dict[str, Any] | None = None,
    tokens: dict[str, Any] | None = None,
    force: bool = False,
    recipe_hints: list[str] | None = None,
) -> AnimationReport:
    """Inject namespace-safe animation into every slide of a .pptx."""
    src = Path(pptx)
    if not src.is_file():
        return AnimationReport(ok=False, notes=[f"missing pptx: {src}"])

    cfg = resolve_animation(tokens, animation)
    if not cfg.get("enabled", True):
        return AnimationReport(ok=True, notes=["animation disabled in config"])

    dest = Path(out) if out else src
    if dest.exists() and dest.resolve() != src.resolve() and not force:
        return AnimationReport(ok=False, notes=[f"refusing to overwrite {dest} without --force"])

    notes: list[str] = []
    slides_touched = 0
    effects_total = 0
    transitions_total = 0

    # Work in memory then write staging-safe
    try:
        with zipfile.ZipFile(src, "r") as zin:
            parts = {name: zin.read(name) for name in zin.namelist()}
    except (OSError, zipfile.BadZipFile) as e:
        return AnimationReport(ok=False, notes=[f"corrupt pptx: {e}"])

    slide_names = sorted(
        n for n in parts
        if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)
    )
    if not slide_names:
        return AnimationReport(ok=False, notes=["no ppt/slides/slideN.xml parts"])

    for i, name in enumerate(slide_names):
        shapes = []
        try:
            root = opc.parse(parts[name])
            shapes = _shape_targets(root)
        except etree.XMLSyntaxError:
            notes.append(f"{name}: parse failed — left untouched")
            continue

        recipe = (recipe_hints[i] if recipe_hints and i < len(recipe_hints)
                  else _guess_recipe_from_shapes(shapes))
        per = (cfg.get("recipes") or {}).get(recipe) or {}
        entrance = str(per.get("entrance") or cfg.get("entrance") or "fade")
        transition = str(per.get("transition") or cfg.get("transition") or "fade")
        prefixes = list(DEFAULT_SHAPE_TARGETS.get(recipe) or DEFAULT_SHAPE_TARGETS["bullets"])

        new_xml, eff, trn = inject_slide_animation(
            parts[name],
            entrance=entrance,
            transition=transition,
            transition_speed=str(cfg.get("transition_speed") or "med"),
            stagger_ms=int(cfg.get("stagger_ms") or 150),
            on=str(cfg.get("on") or "click"),
            name_prefixes=prefixes,
        )
        if new_xml != parts[name]:
            parts[name] = new_xml
            slides_touched += 1
            effects_total += eff
            transitions_total += trn

    # Staging write
    staging = dest.with_suffix(dest.suffix + ".anim-staging")
    try:
        with zipfile.ZipFile(staging, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name, data in parts.items():
                zout.writestr(name, data)
        staging.replace(dest)
    except OSError as e:
        if staging.exists():
            staging.unlink(missing_ok=True)
        return AnimationReport(ok=False, notes=[f"write failed: {e}"])

    return AnimationReport(
        ok=True,
        slides_touched=slides_touched,
        effects_added=effects_total,
        transitions_added=transitions_total,
        notes=notes,
    )


def animation_summary(cfg: dict[str, Any]) -> str:
    if not cfg.get("enabled"):
        return "animation: disabled"
    return (
        f"animation: entrance={cfg.get('entrance')} transition={cfg.get('transition')} "
        f"emphasis={cfg.get('emphasis')} stagger_ms={cfg.get('stagger_ms')}"
    )
