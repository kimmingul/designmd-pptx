"""In-place restyle of an existing .pptx with DESIGN.md brand tokens (v1.2).

Rewrites the theme color scheme + theme fonts, and optionally remaps explicit
srgbClr values / typefaces in slides, layouts, and masters to the nearest
brand token. Layout is never touched. Stdlib only; staging-safe like apply.py:
the destination is never deleted until the restyled copy is fully written.
"""

from __future__ import annotations

import json
import os
import re
import uuid
import zipfile
from pathlib import Path
from typing import Any

from lxml.etree import XMLSyntaxError

from . import opc

# Theme scheme slot → tokens.colors key (first existing key wins)
_SCHEME_MAP: list[tuple[str, list[str]]] = [
    ("dk1", ["text"]),
    ("lt1", ["background"]),
    ("dk2", ["muted", "text"]),
    ("lt2", ["surface", "background"]),
    ("accent1", ["accent"]),
    ("accent2", ["success", "chart_series2", "accent"]),
    ("accent3", ["risk", "chart_series3", "accent"]),
    ("accent4", ["chart_series2", "accent"]),
    ("accent5", ["chart_series3", "accent"]),
    ("accent6", ["surface_elevated", "surface", "accent"]),
    ("hlink", ["accent"]),
    ("folHlink", ["muted", "accent"]),
]

_MONO_HINTS = ("mono", "consolas", "courier", "menlo", "monaco", "code")


def _hex_dist(a: str, b: str) -> int:
    ar, ag, ab = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
    br, bg, bb = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
    return (ar - br) ** 2 + (ag - bg) ** 2 + (ab - bb) ** 2


def _nearest(color: str, palette: list[str]) -> str:
    return min(palette, key=lambda p: _hex_dist(color, p))


def _restyle_theme_tree(theme, colors: dict[str, str], typ: dict[str, Any],
                        report: dict[str, Any]) -> None:
    """Namespace-aware theme rebrand: point each clrScheme slot at an explicit
    srgbClr (replacing srgbClr OR sysClr) and set the major/minor latin fonts."""
    for slot, keys in _SCHEME_MAP:
        val = next((colors[k] for k in keys if colors.get(k)), None)
        if val and opc.set_scheme_color(theme, slot, val):
            report["theme_scheme"][slot] = val.upper()

    heading = typ.get("heading_font")
    body = typ.get("body_font")
    if heading and opc.set_theme_font(theme, "majorFont", heading):
        report["theme_fonts"]["major"] = heading
    if body and opc.set_theme_font(theme, "minorFont", body):
        report["theme_fonts"]["minor"] = body


def _restyle_part_tree(root, palette: list[str], typ: dict[str, Any],
                       explicit_colors: bool, explicit_fonts: bool,
                       color_map: dict[str, str], report: dict[str, Any]) -> None:
    if explicit_colors and palette:
        def _color(old: str) -> str:
            new = color_map.get(old) or _nearest(old, palette)
            if new != old:
                report["colors"].setdefault(old, {"new": new, "count": 0})["count"] += 1
            return new

        opc.remap_srgb_colors(root, _color)

    if explicit_fonts and (typ.get("body_font") or typ.get("mono_font")):
        body = typ.get("body_font", "Calibri")
        mono = typ.get("mono_font", "Consolas")
        heading = typ.get("heading_font", body)
        # Runs at/above the section size keep the HEADING font (v1.5) —
        # flattening titles into the body font was a v1.2 defect. Size comes
        # from the enclosing run-props element; typefaces outside a sized run
        # (size None) fall to the body font unless they look monospace.
        heading_sz = int(typ.get("section_pt", 28)) * 100

        def _font(old: str, sz: int | None) -> str:
            if old.startswith("+"):  # +mj-lt / +mn-lt follow the theme
                return old
            if any(h in old.lower() for h in _MONO_HINTS):
                new = mono
            else:
                new = heading if (sz or 0) >= heading_sz else body
            if new != old:
                report["fonts"].setdefault(old, {"new": new, "count": 0})["count"] += 1
            return new

        opc.remap_typefaces(root, _font)


def rewrite_package(
    src: str | Path,
    dest: str | Path | None,
    transform,
    *,
    force: bool = False,
) -> Path:
    """Copy an OPC package applying transform(name, bytes) → bytes | None.

    Returning None drops the part. dest=None rewrites in place (requires
    force). Staging-safe: the destination is never deleted until the new
    package is fully written (os.replace).
    """
    src = Path(src).resolve()
    if not src.exists():
        raise FileNotFoundError(str(src))
    dest_p = Path(dest).resolve() if dest else src
    if dest_p.exists() and not force:
        raise FileExistsError(
            f"{dest_p} already exists. Pass force=True / --force to overwrite."
        )

    staging = dest_p.with_name(
        f".{dest_p.stem}.staging-{uuid.uuid4().hex[:8]}{dest_p.suffix}"
    )
    try:
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(
            staging, "w", zipfile.ZIP_DEFLATED
        ) as zout:
            for item in zin.infolist():
                data = transform(item.filename, zin.read(item.filename))
                if data is None:
                    continue
                zout.writestr(item, data)
        os.replace(str(staging), str(dest_p))
    finally:
        if staging.exists():
            try:
                staging.unlink()
            except OSError:
                pass
    return dest_p


def restyle_pptx(
    pptx: str | Path,
    tokens: dict[str, Any],
    *,
    out: str | Path | None = None,
    force: bool = False,
    explicit_colors: bool = True,
    explicit_fonts: bool = True,
    color_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Restyle pptx with brand tokens. Returns a report of replacements.

    out=None restyles in place (requires force). A distinct existing out
    also requires force. Never deletes the destination until the restyled
    staging copy is complete (os.replace).
    """
    colors: dict[str, str] = {
        k: str(v).upper() for k, v in (tokens.get("colors") or {}).items()
        if isinstance(v, str) and re.fullmatch(r"[0-9A-Fa-f]{6}", str(v))
    }
    typ: dict[str, Any] = tokens.get("type") or {}
    if not colors:
        raise ValueError("tokens have no usable colors — compile DESIGN.md first")
    palette = sorted(set(colors.values()))
    cmap = {k.upper(): v.upper() for k, v in (color_map or {}).items()}

    report: dict[str, Any] = {
        "source": str(Path(pptx).resolve()), "dest": "",
        "theme_scheme": {}, "theme_fonts": {}, "colors": {}, "fonts": {},
    }

    def transform(name: str, data: bytes) -> bytes:
        is_theme = re.fullmatch(r"ppt/theme/theme\d+\.xml", name)
        is_part = re.fullmatch(
            r"ppt/(slides|slideLayouts|slideMasters)/[^/]+\.xml", name)
        if not (is_theme or is_part):
            return data
        decl = opc.xml_declaration(data)
        try:
            root = opc.parse(data)
        except XMLSyntaxError:
            # A malformed part is left byte-for-byte untouched rather than
            # aborting the whole restyle — never make a bad deck worse.
            report.setdefault("unparsed", []).append(name)
            return data
        if is_theme:
            _restyle_theme_tree(root, colors, typ, report)
        else:
            _restyle_part_tree(
                root, palette, typ, explicit_colors, explicit_fonts, cmap, report)
        return opc.serialize(root, declaration=decl)

    dest = rewrite_package(pptx, out, transform, force=force)
    report["dest"] = str(dest)

    report_path = dest.with_suffix(".restyle.report.json")
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
