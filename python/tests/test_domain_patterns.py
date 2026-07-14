"""Phase 2 / #10 — academic / medical / research domain patterns."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.deck import generate_deck, validate_deck_content_caps
from designmd_pptx.deck import normalize_deck_spec
from designmd_pptx.recipes import (
    CATALOG_SEQUENCE,
    CORE_SEQUENCE,
    DOMAIN_SEQUENCE,
    PREMIUM_SEQUENCE,
    RECIPE_BUILDERS,
    sequence_for,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

DOMAIN = (
    "consort_flow",
    "kaplan_meier",
    "forest_plot",
    "study_design",
    "results_table_insight",
    "multi_panel_figure",
)


class DomainPatterns10(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")
        cls.medical = json.loads(
            (EXAMPLES / "content.medical.deck.json").read_text(encoding="utf-8")
        )

    def test_all_domain_recipes_registered(self) -> None:
        for name in DOMAIN:
            self.assertIn(name, RECIPE_BUILDERS)

    def test_default_ops_on_canvas(self) -> None:
        for name in DOMAIN:
            with self.subTest(pattern=name):
                ops = RECIPE_BUILDERS[name](self.tokens, None)
                self.assertEqual(ops[0]["type"], "slide")
                self.assertGreater(len(ops), 2)

    def test_medical_deck_spec_generates(self) -> None:
        errs = validate_deck_content_caps(self.medical)
        self.assertEqual(errs, [])
        ops, deck, warnings = generate_deck(self.tokens, self.medical, strict=False)
        recipes = [s["recipe"] for s in deck["slides"]]
        for name in DOMAIN:
            self.assertIn(name, recipes)
        self.assertGreater(len(ops), 20)
        # no hard failures in generation
        self.assertIsInstance(warnings, list)

    def test_consort_and_forest_markers(self) -> None:
        cops = RECIPE_BUILDERS["consort_flow"](self.tokens, {
            "stages": [
                {"label": "Assessed", "n": "N=100"},
                {"label": "Randomized", "n": "N=80"},
                {"label": "Analyzed", "n": "N=78"},
            ],
        })
        names = [op.get("props", {}).get("name") for op in cops]
        self.assertTrue(any(n and n.startswith("ConsortBox") for n in names))
        self.assertTrue(any(n and n.startswith("ConsortLink") for n in names))

        fops = RECIPE_BUILDERS["forest_plot"](self.tokens, {
            "rows": [
                {"label": "A", "effect": -0.2, "low": -0.5, "high": 0.1, "text": "0.8"},
                {"label": "B", "effect": 0.1, "low": -0.1, "high": 0.3, "text": "1.1"},
            ],
        })
        fnames = [op.get("props", {}).get("name") for op in fops]
        self.assertTrue(any(n and n.startswith("ForestBar") for n in fnames))
        self.assertTrue(any(n and n.startswith("ForestDot") for n in fnames))
        # private metadata must not leak into officecli props
        for op in fops:
            props = op.get("props") or {}
            self.assertNotIn("_forest", props)

    def test_km_has_chart_and_risk(self) -> None:
        ops = RECIPE_BUILDERS["kaplan_meier"](self.tokens, None)
        self.assertTrue(any(op.get("type") == "chart" for op in ops))
        names = [op.get("props", {}).get("name") for op in ops]
        self.assertTrue(any(n and n.startswith("KmRisk") for n in names))

    def test_sequence_partitions(self) -> None:
        self.assertEqual(sequence_for("core"), list(CORE_SEQUENCE))
        # empty scaffold defaults to core — no medical tax
        deck, warns = normalize_deck_spec(None)
        recipes = [s["recipe"] for s in deck["slides"]]
        self.assertEqual(recipes, list(CORE_SEQUENCE))
        self.assertTrue(any("core" in w for w in warns))
        self.assertNotIn("consort_flow", recipes)
        self.assertNotIn("kpi_dashboard_grid", recipes)
        # full catalog on request
        full, _ = normalize_deck_spec(None, catalog="all")
        full_r = [s["recipe"] for s in full["slides"]]
        self.assertEqual(len(full_r), len(CATALOG_SEQUENCE))
        for name in DOMAIN_SEQUENCE + PREMIUM_SEQUENCE:
            self.assertIn(name, full_r)
        # every builder is reachable via catalog partitions
        covered = set(CORE_SEQUENCE) | set(PREMIUM_SEQUENCE) | set(DOMAIN_SEQUENCE)
        self.assertEqual(set(RECIPE_BUILDERS), covered)
        self.assertEqual(set(CATALOG_SEQUENCE), covered)

    def test_caps(self) -> None:
        bad = {
            "version": "1",
            "slides": [
                {
                    "recipe": "consort_flow",
                    "content": {"stages": [{"label": "only one"}]},
                },
                {
                    "recipe": "multi_panel_figure",
                    "content": {"panels": [{"label": x} for x in "ABCDE"]},
                },
            ],
        }
        errs = validate_deck_content_caps(bad)
        self.assertTrue(any("consort_flow" in e for e in errs))
        self.assertTrue(any("multi_panel_figure" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
