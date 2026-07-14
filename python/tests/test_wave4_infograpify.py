"""Wave 4 — Infograpify long-tail structural recipes."""

from __future__ import annotations

import unittest
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.recipes import (
    PATTERN_LAYOUT,
    RECIPE_BUILDERS,
    WAVE4_SEQUENCE,
    sequence_for,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
PKG = Path(__file__).resolve().parent.parent / "designmd_pptx"


class Wave4Infograpify(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = compile_design_md(FIXTURES / "premium-consulting.DESIGN.md")

    def test_wave4_count_and_registry(self) -> None:
        self.assertEqual(len(WAVE4_SEQUENCE), 14)
        for name in WAVE4_SEQUENCE:
            self.assertIn(name, RECIPE_BUILDERS, name)

    def test_pattern_layout_covers_wave4(self) -> None:
        flat = {n for names in PATTERN_LAYOUT.values() for n in names}
        for name in WAVE4_SEQUENCE:
            self.assertIn(name, flat, name)

    def test_sequence_for_wave4(self) -> None:
        seq = sequence_for("wave4")
        for name in WAVE4_SEQUENCE:
            self.assertIn(name, seq)
        self.assertIn("mindmap_branches", sequence_for("infograpify"))

    def test_builders_emit_slide(self) -> None:
        samples = {
            "mindmap_branches": {"hub": "Core", "branches": [{"label": f"B{i}"} for i in range(6)]},
            "journey_stages": None,
            "pestle_grid": {"political": ["Reg risk"], "economic": ["FX"]},
            "raci_matrix": None,
            "scorecard_balanced": None,
            "hex_cluster": None,
            "puzzle_pieces": None,
            "pillar_columns": None,
            "stairs_ascent": None,
            "checklist_board": {
                "items": [{"label": "A", "done": True}, {"label": "B", "done": False}],
            },
            "empathy_map_quad": {"user": "Alex", "says": "• quote"},
            "risk_heat_matrix": {
                "risks": [{"label": "Delay", "likelihood": 3, "impact": 2}],
            },
            "circle_segments": None,
            "mission_vision_split": {
                "mission": "Why we exist", "vision": "Where we go",
            },
        }
        for name in WAVE4_SEQUENCE:
            ops = RECIPE_BUILDERS[name](self.tokens, samples.get(name))
            self.assertTrue(ops, name)
            self.assertEqual(ops[0].get("type"), "slide", name)
            types = {o.get("type") for o in ops}
            self.assertTrue(types & {"shape", "notes"}, name)

    def test_raci_has_role_headers(self) -> None:
        ops = RECIPE_BUILDERS["raci_matrix"](self.tokens, {
            "roles": ["PM", "Eng"],
            "activities": [{"name": "Ship", "raci": ["A", "R"]}],
        })
        names = [str(o.get("props", {}).get("name", "")) for o in ops]
        self.assertTrue(any(n.startswith("RaciRole") for n in names))
        self.assertTrue(any(n.startswith("RaciCell") for n in names))

    def test_pestle_six_panels(self) -> None:
        ops = RECIPE_BUILDERS["pestle_grid"](self.tokens, None)
        panels = [
            o for o in ops
            if str(o.get("props", {}).get("name", "")).startswith("Pestle")
            and not str(o.get("props", {}).get("name", "")).startswith("PestleLab")
            and not str(o.get("props", {}).get("name", "")).startswith("PestleBody")
            and o.get("type") == "shape"
            and o.get("props", {}).get("fill") not in (None, "none")
        ]
        # 6 background panels
        self.assertGreaterEqual(len(panels), 6)

    def test_compose_title_hints_wave4(self) -> None:
        from designmd_pptx.compose import _role_from_title
        self.assertEqual(_role_from_title("Customer journey map"), "journey_stages")
        self.assertEqual(_role_from_title("PESTLE external scan"), "pestle_grid")
        self.assertEqual(_role_from_title("RACI for launch"), "raci_matrix")
        self.assertEqual(_role_from_title("Empathy map workshop"), "empathy_map_quad")
        self.assertEqual(_role_from_title("Mission and vision"), "mission_vision_split")


if __name__ == "__main__":
    unittest.main()
