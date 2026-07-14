"""doctor --install (issue #34) — version-locked OfficeCLI installer.

Covers plan generation against compatibility.json, dry-run transparency,
CLI wiring, and that real subprocess install is only invoked when needed.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import unittest
from unittest import mock

from designmd_pptx import compat
from designmd_pptx import doctor
from designmd_pptx.__main__ import build_parser, main


class PlanInstallV34(unittest.TestCase):
    def test_plan_includes_official_pin_from_manifest(self) -> None:
        pinned = compat.spec_for("official")["recommended"]
        with mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/npm"), \
                mock.patch.object(doctor, "find_binaries", return_value={}), \
                mock.patch.object(doctor, "_legacy", return_value=(False, "missing")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")):
            steps = doctor.plan_install()
        by_id = {s.id: s for s in steps}
        self.assertIn("official", by_id)
        self.assertIn("pyyaml", by_id)
        self.assertIn("legacy", by_id)
        off = by_id["official"]
        self.assertEqual(off.kind, "run")
        self.assertIn(f"officecli@{pinned}", off.display)
        self.assertIn(pinned, off.downloads)
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
                mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/npm"), \
                mock.patch.object(doctor, "_legacy", return_value=(True, "ok")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")):
            steps = doctor.plan_install()
        off = next(s for s in steps if s.id == "official")
        self.assertEqual(off.kind, "run")
        self.assertIn("upgrade", off.reason.lower())

    def test_manual_when_npm_missing(self) -> None:
        with mock.patch.object(doctor, "find_binaries", return_value={}), \
                mock.patch.object(doctor.shutil, "which", return_value=None), \
                mock.patch.object(doctor, "_legacy", return_value=(True, "ok")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")):
            steps = doctor.plan_install()
        off = next(s for s in steps if s.id == "official")
        self.assertEqual(off.kind, "manual")
        self.assertIn("npm not on PATH", off.reason)


class RunInstallV34(unittest.TestCase):
    def test_dry_run_prints_plan_and_does_not_spawn(self) -> None:
        pinned = compat.spec_for("official")["recommended"]
        calls: list = []

        def boom(*a, **k):
            calls.append((a, k))
            raise AssertionError("subprocess must not run in dry-run")

        with mock.patch.object(doctor, "find_binaries", return_value={}), \
                mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/npm"), \
                mock.patch.object(doctor, "_legacy", return_value=(False, "missing")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")), \
                mock.patch.object(doctor, "_RUN_INSTALL", boom), \
                mock.patch.object(doctor.subprocess, "run", boom):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = doctor.run_install(dry_run=True)
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [])
        self.assertIn("dry-run: yes", out)
        self.assertIn(f"officecli@{pinned}", out)
        self.assertIn("downloads:", out)
        self.assertIn("would run:", out)
        self.assertIn("legacy", out.lower())

    def test_install_invokes_npm_with_pin(self) -> None:
        pinned = compat.spec_for("official")["recommended"]
        seen: list[list[str]] = []

        def fake_run(argv, **kwargs):
            seen.append(list(argv))
            return subprocess.CompletedProcess(argv, 0, stdout="added 1 package", stderr="")

        with mock.patch.object(doctor, "find_binaries", return_value={}), \
                mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/npm"), \
                mock.patch.object(doctor, "_legacy", return_value=(True, "ok v9")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")), \
                mock.patch.object(doctor, "_RUN_INSTALL", fake_run), \
                mock.patch.object(doctor, "run_doctor", return_value=0) as rd:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = doctor.run_install(dry_run=False)
        self.assertEqual(rc, 0)
        self.assertTrue(any(f"officecli@{pinned}" in " ".join(a) for a in seen))
        rd.assert_called_once()
        self.assertIn("re-probing", buf.getvalue())

    def test_failed_npm_returns_nonzero_with_repair(self) -> None:
        def fake_run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="EACCES")

        with mock.patch.object(doctor, "find_binaries", return_value={}), \
                mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/npm"), \
                mock.patch.object(doctor, "_legacy", return_value=(True, "ok")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "importable")), \
                mock.patch.object(doctor, "_RUN_INSTALL", fake_run):
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
        # When checks fail, remedy tip points at --install --dry-run
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
