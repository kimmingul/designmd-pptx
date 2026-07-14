"""v2 design-token schema suite (issue #11): composition / charts / tables /
images / master parsing, defaulting, and validation."""

from __future__ import annotations

import unittest
from pathlib import Path

from designmd_pptx import tokens as T
from designmd_pptx.compile import compile_design_md
from designmd_pptx.validate import validate_tokens_against_schema_file

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

try:
    import jsonschema  # noqa: F401
    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False


class CompileV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.t = compile_design_md(FIXTURES / "v2-tokens.DESIGN.md")

    def test_composition(self) -> None:
        self.assertEqual(self.t["composition"],
                         {"whitespace_density": "spacious", "title_placement": "left"})

    def test_charts_series_drop_invalid(self) -> None:
        self.assertEqual(self.t["charts"]["default_style"], "minimal")
        # "bogus" dropped; the three valid hexes kept, uppercased
        self.assertEqual(self.t["charts"]["series_colors"],
                         ["3B82F6", "10B981", "EF4444"])
        self.assertTrue(any("series_colors" in w for w in self.t["warnings"]))

    def test_tables_and_images_and_master(self) -> None:
        self.assertEqual(self.t["tables"],
                         {"header_style": "underline", "cell_padding_cm": 0.25,
                          "stripe": False})
        self.assertEqual(self.t["images"],
                         {"crop_mode": "fit", "placement": "right"})
        self.assertEqual(self.t["master"],
                         {"footer": "Confidential — V2 Demo",
                          "page_number": True, "navigation": False})

    def test_tokens_validate(self) -> None:
        self.assertEqual(validate_tokens_against_schema_file(self.t), [])


class ExtractV2Unit(unittest.TestCase):
    PALETTE = {"accent": "1111AA", "chart_series2": "22AA22", "background": "FFFFFF"}

    def test_defaults_when_absent(self) -> None:
        sect, warns = T.extract_design_v2({}, self.PALETTE)
        self.assertEqual(sect["composition"]["whitespace_density"], "comfortable")
        self.assertEqual(sect["tables"]["stripe"], True)
        self.assertEqual(sect["master"]["footer"], None)
        # series derived from the palette when none given
        self.assertEqual(sect["charts"]["series_colors"], ["1111AA", "22AA22"])

    def test_bad_enum_falls_back_with_warning(self) -> None:
        sect, warns = T.extract_design_v2(
            {"composition": {"whitespace_density": "huge"}}, self.PALETTE)
        self.assertEqual(sect["composition"]["whitespace_density"], "comfortable")
        self.assertTrue(any("whitespace_density" in w for w in warns))

    def test_bool_and_float_coercion(self) -> None:
        sect, _ = T.extract_design_v2(
            {"tables": {"stripe": "no", "cell_padding_cm": "0.3"},
             "master": {"page_number": "yes"}}, self.PALETTE)
        self.assertIs(sect["tables"]["stripe"], False)
        self.assertEqual(sect["tables"]["cell_padding_cm"], 0.3)
        self.assertIs(sect["master"]["page_number"], True)

    def test_cell_padding_clamped(self) -> None:
        sect, warns = T.extract_design_v2(
            {"tables": {"cell_padding_cm": 5}}, self.PALETTE)
        self.assertEqual(sect["tables"]["cell_padding_cm"], 1.0)
        self.assertTrue(any("cell_padding_cm" in w for w in warns))


@unittest.skipUnless(_HAS_JSONSCHEMA, "jsonschema not installed")
class SchemaEnforcesV2(unittest.TestCase):
    def _valid_tokens(self):
        return compile_design_md(FIXTURES / "linear.DESIGN.md")

    def test_invalid_enum_is_rejected(self) -> None:
        t = self._valid_tokens()
        t["composition"]["whitespace_density"] = "gigantic"
        errors = validate_tokens_against_schema_file(t)
        self.assertTrue(errors, "schema should reject an out-of-enum value")

    def test_bad_series_hex_rejected(self) -> None:
        t = self._valid_tokens()
        t["charts"]["series_colors"] = ["ZZZZZZ"]
        self.assertTrue(validate_tokens_against_schema_file(t))


if __name__ == "__main__":
    unittest.main()
