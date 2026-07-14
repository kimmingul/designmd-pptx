"""Phase 5 / #19 — iterative visual refinement loop."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from designmd_pptx import refine
from designmd_pptx.__main__ import main


class ParseFeedback19(unittest.TestCase):
    def test_density_nl(self) -> None:
        f = refine.parse_nl_feedback("This slide is too dense, please add spacing")
        self.assertTrue(any(x["code"] == "density" for x in f))

    def test_korean_density(self) -> None:
        f = refine.parse_nl_feedback("이 슬라이드는 너무 빽빽해요. 여백을 늘려주세요")
        self.assertTrue(any(x["code"] == "density" for x in f))

    def test_shorten_nl(self) -> None:
        f = refine.parse_nl_feedback("please shorten the verbose body text")
        self.assertTrue(any(x["code"] == "overflow" for x in f))


class ApplyPatches19(unittest.TestCase):
    def test_split_long_bullets(self) -> None:
        deck = {
            "version": "1.1",
            "slides": [{
                "id": "s1",
                "recipe": "bullets",
                "content": {
                    "title": "Agenda",
                    "bullets": [f"Point {i}" for i in range(10)],
                },
            }],
        }
        findings = [{
            "code": "density",
            "severity": "error",
            "message": "too crowded",
            "slide": 1,
        }]
        out, log = refine.apply_patches(deck, findings, max_list_items=4)
        self.assertTrue(log)
        self.assertEqual(log[0]["action"], "split_list")
        self.assertEqual(len(out["slides"]), 2)
        self.assertEqual(len(out["slides"][0]["content"]["bullets"]), 4)
        self.assertEqual(len(out["slides"][1]["content"]["bullets"]), 6)
        self.assertIn("cont", out["slides"][1]["content"]["title"].lower())

    def test_split_does_not_corrupt_later_slides(self) -> None:
        """Adversarial #19: insert must not shift indices mid-pass."""
        deck = {
            "slides": [
                {
                    "id": "s1",
                    "recipe": "bullets",
                    "content": {"title": "A", "bullets": [f"a{i}" for i in range(8)]},
                },
                {
                    "id": "s2",
                    "recipe": "bullets",
                    "content": {"title": "B", "bullets": [f"b{i}" for i in range(8)]},
                },
            ],
        }
        findings = [{
            "code": "density",
            "severity": "error",
            "message": "crowded",
            "slide": None,  # all slides
        }]
        out, log = refine.apply_patches(deck, findings, max_list_items=4)
        ids = [s["id"] for s in out["slides"]]
        self.assertIn("s1", ids)
        self.assertIn("s2", ids)
        # Both originals split → 4 slides (s1, s1-cont, s2, s2-cont) order may vary
        self.assertEqual(len(out["slides"]), 4)
        s2 = next(s for s in out["slides"] if s["id"] == "s2")
        self.assertEqual(len(s2["content"]["bullets"]), 4)
        self.assertTrue(any(p["action"] == "split_list" for p in log))

    def test_shorten_body(self) -> None:
        long_body = "word " * 80
        deck = {
            "slides": [{
                "id": "s1",
                "recipe": "close",
                "content": {"title": "Ask", "body": long_body},
            }],
        }
        findings = [{
            "code": "overflow",
            "severity": "error",
            "message": "text overflow",
            "slide": 1,
        }]
        out, log = refine.apply_patches(deck, findings, max_body_chars=60)
        self.assertTrue(any(p["action"] == "shorten_text" for p in log))
        self.assertLess(len(out["slides"][0]["content"]["body"]), len(long_body))

    def test_vision_findings_drive_loop(self) -> None:
        deck = {
            "slides": [{
                "id": "s1",
                "recipe": "feature_cards",
                "content": {
                    "title": "Cards",
                    "cards": [{"title": f"C{i}", "body": "x"} for i in range(8)],
                },
            }],
        }
        result = refine.refine_loop(
            deck,
            findings=[{
                "code": "density",
                "severity": "error",
                "message": "dense cards",
                "slide": 1,
            }],
            rounds=2,
        )
        self.assertTrue(result["changed"])
        self.assertGreaterEqual(result["total_patches"], 1)
        self.assertGreaterEqual(result["rounds_run"], 1)


class RefineCli19(unittest.TestCase):
    def test_cli_feedback_writes_outputs(self) -> None:
        deck = {
            "version": "1.1",
            "slides": [{
                "id": "dense",
                "recipe": "bullets",
                "content": {
                    "title": "Lots",
                    "bullets": [f"Item {i}" for i in range(9)],
                },
            }],
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "content.deck.json"
            src.write_text(json.dumps(deck), encoding="utf-8")
            out = root / "refined"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main([
                    "refine", str(src),
                    "-o", str(out),
                    "--feedback", "too dense — please split",
                    "--rounds", "3",
                ])
            self.assertEqual(rc, 0, buf.getvalue())
            self.assertTrue((out / "content.deck.json").is_file())
            self.assertTrue((out / "refine.report.json").is_file())
            refined = json.loads((out / "content.deck.json").read_text(encoding="utf-8"))
            self.assertGreater(len(refined["slides"]), 1)
            report = json.loads((out / "refine.report.json").read_text(encoding="utf-8"))
            self.assertTrue(report["changed"])
            self.assertIn("split", buf.getvalue().lower() + str(report))

    def test_cli_with_findings_file(self) -> None:
        deck = {
            "slides": [{
                "id": "s1",
                "recipe": "bullets",
                "content": {"title": "T", "bullets": [f"b{i}" for i in range(7)]},
            }],
        }
        findings = {
            "pass": False,
            "findings": [{
                "code": "density",
                "severity": "error",
                "message": "crowded",
                "slide": 1,
            }],
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "deck.json"
            src.write_text(json.dumps(deck), encoding="utf-8")
            fp = root / "findings.json"
            fp.write_text(json.dumps(findings), encoding="utf-8")
            out = root / "out"
            rc = main(["refine", str(src), "-o", str(out), "--findings", str(fp)])
            self.assertEqual(rc, 0)
            refined = json.loads((out / "content.deck.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(refined["slides"]), 2)


if __name__ == "__main__":
    unittest.main()
