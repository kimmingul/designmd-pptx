"""OfficeCLI ensure / install prompt / status-json (install-check UX)."""

from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from designmd_pptx import doctor
from designmd_pptx.__main__ import _ensure_for_command, build_parser, main


class BackendStatusTests(unittest.TestCase):
    def test_to_dict_flags(self) -> None:
        st = doctor.BackendStatus(
            legacy_ok=False,
            official_ok=True,
            legacy_detail="no",
            official_detail="yes",
        )
        d = st.to_dict()
        self.assertFalse(d["legacy_ok"])
        self.assertTrue(d["official_ok"])
        self.assertFalse(d["materialize_ready"])
        self.assertTrue(d["render_ready"])
        self.assertTrue(d["any_officecli"])
        self.assertIn("OfficeCLI", d["required_message"])

    def test_probe_backends_uses_helpers(self) -> None:
        with mock.patch.object(doctor, "_legacy", return_value=(True, "leg")), \
                mock.patch.object(doctor, "_official", return_value=(False, "off")):
            st = doctor.probe_backends()
        self.assertTrue(st.legacy_ok)
        self.assertFalse(st.official_ok)
        self.assertEqual(st.legacy_detail, "leg")


class PromptTests(unittest.TestCase):
    def test_assume_yes(self) -> None:
        with mock.patch.dict(os.environ, {"DESIGNMD_ASSUME_YES": "1"}, clear=False):
            os.environ.pop("DESIGNMD_NO_PROMPT", None)
            self.assertTrue(doctor.prompt_yes_no("Install?"))

    def test_no_prompt_returns_false(self) -> None:
        with mock.patch.dict(os.environ, {"DESIGNMD_NO_PROMPT": "1"}, clear=False):
            os.environ.pop("DESIGNMD_ASSUME_YES", None)
            self.assertFalse(doctor.prompt_yes_no("Install?"))

    def test_default_on_empty_input(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DESIGNMD_ASSUME_YES", None)
            os.environ.pop("DESIGNMD_NO_PROMPT", None)
            with mock.patch.object(doctor, "_interactive_allowed", return_value=True), \
                    mock.patch("builtins.input", return_value=""):
                self.assertTrue(doctor.prompt_yes_no("q?", default=True))
                self.assertFalse(doctor.prompt_yes_no("q?", default=False))

    def test_yes_variants(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DESIGNMD_ASSUME_YES", None)
            os.environ.pop("DESIGNMD_NO_PROMPT", None)
            with mock.patch.object(doctor, "_interactive_allowed", return_value=True):
                for ans in ("y", "yes", "Y", "YES"):
                    with mock.patch("builtins.input", return_value=ans):
                        self.assertTrue(doctor.prompt_yes_no("q?"), ans)
                with mock.patch("builtins.input", return_value="n"):
                    self.assertFalse(doctor.prompt_yes_no("q?"))


class EnsureOfficecliTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop("DESIGNMD_ASSUME_YES", None)
        os.environ["DESIGNMD_NO_PROMPT"] = "1"

    def tearDown(self) -> None:
        os.environ.pop("DESIGNMD_NO_PROMPT", None)
        os.environ.pop("DESIGNMD_ASSUME_YES", None)

    def test_ready_when_legacy_present_for_apply(self) -> None:
        st = doctor.BackendStatus(True, False, "leg", "no")
        with mock.patch.object(doctor, "probe_backends", return_value=st):
            ok, out = doctor.ensure_officecli(need_legacy=True, interactive=False)
        self.assertTrue(ok)
        self.assertTrue(out.legacy_ok)

    def test_missing_legacy_hard_fails_even_if_official(self) -> None:
        st = doctor.BackendStatus(False, True, "no leg", "official ok")
        buf = io.StringIO()
        with mock.patch.object(doctor, "probe_backends", return_value=st), \
                redirect_stderr(buf):
            ok, out = doctor.ensure_officecli(need_legacy=True, interactive=False)
        self.assertFalse(ok)
        self.assertIn("requires OfficeCLI", buf.getvalue())
        self.assertIn("legacy", buf.getvalue().lower())

    def test_missing_official_hard_fails_for_render(self) -> None:
        st = doctor.BackendStatus(True, False, "leg", "no off")
        buf = io.StringIO()
        with mock.patch.object(doctor, "probe_backends", return_value=st), \
                redirect_stderr(buf):
            ok, _ = doctor.ensure_officecli(need_official=True, interactive=False)
        self.assertFalse(ok)
        self.assertIn("requires OfficeCLI", buf.getvalue())

    def test_soft_any_backend_ok(self) -> None:
        st = doctor.BackendStatus(False, True, "no", "off")
        with mock.patch.object(doctor, "probe_backends", return_value=st):
            ok, _ = doctor.ensure_officecli(interactive=False)
        self.assertTrue(ok)

    def test_soft_none_returns_false_and_banner(self) -> None:
        st = doctor.BackendStatus(False, False, "no", "no")
        buf = io.StringIO()
        with mock.patch.object(doctor, "probe_backends", return_value=st), \
                redirect_stderr(buf):
            ok, _ = doctor.ensure_officecli(interactive=False)
        self.assertFalse(ok)
        self.assertIn("requires OfficeCLI", buf.getvalue())

    def test_assume_yes_runs_install(self) -> None:
        missing = doctor.BackendStatus(False, False, "no", "no")
        after = doctor.BackendStatus(False, True, "no", "installed")
        calls = {"n": 0}

        def probe():
            calls["n"] += 1
            return missing if calls["n"] == 1 else after

        with mock.patch.dict(os.environ, {"DESIGNMD_ASSUME_YES": "1"}, clear=False):
            os.environ.pop("DESIGNMD_NO_PROMPT", None)
            with mock.patch.object(doctor, "probe_backends", side_effect=probe), \
                    mock.patch.object(doctor, "run_install", return_value=0) as ri, \
                    redirect_stderr(io.StringIO()):
                ok, st = doctor.ensure_officecli(
                    need_official=True, interactive=True)
        ri.assert_called_once_with(dry_run=False)
        self.assertTrue(ok)
        self.assertTrue(st.official_ok)

    def test_prompt_yes_triggers_install(self) -> None:
        missing = doctor.BackendStatus(False, False, "no", "no")
        after = doctor.BackendStatus(False, True, "no", "ok")
        probes = [missing, after, after]

        def probe():
            return probes.pop(0) if probes else after

        with mock.patch.object(doctor, "probe_backends", side_effect=probe), \
                mock.patch.object(doctor, "prompt_yes_no", return_value=True), \
                mock.patch.object(doctor, "run_install", return_value=0) as ri, \
                redirect_stderr(io.StringIO()):
            ok, st = doctor.ensure_officecli(
                need_official=True, interactive=True)
        ri.assert_called_once()
        self.assertTrue(ok)
        self.assertTrue(st.official_ok)

    def test_prompt_no_skips_install(self) -> None:
        missing = doctor.BackendStatus(False, False, "no", "no")
        with mock.patch.object(doctor, "probe_backends", return_value=missing), \
                mock.patch.object(doctor, "prompt_yes_no", return_value=False), \
                mock.patch.object(doctor, "run_install") as ri, \
                redirect_stderr(io.StringIO()) as err:
            ok, _ = doctor.ensure_officecli(need_official=True, interactive=True)
        ri.assert_not_called()
        self.assertFalse(ok)
        self.assertIn("skipped install", err.getvalue())


class StatusJsonCli(unittest.TestCase):
    def test_status_json_prints_dict(self) -> None:
        st = doctor.BackendStatus(False, True, "L", "O")
        buf = io.StringIO()
        with mock.patch.object(doctor, "probe_backends", return_value=st), \
                redirect_stdout(buf):
            rc = doctor.run_doctor(status_json=True)
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["official_ok"])
        self.assertFalse(data["materialize_ready"])

    def test_cli_flags_wired(self) -> None:
        p = build_parser()
        args = p.parse_args(["doctor", "--ensure", "--status-json"])
        self.assertTrue(args.ensure)
        self.assertTrue(args.status_json)

    def test_main_status_json(self) -> None:
        st = doctor.BackendStatus(True, True, "a", "b")
        buf = io.StringIO()
        with mock.patch.object(doctor, "probe_backends", return_value=st), \
                redirect_stdout(buf):
            rc = main(["doctor", "--status-json"])
        self.assertEqual(rc, 0)
        self.assertIn("legacy_ok", buf.getvalue())


class EnsureForCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["DESIGNMD_NO_PROMPT"] = "1"

    def tearDown(self) -> None:
        os.environ.pop("DESIGNMD_NO_PROMPT", None)

    def test_soft_never_aborts(self) -> None:
        missing = doctor.BackendStatus(False, False, "no", "no")
        with mock.patch.object(doctor, "probe_backends", return_value=missing), \
                redirect_stderr(io.StringIO()):
            self.assertEqual(_ensure_for_command(soft=True), 0)

    def test_hard_legacy_aborts_when_missing(self) -> None:
        st = doctor.BackendStatus(False, True, "no leg", "off")
        with mock.patch.object(doctor, "probe_backends", return_value=st), \
                redirect_stderr(io.StringIO()):
            self.assertEqual(_ensure_for_command(need_legacy=True), 1)

    def test_hard_legacy_ok(self) -> None:
        st = doctor.BackendStatus(True, False, "leg", "no")
        with mock.patch.object(doctor, "probe_backends", return_value=st):
            self.assertEqual(_ensure_for_command(need_legacy=True), 0)

    def test_hard_official_aborts_when_missing(self) -> None:
        st = doctor.BackendStatus(True, False, "leg", "no")
        with mock.patch.object(doctor, "probe_backends", return_value=st), \
                redirect_stderr(io.StringIO()):
            self.assertEqual(_ensure_for_command(need_official=True), 1)

    def test_apply_cli_aborts_without_legacy(self) -> None:
        st = doctor.BackendStatus(False, False, "no", "no")
        with mock.patch.object(doctor, "probe_backends", return_value=st), \
                redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            rc = main(["apply", "deck.pptx", "seq.json"])
        self.assertEqual(rc, 1)

    def test_render_cli_aborts_without_official(self) -> None:
        st = doctor.BackendStatus(True, False, "leg", "no")
        with mock.patch.object(doctor, "probe_backends", return_value=st), \
                redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            rc = main(["render", "brief.md", "-o", "out.pptx"])
        self.assertEqual(rc, 1)

    def test_doctor_banner_when_missing(self) -> None:
        with mock.patch.object(doctor, "_legacy", return_value=(False, "no")), \
                mock.patch.object(doctor, "_official", return_value=(False, "no")), \
                mock.patch.object(doctor, "_env_check_script",
                                  return_value=(True, "skip")), \
                mock.patch.object(doctor, "_pyyaml", return_value=(True, "ok")), \
                mock.patch.object(doctor, "_skill", return_value=(True, "ok")), \
                mock.patch.object(doctor, "_claude_designmd", return_value=(True, "ok")), \
                mock.patch.object(doctor, "_interactive_allowed", return_value=False):
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                doctor.run_doctor(ensure=False)
        self.assertIn("requires OfficeCLI", buf.getvalue())


class DocsInstallMentionsEnsure(unittest.TestCase):
    def test_install_doc(self) -> None:
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        text = (root / "docs" / "install.md").read_text(encoding="utf-8")
        self.assertIn("doctor --ensure", text)
        self.assertIn("OfficeCLI is required", text)
        self.assertIn("DESIGNMD_NO_PROMPT", text)


if __name__ == "__main__":
    unittest.main()
