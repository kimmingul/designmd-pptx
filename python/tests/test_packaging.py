"""Packaging invariants (issue #33).

The package must be self-contained so an installed wheel works with no
PYTHONPATH: the schemas, the OfficeCLI compatibility manifest, and the default
house style all ship *inside* designmd_pptx/. These run in the normal suite
(cross-OS in CI); the wheel build + clean-venv install is the CI `package` job."""

from __future__ import annotations

import pathlib
import unittest

import designmd_pptx

PKG = pathlib.Path(designmd_pptx.__file__).resolve().parent


class PackagingV33(unittest.TestCase):
    def test_data_files_ship_inside_package(self) -> None:
        for rel in ("compatibility.json", "benchmark_thresholds.json",
                    "default.DESIGN.md",
                    "schema/tokens.slide.schema.json",
                    "schema/content.overlay.schema.json"):
            self.assertTrue((PKG / rel).is_file(), f"{rel} missing from package")

    def test_schema_path_is_package_local(self) -> None:
        # If SCHEMA_PATH escaped the package (the old python/schema/ layout) it
        # would not ship in the wheel and jsonschema validation would break.
        from designmd_pptx.validate import SCHEMA_PATH
        self.assertTrue(SCHEMA_PATH.is_file())
        self.assertEqual(SCHEMA_PATH.resolve().parent.parent, PKG)

    def test_console_entry_point_is_callable(self) -> None:
        from designmd_pptx.__main__ import main
        self.assertTrue(callable(main))

    def test_version_is_a_real_string(self) -> None:
        # pyproject reads this attr dynamically — keep it a plain version literal.
        self.assertRegex(designmd_pptx.__version__, r"^\d+\.\d+")


if __name__ == "__main__":
    unittest.main()
