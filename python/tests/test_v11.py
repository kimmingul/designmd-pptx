"""v1.1 regression suite — drives shipped modules (no fakes of the unit under test)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from designmd_pptx import __version__  # noqa: E402
from designmd_pptx.colors_parse import (  # noqa: E402
    collect_css_vars,
    parse_css_color,
    parse_gradient,
)
from designmd_pptx.compile import COMPILER_VERSION, compile_design_md  # noqa: E402
from designmd_pptx.deck import generate_deck  # noqa: E402
from designmd_pptx.recipes import recipe_image_text_2col, recipe_process  # noqa: E402
from designmd_pptx import apply as apply_mod  # noqa: E402


class Version(unittest.TestCase):
    def test_package_and_compiler_1_1(self):
        self.assertTrue(__version__.startswith("1.2"))
        self.assertTrue(COMPILER_VERSION.startswith("1.2"))


class ColorV11(unittest.TestCase):
    def test_var_without_fallback_resolves(self):
        vmap = {"--brand": "#0B5FFF"}
        diag: list[str] = []
        hx = parse_css_color("var(--brand)", var_map=vmap, diagnostics=diag)
        self.assertEqual(hx, "0B5FFF")

    def test_var_unresolved_without_fallback_is_none(self):
        diag: list[str] = []
        hx = parse_css_color("var(--missing)", var_map={}, diagnostics=diag)
        self.assertIsNone(hx)
        self.assertTrue(any("unresolved" in d for d in diag))

    def test_var_with_fallback(self):
        hx = parse_css_color("var(--missing, #112233)", var_map={})
        self.assertEqual(hx, "112233")

    def test_oklch_converts(self):
        diag: list[str] = []
        hx = parse_css_color("oklch(0.65 0.18 250)", diagnostics=diag)
        self.assertIsNotNone(hx)
        self.assertEqual(len(hx), 6)
        self.assertTrue(any("oklch" in d for d in diag))

    def test_color_mix(self):
        hx = parse_css_color("color-mix(in srgb, #000000 50%, #FFFFFF 50%)")
        self.assertIsNotNone(hx)
        # mid gray-ish
        self.assertTrue(hx[0:2] in ("7F", "80", "7E", "81"))

    def test_collect_vars_from_body(self):
        body = ":root { --extra-muted: #9AA0A6; }"
        m = collect_css_vars({"--brand": "#00FF00"}, body)
        self.assertIn("--brand", m)
        self.assertIn("--extra-muted", m)
        self.assertEqual(m["--extra-muted"].strip().upper().lstrip("#"), "9AA0A6")

    def test_gradient_multi_stop_warns(self):
        diag: list[str] = []
        g = parse_gradient(
            "linear-gradient(90deg, #111111, #555555, #FFFFFF)",
            diagnostics=diag,
        )
        self.assertEqual(g, "111111-FFFFFF-90")
        self.assertTrue(any("multi-stop" in d for d in diag))

    def test_radial_explicit_fail(self):
        diag: list[str] = []
        g = parse_gradient("radial-gradient(circle, #000, #fff)", diagnostics=diag)
        self.assertIsNone(g)
        self.assertTrue(any("radial" in d for d in diag))


class CompileVarFixture(unittest.TestCase):
    def test_var_oklch_fixture(self):
        path = ROOT / "fixtures" / "var-oklch.DESIGN.md"
        tokens = compile_design_md(path, brand="VarOKLCH")
        self.assertTrue(tokens["compiler"]["version"].startswith("1.2"))
        self.assertEqual(tokens["colors"]["accent"], "0B5FFF")
        self.assertTrue(tokens["dark_first"])
        self.assertIn("image_text_2col", tokens["patterns"])


class ProcessConnectors(unittest.TestCase):
    def _tokens(self):
        return compile_design_md(ROOT / "fixtures" / "linear.DESIGN.md", brand="Linear")

    def test_process_emits_connector_ops_with_slide_index(self):
        ops = recipe_process(
            self._tokens(),
            {"title": "Flow", "steps": ["A", "B", "C"]},
            slide_index=3,
        )
        connectors = [o for o in ops if o.get("type") == "connector"]
        self.assertEqual(len(connectors), 2)
        for c in connectors:
            self.assertIn("/slide[3]/shape[@name=", c["props"]["from"])
            self.assertIn("tailEnd", c["props"])
            self.assertEqual(c["props"]["tailEnd"], "triangle")

    def test_deck_process_has_connectors(self):
        tokens = self._tokens()
        deck = {
            "version": "1.1",
            "slides": [
                {"recipe": "cover", "content": {"title": "T"}},
                {
                    "recipe": "process",
                    "content": {"title": "P", "steps": ["A", "B", "C"]},
                },
            ],
        }
        ops, _, _ = generate_deck(tokens, deck, strict=True)
        connectors = [o for o in ops if o.get("type") == "connector"]
        self.assertGreaterEqual(len(connectors), 2)
        # second slide → index 2
        self.assertTrue(any("/slide[2]/" in o["props"]["from"] for o in connectors))


class ImageText2Col(unittest.TestCase):
    def test_recipe_exists_and_layout(self):
        tokens = compile_design_md(ROOT / "fixtures" / "linear.DESIGN.md")
        ops = recipe_image_text_2col(
            tokens,
            {
                "title": "Side by side",
                "body": "Explain here.",
                "image_side": "right",
            },
        )
        self.assertEqual(ops[0]["type"], "slide")
        names = [o["props"].get("name") for o in ops if o.get("type") == "shape"]
        self.assertIn("It2Title", names)
        self.assertIn("It2Placeholder", names)

    def test_alt_required_when_src(self):
        tokens = compile_design_md(ROOT / "fixtures" / "linear.DESIGN.md")
        deck = {
            "slides": [
                {
                    "recipe": "image_text_2col",
                    "content": {"title": "X", "body": "Y", "src": "x.png"},
                }
            ]
        }
        with self.assertRaises(ValueError):
            generate_deck(tokens, deck, strict=True)


class ApplyScripts(unittest.TestCase):
    def test_scaffold_apply_ps1_is_thin_wrapper(self):
        """Generated apply.ps1 must not delete destination before validate."""
        import tempfile
        from designmd_pptx.__main__ import main

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "brand"
            rc = main(
                [
                    "scaffold",
                    str(ROOT / "fixtures" / "linear.DESIGN.md"),
                    "-o",
                    str(out),
                    "--content",
                    str(ROOT / "examples" / "content.deck.json"),
                    "--brand",
                    "T",
                ]
            )
            self.assertEqual(rc, 0)
            ps1 = (out / "apply.ps1").read_text(encoding="utf-8")
            self.assertIn("designmd_pptx apply", ps1)
            self.assertNotIn("Remove-Item", ps1)
            self.assertNotIn("officecli create", ps1)
            sh = (out / "apply.sh").read_text(encoding="utf-8")
            self.assertIn("designmd_pptx apply", sh)
            self.assertNotIn("rm -f", sh)


class ApplyStaging(unittest.TestCase):
    def test_refuse_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            pptx = td_path / "deck.pptx"
            pptx.write_bytes(b"existing")
            seq = td_path / "deck.sequence.json"
            seq.write_text("[]", encoding="utf-8")
            with mock.patch.object(apply_mod, "find_officecli", return_value="officecli"):
                with self.assertRaises(FileExistsError):
                    apply_mod.apply_sequence(pptx, seq, create=True, force=False)
            # destination must remain
            self.assertTrue(pptx.exists())
            self.assertEqual(pptx.read_bytes(), b"existing")

    def test_staging_replace_on_success(self):
        calls: list[list[str]] = []

        def fake_run(exe, args, input_text=None):
            calls.append(list(args))
            # Simulate success for all
            class R:
                returncode = 0
                stdout = "Found 0 issue(s):\n"
                stderr = ""

            if args and args[0] == "view":
                R.stdout = "Found 0 issue(s):\n"
            return R()

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            pptx = td_path / "out.pptx"
            pptx.write_bytes(b"OLD")
            seq = td_path / "deck.sequence.json"
            seq.write_text("[]", encoding="utf-8")
            with mock.patch.object(apply_mod, "find_officecli", return_value="officecli"):
                with mock.patch.object(apply_mod, "_run", side_effect=fake_run):
                    # create=True force=True will stage then replace
                    # But create writes staging via officecli create — we need
                    # to create staging file when create is called
                    real_run = fake_run

                    def run_create_file(exe, args, input_text=None):
                        if args and args[0] == "create":
                            Path(args[1]).write_bytes(b"NEW")
                        return real_run(exe, args, input_text)

                    with mock.patch.object(apply_mod, "_run", side_effect=run_create_file):
                        apply_mod.apply_sequence(
                            pptx, seq, create=True, force=True, require_clean_issues=True
                        )
            self.assertTrue(pptx.exists())
            self.assertEqual(pptx.read_bytes(), b"NEW")


if __name__ == "__main__":
    unittest.main()
