"""Phase 2 / #59 — license-safe reference analysis."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from designmd_pptx.reference import (
    analyze_pptx,
    analyze_tree,
    catalog_filenames,
    family_from_name,
    write_report,
)

NS_DECL = (
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)

THEME_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office">'
    "<a:themeElements><a:clrScheme name=\"Office\">"
    '<a:dk1><a:sysClr val="windowText" lastClr="111111"/></a:dk1>'
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
    '<a:majorFont><a:latin typeface="Inter"/></a:majorFont>'
    '<a:minorFont><a:latin typeface="Inter"/></a:minorFont>'
    "</a:fontScheme><a:fmtScheme name=\"Office\"/></a:themeElements></a:theme>"
)


def _card(text: str, x: int, y: int, w: int = 3_000_000, h: int = 2_500_000,
          sz: int = 3200) -> str:
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="card"/><p:cNvSpPr/><p:nvPr/>'
        f"</p:nvSpPr><p:spPr>"
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        f'<a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="4472C4"/></a:solidFill>'
        f"</p:spPr><p:txBody><a:bodyPr/><a:p><a:r>"
        f'<a:rPr sz="{sz}"><a:latin typeface="Inter"/></a:rPr>'
        f"<a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp>"
    )


def _slide(shapes: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<p:sld {NS_DECL}><p:cSld><p:spTree>{shapes}</p:spTree></p:cSld></p:sld>"
    )


def make_pptx(path: Path, slides: list[str]) -> Path:
    n = len(slides)
    sld_ids = "".join(
        f'<p:sldId id="{256 + i}" r:id="rId{i + 1}"/>' for i in range(n)
    )
    pres = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<p:presentation {NS_DECL}>"
        f'<p:sldSz cx="12192000" cy="6858000"/>'
        f"<p:sldIdLst>{sld_ids}</p:sldIdLst></p:presentation>"
    )
    rel_ns = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    pres_rels = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<Relationships {rel_ns}>"
        + "".join(
            f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/'
            f'officeDocument/2006/relationships/slide" Target="slides/slide{i + 1}.xml"/>'
            for i in range(n)
        )
        + "</Relationships>"
    )
    root_rels = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<Relationships {rel_ns}>"
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
    return path


class FamilyHints(unittest.TestCase):
    def test_family_from_name(self) -> None:
        self.assertEqual(family_from_name("KPI Dashboard.pptx"), "kpi_dashboard")
        self.assertEqual(family_from_name("Product Roadmap.pptx"), "timeline_roadmap")
        self.assertEqual(family_from_name("Funnel-Infographic-01.pptx"), "process_flow")
        self.assertEqual(family_from_name("Fishbone Analysis.pptx"), "process_flow")
        self.assertEqual(family_from_name("Iceberg Model.pptx"), "hierarchy")
        self.assertEqual(family_from_name("Business Model Canvas 1.pptx"), "strategy_canvas")
        self.assertEqual(family_from_name("Random Deck.pptx"), "other")


class ReferenceAnalyze(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cards = "".join(
            _card(f"Metric {i}", 400_000 + i * 3_600_000, 1_200_000)
            for i in range(3)
        )
        cls.pptx = make_pptx(
            root / "KPI Sample Deck.pptx",
            [_slide(cards)],
        )
        (root / "Agenda 1.pptx").write_bytes(cls.pptx.read_bytes())
        cls.root = root

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_analyze_redacts_text_by_default(self) -> None:
        rep = analyze_pptx(self.pptx)
        self.assertFalse(rep["text_included"])
        self.assertEqual(rep["source"]["family_hint"], "kpi_dashboard")
        self.assertEqual(rep["theme"]["fonts"]["major"], "Inter")
        self.assertEqual(rep["theme"]["colors"]["accent1"], "4472C4")
        self.assertEqual(rep["package"]["slide_count"], 1)
        self.assertTrue(rep["slides"][0]["text_samples_redacted"])
        self.assertNotIn("text_samples", rep["slides"][0])
        # SECRET text must not appear anywhere in the redacted report
        blob = json.dumps(rep)
        self.assertNotIn("Metric 0", blob)
        self.assertIn("card_row", " ".join(rep["slides"][0]["layout_hints"]))

    def test_analyze_include_text_opt_in(self) -> None:
        rep = analyze_pptx(self.pptx, include_text=True)
        self.assertTrue(rep["text_included"])
        self.assertIn("Metric 0", rep["slides"][0].get("text_samples", []))

    def test_catalog_filenames(self) -> None:
        cat = catalog_filenames(self.root)
        self.assertEqual(cat["total"], 2)
        self.assertIn("kpi_dashboard", cat["families"])
        self.assertIn("narrative_chrome", cat["families"])

    def test_analyze_tree_and_write(self) -> None:
        idx = analyze_tree(self.root, max_slides=4)
        self.assertEqual(idx["deck_count"], 2)
        out = Path(self.tmp.name) / "report.json"
        write_report(idx, out)
        loaded = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(loaded["deck_count"], 2)
        # basename only — no absolute paths
        for d in loaded["decks"]:
            self.assertNotIn("/", d["filename"])
            self.assertNotIn("\\", d["filename"])

    def test_cli_reference(self) -> None:
        from designmd_pptx.__main__ import main

        out = Path(self.tmp.name) / "cli-out"
        rc = main(["reference", str(self.pptx), "-o", str(out)])
        self.assertEqual(rc, 0)
        files = list(out.glob("*.json"))
        self.assertEqual(len(files), 1)
        data = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(data["source"]["filename"], "KPI Sample Deck.pptx")


if __name__ == "__main__":
    unittest.main()
