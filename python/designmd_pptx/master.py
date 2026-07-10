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

from .restyle import _restyle_theme, rewrite_package

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
) -> dict[str, Any]:
    """Brand theme + slide master of pptx with tokens. Returns a report.

    Unlike restyle, slide content is untouched — only the theme (scheme +
    fonts) and master type scale change, so this is safe on any deck.
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
    }

    def transform(name: str, data: bytes) -> bytes:
        if re.fullmatch(r"ppt/theme/theme\d+\.xml", name):
            return _restyle_theme(data.decode("utf-8"), colors, typ, report).encode("utf-8")
        if re.fullmatch(r"ppt/slideMasters/[^/]+\.xml", name):
            return _style_master(data.decode("utf-8"), typ, report).encode("utf-8")
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
) -> Path:
    """Convert a (branded) .pptx into a .potx template.

    empty=True strips all slides so the template opens blank: slide parts are
    dropped, sldIdLst / presentation rels / content-type overrides cleaned.
    """
    out = Path(out)
    if out.suffix.lower() != ".potx":
        raise ValueError(f"potx output must end with .potx: {out}")

    def transform(name: str, data: bytes) -> bytes | None:
        if empty and re.fullmatch(r"ppt/(slides|notesSlides)/.*", name):
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
