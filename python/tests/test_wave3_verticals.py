"""Wave 3 vertical deck-specs + compose role keyword routing."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from designmd_pptx.compose import compose_outline
from designmd_pptx.recipes import RECIPE_BUILDERS, WAVE1_SEQUENCE, WAVE2_SEQUENCE

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

VERTICALS = [
    "content.business.deck.json",
    "content.marketing.deck.json",
    "content.health.deck.json",
    "content.education.deck.json",
    "content.finance.deck.json",
]


class Wave3Verticals(unittest.TestCase):
    def test_five_vertical_decks_exist_with_wave_recipes(self) -> None:
        wave = set(WAVE1_SEQUENCE) | set(WAVE2_SEQUENCE)
        found = 0
        for name in VERTICALS:
            path = EXAMPLES / name
            self.assertTrue(path.is_file(), f"missing {name}")
            data = json.loads(path.read_text(encoding="utf-8"))
            slides = data.get("slides") or []
            self.assertGreaterEqual(len(slides), 3, name)
            recipes = {s.get("recipe") for s in slides if isinstance(s, dict)}
            self.assertTrue(recipes - {None, "cover", "close", "bullets"}, name)
            # At least one Wave 1/2 recipe in each vertical
            self.assertTrue(recipes & wave, f"{name} has no Wave1/2 recipes: {recipes}")
            for r in recipes:
                if r:
                    self.assertIn(r, RECIPE_BUILDERS, r)
            found += 1
        self.assertGreaterEqual(found, 5)

    def test_finance_skin_fixture_exists(self) -> None:
        self.assertTrue((FIXTURES / "vertical-finance.DESIGN.md").is_file())

    def test_compose_routes_okr_keyword_to_okrs_tree(self) -> None:
        brief = "# Plan\n\n## OKRs for H2\n\n- KR1 — Ship beta\n- KR2 — 10 logos\n"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            bp = out / "brief.md"
            bp.write_text(brief, encoding="utf-8")
            report = compose_outline(bp, out / "composed")
        recipes = [s["recipe"] for s in report["slides"]]
        self.assertIn("okrs_tree", recipes, recipes)

    def test_compose_routes_swot_and_pipeline(self) -> None:
        brief = (
            "# Strategy\n\n"
            "## SWOT analysis\n\n- Strengths — Brand\n- Weaknesses — Scale\n\n"
            "## Demand pipeline\n\n- Aware — 100\n- SQL — 20\n- Won — 4\n"
        )
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            bp = out / "brief.md"
            bp.write_text(brief, encoding="utf-8")
            report = compose_outline(bp, out / "composed")
        recipes = [s["recipe"] for s in report["slides"]]
        self.assertIn("swot_2x2", recipes, recipes)
        self.assertIn("pipeline_stages", recipes, recipes)


if __name__ == "__main__":
    unittest.main()
