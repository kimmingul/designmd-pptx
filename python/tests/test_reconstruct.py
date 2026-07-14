"""Phase 5 / #22 — chart & table reconstruction (modern deck-spec mapping)."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from designmd_pptx import reconstruct as R
from designmd_pptx.__main__ import main
from designmd_pptx.extract import _classify, _parse_chart_part
from designmd_pptx.recipes import RECIPE_BUILDERS


class ModernizeType22(unittest.TestCase):
    def test_strips_3d_and_modernizes_pie(self) -> None:
        self.assertEqual(R.modernize_chart_type("pie3DChart"), "doughnut")
        self.assertEqual(R.modernize_chart_type("bar3D"), "bar")
        self.assertEqual(R.modernize_chart_type("waterfall"), "waterfall")
        self.assertEqual(R.modernize_chart_type("colChart"), "column")


class ChartPayload22(unittest.TestCase):
    def test_lossless_series_and_categories(self) -> None:
        chart = {
            "chart_type": "colChart",
            "categories": ["Q1", "Q2", "Q3"],
            "series": [
                {"name": "Rev", "values": ["10", "12", "15"]},
                {"name": "Cost", "values": ["4", "5", "6"]},
            ],
            "partial": False,
        }
        recipe, content, conf, warns = R.chart_payload_to_content(
            chart, title="Revenue", body=["Grew faster than plan"],
        )
        self.assertIn(recipe, ("chart_insight", "chart_callout_panel"))
        self.assertEqual(content["chart_type"], "column")
        self.assertEqual(content["categories"], "Q1,Q2,Q3")
        self.assertEqual(content["series1_name"], "Rev")
        self.assertEqual(content["series1_values"], "10,12,15")
        self.assertEqual(content["series2_name"], "Cost")
        self.assertEqual(content["series2_values"], "4,5,6")
        self.assertGreaterEqual(conf, 0.9)

    def test_waterfall_recipe(self) -> None:
        chart = {
            "chart_type": "waterfall",
            "categories": ["Start", "Up", "End"],
            "series": [{"name": "Bridge", "values": ["100", "10", "110"]}],
        }
        recipe, content, conf, _ = R.chart_payload_to_content(chart, title="Bridge")
        self.assertEqual(recipe, "waterfall_insight")
        self.assertEqual(content["chart_type"], "waterfall")

    def test_callouts_from_body(self) -> None:
        chart = {
            "chart_type": "line",
            "categories": ["A", "B"],
            "series": [{"name": "S", "values": ["1", "2"]}],
        }
        recipe, content, _, _ = R.chart_payload_to_content(
            chart, title="T", body=["Insight one", "Callout two", "Callout three"],
        )
        self.assertEqual(recipe, "chart_callout_panel")
        self.assertEqual(len(content.get("callouts") or []), 3)


class TablePayload22(unittest.TestCase):
    def test_large_table_becomes_appendix(self) -> None:
        rows = [["H1", "H2", "H3"]] + [[f"r{i}", "1", "2"] for i in range(15)]
        recipe, content, conf, warns = R.table_payload_to_content(rows, title="Big")
        self.assertEqual(recipe, "appendix_table")
        self.assertEqual(len(content["rows"]), 15)
        self.assertTrue(any("appendix" in w for w in warns))

    def test_table_with_insight(self) -> None:
        rows = [["Metric", "Val"], ["A", "1"], ["B", "2"]]
        recipe, content, _, _ = R.table_payload_to_content(
            rows, title="Res", body=["Margin expanded"],
        )
        self.assertEqual(recipe, "results_table_insight")
        self.assertIn("insight", content)

    def test_appendix_recipe_paginates(self) -> None:
        from designmd_pptx.compile import compile_design_md
        from designmd_pptx.recipes import recipe_appendix_table

        tokens = compile_design_md(
            Path(__file__).resolve().parent.parent / "fixtures" / "linear.DESIGN.md"
        )
        rows = [[f"r{i}", "x"] for i in range(30)]
        ops = recipe_appendix_table(
            tokens, {"title": "T", "headers": ["A", "B"], "rows": rows},
        )
        slides = [o for o in ops if o.get("type") == "slide"]
        self.assertGreaterEqual(len(slides), 2)


class ClassifyIntegration22(unittest.TestCase):
    def test_classify_uses_reconstruct(self) -> None:
        slide = {
            "title": "KPI trend",
            "body": ["Beat plan", "EMEA strong", "Watch opex"],
            "subtitle": "",
            "tables": [],
            "pictures": [],
            "charts": [{
                "chart_type": "lineChart",
                "categories": ["Q1", "Q2"],
                "series": [{"name": "ARR", "values": ["10", "12"]}],
                "partial": False,
            }],
            "shapes": [],
            "connectors": 0,
            "smartart_count": 0,
        }
        recipe, content, conf, warnings = _classify(slide, 1, 3)
        self.assertEqual(recipe, "chart_callout_panel")
        self.assertEqual(content["chart_type"], "line")
        self.assertIn("callouts", content)

    def test_parse_chart_xml_roundtrip(self) -> None:
        """Build a minimal chart part and prove series/cats survive parse."""
        # Minimal chart XML with strCache categories + numCache values
        ns = {
            "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        }
        chart = Element("{%s}chart" % ns["c"])
        plot = SubElement(chart, "{%s}plotArea" % ns["c"])
        col = SubElement(plot, "{%s}barChart" % ns["c"])
        ser = SubElement(col, "{%s}ser" % ns["c"])
        tx = SubElement(ser, "{%s}tx" % ns["c"])
        v = SubElement(tx, "{%s}v" % ns["c"])
        v.text = "Revenue"
        cat = SubElement(ser, "{%s}cat" % ns["c"])
        str_cache = SubElement(SubElement(cat, "{%s}strRef" % ns["c"]),
                               "{%s}strCache" % ns["c"])
        for i, lab in enumerate(("Q1", "Q2", "Q3")):
            pt = SubElement(str_cache, "{%s}pt" % ns["c"], {"idx": str(i)})
            SubElement(pt, "{%s}v" % ns["c"]).text = lab
        val = SubElement(ser, "{%s}val" % ns["c"])
        num_cache = SubElement(SubElement(val, "{%s}numRef" % ns["c"]),
                               "{%s}numCache" % ns["c"])
        for i, num in enumerate(("10", "20", "30")):
            pt = SubElement(num_cache, "{%s}pt" % ns["c"], {"idx": str(i)})
            SubElement(pt, "{%s}v" % ns["c"]).text = num

        xml_bytes = tostring(chart, encoding="utf-8", xml_declaration=True)
        with tempfile.TemporaryDirectory() as td:
            pptx = Path(td) / "c.pptx"
            with zipfile.ZipFile(pptx, "w") as zf:
                zf.writestr("ppt/charts/chart1.xml", xml_bytes)
            with zipfile.ZipFile(pptx) as zf:
                parsed = _parse_chart_part(zf, "ppt/charts/chart1.xml")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["chart_type"], "bar")
        self.assertEqual(parsed["categories"], ["Q1", "Q2", "Q3"])
        self.assertEqual(parsed["series"][0]["name"], "Revenue")
        self.assertEqual(parsed["series"][0]["values"], ["10", "20", "30"])
        # Reconstruction keeps data
        recipe, content, conf, _ = R.chart_payload_to_content(parsed, title="R")
        self.assertIn(recipe, RECIPE_BUILDERS)
        self.assertEqual(content["series1_values"], "10,20,30")
        self.assertEqual(content["categories"], "Q1,Q2,Q3")


class ReconstructCli22(unittest.TestCase):
    def test_cli_modernizes_deck(self) -> None:
        deck = {
            "version": "1.1",
            "slides": [{
                "id": "c1",
                "recipe": "chart_insight",
                "content": {
                    "title": "Pie",
                    "chart_type": "pie3DChart",
                    "categories": "A,B",
                    "series1_values": "1,2",
                },
            }],
        }
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "deck.json"
            src.write_text(json.dumps(deck), encoding="utf-8")
            out = Path(td) / "modern.json"
            rc = main(["reconstruct", str(src), "-o", str(out)])
            self.assertEqual(rc, 0)
            modern = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(modern["slides"][0]["content"]["chart_type"], "doughnut")


if __name__ == "__main__":
    unittest.main()
