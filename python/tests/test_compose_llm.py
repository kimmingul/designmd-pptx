"""Phase 3 / #18 — opt-in compose planner (offline + plan file + validation)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from designmd_pptx.compose import compose_outline
from designmd_pptx.compose_llm import (
    apply_plan,
    offline_narrative_plan,
    plan_compose,
)
from designmd_pptx.recipes import RECIPE_BUILDERS

BRIEF = """# Q3 Strategy Review

Narrative for leadership

## Agenda

- Context
- Metrics
- Options
- Recommendation
- Next steps

## Operating pulse

- 84.2 — ARR
- 118% — NRR
- 1.4 — CAC payback
- 42 — NPS

## How we ship

1. Brief
2. Design
3. Build
4. Ship

## Quote

> "Speed is the strategy"

— CEO

## Ask

Approve the plan.

CTA: Approve
"""


class ComposeLlm18(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.brief = self.root / "brief.md"
        self.brief.write_text(BRIEF, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_default_compose_has_no_planner(self) -> None:
        out = self.root / "base"
        report = compose_outline(self.brief, out)
        self.assertNotIn("planner", report)
        deck = json.loads((out / "content.deck.json").read_text(encoding="utf-8"))
        self.assertEqual(deck["slides"][0]["recipe"], "cover")
        self.assertTrue((out / "compose.report.json").exists())

    def test_offline_llm_flag_adds_narrative(self) -> None:
        out = self.root / "llm"
        report = compose_outline(
            self.brief, out, llm=True, style="Apple Keynote storytelling"
        )
        self.assertIn("planner", report)
        planner = report["planner"]
        self.assertTrue(planner.get("accepted") or planner.get("errors") == [])
        self.assertEqual(planner.get("provider"), "offline_narrative")
        self.assertIn("narrative", planner)
        self.assertIn("pacing", planner)
        # confidence model marked heuristic
        self.assertEqual(
            report["slides"][0].get("confidence_model"), "heuristic+rules"
        )
        roles = [n["role"] for n in planner["narrative"]]
        self.assertEqual(roles[0], "introduction")
        self.assertEqual(roles[-1], "conclusion")

    def test_style_can_upgrade_kpi_row_to_dashboard(self) -> None:
        out = self.root / "style"
        report = compose_outline(self.brief, out, llm=True, style="data dashboard consulting")
        deck = json.loads((out / "content.deck.json").read_text(encoding="utf-8"))
        recipes = [s["recipe"] for s in deck["slides"]]
        # 4 KPIs + consulting/data style → dashboard when offline planner fires
        self.assertTrue(
            "kpi_dashboard_grid" in recipes or "kpi_row" in recipes
        )
        if report["planner"].get("accepted") and report["planner"].get("plan_ops", 0) > 0:
            # When ops applied, prefer dashboard for this brief
            self.assertIn("kpi_dashboard_grid", recipes)

    def test_plan_file_validated_and_applied(self) -> None:
        base_out = self.root / "for-plan"
        base_report = compose_outline(self.brief, base_out)
        base_deck = json.loads((base_out / "content.deck.json").read_text(encoding="utf-8"))
        # Force first content slide after cover to quote via plan
        plan = {
            "version": 1,
            "source": "test",
            "ops": [
                {
                    "op": "set_recipe",
                    "index": 1,
                    "recipe": "section_opener_numbered",
                    "content": {"number": "01", "title": "Opening", "blurb": "Hi"},
                }
            ],
        }
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        out = self.root / "planned"
        report = compose_outline(self.brief, out, plan=plan_path)
        self.assertTrue(report["planner"]["accepted"])
        deck = json.loads((out / "content.deck.json").read_text(encoding="utf-8"))
        self.assertEqual(deck["slides"][1]["recipe"], "section_opener_numbered")
        # base path unchanged
        self.assertNotEqual(
            base_deck["slides"][1]["recipe"],
            deck["slides"][1]["recipe"],
        )
        self.assertIsNone(base_report.get("planner"))

    def test_invalid_plan_recipe_rejected(self) -> None:
        base = {
            "version": "1.1",
            "slides": [
                {"id": "c", "recipe": "cover", "content": {"title": "T"}},
                {"id": "b", "recipe": "bullets", "content": {"title": "B", "bullets": ["a"]}},
            ],
        }
        deck, rep = apply_plan(
            base,
            {"ops": [{"op": "set_recipe", "index": 1, "recipe": "not_a_real_recipe"}]},
        )
        self.assertFalse(rep["accepted"])
        self.assertEqual(deck["slides"][1]["recipe"], "bullets")
        self.assertTrue(any("unknown recipe" in e for e in rep["errors"]))

    def test_subprocess_fallback_on_bad_cmd(self) -> None:
        base = {
            "version": "1.1",
            "slides": [
                {"recipe": "cover", "content": {"title": "T"}},
                {"recipe": "close", "content": {"title": "Done"}},
            ],
        }
        deck, rep = plan_compose(
            base, style="keynote", use_subprocess=True, llm_cmd="false"
        )
        self.assertEqual(rep["provider"], "offline_narrative_fallback")
        self.assertTrue(rep.get("warnings"))
        self.assertEqual(deck["slides"][0]["recipe"], "cover")

    def test_offline_plan_only_uses_known_recipes(self) -> None:
        base_out = self.root / "known"
        compose_outline(self.brief, base_out)
        base = json.loads((base_out / "content.deck.json").read_text(encoding="utf-8"))
        plan = offline_narrative_plan(base, style="medical academic")
        for op in plan.get("ops") or []:
            if op.get("recipe"):
                self.assertIn(op["recipe"], RECIPE_BUILDERS)


if __name__ == "__main__":
    unittest.main()
