"""v1.6 suite — constraint-based layout engine, migrated recipes,
template polish (media GC + slot-mapped branded layouts)."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.layout import (
    CANVAS_H, CANVAS_W, COMPACT, HStack, LayoutOverflow, Text, VStack,
    floored_pt, solve, solve_adaptive,
)
from designmd_pptx.master import brand_master, export_potx
from designmd_pptx.recipes import (
    recipe_bullets, recipe_comparison_2col, recipe_feature_cards,
    recipe_image_text_2col,
)

try:
    from test_v13 import MASTER_XML, _content_types
    from test_v12 import NS_DECL, THEME_XML, _slide, _sp
except ImportError:  # pragma: no cover
    from python.tests.test_v13 import MASTER_XML, _content_types
    from python.tests.test_v12 import NS_DECL, THEME_XML, _slide, _sp

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class LayoutEngineV16(unittest.TestCase):
    def test_vstack_title_plus_weighted_body(self) -> None:
        # weight on Text is stripped (ui-kit): body is content-height, free
        # stage stays below — not a hollow text frame to the bottom margin.
        tree = VStack(pad=(1.2, 1.27, 1.0, 1.27), gap=0.5, children=[
            Text("Title", pt=36, name="T"),
            Text("Body", pt=18, name="B", weight=1),
        ])
        placed = solve(tree, 0, 0, CANVAS_W, CANVAS_H)
        by = {p.name: p for p in placed}
        self.assertLess(by["T"].h, 3.0)
        self.assertLess(by["B"].h, 3.0, "body must not fill the stage")
        self.assertLess(by["B"].y + by["B"].h, CANVAS_H - 2.0)
        self.assertAlmostEqual(by["T"].w, CANVAS_W - 2 * 1.27, delta=0.01)

    def test_hstack_equal_columns(self) -> None:
        tree = HStack(gap=0.76, children=[
            Text("a", pt=18, name="C1", weight=1),
            Text("b", pt=18, name="C2", weight=1),
            Text("c", pt=18, name="C3", weight=1),
        ])
        placed = solve(tree, 0, 0, 30.0, 10.0)
        widths = [round(p.w, 2) for p in placed]
        self.assertEqual(len(set(widths)), 1)
        self.assertAlmostEqual(sum(widths) + 2 * 0.76, 30.0, delta=0.05)

    def test_overflow_raises(self) -> None:
        with self.assertRaises(LayoutOverflow):
            solve(VStack(children=[Text("x" * 3000, pt=18, name="Huge")]),
                  0, 0, CANVAS_W, 5.0)

    def test_weighted_text_overflow_detected(self) -> None:
        tree = VStack(children=[
            Text("filler", pt=18, name="A"),
            Text("y" * 4000, pt=18, name="B", weight=1),
        ])
        with self.assertRaises(LayoutOverflow):
            solve(tree, 0, 0, CANVAS_W, CANVAS_H)

    def test_adaptive_falls_back_to_compact(self) -> None:
        def build(d):
            return VStack(pad=(1.0 * d.gap, 1.27, 0.8 * d.gap, 1.27),
                          gap=0.9 * d.gap, children=[
                Text("Title", pt=36, name="T"),
                *[Text("항목 설명이 길게 들어가는 경우 " * 4,
                       pt=floored_pt(20, d), name=f"B{i}") for i in range(6)],
            ])
        placed, density = solve_adaptive(build, 0, 0, CANVAS_W, CANVAS_H)
        self.assertEqual(density.name, "compact")
        self.assertTrue(placed)

    def test_floored_pt_never_below_floor(self) -> None:
        self.assertEqual(floored_pt(18, COMPACT), 18)
        self.assertEqual(floored_pt(20, COMPACT), 18)
        self.assertEqual(floored_pt(24, COMPACT), 22)


class MigratedRecipesV16(unittest.TestCase):
    def setUp(self) -> None:
        self.tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def _shapes(self, ops: list[dict]) -> list[dict]:
        return [o["props"] for o in ops if o.get("type") in ("shape", "picture")]

    def _assert_within_canvas(self, ops: list[dict]) -> None:
        for p in self._shapes(ops):
            bottom = float(p["y"].rstrip("cm")) + float(p["height"].rstrip("cm"))
            self.assertLessEqual(bottom, CANVAS_H + 0.01, p.get("name"))

    def test_bullets_geometry_and_names(self) -> None:
        ops = recipe_bullets(self.tokens, {
            "title": "분기 논의 사항",
            "bullets": ["첫 번째 안건에 대한 상세 설명", "두 번째 안건", "세 번째",
                        "네 번째 안건 상세", "다섯 번째"],
        })
        names = [p.get("name") for p in self._shapes(ops)]
        self.assertIn("BulletTitle", names)
        self.assertIn("BulletBody", names)
        self._assert_within_canvas(ops)

    def test_feature_cards_solved_columns(self) -> None:
        ops = recipe_feature_cards(self.tokens, {
            "title": "Capabilities",
            "cards": [{"title": f"Card {i}", "body": "Body " * 8} for i in range(4)],
        })
        shapes = self._shapes(ops)
        bgs = [p for p in shapes if p.get("name", "").endswith("Bg")]
        self.assertEqual(len(bgs), 4)
        widths = {p["width"] for p in bgs}
        self.assertEqual(len(widths), 1)  # equal columns
        self.assertIn("Card4Body", [p.get("name") for p in shapes])
        self._assert_within_canvas(ops)

    def test_comparison_and_image_text_names_preserved(self) -> None:
        ops = recipe_comparison_2col(self.tokens, {
            "title": "Compare",
            "left": {"title": "A", "body": "a" * 60},
            "right": {"title": "B", "body": "b" * 60},
        })
        names = [p.get("name") for p in self._shapes(ops)]
        for expected in ("CmpTitle", "Cmp1Bg", "Cmp1Body", "Cmp2Body"):
            self.assertIn(expected, names)
        ops2 = recipe_image_text_2col(self.tokens, {
            "title": "Side", "body": "Explain.", "image_side": "right",
        })
        names2 = [p.get("name") for p in self._shapes(ops2)]
        self.assertIn("It2Title", names2)
        self.assertIn("It2Placeholder", names2)
        # image on the right → placeholder x greater than text x
        ph = next(p for p in self._shapes(ops2) if p["name"] == "It2Placeholder")
        ttl = next(p for p in self._shapes(ops2) if p["name"] == "It2Title")
        self.assertGreater(float(ph["x"].rstrip("cm")), float(ttl["x"].rstrip("cm")))

    def test_impossible_content_raises(self) -> None:
        with self.assertRaises(ValueError):
            recipe_image_text_2col(self.tokens, {"title": "X", "body": "z" * 6000})


def make_media_pptx(path: Path) -> Path:
    """Package with two media parts: one referenced by a slide (GC target),
    one referenced by the slide master (must survive --empty-potx)."""
    rel_ns = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    rel_base = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    layout_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<p:sldLayout {NS_DECL}><p:cSld><p:spTree><p:nvGrpSpPr/><p:grpSpPr/>"
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        '<p:spPr><a:solidFill><a:srgbClr val="4472C4"/></a:solidFill>'
        '<a:ln><a:solidFill><a:srgbClr val="123456"/></a:solidFill></a:ln></p:spPr>'
        "</p:sp></p:spTree></p:cSld></p:sldLayout>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types(1).replace(
            "</Types>",
            '<Default Extension="png" ContentType="image/png"/>'
            f'<Override PartName="/ppt/slideLayouts/slideLayout1.xml" '
            f'ContentType="application/vnd.openxmlformats-officedocument'
            f'.presentationml.slideLayout+xml"/></Types>',
        ))
        zf.writestr("_rels/.rels",
                    f'<?xml version="1.0"?><Relationships {rel_ns}>'
                    f'<Relationship Id="rId1" Type="{rel_base}/officeDocument" '
                    'Target="ppt/presentation.xml"/></Relationships>')
        zf.writestr("ppt/presentation.xml",
                    '<?xml version="1.0"?>'
                    f'<p:presentation {NS_DECL}>'
                    '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/>'
                    "</p:sldMasterIdLst>"
                    '<p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>'
                    "</p:presentation>")
        zf.writestr("ppt/_rels/presentation.xml.rels",
                    f'<?xml version="1.0"?><Relationships {rel_ns}>'
                    f'<Relationship Id="rId1" Type="{rel_base}/slideMaster" '
                    'Target="slideMasters/slideMaster1.xml"/>'
                    f'<Relationship Id="rId2" Type="{rel_base}/slide" '
                    'Target="slides/slide1.xml"/></Relationships>')
        zf.writestr("ppt/theme/theme1.xml", THEME_XML)
        zf.writestr("ppt/slideMasters/slideMaster1.xml", MASTER_XML)
        zf.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels",
                    f'<?xml version="1.0"?><Relationships {rel_ns}>'
                    f'<Relationship Id="rId9" Type="{rel_base}/image" '
                    'Target="../media/logo.png"/></Relationships>')
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", layout_xml)
        zf.writestr("ppt/slides/slide1.xml", _slide(_sp(["Hello"], ph="title")))
        zf.writestr("ppt/slides/_rels/slide1.xml.rels",
                    f'<?xml version="1.0"?><Relationships {rel_ns}>'
                    f'<Relationship Id="rId2" Type="{rel_base}/image" '
                    'Target="../media/photo.png"/></Relationships>')
        zf.writestr("ppt/media/logo.png", b"\x89PNGlogo")
        zf.writestr("ppt/media/photo.png", b"\x89PNGphoto")
    return path


class TemplatePolishV16(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pptx = make_media_pptx(self.root / "deck.pptx")
        self.tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_empty_potx_prunes_slide_only_media(self) -> None:
        potx = self.root / "brand.potx"
        stats: dict = {}
        export_potx(self.pptx, potx, empty=True, stats=stats)
        with zipfile.ZipFile(potx) as zf:
            names = zf.namelist()
        self.assertIn("ppt/media/logo.png", names)       # master-referenced
        self.assertNotIn("ppt/media/photo.png", names)   # slide-only → pruned
        self.assertEqual(stats["pruned_media"], ["ppt/media/photo.png"])

    def test_non_empty_potx_keeps_media(self) -> None:
        potx = self.root / "full.potx"
        export_potx(self.pptx, potx, empty=False)
        with zipfile.ZipFile(potx) as zf:
            self.assertIn("ppt/media/photo.png", zf.namelist())

    def test_branded_layouts_slot_mapping(self) -> None:
        out = self.root / "branded.pptx"
        report = brand_master(self.pptx, self.tokens, out=out, layouts=True)
        with zipfile.ZipFile(out) as zf:
            layout = zf.read("ppt/slideLayouts/slideLayout1.xml").decode("utf-8")
        accent = self.tokens["colors"]["accent"]
        # 4472C4 was the OLD theme accent1 → becomes the new accent
        self.assertIn(f'srgbClr val="{accent}"', layout)
        self.assertNotIn('srgbClr val="4472C4"', layout)
        # 123456 matches no old slot → untouched, reported as skipped
        self.assertIn('srgbClr val="123456"', layout)
        self.assertIn("4472C4", report["layout_colors"])
        self.assertIn("123456", report["layout_colors_skipped"])

    def test_layouts_off_by_default(self) -> None:
        out = self.root / "plain.pptx"
        brand_master(self.pptx, self.tokens, out=out)
        with zipfile.ZipFile(out) as zf:
            layout = zf.read("ppt/slideLayouts/slideLayout1.xml").decode("utf-8")
        self.assertIn('srgbClr val="4472C4"', layout)  # untouched without flag


class CliV16(unittest.TestCase):
    def test_master_layouts_flag(self) -> None:
        from designmd_pptx.__main__ import build_parser

        args = build_parser().parse_args(
            ["master", "a.pptx", "default", "--layouts", "--potx", "b.potx"]
        )
        self.assertTrue(args.layouts)


if __name__ == "__main__":
    unittest.main()
