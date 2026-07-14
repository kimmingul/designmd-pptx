"""Namespace-aware OOXML manipulation (issue #16).

The restyle/master paths historically mutated OOXML with regex over the raw
string. That is fragile to namespace-prefix, attribute-order, and whitespace
variation and can silently corrupt a part it only half-matches (e.g. blindly
overwriting the inner content of a ``<a:dk1>`` slot that holds an ``<a:sysClr>``
rather than an ``<a:srgbClr>``). This module parses parts with lxml, matches
elements by **namespace URI** (never by the document's literal prefix), and
preserves unknown elements/attributes across the round-trip.

Fidelity is defined **semantically**, not byte-for-byte: parts we do not touch
are copied verbatim from the source zip; within a part we do mutate, every
element/attribute we did not target survives re-serialization.

Security: untrusted ``.pptx`` parts are parsed with entity resolution and
network access disabled and unbounded trees rejected, so a crafted part cannot
mount an XML entity-expansion ("billion laughs") or external-DTD/SSRF attack.
(defusedxml's lxml shim is deprecated upstream; configuring lxml's own parser
flags is the current recommended control.)
"""

from __future__ import annotations

import re
from typing import Callable

from lxml import etree

# OOXML namespace URIs. Everything is matched by URI, so a document that binds
# these to different prefixes still works.
NS: dict[str, str] = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def qn(tag: str) -> str:
    """``'a:dk1'`` → ``'{uri}dk1'`` (Clark notation) for prefix-independent
    matching; a tag without a known prefix is returned unchanged."""
    prefix, sep, local = tag.partition(":")
    if sep and prefix in NS:
        return f"{{{NS[prefix]}}}{local}"
    return tag


# resolve_entities=False neutralizes entity-expansion bombs; no_network blocks
# external DTD/entity fetches; huge_tree=False keeps lxml's size guards on.
_SAFE_PARSER = etree.XMLParser(
    resolve_entities=False, no_network=True, huge_tree=False,
)

# Capture an optional leading UTF-8 BOM together with the declaration: OOXML
# writers (the legacy OfficeCLI included) emit BOM-prefixed parts, and dropping
# the BOM on the round-trip would be an avoidable fidelity loss.
_BOM = b"\xef\xbb\xbf"
_DECL_RE = re.compile(rb"^(?:\xef\xbb\xbf)?\s*<\?xml[^>]*\?>")
_DEFAULT_DECL = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
_HEX6 = re.compile(r"[0-9A-Fa-f]{6}")


def xml_declaration(data: bytes) -> bytes:
    """The part's original leading bytes up to and including the ``<?xml …?>``
    header (any BOM included), so serialization reproduces it verbatim (BOM,
    quote style, ``standalone``) instead of lxml's own rendering. Falls back to
    a bare default declaration when the part has none."""
    m = _DECL_RE.match(data)
    if m:
        return m.group(0)
    return _BOM + _DEFAULT_DECL if data.startswith(_BOM) else _DEFAULT_DECL


def parse(data: bytes) -> etree._Element:
    """Parse a part with the safe parser. Raises ``etree.XMLSyntaxError`` on
    malformed input (callers may fall back to leaving the part untouched)."""
    return etree.fromstring(data, parser=_SAFE_PARSER)


def serialize(el: etree._Element, *, declaration: bytes = _DEFAULT_DECL) -> bytes:
    """Element → bytes, re-attaching the original XML declaration."""
    body = etree.tostring(el, encoding="utf-8", xml_declaration=False)
    return declaration + body


# ------------------------------------------------------------- theme helpers

# Any DrawingML color child a scheme slot may legitimately hold.
_COLOR_CHILDREN = frozenset(
    qn(f"a:{t}") for t in
    ("srgbClr", "sysClr", "scrgbClr", "hslClr", "prstClr", "schemeClr")
)


def set_scheme_color(theme: etree._Element, slot: str, hexval: str) -> bool:
    """Point a ``clrScheme`` slot (dk1/lt1/accent1/…) at an explicit srgbClr.

    Replaces whatever single color child the slot holds — ``srgbClr`` OR
    ``sysClr`` — keeping the slot element and its siblings intact. Returns True
    iff the slot existed."""
    slot_el = theme.find(f".//{qn('a:clrScheme')}/{qn('a:' + slot)}")
    if slot_el is None:
        return False
    for child in list(slot_el):
        if child.tag in _COLOR_CHILDREN:
            slot_el.remove(child)
    etree.SubElement(slot_el, qn("a:srgbClr")).set("val", hexval.upper())
    return True


def get_scheme_color(theme: etree._Element, slot: str) -> str | None:
    """Effective hex of a ``clrScheme`` slot: ``srgbClr/@val`` or, for a system
    color, ``sysClr/@lastClr`` (the resolved value PowerPoint last wrote).
    None if the slot or a readable color is absent."""
    slot_el = theme.find(f".//{qn('a:clrScheme')}/{qn('a:' + slot)}")
    if slot_el is None:
        return None
    for child in slot_el:
        if child.tag == qn("a:srgbClr") and child.get("val"):
            return child.get("val").upper()
        if child.tag == qn("a:sysClr") and child.get("lastClr"):
            return child.get("lastClr").upper()
    return None


def set_theme_font(theme: etree._Element, kind: str, font: str) -> bool:
    """Set the latin typeface of ``majorFont`` or ``minorFont``. Non-latin
    scripts (``a:ea``/``a:cs``) are left to the caller's font policy."""
    latin = theme.find(f".//{qn('a:' + kind)}/{qn('a:latin')}")
    if latin is None:
        return False
    latin.set("typeface", font)
    return True


# ------------------------------------------------------ generic remappers

def remap_srgb_colors(root: etree._Element,
                      fn: Callable[[str], str | None]) -> int:
    """Apply ``fn(old_hex_upper) -> new_hex`` to every ``a:srgbClr/@val``.

    ``fn`` returning None/falsy or the same value leaves it unchanged. Returns
    the number of values actually changed."""
    changed = 0
    for el in root.iter(qn("a:srgbClr")):
        val = el.get("val")
        if val and _HEX6.fullmatch(val):
            new = fn(val.upper())
            if new and new.upper() != val.upper():
                el.set("val", new.upper())
                changed += 1
    return changed


_RUN_PROPS = frozenset(qn(f"a:{t}") for t in ("rPr", "defRPr", "endParaRPr"))


def remap_typefaces(root: etree._Element,
                    fn: Callable[[str, int | None], str | None]) -> int:
    """Apply ``fn(old_typeface, size|None) -> new`` to every ``@typeface``.

    Size is read from the nearest enclosing run-properties element
    (``rPr``/``defRPr``/``endParaRPr``) ``@sz`` (OOXML hundredths of a point),
    or None when the typeface sits outside a sized run — this replaces the old
    size-aware-block + catch-all two-pass regex with one tree pass. ``fn``
    returning None/falsy or the same value leaves it unchanged."""
    changed = 0
    for el in root.iter():
        face = el.get("typeface")
        if face is None:
            continue
        parent = el.getparent()
        size: int | None = None
        if parent is not None and parent.tag in _RUN_PROPS:
            sz = parent.get("sz")
            if sz and sz.isdigit():
                size = int(sz)
        new = fn(face, size)
        if new and new != face:
            el.set("typeface", new)
            changed += 1
    return changed
