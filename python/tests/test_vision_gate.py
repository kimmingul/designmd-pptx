"""Phase 3 / #14 — structured Gate 3 vision QA (offline + plan + hard fail)."""

from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from designmd_pptx.vision_gate import (
    evaluate_contact_sheet,
    merge_evaluations,
    offline_evaluate,
    write_report,
)


def _minimal_png(path: Path, w: int = 800, h: int = 400) -> Path:
    """Write a tiny valid 1-bit-ish PNG via raw IHDR+IEND (enough for size probe).

    We only need a valid signature + IHDR for offline_evaluate; IDAT can be
    empty/invalid as long as we don't open with a real decoder. For a fully
    valid PNG use a known good 1×1 and then we only test dimensions via IHDR
    parse — offline_evaluate only reads first 32 bytes for dimensions.
    """
    # Full minimal valid 1x1 PNG
    png_1x1 = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15"
        "c4890000000d49444154789c626001000000ffff03000006000557bfabd400"
        "00000049454e44ae426082"
    )
    if w == 1 and h == 1:
        path.write_bytes(png_1x1)
        return path
    # Rewrite IHDR dimensions on a copy of 1x1 template
    data = bytearray(png_1x1)
    # width/height at offset 16
    data[16:24] = struct.pack(">II", w, h)
    # CRC will be wrong — offline_evaluate only checks signature+IHDR type
    path.write_bytes(data)
    # Ensure file is large enough to pass min_bytes when needed
    if path.stat().st_size < 3000:
        path.write_bytes(path.read_bytes() + b"\x00" * (3000 - path.stat().st_size))
    return path


class VisionGate14(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_missing_is_error(self) -> None:
        r = offline_evaluate(self.root / "nope.png")
        self.assertFalse(r["pass"])
        self.assertEqual(r["findings"][0]["code"], "missing")

    def test_valid_png_passes_offline(self) -> None:
        p = _minimal_png(self.root / "ok.png", 1200, 600)
        r = offline_evaluate(p, min_bytes=100)
        self.assertTrue(r["pass"], r)
        self.assertEqual(r["metrics"]["width_px"], 1200)
        self.assertEqual(r["metrics"]["height_px"], 600)

    def test_tiny_dimensions_fail(self) -> None:
        p = _minimal_png(self.root / "tiny.png", 10, 10)
        r = offline_evaluate(p, min_bytes=1, min_width=400, min_height=200)
        self.assertFalse(r["pass"])
        codes = [f["code"] for f in r["findings"]]
        self.assertIn("dimensions", codes)

    def test_plan_can_force_fail(self) -> None:
        p = _minimal_png(self.root / "sheet.png", 1000, 500)
        plan = {
            "pass": False,
            "score": 0.1,
            "provider": "plan_file",
            "findings": [{
                "code": "overflow",
                "severity": "error",
                "message": "title clipped on slide 2",
                "slide": 2,
            }],
        }
        plan_path = self.root / "vision.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        r = evaluate_contact_sheet(p, vision_plan=plan_path)
        self.assertFalse(r["pass"])
        self.assertTrue(any(f["code"] == "overflow" for f in r["findings"]))
        out = write_report(r, self.root / "out.gate3.json")
        self.assertTrue(out.exists())

    def test_merge_prefers_fail(self) -> None:
        a = {"pass": True, "score": 0.9, "provider": "a", "findings": [], "metrics": {}}
        b = {
            "pass": False,
            "score": 0.2,
            "provider": "b",
            "findings": [{"code": "x", "severity": "error", "message": "bad"}],
            "metrics": {},
        }
        m = merge_evaluations(a, b)
        self.assertFalse(m["pass"])
        self.assertEqual(m["score"], 0.2)

    def test_cli_flags_wired(self) -> None:
        from designmd_pptx.__main__ import build_parser

        p = build_parser()
        args = p.parse_args([
            "apply", "x.pptx", "seq.json",
            "--vision", "--gate3-vision", "--vision-plan", "p.json",
        ])
        self.assertTrue(args.vision)
        self.assertTrue(args.gate3_vision)
        self.assertEqual(str(args.vision_plan), "p.json")


if __name__ == "__main__":
    unittest.main()
