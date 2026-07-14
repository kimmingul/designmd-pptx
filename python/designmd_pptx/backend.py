"""OfficeCLI backend abstraction (v1.7 — issues #25/#26/#27/#28).

Two generations of OfficeCLI, one contract:

- LegacyBatchBackend — the shape-level binary (iOfficeAI lineage). All
  subprocess calls and stdout parsing for the precision pipeline live here.
- AgentBridgeBackend — the official `officecli/officecli` agent-bridge:
  JSON-RPC 2.0 over stdio with Content-Length framing, capability-first
  (`initialize` → `capabilities/get`), `office.render` for outline→deck.

Binaries are identified by PROBING (`--version` shape), never by name —
both generations install as `officecli`, and a broken npm shim can shadow
the legacy binary on PATH. See docs/officecli-backends.md.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

# Sourced from compatibility.json (issue #8) — the single place a version is
# pinned. Falls back to a literal only if the manifest is absent/corrupt.
from .compat import official_min_version as _official_min_version

OFFICIAL_MIN_VERSION = _official_min_version()
_LEGACY_DEFAULT_WIN = Path.home() / "AppData" / "Local" / "OfficeCLI" / "officecli.exe"
# doctor --install / install-codex.ps1 place the official binary here when
# npm is unavailable. NOT plain "officecli/" — Windows paths are
# case-insensitive, so that would be the SAME directory as the legacy install
# ("OfficeCLI/") and clobber it.
_OFFICIAL_DEFAULT_WIN = (
    Path.home() / "AppData" / "Local" / "officecli-official" / "officecli.exe"
)


def _official_default_paths() -> list[Path]:
    """Known install locations for the official agent-bridge binary."""
    paths: list[Path] = []
    if os.name == "nt":
        paths.append(_OFFICIAL_DEFAULT_WIN)
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            paths.append(Path(xdg) / "designmd-pptx" / "officecli-official" / "officecli")
        paths.append(
            Path.home() / ".local" / "share" / "designmd-pptx" / "officecli-official" / "officecli"
        )
        paths.append(Path.home() / ".local" / "bin" / "officecli")
    return paths


class BackendUnavailable(RuntimeError):
    """The requested backend / capability is not available on this machine."""


_RUNNING_STATES = frozenset({"running", "pending", "queued", "started"})
_SUCCESS_STATES = frozenset({"completed", "succeeded", "success", "done"})


# ---------------------------------------------------------------- discovery

def classify_binary(exe: str) -> str | None:
    """'official' | 'legacy' | None, by probing --version output.

    A broken shim on PATH must degrade to None, never crash or stall
    discovery — hence the short timeout and the broad probe-failure net."""
    try:
        r = subprocess.run(
            [exe, "--version"], capture_output=True, text=True, timeout=8,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError,
            ValueError):
        return None
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        return None
    if out.startswith("officecli version"):
        return "official"
    if re.match(r"^\d+\.\d+\.\d+", out):
        return "legacy"
    return None


def _candidates() -> list[str]:
    seen: list[str] = []
    for env in ("OFFICECLI_LEGACY_BIN", "OFFICECLI_BRIDGE_BIN"):
        v = os.environ.get(env)
        if v and v not in seen:
            seen.append(v)
    for d in os.environ.get("PATH", "").split(os.pathsep):
        for name in ("officecli.exe", "officecli.cmd", "officecli"):
            p = Path(d) / name
            if p.is_file() and str(p) not in seen:
                seen.append(str(p))
    for default in (_LEGACY_DEFAULT_WIN, *_official_default_paths()):
        if default.is_file() and str(default) not in seen:
            seen.append(str(default))
    return seen


_BINARIES_CACHE: dict[str, str] | None = None


def find_binaries(*, refresh: bool = False) -> dict[str, str]:
    """{'legacy': exe?, 'official': exe?} — env overrides win, then PATH scan.

    Cached per process: probing runs a subprocess per candidate, and doctor
    plus both backends would otherwise re-discover independently."""
    global _BINARIES_CACHE
    if _BINARIES_CACHE is not None and not refresh:
        return dict(_BINARIES_CACHE)
    found: dict[str, str] = {}
    legacy_env = os.environ.get("OFFICECLI_LEGACY_BIN")
    bridge_env = os.environ.get("OFFICECLI_BRIDGE_BIN")
    if legacy_env and classify_binary(legacy_env) == "legacy":
        found["legacy"] = legacy_env
    if bridge_env and classify_binary(bridge_env) == "official":
        found["official"] = bridge_env
    probed: set[str] = set()
    for exe in _candidates():
        if len(found) == 2:
            break
        key = os.path.normcase(os.path.normpath(exe))
        if key in probed:
            continue
        probed.add(key)
        kind = classify_binary(exe)
        if kind and kind not in found:
            found[kind] = exe
    _BINARIES_CACHE = dict(found)
    return dict(found)


# ------------------------------------------------------------------ contract

class OfficeCliBackend(ABC):
    name: str = "abstract"

    @abstractmethod
    def available(self) -> bool: ...


# --------------------------------------------------------------- legacy batch

def _issues_are_clean(stdout: str) -> bool:
    text = stdout or ""
    if re.search(r"Found\s+0\s+issue", text, re.I):
        return True
    if re.search(r"\[[OCSF]\d+\]", text):
        return False
    if '"Count"' in text or '"count"' in text:
        m = re.search(r'"Count"\s*:\s*(\d+)', text) or re.search(r'"count"\s*:\s*(\d+)', text)
        if m:
            return int(m.group(1)) == 0
    if "issue" in text.lower() and re.search(r"\b0\b", text):
        return True
    if not text.strip():
        return True
    if "no issue" in text.lower():
        return True
    return "Found" not in text


class LegacyBatchBackend(OfficeCliBackend):
    """Shape-level precision path. The ONLY place that shells out to the
    legacy binary or parses its human-readable stdout."""

    name = "legacy-batch"

    def __init__(self, exe: str | None = None):
        self.exe = exe or find_binaries().get("legacy")
        self._verbs: set[str] | None = None

    def available(self) -> bool:
        return bool(self.exe)

    def _require_exe(self) -> str:
        if not self.exe:
            raise BackendUnavailable(
                "legacy OfficeCLI binary not found — install from "
                "https://github.com/iOfficeAI/OfficeCLI/releases or set "
                "OFFICECLI_LEGACY_BIN (needed for the shape-level pipeline; "
                "the official officecli npm package is outline-only)"
            )
        return self.exe

    def run(self, args: list[str], *, input_text: str | None = None
            ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self._require_exe(), *args],
            input=input_text, capture_output=True, text=True, check=False,
            encoding="utf-8", errors="replace",
        )

    # capability-first (#26): never assume a verb exists
    def verbs(self) -> set[str]:
        if self._verbs is None:
            r = self.run(["--help"])
            text = (r.stdout or "") + (r.stderr or "")
            self._verbs = set(re.findall(r"^\s{2,}(\w[\w-]*)\b", text, re.M))
        return self._verbs

    def require(self, *verbs: str) -> None:
        """Better-error gate, not a blocker: when help output can't be parsed
        at all (empty verb set), let the actual command surface the failure
        instead of false-negatively rejecting a working binary."""
        known = self.verbs()
        if not known:
            return
        missing = [v for v in verbs if v not in known]
        if missing:
            raise BackendUnavailable(
                f"legacy OfficeCLI at {self.exe} lacks required command(s) "
                f"{missing} — upgrade it (designmd-pptx needs create/batch/"
                "validate/view for the precision pipeline)"
            )

    # operations used by apply.py
    def create(self, pptx: Path) -> subprocess.CompletedProcess:
        return self.run(["create", str(pptx)])

    def open(self, pptx: Path) -> subprocess.CompletedProcess:
        return self.run(["open", str(pptx)])

    def batch(self, pptx: Path, batch_file: Path) -> subprocess.CompletedProcess:
        return self.run(["batch", str(pptx), str(batch_file)])

    def batch_stdin(self, pptx: Path, ops: list[dict]) -> subprocess.CompletedProcess:
        return self.run(["batch", str(pptx)], input_text=json.dumps(ops))

    def save(self, pptx: Path) -> subprocess.CompletedProcess:
        return self.run(["save", str(pptx)])

    def validate(self, pptx: Path) -> subprocess.CompletedProcess:
        return self.run(["validate", str(pptx)])

    def issues_output(self, pptx: Path) -> str:
        r = self.run(["view", str(pptx), "issues"])
        return (r.stdout or "") + (r.stderr or "")

    def issues_clean(self, output: str) -> bool:
        return _issues_are_clean(output)

    def screenshot(self, pptx: Path, out_png: Path, *, grid: bool = True
                   ) -> subprocess.CompletedProcess:
        args = ["view", str(pptx), "screenshot"]
        if grid:
            args.append("--grid")
        args += ["-o", str(out_png)]
        return self.run(args)

    def close(self, pptx: Path) -> subprocess.CompletedProcess:
        return self.run(["close", str(pptx)])


# --------------------------------------------------------------- agent bridge

class AgentBridgeBackend(OfficeCliBackend):
    """Official officecli agent-bridge (JSON-RPC 2.0 / stdio / Content-Length).

    Capability-first: callers should consult capabilities() before invoking;
    render_pptx() checks document_generation.pptx support itself.
    """

    name = "agent-bridge"

    _MAX_HEADER = 8192
    _MAX_BODY = 64 * 1024 * 1024

    def __init__(self, exe: str | None = None, *, call_timeout: float = 60.0):
        self.exe = exe or find_binaries().get("official")
        self.call_timeout = call_timeout
        self._proc: subprocess.Popen | None = None
        self._id = 0
        self._caps: dict[str, Any] | None = None
        self.events: list[dict] = []
        self._lock = __import__("threading").RLock()
        self._queue: Any = None  # queue.Queue fed by the reader thread

    def available(self) -> bool:
        return bool(self.exe)

    # -- transport -----------------------------------------------------------
    # A dedicated reader thread feeds a queue so every wait is TIMED — a
    # silent or crashed bridge raises BackendUnavailable instead of blocking
    # forever (adversarial review finding #1); the transaction lock keeps
    # concurrent callers from consuming each other's responses (#9).

    def _ensure_proc(self) -> subprocess.Popen:
        if self._proc is None or self._proc.poll() is not None:
            if not self.exe:
                raise BackendUnavailable(
                    "official officecli not found — install with "
                    "`npm install -g officecli` or download from "
                    "https://github.com/officecli/officecli-dist/releases, "
                    "or set OFFICECLI_BRIDGE_BIN"
                )
            import queue
            import threading

            self._proc = subprocess.Popen(
                [self.exe, "agent-bridge"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            self._id = 0
            self._queue = queue.Queue()
            threading.Thread(
                target=self._reader_loop, args=(self._proc, self._queue),
                daemon=True,
            ).start()
            init = self._call("initialize", {
                "clientInfo": {"name": "designmd-pptx", "version": "2.1.2"},
            })
            self._caps = None
            self._server = init
        return self._proc

    @staticmethod
    def _frame(payload: dict) -> bytes:
        body = json.dumps(payload).encode("utf-8")
        return f"Content-Length: {len(body)}\r\n\r\n".encode() + body

    @classmethod
    def _read_framed(cls, stream) -> dict:
        header = b""
        while b"\r\n\r\n" not in header:
            if len(header) > cls._MAX_HEADER:
                raise BackendUnavailable("agent-bridge: unframed garbage on stdout")
            chunk = stream.read(1)
            if not chunk:
                raise BackendUnavailable("agent-bridge closed unexpectedly")
            header += chunk
        length = 0
        for line in header.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":")[1].strip())
        if not 0 < length <= cls._MAX_BODY:
            raise BackendUnavailable(f"agent-bridge: bad frame length {length}")
        body = b""
        while len(body) < length:
            chunk = stream.read(length - len(body))
            if not chunk:
                raise BackendUnavailable("agent-bridge closed mid-message")
            body += chunk
        return json.loads(body.decode("utf-8"))

    @classmethod
    def _reader_loop(cls, proc: subprocess.Popen, out_queue) -> None:
        try:
            while True:
                out_queue.put(cls._read_framed(proc.stdout))
        except Exception as e:  # EOF / kill / garbage — deliver to the waiter
            out_queue.put({"__reader_error__": str(e)})

    def _call(self, method: str, params: dict | None = None,
              *, timeout: float | None = None) -> dict:
        """One request/response transaction; events are drained, waits are timed."""
        import queue
        import time as _time

        with self._lock:
            if method != "initialize":
                self._ensure_proc()
            self._id += 1
            rid = self._id
            try:
                self._proc.stdin.write(self._frame(
                    {"jsonrpc": "2.0", "id": rid, "method": method,
                     "params": params or {}}
                ))
                self._proc.stdin.flush()
            except OSError as e:
                self.close()
                raise BackendUnavailable(f"agent-bridge write failed: {e}")

            deadline = _time.monotonic() + (timeout or self.call_timeout)
            while True:
                remaining = deadline - _time.monotonic()
                if remaining <= 0:
                    self.close()
                    raise BackendUnavailable(
                        f"agent-bridge {method}: no response within "
                        f"{timeout or self.call_timeout:.0f}s (bridge killed)"
                    )
                try:
                    msg = self._queue.get(timeout=min(remaining, 1.0))
                except queue.Empty:
                    continue
                if "__reader_error__" in msg:
                    self.close()
                    raise BackendUnavailable(
                        f"agent-bridge transport failed: {msg['__reader_error__']}"
                    )
                if msg.get("id") == rid:
                    if "error" in msg:
                        raise BackendUnavailable(
                            f"agent-bridge {method} failed: {msg['error']}"
                        )
                    return msg.get("result", {})
                self.events.append(msg)  # notification / interleaved event

    # -- capability-first ----------------------------------------------------
    def capabilities(self) -> dict[str, Any]:
        if self._caps is None:
            self._ensure_proc()
            self._caps = self._call("capabilities/get")
        return self._caps

    def pptx_generation(self) -> dict[str, Any]:
        caps = self.capabilities()
        pptx = (caps.get("document_generation") or {}).get("pptx")
        if not isinstance(pptx, dict) or not pptx.get("agent_render_supported"):
            raise BackendUnavailable(
                "agent-bridge does not advertise document_generation.pptx "
                "render support (capabilities/get)"
            )
        return pptx

    # -- operations ----------------------------------------------------------
    def render_pptx(self, payload: dict, out_path: Path, *,
                    enable_images: bool = False, publish: bool = False,
                    timeout_s: float = 600.0) -> dict:
        """office.render, envelope {tool, args} (verified against 0.2.117).

        task/invoke is asynchronous: it returns {task_id, status:"running"};
        we poll task/status (which also drains interleaved event
        notifications) until the task leaves the running states."""
        import time

        pptx = self.pptx_generation()
        tool = pptx.get("preferred_tool", "office.render")
        out_path = Path(out_path)
        # the bridge treats `out` as a DIRECTORY and names the artifact
        # <payload title>.pptx; we relocate to the exact requested path below
        args: dict[str, Any] = {
            "document_type": "pptx",
            "out": str(out_path.parent.resolve()),
            "payload": payload,
            "publish": publish,
        }
        img = pptx.get("image_support") or {}
        args[img.get("invoke_field", "enable_images")] = enable_images
        started = self._call("task/invoke", {"tool": tool, "args": args})
        task_id = started.get("task_id")
        status = started
        if task_id:
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                state = str(status.get("status") or status.get("state") or "").lower()
                if state and state not in _RUNNING_STATES:
                    break
                time.sleep(1.5)
                status = self._call("task/status", {"task_id": task_id})
            state = str(status.get("status") or status.get("state") or "").lower()
            if state in _RUNNING_STATES:
                self.close()
                raise BackendUnavailable(
                    f"agent-bridge render timed out after {timeout_s:.0f}s (task {task_id})"
                )
        # single completion validator for BOTH the sync and async paths —
        # unknown states are failures, and success without an artifact is too
        return self._finalize_render(status, out_path)

    @staticmethod
    def _finalize_render(status: dict, out_path: Path) -> dict:
        result = status.get("result") or {}
        state = str(status.get("status") or status.get("state") or "").lower()
        inner = str(result.get("status") or "").lower()
        if state not in _SUCCESS_STATES and inner not in _SUCCESS_STATES:
            raise BackendUnavailable(
                f"agent-bridge render did not report success: "
                f"{json.dumps(status, ensure_ascii=False)[:300]}"
            )
        produced = result.get("file_path")
        if produced and Path(produced).exists():
            if Path(produced).resolve() != out_path.resolve():
                out_path.parent.mkdir(parents=True, exist_ok=True)
                # shutil.move survives cross-volume relocation; os.replace doesn't
                shutil.move(str(produced), str(out_path))
        if not out_path.is_file():
            raise BackendUnavailable(
                f"agent-bridge reported success but no artifact exists at {out_path} "
                f"(bridge result: {json.dumps(result, ensure_ascii=False)[:200]})"
            )
        if isinstance(status.get("result"), dict):
            status["result"]["file_path"] = str(out_path)
        return status

    def close(self) -> None:
        """Tear the bridge down completely: pipes closed, process TREE ended
        (npm .cmd shims spawn a child node process), no zombies, no
        ResourceWarnings (adversarial review finding #3)."""
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except OSError:
            pass
        if proc.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                        capture_output=True, timeout=10,
                    )
                else:
                    proc.terminate()
                proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
                try:
                    proc.kill()
                    proc.wait(timeout=3)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        try:
            if proc.stdout:
                proc.stdout.close()
        except OSError:
            pass


# ----------------------------------------------------- deck-spec → render payload

_EMPTY_SLIDE: dict[str, Any] = {
    "title": "", "content": "", "isTitle": False, "layout": "", "variant": "",
    "narrativeRole": "", "sectionIndex": 0, "sectionTitle": "", "subtitle": "",
    "points": [], "sections": [], "chart": None, "metrics": [], "source": "",
    "bgColor": "", "bgColor2": "", "hasImage": False, "imagePrompt": "",
    "imagePos": "", "visuals": [],
}


def _floats(csv: str) -> list[float]:
    out = []
    for tok in str(csv).split(","):
        try:
            out.append(float(tok.strip()))
        except ValueError:
            out.append(0.0)
    return out


def tokens_to_bridge_theme(tokens: dict[str, Any]) -> dict[str, str]:
    """DESIGN.md tokens → the bridge's theme object (all fields required).

    This is the surprise win of the agent-bridge investigation: brand colors
    and fonts DO carry over to the outline path, including an East-Asian
    font slot (eaFontFamily) for Korean/Japanese/Chinese decks."""
    c = tokens.get("colors") or {}
    t = tokens.get("type") or {}

    def hx(key: str, fallback: str) -> str:
        v = str(c.get(key) or fallback)
        return v if v.startswith("#") else f"#{v}"

    return {
        "primaryColor": hx("accent", "2563EB"),
        "accentColor": hx("accent", "2563EB"),
        "highlightColor": hx("success", c.get("accent", "16A34A")),
        "backgroundType": "solid",
        "bgColor1": hx("background", "FFFFFF"),
        "bgColor2": hx("surface", c.get("background", "F6F8FA")),
        "textColor": hx("text", "111827"),
        "titleTextColor": hx("text", "111827"),
        "fontFamily": str(t.get("body_font", "Calibri")),
        "eaFontFamily": str(t.get("ea_font", "Malgun Gothic")),
    }


def deck_to_render_payload(deck: dict[str, Any], *, title: str | None = None,
                           style_preset: str = "business",
                           theme: dict[str, str] | None = None) -> dict[str, Any]:
    """Map a designmd deck-spec onto the official office.render payload.

    This is deliberately lossy — the official schema is outline-level (see
    docs/officecli-backends.md). Precise geometry stays with the legacy path.
    """
    slides_out: list[dict[str, Any]] = []
    deck_title = title or ""
    for s in deck.get("slides") or []:
        recipe = s.get("recipe")
        c = s.get("content") or {}
        out = dict(_EMPTY_SLIDE)
        out["title"] = str(c.get("title") or "")
        if recipe == "cover":
            out.update(isTitle=True, subtitle=str(c.get("subtitle") or ""))
            deck_title = deck_title or out["title"]
        elif recipe == "section_divider":
            out.update(layout="section", content=str(c.get("blurb") or ""))
        elif recipe in ("bullets", "close"):
            pts = c.get("bullets") or c.get("items") or []
            if recipe == "close":
                pts = [p for p in (c.get("body"), c.get("cta")) if p]
            out["points"] = [str(p) for p in pts]
        elif recipe in ("kpi_row", "kpi_3", "kpi_dashboard_grid"):
            out["metrics"] = [
                {"label": str(k.get("label", "")), "value": str(k.get("value", "")),
                 "note": str(k.get("chip", "") or "")}
                for k in c.get("kpis") or []
            ]
            if recipe == "kpi_dashboard_grid" and c.get("subtitle"):
                out["content"] = str(c.get("subtitle") or "")
        elif recipe == "big_number":
            out["metrics"] = [{
                "label": str(c.get("label", "")), "value": str(c.get("value", "")),
                "note": str(c.get("context", "") or ""),
            }]
        elif recipe in ("feature_cards", "feature_cards_3"):
            out["sections"] = [
                {"heading": str(card.get("title", "")), "detail": str(card.get("body", ""))}
                for card in c.get("cards") or []
            ]
        elif recipe == "comparison_2col":
            out["sections"] = [
                {"heading": str((c.get(side) or {}).get("title", "")),
                 "detail": str((c.get(side) or {}).get("body", ""))}
                for side in ("left", "right")
            ]
        elif recipe in ("chart_insight", "chart_callout_panel", "kaplan_meier"):
            out["chart"] = {
                "title": str(c.get("title", "Chart")),
                "type": str(c.get("chart_type", "line" if recipe == "kaplan_meier" else "column")),
                "categories": [
                    x.strip()
                    for x in str(c.get("categories", "")).split(",")
                    if x.strip()
                ],
                "values": _floats(c.get("series1_values", "")),
            }
            if recipe == "chart_callout_panel":
                callouts = c.get("callouts") or c.get("bullets") or []
                out["points"] = [str(p) for p in callouts]
            else:
                out["content"] = str(
                    c.get("insight_body") or c.get("insight") or ""
                )
        elif recipe == "quote":
            att = c.get("attribution")
            out["content"] = f"“{c.get('quote', '')}”" + (f" — {att}" if att else "")
        elif recipe in ("table", "appendix_table", "results_table_insight"):
            headers = [str(h) for h in c.get("headers") or []]
            rows = c.get("rows") or []
            lines = [" | ".join(headers)] if headers else []
            lines += [" | ".join(str(x) for x in r) for r in rows]
            out["content"] = "\n".join(lines)
            if recipe == "results_table_insight":
                insight = c.get("insight_body") or c.get("insight") or ""
                if insight:
                    out["content"] = (out["content"] + "\n\n" + str(insight)).strip()
        elif recipe in ("image_full", "image_text_2col", "multi_panel_figure"):
            if recipe == "multi_panel_figure":
                panels = c.get("panels") or c.get("figures") or []
                pts = []
                for p in panels:
                    if isinstance(p, dict):
                        pts.append(
                            f"{p.get('label', '')}: {p.get('caption') or p.get('alt') or ''}".strip(": ")
                        )
                    else:
                        pts.append(str(p))
                out["points"] = pts
            else:
                out["content"] = str(c.get("body", "") or c.get("caption", "") or "")
                alt = str(c.get("alt", "") or "")
                if alt:
                    out["visuals"] = [{"label": alt, "prompt": alt, "caption": alt}]
        elif recipe == "agenda_toc":
            items = c.get("items") or c.get("entries") or []
            pts = []
            for it in items:
                if isinstance(it, dict):
                    num = it.get("number") or ""
                    label = it.get("label") or it.get("title") or ""
                    time = it.get("time") or it.get("duration") or ""
                    pts.append(
                        f"{num} {label}".strip()
                        + (f" ({time})" if time else "")
                    )
                else:
                    pts.append(str(it))
            out["points"] = pts
        elif recipe in ("section_opener_numbered",):
            out.update(
                layout="section",
                content=str(c.get("blurb") or ""),
                title=str(c.get("title") or ""),
            )
            if c.get("number") is not None:
                out["content"] = (
                    f"{c.get('number')}. {out['content']}".strip(". ")
                )
        elif recipe == "vs_scorecard":
            left = c.get("left") or c.get("option_a") or {}
            right = c.get("right") or c.get("option_b") or {}
            if not isinstance(left, dict):
                left = {"title": str(left)}
            if not isinstance(right, dict):
                right = {"title": str(right)}
            out["sections"] = [
                {"heading": str(left.get("title", "A")), "detail": ""},
                {"heading": str(right.get("title", "B")), "detail": ""},
            ]
            crit = c.get("criteria") or c.get("rows") or []
            pts = []
            for row in crit:
                if isinstance(row, dict):
                    pts.append(
                        f"{row.get('name') or row.get('label')}: "
                        f"{row.get('left') or row.get('a')} vs "
                        f"{row.get('right') or row.get('b')}"
                    )
                else:
                    pts.append(str(row))
            out["points"] = pts
        elif recipe == "forest_plot":
            studies = c.get("studies") or c.get("rows") or []
            pts = []
            for row in studies:
                if isinstance(row, dict):
                    pts.append(
                        f"{row.get('label') or row.get('study')}: "
                        f"{row.get('text') or row.get('ci') or row.get('effect', '')}"
                    )
                else:
                    pts.append(str(row))
            out["points"] = pts
        elif recipe in ("consort_flow", "funnel_stages", "pyramid_levels"):
            items = c.get("stages") or c.get("levels") or c.get("steps") or []
            pts = []
            for it in items:
                if isinstance(it, dict):
                    label = it.get("label") or it.get("title") or ""
                    extra = it.get("n") or it.get("value") or it.get("detail") or ""
                    pts.append(f"{label} — {extra}".strip(" —"))
                else:
                    pts.append(str(it))
            out["points"] = pts
        elif recipe == "study_design":
            phases = c.get("phases") or []
            arms = c.get("arms") or c.get("groups") or []
            pts = []
            for it in phases:
                if isinstance(it, dict):
                    pts.append(
                        f"{it.get('label') or it.get('title')}: "
                        f"{it.get('detail') or it.get('body') or ''}".strip(": ")
                    )
                else:
                    pts.append(str(it))
            for it in arms:
                if isinstance(it, dict):
                    pts.append(
                        f"Arm {it.get('label') or it.get('name')}: "
                        f"{it.get('detail') or ''}".strip(": ")
                    )
                else:
                    pts.append(str(it))
            out["points"] = pts
        elif recipe == "roadmap_swimlane":
            phases = c.get("phases") or c.get("columns") or []
            lanes = c.get("lanes") or c.get("rows") or []
            pts = [f"Phases: {', '.join(str(p) for p in phases)}"] if phases else []
            for lane in lanes:
                if isinstance(lane, dict):
                    cells = lane.get("cells") or lane.get("items") or []
                    pts.append(
                        f"{lane.get('name') or lane.get('label')}: "
                        f"{', '.join(str(x) for x in cells)}"
                    )
                else:
                    pts.append(str(lane))
            out["points"] = pts
        else:  # process / timeline / story_timeline / team / pricing / matrix …
            items = (
                c.get("steps")
                or c.get("members")
                or c.get("tiers")
                or c.get("logos")
                or c.get("quadrants")
                or []
            )
            pts = []
            for it in items:
                if isinstance(it, dict):
                    label = (
                        it.get("label")
                        or it.get("name")
                        or it.get("title")
                        or it.get("date")
                        or ""
                    )
                    detail = (
                        it.get("detail")
                        or it.get("body")
                        or it.get("role")
                        or it.get("price")
                        or it.get("text")
                        or ""
                    )
                    pts.append(f"{label} — {detail}".strip(" —"))
                else:
                    pts.append(str(it))
            out["points"] = pts
        slides_out.append(out)

    return {
        "title": deck_title or "Presentation",
        "stylePreset": style_preset,
        "theme": theme,  # object per payload_schema, or None for house default
        "slides": slides_out,
    }
