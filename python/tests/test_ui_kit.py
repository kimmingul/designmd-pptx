"""Shared UI kit contract — spacing system for recipes."""

from __future__ import annotations

import unittest
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx import ui_kit as UI
from designmd_pptx.recipes import (
    recipe_before_after_slider,
    recipe_bullets,
    recipe_comparison_2col,
    recipe_feature_cards,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class StageMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def test_metrics_positive(self) -> None:
        st = UI.stage_metrics(self.tokens)
        self.assertGreater(st.margin, 0.5)
        self.assertGreater(st.gap, 0.4)
        self.assertGreaterEqual(st.pad, 0.85)
        self.assertAlmostEqual(st.usable_w, 33.87 - 2 * st.margin, places=2)
        self.assertGreater(st.content_h, 4.0)

    def test_spacious_demo_design(self) -> None:
        root = Path(__file__).resolve().parents[2]
        demo = root / "demo" / "apple.DESIGN.md"
        if not demo.is_file():
            self.skipTest("demo apple.DESIGN.md missing")
        tok = compile_design_md(demo)
        st = UI.stage_metrics(tok)
        self.assertEqual(st.density_name, "spacious")
        self.assertAlmostEqual(st.margin, 2.2, places=1)
        self.assertAlmostEqual(st.gap, 1.1, places=1)
        self.assertGreaterEqual(st.pad, 1.0)


class RecipeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def _shapes(self, ops: list) -> list[dict]:
        return [o["props"] for o in ops if o.get("type") == "shape"]

    def _h(self, props: dict) -> float:
        return float(str(props["height"]).rstrip("cm"))

    def test_feature_cards_body_not_giant(self) -> None:
        ops = recipe_feature_cards(self.tokens, {
            "title": "Caps",
            "cards": [
                {"title": "A", "body": "Short one."},
                {"title": "B", "body": "Short two."},
                {"title": "C", "body": "Short three."},
            ],
        })
        bodies = [p for p in self._shapes(ops) if str(p.get("name", "")).endswith("Body")]
        self.assertEqual(len(bodies), 3)
        for p in bodies:
            self.assertLess(self._h(p), 6.0, p.get("name"))
        nums = [p for p in self._shapes(ops) if str(p.get("name", "")).endswith("Num")]
        self.assertEqual(len(nums), 3)

    def test_before_after_panel_not_full_canvas(self) -> None:
        ops = recipe_before_after_slider(self.tokens, {
            "title": "Delta",
            "before": {"title": "Before", "body": ["One", "Two", "Three"]},
            "after": {"title": "After", "body": ["A", "B", "C"]},
        })
        panels = [p for p in self._shapes(ops) if str(p.get("name", "")).startswith("BaPanel")]
        self.assertEqual(len(panels), 2)
        for p in panels:
            self.assertLess(self._h(p), 12.0, "panel must not fill 16:9 stage")
        bodies = [p for p in self._shapes(ops) if str(p.get("name", "")).startswith("BaBody")]
        for p in bodies:
            self.assertLess(self._h(p), 7.0)

    def test_bullets_body_not_weight_stretched_alone(self) -> None:
        ops = recipe_bullets(self.tokens, {
            "title": "List",
            "bullets": ["Alpha", "Beta", "Gamma"],
        })
        body = next(p for p in self._shapes(ops) if p.get("name") == "BulletBody")
        # Three short bullets should not claim most of the slide height.
        self.assertLess(self._h(body), 10.0)

    def test_comparison_names_and_body_height(self) -> None:
        ops = recipe_comparison_2col(self.tokens, {
            "title": "Compare",
            "left": {"title": "A", "body": "short a"},
            "right": {"title": "B", "body": "short b"},
        })
        names = {p.get("name") for p in self._shapes(ops)}
        self.assertIn("CmpTitle", names)
        self.assertIn("Cmp1Bg", names)
        self.assertIn("Cmp1Body", names)
        body = next(p for p in self._shapes(ops) if p.get("name") == "Cmp1Body")
        self.assertLess(self._h(body), 8.0)


if __name__ == "__main__":
    unittest.main()
