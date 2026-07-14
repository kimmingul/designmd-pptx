"""Accessibility suite (issue #39) — contrast, reading order, alt/notes."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from designmd_pptx import a11y
from designmd_pptx.__main__ import main
from designmd_pptx.compile import compile_design_md

PKG = Path(__file__).resolve().parent.parent / "designmd_pptx"
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class ContrastV39(unittest.TestCase):
    def test_known_ratio_black_on_white(self) -> None:
        r = a11y.contrast_ratio("000000", "FFFFFF")
        self.assertGreater(r, 20.0)
        self.assertLessEqual(r, 21.01)

    def test_gray_on_white_fails_aa(self) -> None:
        r = a11y.contrast_ratio("AAAAAA", "FFFFFF")
        self.assertLess(r, a11y.WCAG_AA_NORMAL)

    def test_check_token_contrast_flags_bad_pair(self) -> None:
        tokens = {
            "colors": {
                "text": "AAAAAA",
                "background": "FFFFFF",
                "content_background": "FFFFFF",
                "surface": "FFFFFF",
                "muted": "CCCCCC",
                "on_accent": "FFFFFF",
                "accent": "2563EB",
            }
        }
        findings = a11y.check_token_contrast(tokens)
        codes = {f.code for f in findings}
        self.assertIn("a11y.contrast.fail", codes)
        self.assertTrue(any(f.severity == "error" for f in findings))

    def test_auto_correct_makes_pairs_pass(self) -> None:
        tokens = {
            "colors": {
                "text": "AAAAAA",
                "background": "FFFFFF",
                "content_background": "FFFFFF",
                "surface": "FFFFFF",
                "muted": "DDDDDD",
                "on_accent": "EEEEEE",
                "accent": "111111",
            }
        }
        fixed, notes = a11y.auto_correct_contrast(tokens)
        self.assertTrue(notes)
        findings = a11y.check_token_contrast(fixed)
        self.assertFalse(
            [f for f in findings if f.code == "a11y.contrast.fail"],
            msg=findings,
        )


class ReadingOrderV39(unittest.TestCase):
    def test_title_before_body_before_notes(self) -> None:
        slide = {
            "id": "s1",
            "recipe": "bullets",
            "content": {
                "title": "Agenda",
                "bullets": ["One", "Two"],
                "notes": "Walk the list",
            },
        }
        order = a11y.reading_order_for_slide(slide)
        roles = [n["role"] for n in order]
        self.assertEqual(roles[0], "title")
        self.assertIn("bullets[0]", roles)
        self.assertEqual(roles[-1], "notes")
        self.assertEqual([n["reading_index"] for n in order], list(range(len(order))))

    def test_coordinate_sort_top_then_left(self) -> None:
        slide = {
            "id": "s2",
            "recipe": "feature_cards",
            "content": {
                "title": "Cards",
                "items": [
                    {"title": "B", "y": 3, "x": 2},
                    {"title": "A", "y": 1, "x": 5},
                    {"title": "C", "y": 3, "x": 0},
                ],
            },
        }
        order = a11y.reading_order_for_slide(slide)
        texts = [n["text"] for n in order if n["role"].startswith("items")]
        self.assertEqual(texts, ["A", "C", "B"])


class AltNotesV39(unittest.TestCase):
    def test_missing_alt_is_error(self) -> None:
        deck = {
            "slides": [{
                "id": "img",
                "recipe": "image_full",
                "content": {"title": "X", "src": "a.png", "alt": ""},
            }]
        }
        findings = a11y.check_alt_and_notes(deck)
        self.assertTrue(any(f.code == "a11y.alt.missing" and f.severity == "error"
                            for f in findings))

    def test_generate_missing_clears_alt_error(self) -> None:
        deck = {
            "slides": [{
                "id": "img",
                "recipe": "image_full",
                "content": {"title": "Hero", "src": "a.png", "alt": ""},
            }]
        }
        fixed, changes = a11y.ensure_notes_and_alt(deck)
        self.assertTrue(changes)
        self.assertTrue(fixed["slides"][0]["content"]["alt"])
        findings = a11y.check_alt_and_notes(fixed)
        self.assertFalse([f for f in findings if f.code == "a11y.alt.missing"])


class AuditCliV39(unittest.TestCase):
    def test_audit_fails_before_clean_on_bad_contrast(self) -> None:
        tokens = compile_design_md(PKG / "default.DESIGN.md")
        tokens = json.loads(json.dumps(tokens))
        tokens["colors"]["text"] = "BBBBBB"
        tokens["colors"]["background"] = "FFFFFF"
        report = a11y.audit(tokens=tokens)
        self.assertFalse(report.ok)
        self.assertGreater(report.errors, 0)

    def test_audit_ok_after_fix(self) -> None:
        tokens = {
            "colors": {
                "text": "BBBBBB",
                "background": "FFFFFF",
                "content_background": "FFFFFF",
                "surface": "F5F5F5",
                "muted": "EEEEEE",
                "on_accent": "FFFFFF",
                "accent": "000000",
            }
        }
        deck = {
            "slides": [{
                "id": "img",
                "recipe": "image_full",
                "content": {"title": "T", "src": "x.png", "alt": ""},
            }]
        }
        report = a11y.audit(
            tokens=tokens, deck=deck, auto_correct=True, generate_missing=True,
        )
        self.assertTrue(report.ok, msg=report.findings)
        self.assertIsNotNone(report.corrected)

    def test_cli_writes_report_and_exit_code(self) -> None:
        tokens = compile_design_md(PKG / "default.DESIGN.md")
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            tp = tdir / "tokens.json"
            # force a fail
            bad = json.loads(json.dumps(tokens))
            bad["colors"]["text"] = "CCCCCC"
            bad["colors"]["background"] = "FFFFFF"
            tp.write_text(json.dumps(bad), encoding="utf-8")
            out = tdir / "a11y.report.json"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["a11y", "--tokens", str(tp), "-o", str(out)])
            self.assertEqual(rc, 1)
            self.assertTrue(out.is_file())
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse(data["ok"])
            self.assertGreater(data["errors"], 0)
            self.assertIn("FAIL", buf.getvalue())

    def test_cli_default_design_example_can_pass_with_generate(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main([
                "a11y",
                "--design", "default",
                "--content", str(EXAMPLES / "content.deck.json"),
                "--generate-missing",
                "--show-order",
            ])
        # example deck has no src-without-alt; contrast should pass house style
        self.assertEqual(rc, 0, msg=buf.getvalue())
        self.assertIn("PASS", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
