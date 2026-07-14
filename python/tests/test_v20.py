"""v2.0 / Phase 0 suite — OfficeCLI compatibility manifest (issue #8).

Covers the machine-readable version contract: parsing/comparison, support
classification, manifest self-check, single-source wiring into backend +
doctor, and a binary-gated end-to-end that generates → validates → renders a
contact sheet against a real OfficeCLI (self-skips when no binary is present)."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from designmd_pptx import compat

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class ParseVersionV20(unittest.TestCase):
    def test_parses_real_probe_outputs(self) -> None:
        self.assertEqual(
            compat.parse_version("officecli version 0.2.117 (abc)"), (0, 2, 117))
        self.assertEqual(compat.parse_version("9.9.9"), (9, 9, 9))
        self.assertEqual(compat.parse_version("1.2"), (1, 2))
        self.assertIsNone(compat.parse_version(""))
        self.assertIsNone(compat.parse_version("no digits here"))
        self.assertIsNone(compat.parse_version(None))

    def test_cmp_pads_shorter_tuple(self) -> None:
        self.assertEqual(compat.cmp_version((1, 2), (1, 2, 0)), 0)
        self.assertEqual(compat.cmp_version((0, 2, 117), (0, 3, 0)), -1)
        self.assertEqual(compat.cmp_version((0, 3, 0), (0, 2, 117)), 1)
        # string comparison would get this wrong ("0.2.117" vs "0.2.9")
        self.assertEqual(compat.cmp_version((0, 2, 117), (0, 2, 9)), 1)


class ClassifySupportV20(unittest.TestCase):
    def _manifest(self, **official) -> dict:
        spec = {"min": "0.2.117", "recommended": "0.2.117",
                "max_tested": "0.2.117", "install": "npm i -g officecli@0.2.117"}
        spec.update(official)
        return {"schema": 1, "officecli": {
            "official": spec,
            "legacy": {"min": None, "recommended": None, "max_tested": None},
        }}

    def test_all_levels(self) -> None:
        m = self._manifest()
        self.assertEqual(compat.classify_support("official", "0.2.117", m)[0], compat.OK)
        self.assertEqual(
            compat.classify_support("official", "0.2.100", m)[0], compat.TOO_OLD)
        self.assertEqual(
            compat.classify_support("official", "0.3.0", m)[0], compat.UNTESTED_NEWER)
        self.assertEqual(
            compat.classify_support("official", "garbage", m)[0], compat.UNKNOWN)

    def test_open_range_accepts_any_version(self) -> None:
        # legacy bounds are null → any parseable version is supported
        m = self._manifest()
        self.assertEqual(compat.classify_support("legacy", "9.9.9", m)[0], compat.OK)


class ManifestV20(unittest.TestCase):
    def test_shipped_manifest_selfcheck(self) -> None:
        compat.selfcheck()  # raises on any inconsistency in compatibility.json

    def test_selfcheck_rejects_bad_ordering(self) -> None:
        bad = {"schema": 1, "officecli": {
            "official": {"min": "0.3.0", "recommended": "0.2.0", "max_tested": "0.2.0"},
            "legacy": {"min": None, "recommended": None, "max_tested": None},
        }}
        with self.assertRaises(AssertionError):
            compat.selfcheck(bad)

    def test_selfcheck_rejects_unparseable_version(self) -> None:
        bad = {"schema": 1, "officecli": {
            "official": {"min": "not-a-version", "recommended": None, "max_tested": None},
            "legacy": {"min": None, "recommended": None, "max_tested": None},
        }}
        with self.assertRaises(AssertionError):
            compat.selfcheck(bad)

    def test_backend_min_sources_from_manifest(self) -> None:
        from designmd_pptx.backend import OFFICIAL_MIN_VERSION
        self.assertEqual(OFFICIAL_MIN_VERSION, compat.spec_for("official")["min"])

    def test_explicit_path_bypasses_cache(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.json"
            p.write_text(json.dumps({"schema": 1, "officecli": {
                "official": {"min": "1.0.0", "recommended": "1.0.0",
                             "max_tested": "1.0.0"},
                "legacy": {"min": None, "recommended": None, "max_tested": None},
            }}), encoding="utf-8")
            self.assertEqual(
                compat.spec_for("official", compat.load_manifest(p))["min"], "1.0.0")


class DoctorUsesCompatV20(unittest.TestCase):
    def test_present_but_too_old_official_fails_with_reason(self) -> None:
        # No real binary: force discovery + probe so doctor classifies the
        # version against the manifest and marks a too-old build as failing.
        from designmd_pptx import doctor

        def fake_run(exe, *args, **kwargs):
            if args[:1] == ("--version",):
                return 0, "officecli version 0.2.100 (old build)"
            return 1, ""  # config status n/a

        with mock.patch.object(doctor, "find_binaries",
                               return_value={"official": "fake-official"}), \
                mock.patch.object(doctor, "_run", side_effect=fake_run):
            ok, msg = doctor._official()
        self.assertFalse(ok)
        self.assertIn("TOO OLD", msg)
        self.assertIn("0.2.100", msg)

    def test_supported_official_reports_ok(self) -> None:
        from designmd_pptx import doctor
        pinned = compat.spec_for("official")["recommended"]

        def fake_run(exe, *args, **kwargs):
            if args[:1] == ("--version",):
                return 0, f"officecli version {pinned} (ok)"
            return 0, "logged in"

        with mock.patch.object(doctor, "find_binaries",
                               return_value={"official": "fake-official"}), \
                mock.patch.object(doctor, "_run", side_effect=fake_run):
            ok, msg = doctor._official()
        self.assertTrue(ok)
        self.assertIn("supported", msg)

    def test_doctor_still_green(self) -> None:
        from designmd_pptx.__main__ import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["doctor"])
        self.assertEqual(rc, 0)


def _legacy_available() -> bool:
    try:
        from designmd_pptx.backend import find_binaries
        return bool(find_binaries().get("legacy"))
    except Exception:
        return False


@unittest.skipUnless(
    _legacy_available() or os.environ.get("DESIGNMD_E2E") == "1",
    "no legacy OfficeCLI binary — E2E generate/validate/contact-sheet skipped")
class EndToEndV20(unittest.TestCase):
    """The CI e2e job installs the manifest-pinned OfficeCLI and runs this."""

    def test_generate_validate_contact_sheet(self) -> None:
        from designmd_pptx.__main__ import main

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "deck"
            rc = main([
                "scaffold", str(FIXTURES / "linear.DESIGN.md"),
                "-o", str(out), "--brand", "Linear",
                "--content", str(EXAMPLES / "content.deck.json"),
                "--apply", "--force", "--screenshot",
            ])
            self.assertEqual(rc, 0, "scaffold --apply exited non-zero")
            produced = list(out.glob("*.pptx"))
            self.assertTrue(produced, "no .pptx was materialized")
            self.assertGreater(produced[0].stat().st_size, 1024,
                               "materialized .pptx is implausibly small")
            contact = produced[0].with_suffix(".contact.png")
            self.assertTrue(contact.exists(),
                            "Gate 3 contact sheet was not rendered")


if __name__ == "__main__":
    unittest.main()
