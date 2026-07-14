"""Safer restyle color mapping suite (issue #13): theme-only default, hue-aware
semantic preservation, pins, and the no-write preview."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from designmd_pptx.restyle import restyle_pptx, restyle_preview

try:
    from test_v12 import NS_DECL, make_pptx  # discover puts tests/ on sys.path
except ImportError:  # pragma: no cover - dotted invocation
    from python.tests.test_v12 import NS_DECL, make_pptx

A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _fill(hex6):
    return f'<a:solidFill><a:srgbClr val="{hex6}"/></a:solidFill>'


def _shape(name, hex6):
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="1" name="{name}"/><p:cNvSpPr/>'
            f'<p:nvPr/></p:nvSpPr><p:spPr>{_fill(hex6)}</p:spPr></p:sp>')


def _slide_with(colors):
    shapes = "".join(_shape(f"s{i}", c) for i, c in enumerate(colors))
    return f"<p:sld {NS_DECL}><p:cSld><p:spTree>{shapes}</p:spTree></p:cSld></p:sld>"


# Brand palette with NO red and NO green — only neutrals + a blue accent.
TOKENS = {
    "colors": {"background": "FFFFFF", "text": "111111", "accent": "2244CC",
               "surface": "EEEEEE", "muted": "777777"},
    "type": {"heading_font": "Arial", "body_font": "Arial"},
}


class SemanticColorV13(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # a semantic red, a semantic green, and a neutral grey
        self.pptx = make_pptx(self.root / "in.pptx",
                              [_slide_with(["FF0000", "00AA00", "808080"])])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _slide(self, pptx):
        with zipfile.ZipFile(pptx) as z:
            return z.read("ppt/slides/slide1.xml").decode("utf-8")

    def test_default_is_theme_only(self) -> None:
        out = self.root / "out.pptx"
        report = restyle_pptx(self.pptx, TOKENS, out=out)
        s = self._slide(out)
        # every explicit color is left as-is by default
        for c in ("FF0000", "00AA00", "808080"):
            self.assertIn(c, s)
        self.assertEqual(report["colors"], {})

    def test_map_colors_preserves_semantics_snaps_neutral(self) -> None:
        out = self.root / "out.pptx"
        report = restyle_pptx(self.pptx, TOKENS, out=out, explicit_colors=True)
        s = self._slide(out)
        # saturated off-hue colors preserved (no brand red/green to collapse into)
        self.assertIn("FF0000", s)
        self.assertIn("00AA00", s)
        self.assertIn("FF0000", report["colors_preserved"])
        self.assertIn("00AA00", report["colors_preserved"])
        # the neutral grey IS rebranded to the nearest brand neutral
        self.assertNotIn("808080", s)
        self.assertIn("808080", report["colors"])

    def test_pin_is_honored_even_in_default_mode(self) -> None:
        out = self.root / "out.pptx"
        report = restyle_pptx(self.pptx, TOKENS, out=out,
                              color_map={"FF0000": "2244CC"})
        s = self._slide(out)
        self.assertNotIn("FF0000", s)              # pin applied
        self.assertIn("2244CC", s)
        self.assertIn("00AA00", s)                 # non-pinned still preserved

    def test_preview_writes_nothing_but_reports(self) -> None:
        before = self.pptx.read_bytes()
        report = restyle_preview(self.pptx, TOKENS, explicit_colors=True)
        self.assertTrue(report.get("preview"))
        self.assertIn("808080", report["colors"])          # would snap
        self.assertIn("FF0000", report["colors_preserved"])  # would preserve
        self.assertEqual(self.pptx.read_bytes(), before)   # source untouched
        # no output/report file created
        self.assertFalse((self.root / "in.restyle.report.json").exists())


if __name__ == "__main__":
    unittest.main()
