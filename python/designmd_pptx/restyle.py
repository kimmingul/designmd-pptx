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


def _restyle_theme(xml: str, colors: dict[str, str], typ: dict[str, Any],
                   report: dict[str, Any]) -> str:
    for slot, keys in _SCHEME_MAP:
        val = next((colors[k] for k in keys if colors.get(k)), None)
        if not val:
            continue
        pattern = re.compile(rf"(<a:{slot}>).*?(</a:{slot}>)", re.S)
        new_xml, n = pattern.subn(rf'\g<1><a:srgbClr val="{val.upper()}"/>\g<2>', xml)
        if n:
            report["theme_scheme"][slot] = val.upper()
            xml = new_xml

    heading = typ.get("heading_font")
    body = typ.get("body_font")
    if heading:
        xml, n = re.subn(
            r'(<a:majorFont>\s*<a:latin[^>]*typeface=")[^"]*(")',
            rf"\g<1>{heading}\g<2>", xml, flags=re.S,
        )
        if n:
            report["theme_fonts"]["major"] = heading
    if body:
        xml, n = re.subn(
            r'(<a:minorFont>\s*<a:latin[^>]*typeface=")[^"]*(")',
            rf"\g<1>{body}\g<2>", xml, flags=re.S,
        )
        if n:
            report["theme_fonts"]["minor"] = body
    return xml


def _restyle_part(xml: str, palette: list[str], typ: dict[str, Any],
                  explicit_colors: bool, explicit_fonts: bool,
                  color_map: dict[str, str], report: dict[str, Any]) -> str:
    if explicit_colors and palette:
        def _sub_color(m: re.Match) -> str:
            old = m.group(1).upper()
            new = color_map.get(old) or _nearest(old, palette)
            if new != old:
                entry = report["colors"].setdefault(old, {"new": new, "count": 0})
                entry["count"] += 1
            return f'srgbClr val="{new}"'

        xml = re.sub(r'srgbClr val="([0-9A-Fa-f]{6})"', _sub_color, xml)

    if explicit_fonts and (typ.get("body_font") or typ.get("mono_font")):
        body = typ.get("body_font", "Calibri")
        mono = typ.get("mono_font", "Consolas")
        heading = typ.get("heading_font", body)
        # Runs at/above the section size keep the HEADING font (v1.5) —
        # flattening titles into the body font was a v1.2 defect.
        heading_sz = int(typ.get("section_pt", 28)) * 100

        def _map_font(old: str, sz: int) -> str:
            if any(h in old.lower() for h in _MONO_HINTS):
                return mono
            return heading if sz >= heading_sz else body

        def _record(old: str, new: str) -> None:
            if new != old:
                entry = report["fonts"].setdefault(old, {"new": new, "count": 0})
                entry["count"] += 1

        def _sub_block(m: re.Match) -> str:
            block = m.group(0)
            if "typeface" not in block:
                return block
            szm = re.search(r'\bsz="(\d+)"', block)
            sz = int(szm.group(1)) if szm else 0

            def _sub_face(tm: re.Match) -> str:
                old = tm.group(2)
                if old.startswith("+"):  # +mj-lt / +mn-lt follow the theme
                    return tm.group(0)
                new = _map_font(old, sz)
                _record(old, new)
                return f"{tm.group(1)}{new}{tm.group(3)}"

            return re.sub(r'(typeface=")([^"]+)(")', _sub_face, block)

        # Size-aware pass over run/paragraph property blocks…
        xml = re.sub(
            r"<a:(rPr|defRPr|endParaRPr)\b[^>]*?>.*?</a:\1>", _sub_block, xml, flags=re.S
        )

        # …then a catch-all for typefaces outside sized blocks (no size → body).
        # Brand fonts already placed by the first pass must not be re-mapped.
        def _sub_font(m: re.Match) -> str:
            old = m.group(1)
            if old.startswith("+") or old in (heading, body, mono):
                return m.group(0)
            new = _map_font(old, 0)
            _record(old, new)
            return f'typeface="{new}"'

        xml = re.sub(r'typeface="([^"]+)"', _sub_font, xml)
    return xml


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
        if re.fullmatch(r"ppt/theme/theme\d+\.xml", name):
            return _restyle_theme(data.decode("utf-8"), colors, typ, report).encode("utf-8")
        if re.fullmatch(r"ppt/(slides|slideLayouts|slideMasters)/[^/]+\.xml", name):
            return _restyle_part(
                data.decode("utf-8"), palette, typ,
                explicit_colors, explicit_fonts, cmap, report,
            ).encode("utf-8")
        return data

    dest = rewrite_package(pptx, out, transform, force=force)
    report["dest"] = str(dest)

    report_path = dest.with_suffix(".restyle.report.json")
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
