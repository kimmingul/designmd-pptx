"""Phase 2 / #58 — first-wave premium patterns."""

from __future__ import annotations

import unittest
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.deck import validate_deck_content_caps
from designmd_pptx.recipes import (
    RECIPE_BUILDERS,
    recipe_agenda_toc,
    recipe_chart_callout_panel,
    recipe_funnel_stages,
    recipe_kpi_dashboard_grid,
    recipe_pyramid_levels,
    recipe_roadmap_swimlane,
    recipe_story_timeline,
    recipe_vs_scorecard,
    recipe_quadrant_matrix_rich,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class PremiumPatterns58(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = compile_design_md(FIXTURES / "premium-consulting.DESIGN.md")
        cls.linear = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def test_dashboard_fit_matches_render_scale(self) -> None:
        from designmd_pptx.fit import check_text

        # Realistic multi-digit KPI must not false-fail at dashboard scale.
        err = check_text(
            "kpi_dashboard_grid",
            "kpis.value",
            "1,234,567",
            self.linear,
            items=6,
        )
        self.assertIsNone(err, err)

    def test_forest_swaps_inverted_ci(self) -> None:
        from designmd_pptx.recipes import recipe_forest_plot

        ops = recipe_forest_plot(
            self.linear,
            {
                "studies": [
                    {
                        "label": "X",
                        "effect": 0.0,
                        "low": 0.5,
                        "high": -0.5,
                        "text": "bad",
                    }
                ]
            },
        )
        notes = [
            op["props"]["text"]
            for op in ops
            if op.get("type") == "notes"
        ]
        self.assertTrue(any("swapped inverted CI" in n for n in notes))
        bars = [
            op
            for op in ops
            if str(op.get("props", {}).get("name", "")).startswith("ForestBar")
        ]
        # After swap, bar should span a real interval (not a 0.12 stub only by accident).
        self.assertTrue(bars)
        w = float(bars[0]["props"]["width"].replace("cm", ""))
        self.assertGreater(w, 0.2)

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
        for name in (
            "kpi_dashboard_grid", "agenda_toc", "section_opener_numbered",
            "story_timeline", "funnel_stages", "roadmap_swimlane",
            "quadrant_matrix_rich", "pyramid_levels", "vs_scorecard",
            "chart_callout_panel",
        ):
            ops = RECIPE_BUILDERS[name](self.tokens, None)
            self.assertEqual(ops[0]["type"], "slide")

    def test_story_timeline_milestones(self) -> None:
        ops = recipe_story_timeline(self.tokens, {
            "title": "Arc",
            "era": "FY26",
            "steps": [
                {"date": "Q1", "title": "Start", "detail": "Kickoff"},
                {"date": "Q2", "title": "Build", "detail": "MVP"},
                {"date": "Q3", "title": "Scale", "detail": "GTM"},
            ],
        })
        names = [op.get("props", {}).get("name") for op in ops]
        self.assertIn("StoryTlTitle", names)
        self.assertIn("StoryEra", names)
        self.assertTrue(any(n and n.startswith("StoryDot") for n in names))

    def test_funnel_and_pyramid_widths(self) -> None:
        fops = recipe_funnel_stages(self.linear, {
            "stages": [
                {"label": "Top", "value": "100"},
                {"label": "Mid", "value": "40"},
                {"label": "Bot", "value": "10"},
            ],
        })
        bands = [
            op for op in fops
            if str(op.get("props", {}).get("name", "")).startswith("FunnelBand")
        ]
        self.assertEqual(len(bands), 3)
        widths = [float(op["props"]["width"].replace("cm", "")) for op in bands]
        self.assertGreater(widths[0], widths[-1])

        pops = recipe_pyramid_levels(self.linear, {
            "levels": [{"label": "A"}, {"label": "B"}, {"label": "C"}, {"label": "D"}],
        })
        pbands = [
            op for op in pops
            if str(op.get("props", {}).get("name", "")).startswith("PyramidBand")
        ]
        self.assertEqual(len(pbands), 4)
        pwidths = [float(op["props"]["width"].replace("cm", "")) for op in pbands]
        self.assertLess(pwidths[0], pwidths[-1])

    def test_roadmap_scorecard_callout(self) -> None:
        rops = recipe_roadmap_swimlane(self.tokens, None)
        self.assertTrue(any(
            str(op.get("props", {}).get("name", "")).startswith("RoadCell")
            for op in rops
        ))
        sops = recipe_vs_scorecard(self.tokens, {
            "left": {"title": "Build"},
            "right": {"title": "Buy"},
            "criteria": [
                {"name": "Cost", "left": "High", "right": "Med"},
                {"name": "Control", "left": "High", "right": "Low"},
            ],
        })
        self.assertIn("VsTitle", [op.get("props", {}).get("name") for op in sops])
        cops = recipe_chart_callout_panel(self.tokens, {
            "callouts": ["One", "Two", "Three"],
        })
        self.assertTrue(any(op.get("type") == "chart" for op in cops))
        qops = recipe_quadrant_matrix_rich(self.tokens, None)
        self.assertIn("RichMatrixTitle", [op.get("props", {}).get("name") for op in qops])


if __name__ == "__main__":
    unittest.main()
