"""Phase 5 / #35 — Windows standalone installer plan + one-file script."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from designmd_pptx import win_install as wi
from designmd_pptx.__main__ import main

REPO = Path(__file__).resolve().parents[2]
INSTALLER = REPO / "packaging" / "windows" / "Install-DesignmdPptx.ps1"
ISS = REPO / "packaging" / "windows" / "designmd-pptx.iss"
BUILD = REPO / "packaging" / "windows" / "build-installer.ps1"
README = REPO / "packaging" / "windows" / "README.md"


class WinInstallPlan35(unittest.TestCase):
    def test_default_root_contains_product(self) -> None:
        root = wi.default_install_root(home=Path("/tmp/home"), local_appdata="/tmp/la")
        self.assertEqual(root, Path("/tmp/la") / "designmd-pptx")

    def test_paths_layout(self) -> None:
        p = wi.resolve_paths(Path("/tmp/designmd-pptx"))
        self.assertEqual(p.bin_dir, Path("/tmp/designmd-pptx/bin"))
        self.assertEqual(p.manifest.name, "install.manifest.json")
        self.assertTrue(str(p.uninstall_ps1).endswith("Uninstall-DesignmdPptx.ps1"))

    def test_officecli_pin_from_compat(self) -> None:
        pin = wi.officecli_pin()
        self.assertRegex(pin, r"^\d+\.\d+")
        url = wi.officecli_windows_url(pin)
        self.assertIn("officecli-dist", url)
        self.assertIn("windows", url)
        self.assertIn(pin, url)

    def test_build_plan_has_required_steps(self) -> None:
        plan = wi.build_install_plan(root="/tmp/dmd")
        ids = [s.id for s in plan.steps]
        for need in ("ensure_python", "create_venv", "pip_install",
                     "officecli_pin", "shim", "user_path", "write_manifest"):
            self.assertIn(need, ids, need)
        self.assertTrue(plan.uninstall_command)
        self.assertIn("Uninstall", plan.uninstall_command)
        text = wi.render_plan_text(plan)
        self.assertIn("OfficeCLI pin", text)
        self.assertIn("Install-DesignmdPptx.ps1", text)

    def test_skip_officecli(self) -> None:
        plan = wi.build_install_plan(skip_officecli=True)
        self.assertNotIn("officecli_pin", [s.id for s in plan.steps])

    def test_manifest_roundtrip(self) -> None:
        plan = wi.build_install_plan(root="/tmp/dmd")
        data = wi.new_manifest(
            plan,
            installed_at="2026-07-15T00:00:00Z",
            python_exe=r"C:\Python312\python.exe",
            officecli_path=r"C:\Users\x\AppData\Local\officecli-official\officecli.exe",
            path_modified=True,
        )
        errs = wi.validate_manifest(data)
        self.assertEqual(errs, [])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "install.manifest.json"
            wi.write_manifest(path, data)
            loaded = wi.load_manifest(path)
            self.assertEqual(loaded["product"], "designmd-pptx")
            self.assertTrue(loaded["uninstall"]["command"])

    def test_validate_manifest_errors(self) -> None:
        self.assertTrue(wi.validate_manifest({}))
        self.assertTrue(wi.validate_manifest("nope"))


class OneFileInstaller35(unittest.TestCase):
    def test_installer_files_exist(self) -> None:
        self.assertTrue(INSTALLER.is_file(), INSTALLER)
        self.assertTrue(ISS.is_file(), ISS)
        self.assertTrue(BUILD.is_file(), BUILD)
        self.assertTrue(README.is_file(), README)

    def test_ps1_acceptance_markers(self) -> None:
        text = INSTALLER.read_text(encoding="utf-8")
        # One-file + uninstall + pin fetch
        for needle in (
            "param(",
            "-Uninstall",
            "DryRun",
            "officecli-dist",
            "install.manifest.json",
            "LOCALAPPDATA",
            "designmd-pptx",
            "winget",
            "User",  # user PATH scope
            "Invoke-Uninstall",
            "Get-OfficeCliUrl",
            "0.2.117",
            "designmd-pptx==2.1.2",  # pinned package
            "Assert-SafeInstallRoot",
            "SHA256",
            "officecli.exe",  # exact binary name (no ambiguous officecli*)
        ):
            self.assertIn(needle, text, f"missing {needle!r}")

    def test_iss_has_uninstall_run(self) -> None:
        text = ISS.read_text(encoding="utf-8")
        self.assertIn("[UninstallRun]", text)
        self.assertIn("Install-DesignmdPptx.ps1", text)
        self.assertIn("PrivilegesRequired=lowest", text)

    def test_assert_installer_present(self) -> None:
        p = wi.assert_installer_present(REPO)
        self.assertEqual(p.resolve(), INSTALLER.resolve())


class CliWindowsInstall35(unittest.TestCase):
    def test_cli_plan(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["windows-install", "--plan"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("OfficeCLI pin", out)
        self.assertIn("ensure_python", out)

    def test_cli_check_script(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["windows-install", "--check-script", "--repo-root", str(REPO)])
        self.assertEqual(rc, 0, buf.getvalue())
        self.assertIn("OK windows installer", buf.getvalue())

    def test_cli_json_out(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "plan.json"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["windows-install", "--json", "-o", str(out)])
            self.assertEqual(rc, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["product"], "designmd-pptx")
            self.assertTrue(data["steps"])

    def test_cli_validate_manifest(self) -> None:
        plan = wi.build_install_plan()
        data = wi.new_manifest(
            plan, installed_at="t", python_exe="py", path_modified=False,
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.json"
            wi.write_manifest(path, data)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["windows-install", "--validate-manifest", str(path)])
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
