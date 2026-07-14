"""Table auto-split suite (issue #17): appendix_table paginates instead of
silently truncating."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from designmd_pptx import layout as L
from designmd_pptx.compile import compile_design_md
from designmd_pptx.deck import generate_deck, validate_deck_content_caps
from designmd_pptx.recipes import APPENDIX_ROWS_PER_SLIDE, recipe_appendix_table

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _cm(v):
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)cm", str(v).strip())
    return float(m.group(1)) if m else None


class AppendixPaginationV17(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.t = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def _table(self, n_rows, cols=3):
        headers = [f"H{i}" for i in range(cols)]
        rows = [[f"r{r}c{c}" for c in range(cols)] for r in range(n_rows)]
        return {"title": "Data", "headers": headers, "rows": rows}

    def _slides(self, ops):
        return [o for o in ops if o["type"] == "slide"]

    def _cells(self, ops):
        return [o for o in ops if o.get("props", {}).get("name", "").startswith("ATd")]

    def _titles(self, ops):
        return [o["props"]["text"] for o in ops
                if o.get("props", {}).get("name") == "AppTitle"]

    def test_small_table_single_slide_untagged(self) -> None:
        ops = recipe_appendix_table(self.t, self._table(10))
        self.assertEqual(len(self._slides(ops)), 1)
        self.assertEqual(self._titles(ops), ["Data"])          # no (1/1) tag

    def test_boundary_14_then_15(self) -> None:
        self.assertEqual(len(self._slides(recipe_appendix_table(self.t, self._table(14)))), 1)
        self.assertEqual(len(self._slides(recipe_appendix_table(self.t, self._table(15)))), 2)

    def test_large_table_splits_and_keeps_every_row(self) -> None:
        ops = recipe_appendix_table(self.t, self._table(30, cols=3))
        self.assertEqual(len(self._slides(ops)), 3)            # 14 + 14 + 2
        self.assertEqual(len(self._cells(ops)), 30 * 3)        # nothing truncated
        titles = self._titles(ops)
        self.assertEqual(titles[0], "Data (1/3)")
        self.assertTrue(all("cont." in x for x in titles[1:]))

    def test_each_page_header_repeated_and_on_canvas(self) -> None:
        ops = recipe_appendix_table(self.t, self._table(30))
        headers = [o for o in ops if o.get("props", {}).get("name", "").startswith("ATh")]
        self.assertEqual(len(headers), 3 * 3)                  # header band per page
        for o in ops:
            p = o.get("props", {})
            y, h = _cm(p.get("y")), _cm(p.get("height"))
            if y is not None and h is not None:
                self.assertLessEqual(y + h, L.CANVAS_H + 0.3,
                                     f"{p.get('name')} off-canvas")

    def test_strict_deck_accepts_large_table(self) -> None:
        # Previously appendix_table rows > 14 was a hard rejection; now it paginates.
        deck = {"version": "1.0", "slides": [
            {"recipe": "appendix_table", "content": self._table(40)}]}
        ops, _d, _w = generate_deck(self.t, deck, strict=True)
        self.assertEqual(len([o for o in ops if o["type"] == "slide"]), 3)  # 14+14+12

    def test_header_cap_still_enforced(self) -> None:
        deck = {"version": "1.0", "slides": [
            {"recipe": "appendix_table",
             "content": {"headers": [f"H{i}" for i in range(9)], "rows": [["x"] * 9]}}]}
        errs = validate_deck_content_caps(deck)
        self.assertTrue(any("headers max 8" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
