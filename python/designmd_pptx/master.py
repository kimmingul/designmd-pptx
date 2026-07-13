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

from .restyle import _SCHEME_MAP, _restyle_theme, rewrite_package

_PRESENTATION_CT = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
)
_TEMPLATE_CT = (
    "application/vnd.openxmlformats-officedocument.presentationml.template.main+xml"
)


def _style_master(xml: str, typ: dict[str, Any], report: dict[str, Any]) -> str:
    """Set title/body default sizes in slideMaster txStyles from the token
    type scale. Font faces are left as +mj-lt / +mn-lt so they follow the
    theme set by _restyle_theme."""
    title_pt = typ.get("title_pt")
    body_pt = typ.get("body_pt")
    if title_pt:
        xml, n = re.subn(
            r'(<p:titleStyle>.*?<a:defRPr[^>]*?sz=")\d+(")',
            rf"\g<1>{int(title_pt) * 100}\g<2>", xml, count=1, flags=re.S,
        )
        if n:
            report["master_styles"]["title_pt"] = title_pt
    if body_pt:
        xml, n = re.subn(
            r'(<p:bodyStyle>.*?<a:defRPr[^>]*?sz=")\d+(")',
            rf"\g<1>{int(body_pt) * 100}\g<2>", xml, count=1, flags=re.S,
        )
        if n:
            report["master_styles"]["body_pt"] = body_pt
    return xml


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

    def _brand_layout(xml: str) -> str:
        skipped: set[str] = set()

        def sub(m: re.Match) -> str:
            old = m.group(1).upper()
            new = slot_remap.get(old)
            if new is None:
                if old not in slot_remap.values():
                    skipped.add(old)
                return m.group(0)
            entry = report["layout_colors"].setdefault(old, {"new": new, "count": 0})
            entry["count"] += 1
            return f'srgbClr val="{new}"'

        xml = re.sub(r'srgbClr val="([0-9A-Fa-f]{6})"', sub, xml)
        for s in sorted(skipped):
            if s not in report["layout_colors_skipped"]:
                report["layout_colors_skipped"].append(s)
        return xml

    def transform(name: str, data: bytes) -> bytes:
        if re.fullmatch(r"ppt/theme/theme\d+\.xml", name):
            return _restyle_theme(data.decode("utf-8"), colors, typ, report).encode("utf-8")
        if re.fullmatch(r"ppt/slideMasters/[^/]+\.xml", name):
            return _style_master(data.decode("utf-8"), typ, report).encode("utf-8")
        if layouts and re.fullmatch(r"ppt/slideLayouts/[^/]+\.xml", name):
            return _brand_layout(data.decode("utf-8")).encode("utf-8")
        return data

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
            xml = data.decode("utf-8")
            if _PRESENTATION_CT not in xml:
                raise ValueError("source is not a .pptx presentation package")
            xml = xml.replace(_PRESENTATION_CT, _TEMPLATE_CT, 1)
            if empty:
                xml = re.sub(
                    r'<Override PartName="/ppt/(slides|notesSlides)/[^"]*"[^>]*/>', "", xml
                )
                for media in dropped_media:
                    # media is usually covered by extension Defaults (kept);
                    # only a part-specific Override must go with the part
                    xml = re.sub(
                        rf'<Override PartName="/{re.escape(media)}"[^>]*/>', "", xml
                    )
            return xml.encode("utf-8")
        if empty and name == "ppt/presentation.xml":
            xml = data.decode("utf-8")
            xml = re.sub(r"<p:sldId [^>]*/>", "", xml)
            return xml.encode("utf-8")
        if empty and name == "ppt/_rels/presentation.xml.rels":
            xml = data.decode("utf-8")
            xml = re.sub(r'<Relationship [^>]*Target="slides/[^"]*"[^>]*/>', "", xml)
            return xml.encode("utf-8")
        return data

    return rewrite_package(pptx, out, transform, force=force)


def _scheme_slot_colors(pptx: Path) -> dict[str, str]:
    """Old theme scheme slot → hex, read before any rewrite (srgbClr val or
    sysClr lastClr)."""
    import zipfile

    slots: dict[str, str] = {}
    with zipfile.ZipFile(pptx) as zf:
        for name in zf.namelist():
            if not re.fullmatch(r"ppt/theme/theme\d+\.xml", name):
                continue
            xml = zf.read(name).decode("utf-8", errors="replace")
            for slot, _keys in _SCHEME_MAP:
                m = re.search(
                    rf"<a:{slot}>.*?(?:srgbClr val|lastClr)=\"([0-9A-Fa-f]{{6}})\"",
                    xml, re.S,
                )
                if m and slot not in slots:
                    slots[slot] = m.group(1).upper()
            break  # theme1 wins
    return slots


def _unreferenced_media(pptx: Path) -> set[str]:
    """Media parts referenced ONLY by slides/notesSlides (which --empty drops).

    Scans every surviving part's .rels for targets resolving under ppt/media/;
    whatever the survivors reference is kept, the rest is garbage-collected.
    """
    import zipfile

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
            xml = zf.read(name).decode("utf-8", errors="replace")
            for target in re.findall(r'Target="([^"]+)"', xml):
                if "://" in target:  # TargetMode="External" URLs
                    continue
                from urllib.parse import unquote

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
