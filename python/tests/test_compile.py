"""Full test suite for designmd-pptx v1.0 (no officecli required)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from designmd_pptx.colors_parse import parse_css_color, parse_gradient  # noqa: E402
from designmd_pptx.compile import compile_design_md  # noqa: E402
from designmd_pptx.recipes import generate_all_recipes, recipe_kpi_row  # noqa: E402
from designmd_pptx.tokens import (  # noqa: E402
    NEUTRAL,
    extract_semantic_colors,
    floor_body_pt,
    floor_title_pt,
    hex_brightness,
    to_pt,
)
from designmd_pptx.validate import (  # noqa: E402
    validate_content_overlay,
    validate_tokens_struct,
)


class CompileLinear(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = ROOT / "fixtures" / "linear.DESIGN.md"
        if not cls.fixture.exists():
            raise unittest.SkipTest("fixtures/linear.DESIGN.md missing")
        cls.tokens = compile_design_md(cls.fixture, brand="Linear")

    def test_accent_and_canvas(self):
        c = self.tokens["colors"]
        self.assertEqual(c["background"], "010102")
        self.assertEqual(c["accent"], "5E6AD2")

    def test_type_floors(self):
        t = self.tokens["type"]
        self.assertGreaterEqual(t["title_pt"], 36)
        self.assertGreaterEqual(t["body_pt"], 18)
        self.assertIn("micro_pt", t)

    def test_provenance(self):
        prov = self.tokens["color_provenance"]
        self.assertEqual(prov.get("accent"), "sourced")
        self.assertEqual(prov.get("risk"), "fallback")

    def test_schema_struct(self):
        errs = validate_tokens_struct(self.tokens)
        self.assertEqual(errs, [], errs)

    def test_all_patterns_present(self):
        recipes = generate_all_recipes(self.tokens, validate=False)
        for name in (
            "cover",
            "timeline",
            "process",
            "table",
            "image_full",
            "image_text_2col",
            "kpi_row",
            "close",
        ):
            self.assertIn(name, recipes)
            self.assertEqual(recipes[name][0]["type"], "slide")

    def test_floors_helpers(self):
        self.assertEqual(floor_body_pt(12), 18)
        self.assertEqual(floor_title_pt(20), 36)


class CompileLight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = ROOT / "fixtures" / "light-notionish.DESIGN.md"
        cls.tokens = compile_design_md(cls.fixture, brand="LightEditorial")

    def test_light_not_dark(self):
        self.assertFalse(self.tokens["dark_first"])
        self.assertEqual(self.tokens["colors"]["background"], "FAF8F5")

    def test_rgb_hsl_parsed(self):
        # primary rgb(200, 85, 61)
        self.assertEqual(self.tokens["colors"]["accent"], "C8553D")
        self.assertEqual(self.tokens["color_provenance"]["accent"], "sourced")

    def test_gradient_token(self):
        g = self.tokens.get("background_gradient")
        self.assertIsNotNone(g)
        self.assertIn("-", g)

    def test_schema_struct(self):
        self.assertEqual(validate_tokens_struct(self.tokens), [])


class NeutralFallbacks(unittest.TestCase):
    def test_empty_colors_no_linear_accent(self):
        palette, prov, warnings, _extras = extract_semantic_colors({})
        self.assertNotEqual(palette["accent"], "5E6AD2")
        self.assertEqual(palette["accent"], NEUTRAL["accent"])
        self.assertEqual(prov["accent"], "fallback")

    def test_secondary_not_muted(self):
        palette, _p, _w, _e = extract_semantic_colors(
            {
                "canvas": "#FFFFFF",
                "ink": "#111111",
                "primary": "#0066FF",
                "secondary": "#FF00AA",
            }
        )
        self.assertNotEqual(palette["muted"], "FF00AA")

    def test_px_conversion(self):
        self.assertAlmostEqual(to_pt("40px"), 30.0)
        self.assertAlmostEqual(to_pt("28px"), 21.0)
        self.assertAlmostEqual(to_pt("18pt"), 18.0)

    def test_css_color_parsers(self):
        self.assertEqual(parse_css_color("#abc"), "AABBCC")
        self.assertEqual(parse_css_color("rgb(255, 0, 0)"), "FF0000")
        self.assertIsNotNone(parse_css_color("hsl(140, 45%, 38%)"))
        self.assertEqual(
            parse_gradient("linear-gradient(135deg, #111111, #FFFFFF)"),
            "111111-FFFFFF-135",
        )


class AdaptiveGrid(unittest.TestCase):
    def _tokens(self):
        return {
            "colors": {
                "background": "FFFFFF",
                "content_background": "FFFFFF",
                "surface": "F5F7FA",
                "accent": "4A5568",
                "on_accent": "FFFFFF",
                "text": "333333",
                "text_on_surface": "333333",
                "text_on_content": "333333",
                "muted": "6B7B8D",
                "hairline": "D0D5DD",
                "success": "2F9E44",
                "risk": "C92A2A",
                "chart_series1": "4A5568",
                "chart_series2": "A0AEC0",
                "chart_series3": "2F9E44",
            },
            "type": {
                "heading_font": "Arial",
                "body_font": "Calibri",
                "cover_pt": 44,
                "title_pt": 36,
                "section_pt": 22,
                "body_pt": 18,
                "caption_pt": 12,
                "micro_pt": 14,
                "kpi_pt": 60,
            },
            "shape": {"card_preset": "roundRect"},
            "margin_cm": 1.27,
            "gap_cm": 0.76,
            "dark_first": False,
        }

    def test_kpi_two_items(self):
        ops = recipe_kpi_row(
            self._tokens(),
            {
                "title": "Two",
                "kpis": [
                    {"value": "1", "label": "A", "chip": ""},
                    {"value": "2", "label": "B", "chip": ""},
                ],
            },
        )
        names = [
            o["props"].get("name")
            for o in ops
            if o.get("type") == "shape" and "name" in o.get("props", {})
        ]
        self.assertIn("Kpi1Bg", names)
        self.assertNotIn("Kpi3Bg", names)


class ContentValidation(unittest.TestCase):
    def test_sample_content_ok(self):
        import json

        path = ROOT / "examples" / "content.sample.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(validate_content_overlay(data), [])

    def test_unknown_section(self):
        errs = validate_content_overlay({"nope": {}})
        self.assertTrue(any("unknown" in e for e in errs))

    def test_kpi_too_many(self):
        errs = validate_content_overlay(
            {"kpi_row": {"kpis": [{"value": str(i)} for i in range(5)]}}
        )
        self.assertTrue(any("max 4" in e for e in errs))


class DeckSpec(unittest.TestCase):
    def test_deck_repeat_recipes(self):
        import json

        from designmd_pptx.deck import generate_deck

        fixture = ROOT / "fixtures" / "linear.DESIGN.md"
        tokens = compile_design_md(fixture, brand="Linear")
        deck = json.loads((ROOT / "examples" / "content.deck.json").read_text(encoding="utf-8"))
        ops, normalized, warnings = generate_deck(tokens, deck, strict=True)
        self.assertGreaterEqual(len(normalized["slides"]), 7)
        self.assertGreater(len(ops), 20)
        self.assertTrue(any(s["recipe"] == "process" for s in normalized["slides"]))
        self.assertTrue(any(s["recipe"] == "image_text_2col" for s in normalized["slides"]))
        # first op of each slide is type slide
        slide_ops = [o for o in ops if o.get("type") == "slide"]
        self.assertEqual(len(slide_ops), len(normalized["slides"]))

    def test_cap_reject(self):
        from designmd_pptx.deck import generate_deck

        fixture = ROOT / "fixtures" / "linear.DESIGN.md"
        tokens = compile_design_md(fixture, brand="Linear")
        bad = {
            "version": "1.0",
            "slides": [
                {
                    "recipe": "kpi_row",
                    "content": {
                        "title": "x",
                        "kpis": [{"value": str(i), "label": "L"} for i in range(5)],
                    },
                }
            ],
        }
        with self.assertRaises(ValueError):
            generate_deck(tokens, bad, strict=True)


if __name__ == "__main__":
    unittest.main()
