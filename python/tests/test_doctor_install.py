"""doctor --install (issue #34) — version-locked OfficeCLI installer.

Covers plan generation against compatibility.json, dry-run transparency,
officecli-dist download path, and CLI wiring.
"""

from __future__ import annotations

import contextlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from designmd_pptx import compat
from designmd_pptx import doctor
from designmd_pptx.__main__ import build_parser, main


class PlanInstallV34(unittest.TestCase):
    def test_plan_includes_official_pin_from_dist(self) -> None:
        pinned = compat.spec_for("official")["recommended"]
        with mock.patch.object(doctor, "find_binaries", return_value={}), \
                mock.patch.object(doctor, "_legacy", return_value=(False, "missing")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")):
            steps = doctor.plan_install()
        by_id = {s.id: s for s in steps}
        self.assertIn("official", by_id)
        self.assertIn("pyyaml", by_id)
        self.assertIn("legacy", by_id)
        off = by_id["official"]
        self.assertEqual(off.kind, "run")
        self.assertIn(pinned, off.downloads)
        self.assertIn("officecli-dist", off.downloads)
        self.assertIn(f"officecli_{pinned}_", off.downloads)
        self.assertEqual(by_id["legacy"].kind, "manual")

    def test_skip_official_when_supported_version_present(self) -> None:
        pinned = compat.spec_for("official")["recommended"]

        def fake_run(exe, *args, **kwargs):
            if args[:1] == ("--version",):
                return 0, f"officecli version {pinned}"
            return 0, "ok"

        with mock.patch.object(doctor, "find_binaries",
                               return_value={"official": "fake-oc"}), \
                mock.patch.object(doctor, "_run", side_effect=fake_run), \
                mock.patch.object(doctor, "_legacy", return_value=(True, "ok")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")):
            steps = doctor.plan_install()
        off = next(s for s in steps if s.id == "official")
        self.assertEqual(off.kind, "skip")
        self.assertIn("already present", off.reason)

    def test_upgrade_when_too_old(self) -> None:
        def fake_run(exe, *args, **kwargs):
            if args[:1] == ("--version",):
                return 0, "officecli version 0.2.100 (old)"
            return 1, ""

        with mock.patch.object(doctor, "find_binaries",
                               return_value={"official": "fake-oc"}), \
                mock.patch.object(doctor, "_run", side_effect=fake_run), \
                mock.patch.object(doctor, "_legacy", return_value=(True, "ok")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")):
            steps = doctor.plan_install()
        off = next(s for s in steps if s.id == "official")
        self.assertEqual(off.kind, "run")
        self.assertIn("upgrade", off.reason.lower())

    def test_dist_asset_url_uses_platform_triple(self) -> None:
        url = doctor.dist_asset_url("0.2.117", triple="darwin_arm64")
        self.assertIn("officecli-dist/releases/download/v0.2.117/", url)
        self.assertIn("officecli_0.2.117_darwin_arm64.tar.gz", url)


class RunInstallV34(unittest.TestCase):
    def test_dry_run_prints_plan_and_does_not_download(self) -> None:
        pinned = compat.spec_for("official")["recommended"]
        calls: list = []

        def boom(*a, **k):
            calls.append((a, k))
            raise AssertionError("must not download in dry-run")

        with mock.patch.object(doctor, "find_binaries", return_value={}), \
                mock.patch.object(doctor, "_legacy", return_value=(False, "missing")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")), \
                mock.patch.object(doctor, "_URLOPEN", boom), \
                mock.patch.object(doctor, "install_official_from_dist", boom):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = doctor.run_install(dry_run=True)
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [])
        self.assertIn("dry-run: yes", out)
        self.assertIn(pinned, out)
        self.assertIn("officecli-dist", out)
        self.assertIn("would run:", out)

    def test_install_from_dist_extracts_binary(self) -> None:
        pinned = compat.spec_for("official")["recommended"]
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "officecli-official"
            # Build a tiny tar.gz with a fake officecli binary
            raw = Path(td) / "payload"
            raw.mkdir()
            bin_path = raw / doctor.official_bin_name()
            bin_path.write_bytes(b"#!/bin/sh\necho officecli version "
                                 + pinned.encode() + b"\n")
            tgz = Path(td) / "oc.tgz"
            with tarfile.open(tgz, "w:gz") as tf:
                tf.add(bin_path, arcname=doctor.official_bin_name())

            class FakeResp:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    return tgz.read_bytes()

            with mock.patch.object(doctor, "_URLOPEN", return_value=FakeResp()), \
                    mock.patch.object(doctor, "find_binaries", return_value={}):
                ok, detail = doctor.install_official_from_dist(pinned, dest_dir=dest)
            self.assertTrue(ok, msg=detail)
            self.assertTrue((dest / doctor.official_bin_name()).is_file())
            self.assertIn(pinned, detail)
            self.assertIn("officecli-dist", detail)

    def test_install_invokes_dist_path(self) -> None:
        with mock.patch.object(doctor, "find_binaries", return_value={}), \
                mock.patch.object(doctor, "_legacy", return_value=(True, "ok v9")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")), \
                mock.patch.object(doctor, "install_official_from_dist",
                                  return_value=(True, "installed ok")) as inst, \
                mock.patch.object(doctor, "run_doctor", return_value=0) as rd:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = doctor.run_install(dry_run=False)
        self.assertEqual(rc, 0)
        inst.assert_called()
        rd.assert_called_once()
        self.assertIn("re-probing", buf.getvalue())

    def test_failed_download_returns_nonzero_with_repair(self) -> None:
        with mock.patch.object(doctor, "find_binaries", return_value={}), \
                mock.patch.object(doctor, "_legacy", return_value=(True, "ok")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")), \
                mock.patch.object(doctor, "install_official_from_dist",
                                  return_value=(False, "download failed: ECONN")):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = doctor.run_install(dry_run=False)
        self.assertEqual(rc, 1)
        self.assertIn("failed", buf.getvalue().lower())
        self.assertIn("repair", buf.getvalue().lower())


class CliWiringV34(unittest.TestCase):
    def test_parser_accepts_install_and_dry_run(self) -> None:
        args = build_parser().parse_args(["doctor", "--install", "--dry-run"])
        self.assertTrue(args.install)
        self.assertTrue(args.dry_run)

    def test_main_install_dry_run(self) -> None:
        buf = io.StringIO()
        with mock.patch("designmd_pptx.doctor.run_install", return_value=0) as ri, \
                contextlib.redirect_stdout(buf):
            rc = main(["doctor", "--install", "--dry-run"])
        self.assertEqual(rc, 0)
        ri.assert_called_once_with(dry_run=True)

    def test_doctor_tip_mentions_install(self) -> None:
        with mock.patch.object(doctor, "_legacy", return_value=(False, "no")), \
                mock.patch.object(doctor, "_official", return_value=(False, "no")), \
                mock.patch.object(doctor, "_env_check_script",
                                 return_value=(True, "skip")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "ok")), \
                mock.patch.object(doctor, "_skill", return_value=(True, "ok")), \
                mock.patch.object(doctor, "_claude_designmd", return_value=(True, "ok")):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                doctor.run_doctor()
        self.assertIn("doctor --install --dry-run", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
