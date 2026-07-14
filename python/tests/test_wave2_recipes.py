"""Wave 2 long-tail role recipes (recipe-coverage-roadmap.md)."""

from __future__ import annotations

import unittest
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.recipes import (
    PATTERN_LAYOUT,
    RECIPE_BUILDERS,
    WAVE2_SEQUENCE,
    sequence_for,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class Wave2Recipes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = compile_design_md(FIXTURES / "premium-consulting.DESIGN.md")

    def test_wave2_registered(self) -> None:
        self.assertEqual(len(WAVE2_SEQUENCE), 12)
        for name in WAVE2_SEQUENCE:
            self.assertIn(name, RECIPE_BUILDERS)

    def test_pattern_layout_covers_wave2(self) -> None:
        flat = {n for names in PATTERN_LAYOUT.values() for n in names}
        for name in WAVE2_SEQUENCE:
            self.assertIn(name, flat)

    def test_builders_emit_slide(self) -> None:
        for name in WAVE2_SEQUENCE:
            ops = RECIPE_BUILDERS[name](self.tokens, None)
            self.assertTrue(ops, name)
            self.assertEqual(ops[0].get("type"), "slide", name)

    def test_sequence_for_wave2_and_all(self) -> None:
        w2 = sequence_for("wave2")
        for name in WAVE2_SEQUENCE:
            self.assertIn(name, w2)
        all_r = sequence_for("all")
        for name in WAVE2_SEQUENCE:
            self.assertIn(name, all_r)

    def test_finance_statement_has_table_and_insight(self) -> None:
        ops = RECIPE_BUILDERS["finance_statement"](self.tokens, {
            "headers": ["Line", "Actual"],
            "rows": [["Rev", "10"], ["Cost", "4"]],
            "insight": "Margin expanded.",
        })
        names = [str(o.get("props", {}).get("name", "")) for o in ops]
        self.assertTrue(any(n.startswith("FinHead") for n in names))
        self.assertTrue(any(n.startswith("FinInsight") for n in names))

    def test_project_status_rag_emits_dots(self) -> None:
        ops = RECIPE_BUILDERS["project_status_rag"](self.tokens, {
            "rows": [
                {"name": "A", "status": "green", "note": "ok"},
                {"name": "B", "status": "red", "note": "risk"},
            ],
        })
        dots = [
            o for o in ops
            if str(o.get("props", {}).get("name", "")).startswith("RagDot")
        ]
        self.assertEqual(len(dots), 2)

    def test_geo_and_device_without_src_use_placeholders(self) -> None:
        geo = RECIPE_BUILDERS["geo_callout"](self.tokens, {"title": "Map"})
        gnames = " ".join(str(o.get("props", {}).get("name", "")) for o in geo)
        self.assertIn("Placeholder", gnames)
        dev = RECIPE_BUILDERS["device_frame"](self.tokens, {"title": "UI"})
        dnames = " ".join(str(o.get("props", {}).get("name", "")) for o in dev)
        self.assertIn("Device", dnames)

    def test_pipeline_stage_count(self) -> None:
        ops = RECIPE_BUILDERS["pipeline_stages"](self.tokens, {
            "stages": [
                {"label": "A", "value": "10"},
                {"label": "B", "value": "5"},
                {"label": "C", "value": "2"},
            ],
        })
        stages = [
            o for o in ops
            if str(o.get("props", {}).get("name", "")).startswith("PipeStage")
        ]
        self.assertEqual(len(stages), 3)

    def test_total_recipe_count_agent_usable(self) -> None:
        # Roadmap: roughly ≤55–65, not hundreds (freeform #21 adds +1)
        self.assertLessEqual(len(RECIPE_BUILDERS), 65)
        self.assertGreaterEqual(len(RECIPE_BUILDERS), 60)


if __name__ == "__main__":
    unittest.main()
