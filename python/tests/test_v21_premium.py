"""Phase 2 / #58 — first-wave premium patterns."""

from __future__ import annotations

import unittest
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.deck import validate_deck_content_caps
from designmd_pptx.recipes import RECIPE_BUILDERS, recipe_agenda_toc, recipe_kpi_dashboard_grid

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class PremiumPatterns58(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = compile_design_md(FIXTURES / "premium-consulting.DESIGN.md")
        cls.linear = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def test_dashboard_emits_grid(self) -> None:
        kpis = [
            {"value": f"{10 + i}%", "label": f"Metric {i}", "chip": "+1%"}
            for i in range(6)
        ]
        ops = recipe_kpi_dashboard_grid(
            self.tokens, {"title": "Ops dashboard", "subtitle": "QoQ", "kpis": kpis}
        )
        names = [op.get("props", {}).get("name") for op in ops if op.get("type") == "shape"]
        self.assertIn("DashTitle", names)
        self.assertIn("DashSubtitle", names)
        self.assertTrue(any(n and n.startswith("DashKpi") for n in names))
        # 6 tiles × (bg + value + label + chip) ≥ 6 value labels
        values = [n for n in names if n and n.endswith("Value")]
        self.assertEqual(len(values), 6)

    def test_dashboard_clamps_to_eight(self) -> None:
        kpis = [{"value": "1", "label": f"M{i}"} for i in range(12)]
        ops = recipe_kpi_dashboard_grid(self.linear, {"title": "Too many", "kpis": kpis})
        values = [
            op["props"]["name"]
            for op in ops
            if op.get("type") == "shape"
            and str(op.get("props", {}).get("name", "")).endswith("Value")
        ]
        self.assertEqual(len(values), 8)

    def test_agenda_rows(self) -> None:
        items = [
            {"label": "Intro", "time": "5m"},
            {"label": "Context"},
            {"label": "Options"},
            {"label": "Decision"},
            {"label": "Next steps", "time": "10m"},
        ]
        ops = recipe_agenda_toc(self.tokens, {"title": "Today", "items": items})
        names = [op.get("props", {}).get("name") for op in ops if op.get("type") == "shape"]
        self.assertIn("AgendaTitle", names)
        self.assertEqual(sum(1 for n in names if n and n.startswith("AgendaNum") and "Wrap" not in n), 5)

    def test_caps_validation(self) -> None:
        bad = {
            "version": "1",
            "slides": [
                {"recipe": "kpi_dashboard_grid", "content": {"kpis": [{"value": "1"}]}},
                {
                    "recipe": "agenda_toc",
                    "content": {"items": ["a", "b", "c"]},  # < 5
                },
            ],
        }
        errs = validate_deck_content_caps(bad)
        self.assertTrue(any("kpi_dashboard_grid" in e for e in errs))
        self.assertTrue(any("agenda_toc" in e for e in errs))

    def test_builders_registered(self) -> None:
        for name in ("kpi_dashboard_grid", "agenda_toc", "section_opener_numbered"):
            ops = RECIPE_BUILDERS[name](self.tokens, None)
            self.assertEqual(ops[0]["type"], "slide")


if __name__ == "__main__":
    unittest.main()
