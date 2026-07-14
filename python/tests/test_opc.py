"""OPC layer suite (issue #16) — namespace-aware OOXML editing.

These are the properties regex-on-XML could not guarantee: matching by
namespace URI regardless of the document's prefix, correctly replacing a
scheme slot that holds a sysClr (not just srgbClr), preserving unknown
elements/comments across a round-trip, size-aware typeface remapping, XML
declaration fidelity, and entity-expansion safety on untrusted input."""

from __future__ import annotations

import unittest

from lxml import etree

from designmd_pptx import opc

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"

# A theme that binds the DrawingML namespace to a NON-standard prefix ("d"),
# holds a sysClr in dk1, and carries a foreign element + comment to preserve.
THEME_ALT_PREFIX = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<d:theme xmlns:d="{A}" xmlns:x="urn:test" name="Office">'
    "<d:themeElements><d:clrScheme name=\"Office\">"
    '<d:dk1><d:sysClr val="windowText" lastClr="000000"/></d:dk1>'
    '<d:accent1><d:srgbClr val="4472C4"/></d:accent1>'
    "</d:clrScheme>"
    "<d:fontScheme name=\"Office\">"
    '<d:majorFont><d:latin typeface="OldHead"/><d:ea typeface="OldEA"/></d:majorFont>'
    '<d:minorFont><d:latin typeface="OldBody"/></d:minorFont>'
    "</d:fontScheme>"
    '<x:custom keep="yes"/><!-- keep this comment -->'
    "</d:themeElements></d:theme>"
).encode("utf-8")


class NamespaceAware(unittest.TestCase):
    def test_slot_matched_by_uri_not_prefix(self) -> None:
        theme = opc.parse(THEME_ALT_PREFIX)
        # dk1 is under the "d" prefix here; a prefix-literal regex for "a:dk1"
        # would miss it entirely.
        self.assertTrue(opc.set_scheme_color(theme, "dk1", "112233"))
        self.assertTrue(opc.set_scheme_color(theme, "accent1", "ABCDEF"))
        self.assertFalse(opc.set_scheme_color(theme, "accent6", "000000"))  # absent

    def test_syscolor_slot_is_replaced_with_srgb(self) -> None:
        theme = opc.parse(THEME_ALT_PREFIX)
        opc.set_scheme_color(theme, "dk1", "112233")
        dk1 = theme.find(f".//{{{A}}}clrScheme/{{{A}}}dk1")
        kids = list(dk1)
        self.assertEqual(len(kids), 1)                     # sysClr swapped out
        self.assertEqual(kids[0].tag, f"{{{A}}}srgbClr")
        self.assertEqual(kids[0].get("val"), "112233")

    def test_theme_fonts_set_latin_only(self) -> None:
        theme = opc.parse(THEME_ALT_PREFIX)
        self.assertTrue(opc.set_theme_font(theme, "majorFont", "Inter"))
        self.assertTrue(opc.set_theme_font(theme, "minorFont", "Inter Text"))
        major_latin = theme.find(f".//{{{A}}}majorFont/{{{A}}}latin")
        major_ea = theme.find(f".//{{{A}}}majorFont/{{{A}}}ea")
        self.assertEqual(major_latin.get("typeface"), "Inter")
        self.assertEqual(major_ea.get("typeface"), "OldEA")  # non-latin untouched

    def test_unknown_elements_and_comments_survive(self) -> None:
        theme = opc.parse(THEME_ALT_PREFIX)
        opc.set_scheme_color(theme, "dk1", "112233")
        out = opc.serialize(theme)
        self.assertIn(b"<x:custom", out)
        self.assertIn(b"keep=\"yes\"", out)
        self.assertIn(b"<!-- keep this comment -->", out)


class Remappers(unittest.TestCase):
    def test_remap_srgb_only_touches_srgb(self) -> None:
        xml = (
            f'<p:sld xmlns:a="{A}" xmlns:p="{P}"><p:cSld>'
            '<a:srgbClr val="FF0000"/><a:sysClr val="window" lastClr="FFFFFF"/>'
            '<a:schemeClr val="accent1"/><a:srgbClr val="00ff00"/>'
            "</p:cSld></p:sld>"
        ).encode("utf-8")
        root = opc.parse(xml)
        n = opc.remap_srgb_colors(root, lambda old: "000000" if old == "FF0000" else old)
        self.assertEqual(n, 1)
        vals = [e.get("val") for e in root.iter(f"{{{A}}}srgbClr")]
        self.assertEqual(vals, ["000000", "00ff00"])        # only the match changed
        # sysClr/schemeClr are untouched
        self.assertEqual(root.find(f".//{{{A}}}sysClr").get("lastClr"), "FFFFFF")

    def test_remap_typefaces_is_size_aware(self) -> None:
        xml = (
            f'<p:sld xmlns:a="{A}" xmlns:p="{P}"><p:cSld>'
            '<a:rPr sz="4000"><a:latin typeface="OldHeadFont"/></a:rPr>'
            '<a:rPr sz="1800"><a:latin typeface="OldBodyFont"/></a:rPr>'
            '<a:defRPr><a:latin typeface="+mn-lt"/></a:defRPr>'
            '<a:latin typeface="FiraCode"/>'          # outside a run: size None
            "</p:cSld></p:sld>"
        ).encode("utf-8")
        root = opc.parse(xml)
        heading_sz = 2800

        def fn(old, sz):
            if old.startswith("+"):
                return old
            if "code" in old.lower() or "mono" in old.lower():
                return "Mono"
            return "Head" if (sz or 0) >= heading_sz else "Body"

        opc.remap_typefaces(root, fn)
        faces = [e.get("typeface") for e in root.iter() if e.get("typeface")]
        self.assertEqual(faces, ["Head", "Body", "+mn-lt", "Mono"])


class Serialization(unittest.TestCase):
    def test_declaration_preserved(self) -> None:
        data = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><r/>'
        self.assertEqual(opc.xml_declaration(data),
                         b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
        out = opc.serialize(opc.parse(data), declaration=opc.xml_declaration(data))
        self.assertTrue(out.startswith(
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'))

    def test_missing_declaration_falls_back_to_default(self) -> None:
        self.assertEqual(opc.xml_declaration(b"<r/>"), opc._DEFAULT_DECL)


class Security(unittest.TestCase):
    def test_internal_entities_are_not_expanded(self) -> None:
        # If entity resolution were on, &a; would expand to EXPANDED — the seed
        # of a billion-laughs amplification. The safe parser must not expand it.
        data = (b'<?xml version="1.0"?>'
                b'<!DOCTYPE r [<!ENTITY a "EXPANDED">]><r>&a;</r>')
        root = opc.parse(data)
        self.assertNotIn("EXPANDED", "".join(root.itertext()))


class BomFidelity(unittest.TestCase):
    """Legacy OfficeCLI writes BOM-prefixed parts (e.g. [Content_Types].xml);
    the round-trip must keep the BOM where it exists and never invent one."""

    def test_bom_declaration_preserved(self) -> None:
        data = (b"\xef\xbb\xbf<?xml version=\"1.0\" encoding=\"UTF-8\" "
                b"standalone=\"yes\"?><r/>")
        decl = opc.xml_declaration(data)
        self.assertTrue(decl.startswith(b"\xef\xbb\xbf"))
        out = opc.serialize(opc.parse(data), declaration=decl)
        self.assertTrue(out.startswith(b"\xef\xbb\xbf<?xml"))

    def test_bom_not_invented_when_absent(self) -> None:
        self.assertFalse(
            opc.xml_declaration(b'<?xml version="1.0"?><r/>').startswith(b"\xef\xbb\xbf"))


class PotxContentTypes(unittest.TestCase):
    """master._potx_content_types (issue #16) must flip the presentation content
    type whether the writer declared it as an Override OR a Default — the real
    legacy deck uses a Default, which the synthetic test fixtures did not."""

    CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

    def _types(self, body: str) -> bytes:
        return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<Types xmlns="{self.CT_NS}">{body}</Types>').encode("utf-8")

    def test_swaps_presentation_ct_declared_as_default(self) -> None:
        from designmd_pptx.master import (_PRESENTATION_CT, _TEMPLATE_CT,
                                          _potx_content_types)
        data = self._types(
            f'<Default Extension="xml" ContentType="{_PRESENTATION_CT}"/>')
        out = _potx_content_types(data, empty=False, dropped_media=set())
        self.assertIn(_TEMPLATE_CT.encode(), out)
        self.assertNotIn(_PRESENTATION_CT.encode(), out)

    def test_swaps_presentation_ct_declared_as_override(self) -> None:
        from designmd_pptx.master import (_PRESENTATION_CT, _TEMPLATE_CT,
                                          _potx_content_types)
        data = self._types(
            f'<Override PartName="/ppt/presentation.xml" '
            f'ContentType="{_PRESENTATION_CT}"/>')
        out = _potx_content_types(data, empty=False, dropped_media=set())
        self.assertIn(_TEMPLATE_CT.encode(), out)

    def test_non_presentation_package_raises(self) -> None:
        from designmd_pptx.master import _potx_content_types
        data = self._types('<Default Extension="xml" ContentType="application/xml"/>')
        with self.assertRaises(ValueError):
            _potx_content_types(data, empty=False, dropped_media=set())

    def test_empty_drops_slide_overrides(self) -> None:
        from designmd_pptx.master import _PRESENTATION_CT, _potx_content_types
        data = self._types(
            f'<Default Extension="xml" ContentType="{_PRESENTATION_CT}"/>'
            '<Override PartName="/ppt/slides/slide1.xml" ContentType="app/slide"/>')
        out = _potx_content_types(data, empty=True, dropped_media=set())
        self.assertNotIn(b"/ppt/slides/slide1.xml", out)


if __name__ == "__main__":
    unittest.main()
