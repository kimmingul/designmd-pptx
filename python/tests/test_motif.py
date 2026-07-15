"""Visual motif catalog + builders (SmartArt-like originals)."""

from __future__ import annotations

import unittest
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.motif import catalog, list_motifs, motif_info, render_motif
from designmd_pptx.recipes import (
    recipe_before_after_slider,
    recipe_feature_cards,
    recipe_process,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class MotifCatalog(unittest.TestCase):
    def test_catalog_lists_core_motifs(self) -> None:
        ids = list_motifs()
        for required in (
            "split_hero", "card_row", "step_rail", "kpi_hero",
            "stair_ascent", "check_stack", "tile_row",
        ):
            self.assertIn(required, ids, required)
        cat = catalog()
        self.assertEqual(cat.get("schema"), 1)
        self.assertIn("license_note", cat)
        info = motif_info("card_row")
        self.assertIsNotNone(info)
        self.assertIn("feature_cards", info.get("recipes") or [])


class MotifRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def test_card_row_ops(self) -> None:
        ops = render_motif("card_row", self.tokens, {
            "title": "Caps",
            "cards": [
                {"title": "A", "body": "One"},
                {"title": "B", "body": "Two"},
                {"title": "C", "body": "Three"},
            ],
        })
        names = [o.get("props", {}).get("name") for o in ops if o.get("type") == "shape"]
        self.assertIn("FeatTitle", names)
        self.assertTrue(any(n and n.startswith("Card1") for n in names))

    def test_split_hero_ops(self) -> None:
        ops = render_motif("split_hero", self.tokens, {
            "title": "Delta",
            "left": {"title": "Before", "body": ["x", "y"]},
            "right": {"title": "After", "body": ["a", "b"]},
            "name_prefix": "Ba",
        })
        names = [o.get("props", {}).get("name") for o in ops if o.get("type") == "shape"]
        self.assertTrue(any(n and n.startswith("BaPanel") for n in names))

    def test_step_rail_with_connectors(self) -> None:
        ops = render_motif("step_rail", self.tokens, {
            "title": "Flow",
            "steps": [{"label": "A"}, {"label": "B"}, {"label": "C"}],
            "slide_index": 1,
        })
        self.assertTrue(any(o.get("type") == "connector" for o in ops))

    def test_recipes_delegate_to_motifs(self) -> None:
        ops = recipe_feature_cards(self.tokens, {
            "title": "T",
            "cards": [{"title": "X", "body": "Y"}] * 3,
        })
        self.assertTrue(any(o.get("type") == "slide" for o in ops))
        ops2 = recipe_before_after_slider(self.tokens, {
            "title": "T",
            "before": {"title": "B", "body": ["1"]},
            "after": {"title": "A", "body": ["2"]},
        })
        self.assertTrue(any(o.get("type") == "slide" for o in ops2))
        ops3 = recipe_process(self.tokens, {"title": "P", "steps": ["A", "B"]}, slide_index=2)
        self.assertTrue(any(o.get("type") == "connector" for o in ops3))

    def test_unknown_motif_raises(self) -> None:
        with self.assertRaises(KeyError):
            render_motif("not_a_real_motif", self.tokens, {})


if __name__ == "__main__":
    unittest.main()
