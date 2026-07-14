"""Slide master / theme branding + .potx template export (v1.3).

brand_master injects DESIGN.md tokens into the presentation *theme* (color
scheme + major/minor fonts) and sets the slide-master type scale, so slides
added later in PowerPoint inherit the brand. export_potx converts a branded
deck into a PowerPoint template (.potx), optionally stripped of its slides.
Stdlib only; staging-safe via restyle.rewrite_package.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lxml.etree import XMLSyntaxError

from . import opc
from .opc import qn
from .restyle import _SCHEME_MAP, _restyle_theme_tree, rewrite_package

_PRESENTATION_CT = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
)
_TEMPLATE_CT = (
    "application/vnd.openxmlformats-officedocument.presentationml.template.main+xml"
)


def _style_master_tree(root, typ: dict[str, Any], report: dict[str, Any]) -> None:
    """Set title/body default sizes in slideMaster txStyles from the token type
    scale (the first defRPr under titleStyle / bodyStyle). Font faces are left
    as +mj-lt / +mn-lt so they follow the theme set by _restyle_theme_tree."""
    def _set(style_tag: str, pt: Any, key: str) -> None:
        if not pt:
            return
        style = root.find(f".//{qn('p:' + style_tag)}")
        if style is None:
            return
        defrpr = style.find(f".//{qn('a:defRPr')}")
        if defrpr is None:
            return
        defrpr.set("sz", str(int(pt) * 100))
        report["master_styles"][key] = pt

    _set("titleStyle", typ.get("title_pt"), "title_pt")
    _set("bodyStyle", typ.get("body_pt"), "body_pt")


def brand_master(
    pptx: str | Path,
    tokens: dict[str, Any],
    *,
    out: str | Path | None = None,
    force: bool = False,
    layouts: bool = False,
) -> dict[str, Any]:
    """Brand theme + slide master of pptx with tokens. Returns a report.

    Unlike restyle, slide content is untouched — only the theme (scheme +
    fonts) and master type scale change, so this is safe on any deck.
    layouts=True additionally rebrands slideLayouts: explicit srgbClr values
    that EXACTLY match an old theme-scheme slot are mapped to that slot's new
    brand color (a layout that hard-coded the old accent gets the new accent).
    Unmatched colors are left alone and reported — nearest-palette snapping
    would risk collapsing foreground and background into one color.
    """
    colors: dict[str, str] = {
        k: str(v).upper() for k, v in (tokens.get("colors") or {}).items()
        if isinstance(v, str) and re.fullmatch(r"[0-9A-Fa-f]{6}", str(v))
    }
    if not colors:
        raise ValueError("tokens have no usable colors — compile DESIGN.md first")
    typ: dict[str, Any] = tokens.get("type") or {}

    report: dict[str, Any] = {
        "source": str(Path(pptx).resolve()), "dest": "",
        "theme_scheme": {}, "theme_fonts": {}, "master_styles": {},
        "layout_colors": {}, "layout_colors_skipped": [],
    }

    # old scheme slot hex → new brand hex (captured BEFORE the theme rewrite)
    slot_remap: dict[str, str] = {}
    if layouts:
        old_slots = _scheme_slot_colors(Path(pptx))
        for slot, keys in _SCHEME_MAP:
            new = next((colors[k] for k in keys if colors.get(k)), None)
            old = old_slots.get(slot)
            if old and new and old != new.upper():
                slot_remap[old] = new.upper()

    def _brand_layout_tree(root) -> None:
        skipped: set[str] = set()

        def _fn(old: str) -> str:
            new = slot_remap.get(old)
            if new is None:
                if old not in slot_remap.values():
                    skipped.add(old)
                return old
            report["layout_colors"].setdefault(old, {"new": new, "count": 0})["count"] += 1
            return new

        opc.remap_srgb_colors(root, _fn)
        for s in sorted(skipped):
            if s not in report["layout_colors_skipped"]:
                report["layout_colors_skipped"].append(s)

    def transform(name: str, data: bytes) -> bytes:
        is_theme = re.fullmatch(r"ppt/theme/theme\d+\.xml", name)
        is_master = re.fullmatch(r"ppt/slideMasters/[^/]+\.xml", name)
        is_layout = layouts and re.fullmatch(r"ppt/slideLayouts/[^/]+\.xml", name)
        if not (is_theme or is_master or is_layout):
            return data
        decl = opc.xml_declaration(data)
        try:
            root = opc.parse(data)
        except XMLSyntaxError:
            report.setdefault("unparsed", []).append(name)
            return data
        if is_theme:
            _restyle_theme_tree(root, colors, typ, report)
        elif is_master:
            _style_master_tree(root, typ, report)
        else:
            _brand_layout_tree(root)
        return opc.serialize(root, declaration=decl)

    dest = rewrite_package(pptx, out, transform, force=force)
    report["dest"] = str(dest)
    dest.with_suffix(".master.report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def export_potx(
    pptx: str | Path,
    out: str | Path,
    *,
    force: bool = False,
    empty: bool = False,
    stats: dict[str, Any] | None = None,
) -> Path:
    """Convert a (branded) .pptx into a .potx template.

    empty=True strips all slides so the template opens blank: slide parts are
    dropped, sldIdLst / presentation rels / content-type overrides cleaned,
    and media parts no longer referenced by any surviving part are pruned
    (masters / layouts / theme / notesMaster references always survive).
    """
    out = Path(out)
    if out.suffix.lower() != ".potx":
        raise ValueError(f"potx output must end with .potx: {out}")

    dropped_media: set[str] = set()
    if empty:
        dropped_media = _unreferenced_media(Path(pptx))
    if stats is not None:
        stats["pruned_media"] = sorted(dropped_media)

    def transform(name: str, data: bytes) -> bytes | None:
        if empty and re.fullmatch(r"ppt/(slides|notesSlides)/.*", name):
            return None
        if empty and name in dropped_media:
            return None
        if name == "[Content_Types].xml":
            return _potx_content_types(data, empty, dropped_media)
        if empty and name == "ppt/presentation.xml":
            return _strip_slide_ids(data)
        if empty and name == "ppt/_rels/presentation.xml.rels":
            return _strip_slide_rels(data)
        return data

    return rewrite_package(pptx, out, transform, force=force)


def _potx_content_types(data: bytes, empty: bool, dropped_media: set[str]) -> bytes:
    """Flip the presentation content-type Override to the template type and,
    when emptying, drop Overrides for the removed slide/media parts."""
    decl = opc.xml_declaration(data)
    root = opc.parse(data)
    swapped = False
    # The presentation content type may be carried by an Override (specific
    # part) OR a Default (extension) depending on the writer — swap it wherever
    # it lives, matching the old substring-replace behavior namespace-aware.
    for el in (*root.iter(qn("ct:Override")), *root.iter(qn("ct:Default"))):
        if el.get("ContentType") == _PRESENTATION_CT:
            el.set("ContentType", _TEMPLATE_CT)
            swapped = True
    if not swapped:
        raise ValueError("source is not a .pptx presentation package")
    if empty:
        drop_parts = {"/" + m for m in dropped_media}
        for ov in list(root.iter(qn("ct:Override"))):
            part = ov.get("PartName", "")
            # media is usually covered by extension Defaults (kept); only a
            # part-specific Override must go with its part.
            if re.match(r"/ppt/(slides|notesSlides)/", part) or part in drop_parts:
                ov.getparent().remove(ov)
    return opc.serialize(root, declaration=decl)


def _strip_slide_ids(data: bytes) -> bytes:
    """Remove every ``p:sldId`` so an emptied template opens with no slides."""
    decl = opc.xml_declaration(data)
    root = opc.parse(data)
    for sld in list(root.iter(qn("p:sldId"))):
        sld.getparent().remove(sld)
    return opc.serialize(root, declaration=decl)


def _strip_slide_rels(data: bytes) -> bytes:
    """Drop presentation relationships that target the removed slide parts."""
    decl = opc.xml_declaration(data)
    root = opc.parse(data)
    for rel in list(root.iter(qn("rel:Relationship"))):
        if (rel.get("Target") or "").startswith("slides/"):
            rel.getparent().remove(rel)
    return opc.serialize(root, declaration=decl)


def _scheme_slot_colors(pptx: Path) -> dict[str, str]:
    """Old theme scheme slot → hex, read before any rewrite (srgbClr val or
    sysClr lastClr), namespace-aware via opc."""
    import zipfile

    slots: dict[str, str] = {}
    with zipfile.ZipFile(pptx) as zf:
        for name in zf.namelist():
            if not re.fullmatch(r"ppt/theme/theme\d+\.xml", name):
                continue
            try:
                theme = opc.parse(zf.read(name))
            except XMLSyntaxError:
                break
            for slot, _keys in _SCHEME_MAP:
                hexv = opc.get_scheme_color(theme, slot)
                if hexv and slot not in slots:
                    slots[slot] = hexv
            break  # theme1 wins
    return slots


def _unreferenced_media(pptx: Path) -> set[str]:
    """Media parts referenced ONLY by slides/notesSlides (which --empty drops).

    Scans every surviving part's .rels for targets resolving under ppt/media/;
    whatever the survivors reference is kept, the rest is garbage-collected.
    """
    import zipfile
    from urllib.parse import unquote

    referenced: set[str] = set()
    all_media: set[str] = set()
    with zipfile.ZipFile(pptx) as zf:
        for name in zf.namelist():
            if name.startswith("ppt/media/"):
                all_media.add(name)
                continue
            if not name.endswith(".rels"):
                continue
            if re.match(r"ppt/(slides|notesSlides)/_rels/", name):
                continue  # these parts are dropped; their refs don't count
            base = name.split("/_rels/")[0]
            try:
                rels = opc.parse(zf.read(name))
            except XMLSyntaxError:
                continue
            for rel in rels.iter(qn("rel:Relationship")):
                target = rel.get("Target")
                if not target or "://" in target:  # TargetMode="External" URLs
                    continue
                t = unquote(target).lstrip("/")
                b = base
                while t.startswith("../"):
                    b = b.rsplit("/", 1)[0] if "/" in b else ""
                    t = t[3:]
                resolved = f"{b}/{t}" if b and not t.startswith("ppt/") else t
                if "media/" in resolved:
                    referenced.add(
                        "ppt/media/" + resolved.split("media/", 1)[1]
                    )
    return all_media - referenced
