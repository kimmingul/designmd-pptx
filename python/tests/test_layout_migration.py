"""Layout-migration regression suite (issue #9).

Guards the specific bugs the codex adversarial review of the matrix_2x2 / kpi_row
engine migrations surfaced: a 1-item KPI crash and a matrix grid/axis overlap."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.recipes import recipe_kpi_row, recipe_matrix_2x2

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _cm(v):
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)cm", str(v).strip())
    return float(m.group(1)) if m else None


def _rects(ops, name_pred):
    for o in ops:
        p = o.get("props", {})
        if name_pred(p.get("name", "")):
            x, y, w, h = (_cm(p.get(k)) for k in ("x", "y", "width", "height"))
            if None not in (x, y, w, h):
                yield p["name"], x, y, w, h


def _overlap(a, b) -> bool:
    _, ax, ay, aw, ah = a
    _, bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


class MigrationRegressionV9(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.t = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def test_kpi_row_single_item_does_not_crash(self) -> None:
        # range(n) with n>=2 indexed past a 1-item list — regression from #9.
        ops = recipe_kpi_row(self.t, {"kpis": [{"value": "42", "label": "Solo", "chip": ""}]})
        cards = [o for o in ops if o.get("props", {}).get("name", "").endswith("Value")]
        self.assertEqual(len(cards), 1)

    def test_kpi_row_item_count_matches_input(self) -> None:
        for k in (2, 3, 4):
            ops = recipe_kpi_row(self.t, {"kpis": [{"value": str(i)} for i in range(k)]})
            cards = [o for o in ops if o.get("props", {}).get("name", "").endswith("Value")]
            self.assertEqual(len(cards), k)

    def test_matrix_axis_labels_do_not_overlap_quadrants(self) -> None:
        ops = recipe_matrix_2x2(self.t, {
            "quadrants": [{"title": f"Q{i}", "body": "body"} for i in range(4)],
            "axes": {"x": "Market share", "y": "Market growth"}})
        axes = list(_rects(ops, lambda n: n in ("AxisX", "AxisY")))
        quads = list(_rects(ops, lambda n: n.endswith("Bg")))
        self.assertEqual(len(axes), 2)
        self.assertEqual(len(quads), 4)
        for ax in axes:
            for q in quads:
                self.assertFalse(_overlap(ax, q),
                                 f"{ax[0]} overlaps {q[0]}")


if __name__ == "__main__":
    unittest.main()
