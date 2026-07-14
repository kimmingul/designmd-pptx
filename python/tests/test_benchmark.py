"""Before/after benchmark harness (issue #37)."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from designmd_pptx import benchmark as bench
from designmd_pptx.__main__ import main

PKG = Path(__file__).resolve().parent.parent / "designmd_pptx"


class ThresholdsV37(unittest.TestCase):
    def test_shipped_thresholds_load(self) -> None:
        th = bench.load_thresholds()
        self.assertEqual(th["schema"], 1)
        for key in ("corruption", "extraction_loss", "layout_failure",
                    "visual_gate_failure", "a11y_error"):
            self.assertIn(key, th["metrics"])
            self.assertIn("max", th["metrics"][key])


class MetricsV37(unittest.TestCase):
    def test_pptx_corruption_detects_bad_zip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.pptx"
            p.write_bytes(b"not a zip")
            n, note = bench._pptx_corruption(p)
            self.assertEqual(n, 1)
            self.assertTrue(note)

    def test_pptx_ok_minimal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ok.pptx"
            with zipfile.ZipFile(p, "w") as zf:
                zf.writestr("[Content_Types].xml", "<Types/>")
                zf.writestr("ppt/slides/slide1.xml", "<s/>")
            n, note = bench._pptx_corruption(p)
            self.assertEqual(n, 0)
            self.assertEqual(note, "ok")

    def test_extraction_loss_counts_high(self) -> None:
        report = {
            "loss_ledger": [
                {"severity": "info"},
                {"severity": "high"},
                {"severity": "error"},
            ]
        }
        self.assertEqual(bench._count_extraction_loss(report), 2)

    def test_threshold_breach(self) -> None:
        th = bench.load_thresholds()
        m = bench.DeckMetrics(deck_id="x", corruption=1)
        breaches = bench.evaluate_against_thresholds(m, th)
        self.assertTrue(any("corruption" in b for b in breaches))


class SuiteV37(unittest.TestCase):
    def test_fixture_suite_pass_and_fail(self) -> None:
        from designmd_pptx.compile import compile_design_md

        th = bench.load_thresholds()
        tokens = compile_design_md(PKG / "default.DESIGN.md")
        good = {
            "id": "good",
            "after_deck": {"slides": [{"id": "s", "recipe": "cover",
                                       "content": {"title": "T"}}]},
            "after_tokens": tokens,
            "after_extract": {"loss_ledger": []},
            "after_gate": {"pass": True},
        }
        bad = {
            "id": "bad",
            "after_deck": {"slides": []},  # layout failure
            "after_tokens": tokens,
            "after_extract": {"loss_ledger": [{"severity": "error"}] * 9},
            "after_gate": {"pass": False},
        }
        report = bench.run_fixture_suite(fixtures=[good, bad], thresholds=th)
        self.assertFalse(report.ok)
        by_id = {r.deck_id: r for r in report.results}
        self.assertEqual(by_id["good"].status, "pass", msg=by_id["good"])
        self.assertEqual(by_id["bad"].status, "fail")
        self.assertTrue(by_id["bad"].threshold_breaches)

    def test_default_fixture_benchmark_passes(self) -> None:
        report = bench.run_default_fixture_benchmark()
        self.assertTrue(report.ok, msg=report.to_dict())
        self.assertGreaterEqual(report.decks_pass, 1)
        self.assertEqual(report.decks_fail, 0)

    def test_corpus_missing_assets_skip_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            man = Path(td) / "corpus.manifest.json"
            man.write_text(json.dumps({
                "schema": 1,
                "entries": [{
                    "id": "ghost",
                    "file": "missing/ghost.pptx",
                    "source": "test",
                    "license": "test",
                    "provenance": "synthetic",
                    "held_out": True,
                }],
            }), encoding="utf-8")
            report = bench.run_corpus_suite(man)
            self.assertEqual(report.decks_skip, 1)
            self.assertEqual(report.decks_fail, 0)
            self.assertTrue(report.ok)

    def test_cli_fixture_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "bm"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["benchmark", "-o", str(out)])
            self.assertEqual(rc, 0, msg=buf.getvalue())
            self.assertTrue((out / "benchmark.report.json").is_file())
            data = json.loads((out / "benchmark.report.json").read_text(encoding="utf-8"))
            self.assertTrue(data["ok"])
            self.assertIn("PASS", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
