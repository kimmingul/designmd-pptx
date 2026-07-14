"""v1.2 suite — extract (pptx → deck-spec draft) and restyle (in-place brand)."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.deck import generate_deck
from designmd_pptx.extract import extract_pptx
from designmd_pptx.restyle import restyle_pptx

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

NS_DECL = (
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)

THEME_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office">'
    "<a:themeElements><a:clrScheme name=\"Office\">"
    '<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
    '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
    '<a:dk2><a:srgbClr val="44546A"/></a:dk2>'
    '<a:lt2><a:srgbClr val="E7E6E6"/></a:lt2>'
    '<a:accent1><a:srgbClr val="4472C4"/></a:accent1>'
    '<a:accent2><a:srgbClr val="ED7D31"/></a:accent2>'
    '<a:accent3><a:srgbClr val="A5A5A5"/></a:accent3>'
    '<a:accent4><a:srgbClr val="FFC000"/></a:accent4>'
    '<a:accent5><a:srgbClr val="5B9BD5"/></a:accent5>'
    '<a:accent6><a:srgbClr val="70AD47"/></a:accent6>'
    '<a:hlink><a:srgbClr val="0563C1"/></a:hlink>'
    '<a:folHlink><a:srgbClr val="954F72"/></a:folHlink>'
    "</a:clrScheme><a:fontScheme name=\"Office\">"
    '<a:majorFont><a:latin typeface="Calibri Light"/></a:majorFont>'
    '<a:minorFont><a:latin typeface="Calibri"/></a:minorFont>'
    "</a:fontScheme><a:fmtScheme name=\"Office\"/></a:themeElements></a:theme>"
)

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c626001000000ffff03000006000557bfabd4000000"
    "0049454e44ae426082"
)


def _sp(paras: list[str], ph: str | None = None, extra_run_pr: str = "",
        fill: str = "") -> str:
    ph_xml = f'<p:ph type="{ph}"/>' if ph else ""
    runs = "".join(
        f"<a:p><a:r>{extra_run_pr}<a:t>{t}</a:t></a:r></a:p>" for t in paras
    )
    return (
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="shape"/><p:cNvSpPr/>'
        f"<p:nvPr>{ph_xml}</p:nvPr></p:nvSpPr><p:spPr>{fill}</p:spPr>"
        f"<p:txBody><a:bodyPr/>{runs}</p:txBody></p:sp>"
    )


def _table(rows: list[list[str]]) -> str:
    trs = ""
    for row in rows:
        tcs = "".join(
            f"<a:tc><a:txBody><a:bodyPr/><a:p><a:r><a:t>{c}</a:t></a:r></a:p>"
            "</a:txBody></a:tc>"
            for c in row
        )
        trs += f'<a:tr h="370840">{tcs}</a:tr>'
    return (
        '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="5" name="tbl"/>'
        "<p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>"
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
        f"<a:tbl>{trs}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>"
    )


def _pic(rid: str = "rId2", alt: str = "diagram") -> str:
    return (
        f'<p:pic><p:nvPicPr><p:cNvPr id="7" name="pic" descr="{alt}"/>'
        "<p:cNvPicPr/><p:nvPr/></p:nvPicPr>"
        f'<p:blipFill><a:blip r:embed="{rid}"/></p:blipFill><p:spPr/></p:pic>'
    )


def _slide(shapes: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<p:sld {NS_DECL}><p:cSld><p:spTree>{shapes}</p:spTree></p:cSld></p:sld>"
    )


def make_pptx(path: Path, slides: list[str],
              slide_rels: dict[int, str] | None = None) -> Path:
    """Write a minimal .pptx: presentation + rels + theme + slides (+ media)."""
    n = len(slides)
    sld_ids = "".join(
        f'<p:sldId id="{256 + i}" r:id="rId{i + 1}"/>' for i in range(n)
    )
    pres = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<p:presentation {NS_DECL}><p:sldIdLst>{sld_ids}</p:sldIdLst></p:presentation>"
    )
    rel_ns = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    pres_rels = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {rel_ns}>'
        + "".join(
            f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/'
            f'officeDocument/2006/relationships/slide" Target="slides/slide{i + 1}.xml"/>'
            for i in range(n)
        )
        + "</Relationships>"
    )
    root_rels = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {rel_ns}>'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("ppt/presentation.xml", pres)
        zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        zf.writestr("ppt/theme/theme1.xml", THEME_XML)
        for i, xml in enumerate(slides):
            zf.writestr(f"ppt/slides/slide{i + 1}.xml", xml)
            rels = (slide_rels or {}).get(i + 1)
            if rels:
                zf.writestr(f"ppt/slides/_rels/slide{i + 1}.xml.rels", rels)
        if slide_rels:
            zf.writestr("ppt/media/image1.png", PNG_BYTES)
    return path


def _pic_rels() -> str:
    rel_ns = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {rel_ns}>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/image" Target="../media/image1.png"/>'
        "</Relationships>"
    )


class ExtractV12(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        slides = [
            _slide(_sp(["Linear Review"], ph="ctrTitle") + _sp(["Q3 2026"], ph="subTitle")),
            _slide(_sp(["Metrics"], ph="title") + _table([["KPI", "Value"], ["NPS", "62"]])),
            _slide(
                _sp(["Agenda"], ph="title")
                + _sp([
                    "First topic covers the roadmap in detail",
                    "Second topic reviews the incident postmortem",
                    "Third topic walks through hiring plans",
                ])
            ),
            _slide(_sp(["Part Two"], ph="title")),
            _slide(_sp(['"Ship fast, learn faster"', "— CEO"])),
            _slide(_sp(["Numbers"], ph="title") + _sp(["62% retention", "3x growth"])),
            _slide(
                _sp(["Architecture"], ph="title")
                + _pic()
                + _sp(["The gateway routes traffic to regional clusters."])
            ),
            _slide(_sp(["Next"], ph="title") + _sp(["Do the follow-up", "Contact us"])),
        ]
        cls.pptx = make_pptx(root / "deck.pptx", slides, slide_rels={7: _pic_rels()})
        cls.out = root / "extracted"
        cls.report = extract_pptx(cls.pptx, cls.out)
        cls.spec = json.loads((cls.out / "content.deck.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_recipe_mapping(self) -> None:
        recipes = [s["recipe"] for s in self.spec["slides"]]
        self.assertEqual(
            recipes,
            ["cover", "table", "bullets", "section_divider",
             "quote", "kpi_row", "image_text_2col", "close"],
        )

    def test_cover_and_table_content(self) -> None:
        cover = self.spec["slides"][0]["content"]
        self.assertEqual(cover["title"], "Linear Review")
        self.assertEqual(cover["subtitle"], "Q3 2026")
        table = self.spec["slides"][1]["content"]
        self.assertEqual(table["headers"], ["KPI", "Value"])
        self.assertEqual(table["rows"], [["NPS", "62"]])

    def test_kpi_quote_close(self) -> None:
        kpis = self.spec["slides"][5]["content"]["kpis"]
        self.assertEqual([k["value"] for k in kpis], ["62%", "3x"])
        quote = self.spec["slides"][4]["content"]
        self.assertEqual(quote["attribution"], "CEO")
        close = self.spec["slides"][7]["content"]
        self.assertEqual(close["cta"], "Contact us")

    def test_media_exported(self) -> None:
        self.assertTrue((self.out / "assets" / "image1.png").exists())
        img = self.spec["slides"][6]["content"]
        self.assertEqual(img["src"], "assets/image1.png")
        self.assertEqual(img["alt"], "diagram")

    def test_report_shape(self) -> None:
        self.assertEqual(len(self.report["slides"]), 8)
        for s in self.report["slides"]:
            self.assertIn("recipe", s)
            self.assertIn("confidence", s)
        self.assertTrue((self.out / "extract.report.json").exists())

    def test_spec_feeds_deck_generation(self) -> None:
        tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")
        ops, deck, _warnings = generate_deck(tokens, self.spec, strict=False)
        self.assertEqual(len(deck["slides"]), 8)
        self.assertGreater(len(ops), 8)


class RestyleV12(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        red_fill = '<a:solidFill><a:srgbClr val="FF0000"/></a:solidFill>'
        comic = '<a:rPr lang="en-US"><a:latin typeface="Comic Sans MS"/></a:rPr>'
        slides = [
            _slide(_sp(["Old Deck"], ph="title")),
            _slide(_sp(["Body text"], extra_run_pr=comic, fill=red_fill)),
        ]
        self.pptx = make_pptx(self.root / "old.pptx", slides)
        self.tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _read(self, pptx: Path, part: str) -> str:
        with zipfile.ZipFile(pptx) as zf:
            return zf.read(part).decode("utf-8")

    def test_theme_scheme_and_fonts(self) -> None:
        out = self.root / "restyled.pptx"
        report = restyle_pptx(self.pptx, self.tokens, out=out)
        theme = self._read(out, "ppt/theme/theme1.xml")
        colors = self.tokens["colors"]
        self.assertIn(f'<a:dk1><a:srgbClr val="{colors["text"]}"/></a:dk1>', theme)
        self.assertIn(f'<a:lt1><a:srgbClr val="{colors["background"]}"/></a:lt1>', theme)
        self.assertIn(f'<a:accent1><a:srgbClr val="{colors["accent"]}"/></a:accent1>', theme)
        self.assertIn(f'typeface="{self.tokens["type"]["heading_font"]}"', theme)
        self.assertGreaterEqual(len(report["theme_scheme"]), 10)

    def test_explicit_colors_and_fonts(self) -> None:
        out = self.root / "restyled.pptx"
        restyle_pptx(self.pptx, self.tokens, out=out)
        slide2 = self._read(out, "ppt/slides/slide2.xml")
        self.assertNotIn("FF0000", slide2)
        self.assertNotIn("Comic Sans MS", slide2)
        self.assertIn(f'typeface="{self.tokens["type"]["body_font"]}"', slide2)

    def test_color_map_pin(self) -> None:
        out = self.root / "pinned.pptx"
        restyle_pptx(self.pptx, self.tokens, out=out, color_map={"FF0000": "112233"})
        slide2 = self._read(out, "ppt/slides/slide2.xml")
        self.assertIn('srgbClr val="112233"', slide2)

    def test_staging_safety(self) -> None:
        before = self.pptx.read_bytes()
        with self.assertRaises(FileExistsError):
            restyle_pptx(self.pptx, self.tokens)  # in-place needs force
        self.assertEqual(self.pptx.read_bytes(), before)
        out = self.root / "restyled.pptx"
        out.write_bytes(b"sentinel")
        with self.assertRaises(FileExistsError):
            restyle_pptx(self.pptx, self.tokens, out=out)
        self.assertEqual(out.read_bytes(), b"sentinel")
        restyle_pptx(self.pptx, self.tokens, out=out, force=True)
        self.assertNotEqual(out.read_bytes(), b"sentinel")

    def test_in_place_with_force(self) -> None:
        report = restyle_pptx(self.pptx, self.tokens, force=True)
        # dest echoes the resolved path (restyle resolve()s src); compare
        # resolved-to-resolved so CI temp dirs with symlinks (/var ->
        # /private/var) or 8.3 short names (RUNNER~1) don't spuriously differ.
        self.assertEqual(report["dest"], str(self.pptx.resolve()))
        theme = self._read(self.pptx, "ppt/theme/theme1.xml")
        self.assertIn(self.tokens["colors"]["accent"], theme)

    def test_report_written(self) -> None:
        out = self.root / "restyled.pptx"
        restyle_pptx(self.pptx, self.tokens, out=out)
        report_path = out.with_suffix(".restyle.report.json")
        self.assertTrue(report_path.exists())
        data = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertIn("theme_scheme", data)


class CliV12(unittest.TestCase):
    def test_extract_cli(self) -> None:
        from designmd_pptx.__main__ import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pptx = make_pptx(
                root / "deck.pptx",
                [_slide(_sp(["Only Title"], ph="ctrTitle"))],
            )
            rc = main(["extract", str(pptx), "-o", str(root / "x")])
            self.assertEqual(rc, 0)
            self.assertTrue((root / "x" / "content.deck.json").exists())

    def test_restyle_cli_requires_force_in_place(self) -> None:
        from designmd_pptx.__main__ import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pptx = make_pptx(root / "deck.pptx", [_slide(_sp(["T"], ph="title"))])
            rc = main(["restyle", str(pptx), str(FIXTURES / "linear.DESIGN.md")])
            self.assertEqual(rc, 1)  # in-place without --force fails
            rc = main([
                "restyle", str(pptx), str(FIXTURES / "linear.DESIGN.md"),
                "-o", str(root / "new.pptx"),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue((root / "new.pptx").exists())


if __name__ == "__main__":
    unittest.main()
