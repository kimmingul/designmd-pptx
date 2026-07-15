"""Visual motif catalog + builders (Infograpify structural coverage)."""

from __future__ import annotations

import unittest
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.motif import MOTIF_BUILDERS, catalog, list_motifs, motif_info, render_motif
from designmd_pptx.motifs.coverage import RECIPE_TO_MOTIF, all_motif_ids
from designmd_pptx.recipes import (
    RECIPE_BUILDERS,
    recipe_before_after_slider,
    recipe_chevron_process,
    recipe_feature_cards,
    recipe_org_tree,
    recipe_process,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class MotifCatalog(unittest.TestCase):
    def test_catalog_covers_infograpify_collapse(self) -> None:
        ids = list_motifs()
        self.assertGreaterEqual(len(ids), 60)
        for required in (
            "split_hero", "card_row", "step_rail", "kpi_hero", "kpi_band",
            "stair_ascent", "check_stack", "tile_row", "sparse_hero",
            "funnel_cascade", "matrix_quad", "section_mark",
            "org_cascade", "chevron_flow", "hub_orbit", "pyramid_stack",
            "timeline_rail", "pricing_tiers", "canvas_bmc",
        ):
            self.assertIn(required, ids, required)
        cat = catalog()
        self.assertIn(cat.get("schema"), (1, 2))
        self.assertIn("license_note", cat)
        self.assertEqual(cat.get("infograpify_decks_collapsed"), 400)
        info = motif_info("card_row")
        self.assertIsNotNone(info)
        self.assertIn("feature_cards", info.get("recipes") or [])

    def test_every_recipe_maps_to_buildable_motif(self) -> None:
        for recipe, mid in RECIPE_TO_MOTIF.items():
            self.assertIn(recipe, RECIPE_BUILDERS, recipe)
            self.assertIn(mid, MOTIF_BUILDERS, f"{recipe} → {mid}")
        # coverage set equals builders for custom + recipe-backed
        for mid in all_motif_ids():
            self.assertIn(mid, MOTIF_BUILDERS, mid)


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
            render_motif("not_a_real_motif_xyz", self.tokens, {})

    def test_all_builders_emit_slides(self) -> None:
        """Every registered motif must produce a slide op (Gate 0)."""
        for mid in sorted(MOTIF_BUILDERS):
            with self.subTest(mid=mid):
                ops = render_motif(mid, self.tokens, {"title": mid})
                self.assertTrue(
                    any(o.get("type") == "slide" for o in ops), mid,
                )

    def test_org_and_chevron_recipes_delegate(self) -> None:
        org = recipe_org_tree(self.tokens, {
            "title": "Team",
            "root": {"name": "Min", "role": "Lead"},
            "reports": [{"name": "A", "role": "R"}],
        })
        names = [o.get("props", {}).get("name") for o in org if o.get("type") == "shape"]
        self.assertIn("OrgRoot", names)
        self.assertTrue(any(n and n.startswith("OrgChild") for n in names))
        ch = recipe_chevron_process(self.tokens, {
            "title": "Path",
            "steps": [{"label": "A"}, {"label": "B"}, {"label": "C"}],
        })
        names2 = [o.get("props", {}).get("name") for o in ch if o.get("type") == "shape"]
        self.assertTrue(any(n and n.startswith("Chevron") for n in names2))

    def test_structural_family_samples(self) -> None:
        samples = {
            "hub_orbit": {"title": "C", "hub": "Core", "steps": [{"label": "A"}] * 4},
            "pyramid_stack": {"title": "P", "levels": [{"label": "L1"}, {"label": "L2"}, {"label": "L3"}]},
            "timeline_rail": {"title": "T", "steps": [{"label": "Q1"}, {"label": "Q2"}, {"label": "Q3"}]},
            "pricing_tiers": {"title": "$$", "tiers": [{"name": "A", "price": "$1"}]},
            "kpi_grid": {"title": "K", "kpis": [{"value": "1", "label": "a"}] * 4},
            "canvas_bmc": {"title": "BMC"},
            "risk_heat": {"title": "Risk"},
            "venn_duo": {"title": "V", "left": "A", "right": "B", "overlap": "C"},
        }
        for mid, slots in samples.items():
            with self.subTest(mid=mid):
                ops = render_motif(mid, self.tokens, slots)
                self.assertTrue(any(o.get("type") == "slide" for o in ops), mid)


if __name__ == "__main__":
    unittest.main()
