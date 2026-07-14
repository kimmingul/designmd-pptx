"""Geometry-contract suite (issue #9).

Layout quality is asserted on the SOLVED geometry (the emitted add-ops), not on
screenshots, and across EVERY registered pattern: shapes stay on-canvas, text
stays readable, output is deterministic, and heavy content degrades gracefully
(either a bounded layout or a clean typed LayoutOverflow — never a crash or
silent drop). This locks quality for the migrated engine patterns and guards the
fixed ones against regression as more patterns move onto the engine."""

from __future__ import annotations

import re
import unittest

from designmd_pptx import layout as L
from designmd_pptx.compile import compile_design_md
from designmd_pptx.recipes import PATTERN_LAYOUT, RECIPE_BUILDERS, _call_builder
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
TOL = 0.3          # cm tolerance for full-bleed / rounding
READABLE_PT = 10   # nothing smaller than a caption

# One over-stuffed content blob; each builder reads only the keys it needs, so
# this simultaneously stresses every list-driven pattern.
HEAVY = {
    "title": "Heavy " * 8, "subtitle": "Subtitle " * 8, "blurb": "Blurb " * 30,
    "number": "07", "meta": "meta " * 10,
    "bullets": ["A fairly long bullet point number " * 3] * 12,
    "cards": [{"title": "Card", "body": "Card body text " * 8}] * 8,
    "steps": [{"title": "Step", "body": "Step detail " * 6}] * 10,
    "kpis": [{"value": "42.1", "label": "Label " * 4, "chip": "+9%"}] * 8,
    # agenda_toc + any list that reads content["items"]
    "items": [
        {"number": f"{i:02d}", "label": "Agenda topic " * 4, "time": "10m"}
        for i in range(1, 14)
    ],
    "headers": ["Metric", "Q1", "Q2", "Q3"],
    "rows": [["Row label " * 2, "1", "2", "3"]] * 30,
    "columns": [{"title": "Column", "points": ["point " * 6] * 6}] * 2,
    "members": [{"name": "Given Family", "role": "Role title " * 2}] * 10,
    "tiers": [{"name": "Tier", "price": "$99", "features": ["feature " * 5] * 6}] * 4,
    "logos": ["Acme"] * 10,
    "quote": "A rather long pull quote that keeps going and going " * 6,
    "attribution": "Someone Notable, Title",
    "chart_type": "bar", "categories": "A,B,C,D", "series1_values": "4,8,15,16",
    # Shared blob: each builder reads only the keys it understands. Prefer
    # distinct keys (studies vs rows) so forest_plot is not starved by table rows.
    "stages": [
        {"label": "Stage " * 4, "value": "10%", "n": "N=99", "note": "note " * 6}
    ] * 10,
    "levels": [{"label": "Level", "detail": "Detail " * 4}] * 8,
    "phases": ["Now", "Next", "Later", "Future", "Horizon", "Extra"],
    "lanes": [{"name": "Lane", "cells": ["A", "B", "C", "D"]}] * 8,
    "criteria": [{"name": "Crit", "left": "High", "right": "Low"}] * 12,
    "callouts": ["Callout line " * 8] * 6,
    "era": "2024–2026",
    "left": {"title": "Option A"}, "right": {"title": "Option B"},
    "arms": [{"label": "Arm", "detail": "Detail " * 4}] * 6,
    "panels": [{"label": "X", "caption": "Caption " * 6, "src": "", "alt": "a"}] * 6,
    "studies": [
        {
            "label": "Study",
            "effect": 0.1,
            "low": -0.5,
            "high": 0.6,
            "text": "1.1 (0.6–1.6)",
        }
    ] * 12,
    "risk_table": [["0", "100", "100"]] * 10,
    "insight": "Insight text " * 20,
    "insight_body": "Insight body " * 20,
    "domain": [-2.0, 2.0],
    # Wave 1 keys (builders ignore unknowns)
    "hub": "Loop", "center": "Core",
    "sets": [{"label": "A"}, {"label": "B"}, {"label": "C"}],
    "intersection": "Shared " * 4,
    "strengths": ["S1", "S2"], "weaknesses": ["W1"],
    "opportunities": ["O1"], "threats": ["T1"],
    "tasks": [{"name": "Task " * 3, "start": 0, "end": 2}] * 10,
    "root": {"name": "Lead", "role": "CEO"},
    "reports": [{"name": "R", "role": "Role"}] * 6,
    "name": "Persona Name", "role": "Buyer role",
    "attrs": ["Attr " * 4] * 8,
    "effect": "Outcome",
    "causes": [{"label": "Bone", "items": ["item"]}] * 8,
    "above": [{"label": "Events", "detail": "seen"}],
    "below": [{"label": "Structure", "detail": "hidden"}] * 4,
    "framework": "ADKAR",
    "blocks": [{"label": f"B{i}", "body": "x"} for i in range(9)],
    # Wave 2
    "stats": [{"value": "1", "label": "L", "icon": "A"}] * 8,
    "points": ["1", "2", "3", "4", "5", "6", "7"],
    "selected": "4",
    "spokes": [{"label": "S"}] * 8,
    "before": {"title": "Before", "body": "x " * 20},
    "after": {"title": "After", "body": "y " * 20},
    "cells": [1, 2, 3, 0] * 12,
    "customer": "Acme",
    "objective": "Objective " * 6,
    "key_results": [{"label": "KR", "detail": "d"}] * 6,
    "projects": [{"name": "P", "status": "red", "note": "n"}] * 12,
    "device": "phone",
}


def _cm(v: str):
    if not isinstance(v, str):
        return None
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)cm", v.strip())
    return float(m.group(1)) if m else None


def _iter_geometry(ops):
    for op in ops:
        p = op.get("props", {})
        x, y, w, h = (_cm(p.get(k)) for k in ("x", "y", "width", "height"))
        if None in (x, y, w, h):
            continue
        yield op, p, x, y, w, h


class GeometryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def _ops(self, name, content):
        idx = 1 if name == "process" else None
        return _call_builder(RECIPE_BUILDERS[name], self.tokens, content, idx)

    def test_every_pattern_registered(self) -> None:
        # Phase 2: premium (#58) + domain (#10) catalogs.
        self.assertGreaterEqual(len(RECIPE_BUILDERS), 60)
        for name in (
            "kpi_dashboard_grid", "agenda_toc", "section_opener_numbered",
            "story_timeline", "funnel_stages", "roadmap_swimlane",
            "quadrant_matrix_rich", "pyramid_levels", "vs_scorecard",
            "chart_callout_panel",
            "consort_flow", "kaplan_meier", "forest_plot",
            "study_design", "results_table_insight", "multi_panel_figure",
        ):
            self.assertIn(name, RECIPE_BUILDERS)

    def test_pattern_layout_covers_registry(self) -> None:
        # every pattern is categorized exactly once (engine/structured/fixed),
        # so adding a pattern forces a deliberate layout-strategy choice.
        buckets = list(PATTERN_LAYOUT.values())
        flat = [p for bucket in buckets for p in bucket]
        self.assertEqual(len(flat), len(set(flat)), "a pattern is in two buckets")
        self.assertEqual(set(flat), set(RECIPE_BUILDERS),
                         "PATTERN_LAYOUT and RECIPE_BUILDERS disagree")
        # Phase 2: hybrid is first-class (timeline dots, forest bars, …).
        self.assertIn("hybrid", PATTERN_LAYOUT)
        self.assertGreaterEqual(len(PATTERN_LAYOUT["engine"]), 8)
        self.assertGreaterEqual(len(PATTERN_LAYOUT["hybrid"]), 4)

    def test_default_content_is_on_canvas_and_readable(self) -> None:
        for name in RECIPE_BUILDERS:
            with self.subTest(pattern=name):
                ops = self._ops(name, None)
                self.assertTrue(ops and ops[0]["type"] == "slide")
                for op, p, x, y, w, h in _iter_geometry(ops):
                    self.assertGreaterEqual(x, -TOL, f"{name}:{p.get('name')} x<0")
                    self.assertGreaterEqual(y, -TOL, f"{name}:{p.get('name')} y<0")
                    self.assertLessEqual(x + w, L.CANVAS_W + TOL,
                                         f"{name}:{p.get('name')} right edge off-canvas")
                    self.assertLessEqual(y + h, L.CANVAS_H + TOL,
                                         f"{name}:{p.get('name')} bottom edge off-canvas")
                    size = p.get("size")
                    if size and str(size).isdigit():
                        self.assertGreaterEqual(
                            int(size), READABLE_PT,
                            f"{name}:{p.get('name')} font {size}pt < {READABLE_PT}")

    def test_output_is_deterministic(self) -> None:
        for name in RECIPE_BUILDERS:
            with self.subTest(pattern=name):
                self.assertEqual(self._ops(name, None), self._ops(name, None))

    def test_heavy_content_degrades_gracefully(self) -> None:
        # Either a bounded layout or a clean typed LayoutOverflow — never another
        # exception, a crash, or silently-dropped content.
        for name in RECIPE_BUILDERS:
            with self.subTest(pattern=name):
                try:
                    ops = self._ops(name, dict(HEAVY))
                except L.LayoutOverflow as e:
                    self.assertIn(e.policy, (L.Overflow.SHORTEN, L.Overflow.PAGINATE,
                                             L.Overflow.FAIL))
                    continue
                for op, p, x, y, w, h in _iter_geometry(ops):
                    self.assertLessEqual(x + w, L.CANVAS_W + TOL,
                                         f"{name}:{p.get('name')} overflows under load")
                    self.assertLessEqual(y + h, L.CANVAS_H + TOL,
                                         f"{name}:{p.get('name')} overflows under load")


if __name__ == "__main__":
    unittest.main()
