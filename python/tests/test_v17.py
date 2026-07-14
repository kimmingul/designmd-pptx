"""v1.7 suite — backend abstraction (#27), capability detection (#26),
agent-bridge protocol + payload mapping (#28), binary classification (#25)."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from designmd_pptx.backend import (
    _EMPTY_SLIDE, AgentBridgeBackend, BackendUnavailable, LegacyBatchBackend,
    classify_binary, deck_to_render_payload, tokens_to_bridge_theme,
)

FAKE_BRIDGE = r'''
import json, sys, os

def read_msg(stream):
    header = b""
    while b"\r\n\r\n" not in header:
        ch = stream.read(1)
        if not ch:
            raise SystemExit(0)
        header += ch
    length = 0
    for line in header.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":")[1])
    body = b""
    while len(body) < length:
        body += stream.read(length - len(body))
    return json.loads(body)

def send(obj):
    body = json.dumps(obj).encode()
    sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    sys.stdout.buffer.flush()

stdin = sys.stdin.buffer
while True:
    msg = read_msg(stdin)
    mid, method = msg.get("id"), msg.get("method")
    params = msg.get("params") or {}
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": mid, "result": {"server_name": "fake"}})
    elif method == "capabilities/get":
        send({"jsonrpc": "2.0", "id": mid, "result": {"document_generation": {
            "pptx": {"agent_render_supported": True,
                     "preferred_tool": "office.render",
                     "image_support": {"invoke_field": "enable_images"}}}}})
    elif method == "task/invoke":
        MODE = os.environ.get("FAKE_BRIDGE_MODE", "sync")
        args = params.get("args") or {}
        if params.get("tool") != "office.render" or "payload" not in args:
            send({"jsonrpc": "2.0", "id": mid,
                  "error": {"code": -32000, "message": "payload is required"}})
            continue
        title = args["payload"].get("title", "Deck")
        os.makedirs(args.get("out", "."), exist_ok=True)
        produced = os.path.join(args.get("out", "."), title + ".pptx")
        with open(produced, "wb") as f:
            f.write(b"FAKEPPTX")
        send({"jsonrpc": "2.0", "method": "event",
              "params": {"type": "task.progress", "payload": {"content": "assembling"}}})
        if MODE == "weird":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "task_id": "t-1", "status": "sideways", "result": {}}})
        elif MODE == "async":
            PENDING["produced"] = produced
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "task_id": "t-1", "status": "running"}})
        else:
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "task_id": "t-1", "status": "completed",
                "result": {"status": "success", "file_path": produced}}})
    elif method == "task/status":
        PENDING["polls"] = PENDING.get("polls", 0) + 1
        if PENDING["polls"] < 2:
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "task_id": "t-1", "status": "running"}})
        else:
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "task_id": "t-1", "status": "completed",
                "result": {"status": "success", "file_path": PENDING["produced"]}}})
    else:
        send({"jsonrpc": "2.0", "id": mid, "result": {}})
'''

FAKE_BRIDGE = "PENDING = {}\n" + FAKE_BRIDGE

# silent-mode: accepts requests, never answers — must trip the call timeout
FAKE_SILENT = r'''
import sys, time
while True:
    if not sys.stdin.buffer.read(1):
        raise SystemExit(0)
'''


def _make_fake_bridge(tmp: Path, *, mode: str = "sync",
                      body: str | None = None) -> str:
    """A launcher the backend can spawn as `<exe> agent-bridge`."""
    script = tmp / f"fake_bridge_{mode}.py"
    script.write_text(body or FAKE_BRIDGE, encoding="utf-8")
    if os.name == "nt":
        cmd = tmp / f"fake-officecli-{mode}.cmd"
        cmd.write_text(
            f'@echo off\r\nset FAKE_BRIDGE_MODE={mode}\r\n'
            f'"{sys.executable}" "{script}" %*\r\n',
            encoding="utf-8")
        return str(cmd)
    sh = tmp / f"fake-officecli-{mode}"
    sh.write_text(
        f'#!/bin/sh\nexport FAKE_BRIDGE_MODE={mode}\n'
        f'exec "{sys.executable}" "{script}" "$@"\n',
        encoding="utf-8")
    sh.chmod(0o755)
    return str(sh)


class ClassifyV17(unittest.TestCase):
    def test_classify_by_version_shape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            if os.name == "nt":
                legacy = tmp / "legacy.cmd"
                legacy.write_text("@echo off\r\necho 9.9.9\r\n", encoding="utf-8")
                official = tmp / "official.cmd"
                official.write_text(
                    "@echo off\r\necho officecli version 0.9.9 (abc)\r\n",
                    encoding="utf-8")
            else:
                legacy = tmp / "legacy"
                legacy.write_text("#!/bin/sh\necho 9.9.9\n"); legacy.chmod(0o755)
                official = tmp / "official"
                official.write_text("#!/bin/sh\necho officecli version 0.9.9\n")
                official.chmod(0o755)
            self.assertEqual(classify_binary(str(legacy)), "legacy")
            self.assertEqual(classify_binary(str(official)), "official")
            self.assertIsNone(classify_binary(str(tmp / "missing")))


class LegacyBackendV17(unittest.TestCase):
    def test_verbs_capability_probe(self) -> None:
        be = LegacyBatchBackend(exe="fake")

        class R:
            returncode = 0
            stdout = "Commands:\n  create <f>  x\n  batch <f>   y\n  view <f>    z\n"
            stderr = ""

        with mock.patch.object(be, "run", return_value=R()):
            self.assertEqual(be.verbs(), {"create", "batch", "view"})
            be.require("create", "batch")
            with self.assertRaisesRegex(BackendUnavailable, "validate"):
                be.require("validate")

    def test_unavailable_message_mentions_legacy_install(self) -> None:
        be = LegacyBatchBackend(exe="placeholder")
        be.exe = None  # constructor auto-discovers; force the missing state
        with self.assertRaisesRegex(BackendUnavailable, "iOfficeAI/OfficeCLI"):
            be._require_exe()


class AgentBridgeV17(unittest.TestCase):
    def test_full_render_roundtrip_against_fake_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            bridge = AgentBridgeBackend(_make_fake_bridge(tmp))
            try:
                pptx = bridge.pptx_generation()  # capabilities/get
                self.assertEqual(pptx["preferred_tool"], "office.render")
                out = tmp / "final" / "draft.pptx"
                payload = {"title": "Probe", "stylePreset": "business",
                           "theme": None, "slides": []}
                status = bridge.render_pptx(payload, out)
                self.assertEqual(status["status"], "completed")
                self.assertTrue(out.exists())          # relocated to exact path
                self.assertEqual(out.read_bytes(), b"FAKEPPTX")
                self.assertTrue(any(
                    e.get("method") == "event" for e in bridge.events
                ))  # interleaved notifications were drained, not lost
            finally:
                bridge.close()

    def test_async_polling_via_task_status(self) -> None:
        """task/invoke → running; completion must come from task/status."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            bridge = AgentBridgeBackend(_make_fake_bridge(tmp, mode="async"))
            try:
                out = tmp / "async.pptx"
                payload = {"title": "Async", "stylePreset": "b",
                           "theme": None, "slides": []}
                status = bridge.render_pptx(payload, out, timeout_s=30)
                self.assertEqual(status["status"], "completed")
                self.assertTrue(out.exists())
            finally:
                bridge.close()

    def test_unknown_terminal_status_is_a_failure(self) -> None:
        """'completed-shaped' but unknown states must not pass as success."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            bridge = AgentBridgeBackend(_make_fake_bridge(tmp, mode="weird"))
            try:
                payload = {"title": "Weird", "stylePreset": "b",
                           "theme": None, "slides": []}
                with self.assertRaisesRegex(BackendUnavailable,
                                            "did not report success"):
                    bridge.render_pptx(payload, tmp / "w.pptx", timeout_s=30)
            finally:
                bridge.close()

    def test_silent_bridge_times_out_instead_of_hanging(self) -> None:
        """A live-but-mute bridge must raise within the call timeout."""
        import time as _time

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            bridge = AgentBridgeBackend(
                _make_fake_bridge(tmp, mode="silent", body=FAKE_SILENT),
                call_timeout=3.0,
            )
            start = _time.monotonic()
            try:
                with self.assertRaisesRegex(BackendUnavailable, "no response"):
                    bridge.capabilities()
                self.assertLess(_time.monotonic() - start, 15.0)
            finally:
                bridge.close()

    def test_unavailable_without_binary(self) -> None:
        bridge = AgentBridgeBackend(exe="placeholder")
        bridge.exe = None  # constructor auto-discovers; force the missing state
        self.assertFalse(bridge.available())
        with self.assertRaisesRegex(BackendUnavailable, "officecli-dist"):
            bridge.capabilities()


class PayloadMappingV17(unittest.TestCase):
    def setUp(self) -> None:
        self.deck = {"version": "1.1", "slides": [
            {"id": "c", "recipe": "cover",
             "content": {"title": "FY26 전략", "subtitle": "부제"}},
            {"id": "k", "recipe": "kpi_row", "content": {"title": "지표", "kpis": [
                {"value": "84.2", "label": "ARR", "chip": "+24%"}]}},
            {"id": "b", "recipe": "bullets",
             "content": {"title": "안건", "bullets": ["하나", "둘"]}},
            {"id": "q", "recipe": "quote",
             "content": {"quote": "속도가 전략이다", "attribution": "CEO"}},
            {"id": "g", "recipe": "chart_insight",
             "content": {"title": "Mix", "chart_type": "pie",
                         "categories": "A,B", "series1_values": "5,3"}},
        ]}

    def test_mapping_and_required_fields(self) -> None:
        payload = deck_to_render_payload(self.deck)
        self.assertEqual(payload["title"], "FY26 전략")
        slides = payload["slides"]
        self.assertTrue(slides[0]["isTitle"])
        self.assertEqual(slides[1]["metrics"],
                         [{"label": "ARR", "value": "84.2", "note": "+24%"}])
        self.assertEqual(slides[2]["points"], ["하나", "둘"])
        self.assertIn("CEO", slides[3]["content"])
        self.assertEqual(slides[4]["chart"]["values"], [5.0, 3.0])
        required = set(_EMPTY_SLIDE)
        for s in slides:  # schema: every slide field is required
            self.assertEqual(set(s), required)

    def test_phase2_recipes_not_empty_points(self) -> None:
        """New premium/domain recipes must not fall into the empty generic else."""
        deck = {"version": "1.1", "slides": [
            {"recipe": "kpi_dashboard_grid", "content": {
                "title": "Dash", "subtitle": "QoQ",
                "kpis": [{"value": "1", "label": "A", "chip": "+1"}],
            }},
            {"recipe": "agenda_toc", "content": {
                "items": [{"number": "01", "label": "Intro", "time": "5m"}],
            }},
            {"recipe": "consort_flow", "content": {
                "stages": [{"label": "Screened", "n": "N=10"}],
            }},
            {"recipe": "forest_plot", "content": {
                "studies": [{"label": "S1", "text": "0.8 (0.6–1.0)"}],
            }},
            {"recipe": "chart_callout_panel", "content": {
                "title": "C", "categories": "A,B", "series1_values": "1,2",
                "callouts": ["One", "Two"],
            }},
            {"recipe": "kaplan_meier", "content": {
                "categories": "0,12", "series1_values": "100,80",
                "insight": "HR 0.8",
            }},
        ]}
        slides = deck_to_render_payload(deck)["slides"]
        self.assertEqual(slides[0]["metrics"][0]["value"], "1")
        self.assertEqual(slides[0]["content"], "QoQ")
        self.assertTrue(slides[1]["points"] and "Intro" in slides[1]["points"][0])
        self.assertTrue(slides[2]["points"] and "Screened" in slides[2]["points"][0])
        self.assertTrue(slides[3]["points"] and "S1" in slides[3]["points"][0])
        self.assertEqual(slides[4]["points"], ["One", "Two"])
        self.assertEqual(slides[4]["chart"]["values"], [1.0, 2.0])
        self.assertEqual(slides[5]["chart"]["type"], "line")
        self.assertIn("HR", slides[5]["content"])

    def test_tokens_to_bridge_theme(self) -> None:
        from designmd_pptx.compile import compile_design_md

        fixtures = Path(__file__).resolve().parent.parent / "fixtures"
        theme = tokens_to_bridge_theme(compile_design_md(fixtures / "linear.DESIGN.md"))
        self.assertEqual(len(theme), 10)
        self.assertTrue(theme["primaryColor"].startswith("#"))
        self.assertEqual(theme["eaFontFamily"], "Malgun Gothic")
        self.assertEqual(theme["backgroundType"], "solid")


class CliV17(unittest.TestCase):
    def test_render_parser(self) -> None:
        from designmd_pptx.__main__ import build_parser

        args = build_parser().parse_args(
            ["render", "brief.md", "-o", "x.pptx", "--design", "default", "--images"]
        )
        self.assertTrue(args.images)
        self.assertEqual(args.design, "default")

    def test_doctor_still_green(self) -> None:
        from designmd_pptx.__main__ import main

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["doctor"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
