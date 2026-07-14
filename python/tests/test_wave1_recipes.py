"""Wave 1 full-family coverage recipes (recipe-coverage-roadmap.md)."""

from __future__ import annotations

import unittest
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.recipes import RECIPE_BUILDERS, PATTERN_LAYOUT

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

WAVE1 = [
    "chevron_process",
    "cycle_loop",
    "waterfall_insight",
    "venn_overlap",
    "swot_2x2",
    "gantt_bars",
    "org_tree",
    "persona_card",
    "business_canvas",
    "fishbone_causes",
    "iceberg_levels",
    "framework_row",
]


class Wave1Recipes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = compile_design_md(FIXTURES / "premium-consulting.DESIGN.md")

    def test_all_registered(self) -> None:
        for name in WAVE1:
            self.assertIn(name, RECIPE_BUILDERS)

    def test_pattern_layout_bucket(self) -> None:
        flat = {n for names in PATTERN_LAYOUT.values() for n in names}
        for name in WAVE1:
            self.assertIn(name, flat, f"{name} missing from PATTERN_LAYOUT")

    def test_builders_emit_slide_and_shapes(self) -> None:
        for name in WAVE1:
            ops = RECIPE_BUILDERS[name](self.tokens, None)
            self.assertTrue(ops, name)
            self.assertEqual(ops[0].get("type"), "slide", name)
            types = {op.get("type") for op in ops}
            self.assertTrue(types & {"shape", "chart", "notes"}, name)

    def test_waterfall_forces_chart_type(self) -> None:
        ops = RECIPE_BUILDERS["waterfall_insight"](self.tokens, {
            "title": "Bridge",
            "categories": "A,B,C",
            "series1_values": "10,2,-1",
        })
        charts = [o for o in ops if o.get("type") == "chart"]
        self.assertTrue(charts)
        self.assertEqual(
            str(charts[0]["props"].get("chartType", "")).lower(), "waterfall")

    def test_swot_labels_default_quadrants(self) -> None:
        ops = RECIPE_BUILDERS["swot_2x2"](self.tokens, {
            "strengths": ["Brand"],
            "weaknesses": ["Scale"],
            "opportunities": ["Partner"],
            "threats": ["Churn"],
        })
        texts = " ".join(
            str(o.get("props", {}).get("text", "")) for o in ops
        )
        self.assertIn("Strengths", texts)
        self.assertIn("Threats", texts)

    def test_gantt_respects_task_span(self) -> None:
        ops = RECIPE_BUILDERS["gantt_bars"](self.tokens, {
            "phases": ["Q1", "Q2", "Q3", "Q4"],
            "tasks": [{"name": "Long", "start": 0, "end": 3}],
        })
        bars = [
            o for o in ops
            if str(o.get("props", {}).get("name", "")).startswith("GanttBar")
        ]
        self.assertTrue(bars)
        w = float(str(bars[0]["props"]["width"]).replace("cm", ""))
        self.assertGreater(w, 5.0)

    def test_business_canvas_nine_blocks(self) -> None:
        ops = RECIPE_BUILDERS["business_canvas"](self.tokens, None)
        blocks = [
            o for o in ops
            if str(o.get("props", {}).get("name", "")).startswith("BmcBlock")
        ]
        self.assertEqual(len(blocks), 9)

    def test_framework_row_adkar_default_count(self) -> None:
        ops = RECIPE_BUILDERS["framework_row"](self.tokens, {
            "framework": "ADKAR",
            "steps": [
                {"label": "Awareness"}, {"label": "Desire"},
                {"label": "Knowledge"}, {"label": "Ability"},
                {"label": "Reinforcement"},
            ],
        })
        cards = [
            o for o in ops
            if str(o.get("props", {}).get("name", "")).startswith("FwCard")
        ]
        self.assertEqual(len(cards), 5)


if __name__ == "__main__":
    unittest.main()
