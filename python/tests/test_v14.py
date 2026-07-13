"""v1.4 suite — doctor, bundled default DESIGN.md, Gate 3 screenshot flag."""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import tempfile
import unittest
from pathlib import Path

from designmd_pptx.__main__ import _resolve_design, build_parser, main
from designmd_pptx.apply import apply_sequence
from designmd_pptx.doctor import run_doctor

PKG = Path(__file__).resolve().parent.parent / "designmd_pptx"


class DoctorV14(unittest.TestCase):
    def test_run_doctor_reports_rows(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run_doctor()
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("officecli", out)
        self.assertIn("claude:", out)
        self.assertIn("codex:", out)
        self.assertIn("grok:", out)

    def test_doctor_cli_wired(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["doctor"])
        self.assertEqual(rc, 0)


class DefaultDesignV14(unittest.TestCase):
    def test_bundled_design_exists(self) -> None:
        self.assertTrue((PKG / "default.DESIGN.md").exists())

    def test_resolve_design_literal(self) -> None:
        self.assertEqual(_resolve_design("default"), PKG / "default.DESIGN.md")
        self.assertEqual(_resolve_design("DEFAULT"), PKG / "default.DESIGN.md")
        self.assertEqual(_resolve_design("brand.DESIGN.md"), Path("brand.DESIGN.md"))

    def test_compile_default_no_color_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "tokens.json"
            rc = main(["compile", "default", "-o", str(out)])
            self.assertEqual(rc, 0)
            tokens = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(tokens["brand"], "Default-House-Style")
            self.assertEqual(tokens["colors"]["accent"], "2563EB")
            self.assertEqual(tokens["colors"]["risk"], "DC2626")
            self.assertFalse([w for w in tokens.get("warnings", []) if "fallback" in w])


class ScreenshotFlagV14(unittest.TestCase):
    def test_apply_parser_accepts_screenshot(self) -> None:
        args = build_parser().parse_args(["apply", "a.pptx", "seq.json", "--screenshot"])
        self.assertTrue(args.screenshot)

    def test_scaffold_parser_accepts_screenshot(self) -> None:
        args = build_parser().parse_args(
            ["scaffold", "default", "-o", "out", "--apply", "--screenshot"]
        )
        self.assertTrue(args.screenshot)

    def test_apply_sequence_signature(self) -> None:
        self.assertIn("screenshot", inspect.signature(apply_sequence).parameters)


if __name__ == "__main__":
    unittest.main()
