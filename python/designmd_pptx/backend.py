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

OFFICIAL_MIN_VERSION = "0.2.117"
_LEGACY_DEFAULT_WIN = Path.home() / "AppData" / "Local" / "OfficeCLI" / "officecli.exe"
# install-codex.ps1 places the official binary here when npm is unavailable.
# NOT "officecli/" — Windows paths are case-insensitive, so that would be the
# SAME directory as the legacy install ("OfficeCLI/") and clobber it.
_OFFICIAL_DEFAULT_WIN = (
    Path.home() / "AppData" / "Local" / "officecli-official" / "officecli.exe"
)


class BackendUnavailable(RuntimeError):
    """The requested backend / capability is not available on this machine."""


# ---------------------------------------------------------------- discovery

def classify_binary(exe: str) -> str | None:
    """'official' | 'legacy' | None, by probing --version output."""
    try:
        r = subprocess.run(
            [exe, "--version"], capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace",
        )
    except OSError:
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
    for default in (_LEGACY_DEFAULT_WIN, _OFFICIAL_DEFAULT_WIN):
        if default.is_file() and str(default) not in seen:
            seen.append(str(default))
    return seen


def find_binaries() -> dict[str, str]:
    """{'legacy': exe?, 'official': exe?} — env overrides win, then PATH scan."""
    found: dict[str, str] = {}
    legacy_env = os.environ.get("OFFICECLI_LEGACY_BIN")
    bridge_env = os.environ.get("OFFICECLI_BRIDGE_BIN")
    if legacy_env and classify_binary(legacy_env) == "legacy":
        found["legacy"] = legacy_env
    if bridge_env and classify_binary(bridge_env) == "official":
        found["official"] = bridge_env
    for exe in _candidates():
        if len(found) == 2:
            break
        kind = classify_binary(exe)
        if kind and kind not in found:
            found[kind] = exe
    return found


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
            self._verbs = set(
                re.findall(r"^  (\w[\w-]*)\b", r.stdout or "", re.M)
            )
        return self._verbs

    def require(self, *verbs: str) -> None:
        missing = [v for v in verbs if v not in self.verbs()]
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

    def __init__(self, exe: str | None = None):
        self.exe = exe or find_binaries().get("official")
        self._proc: subprocess.Popen | None = None
        self._id = 0
        self._caps: dict[str, Any] | None = None
        self.events: list[dict] = []

    def available(self) -> bool:
        return bool(self.exe)

    # -- transport -----------------------------------------------------------
    def _ensure_proc(self) -> subprocess.Popen:
        if self._proc is None or self._proc.poll() is not None:
            if not self.exe:
                raise BackendUnavailable(
                    "official officecli not found — install with "
                    "`npm install -g officecli` or download from "
                    "https://github.com/officecli/officecli-dist/releases, "
                    "or set OFFICECLI_BRIDGE_BIN"
                )
            self._proc = subprocess.Popen(
                [self.exe, "agent-bridge"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            self._id = 0
            init = self._call("initialize", {
                "clientInfo": {"name": "designmd-pptx", "version": "1.7.0"},
            })
            self._caps = None
            self._server = init
        return self._proc

    @staticmethod
    def _frame(payload: dict) -> bytes:
        body = json.dumps(payload).encode("utf-8")
        return f"Content-Length: {len(body)}\r\n\r\n".encode() + body

    def _read_message(self) -> dict:
        stream = self._proc.stdout
        header = b""
        while b"\r\n\r\n" not in header:
            chunk = stream.read(1)
            if not chunk:
                raise BackendUnavailable("agent-bridge closed unexpectedly")
            header += chunk
        length = 0
        for line in header.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":")[1].strip())
        body = b""
        while len(body) < length:
            chunk = stream.read(length - len(body))
            if not chunk:
                raise BackendUnavailable("agent-bridge closed mid-message")
            body += chunk
        return json.loads(body.decode("utf-8"))

    def _call(self, method: str, params: dict | None = None,
              *, max_messages: int = 10_000) -> dict:
        """Send one request; collect event notifications until our response."""
        if method != "initialize":
            self._ensure_proc()
        self._id += 1
        rid = self._id
        self._proc.stdin.write(self._frame(
            {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
        ))
        self._proc.stdin.flush()
        for _ in range(max_messages):
            msg = self._read_message()
            if msg.get("id") == rid:
                if "error" in msg:
                    raise BackendUnavailable(
                        f"agent-bridge {method} failed: {msg['error']}"
                    )
                return msg.get("result", {})
            self.events.append(msg)  # notification / interleaved event
        raise BackendUnavailable(f"agent-bridge {method}: no response")

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
        if not task_id:
            return started  # synchronous completion

        deadline = time.time() + timeout_s
        status = started
        while time.time() < deadline:
            state = str(status.get("status") or status.get("state") or "").lower()
            if state and state not in ("running", "pending", "queued", "started"):
                break
            time.sleep(1.5)
            status = self._call("task/status", {"task_id": task_id})
        state = str(status.get("status") or status.get("state") or "").lower()
        if state in ("running", "pending", "queued", "started"):
            raise BackendUnavailable(
                f"agent-bridge render timed out after {timeout_s:.0f}s (task {task_id})"
            )
        if state in ("failed", "error", "cancelled", "canceled"):
            raise BackendUnavailable(
                f"agent-bridge render {state}: {json.dumps(status)[:300]}"
            )
        produced = (status.get("result") or {}).get("file_path")
        if produced and Path(produced).exists() and Path(produced) != out_path:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(produced, str(out_path))
            status.setdefault("result", {})["file_path"] = str(out_path)
        return status

    def close(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.kill()
            except OSError:
                pass
        self._proc = None


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
        elif recipe in ("kpi_row", "kpi_3"):
            out["metrics"] = [
                {"label": str(k.get("label", "")), "value": str(k.get("value", "")),
                 "note": str(k.get("chip", "") or "")}
                for k in c.get("kpis") or []
            ]
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
        elif recipe == "chart_insight":
            out["chart"] = {
                "title": str(c.get("title", "Chart")),
                "type": str(c.get("chart_type", "column")),
                "categories": [x.strip() for x in str(c.get("categories", "")).split(",") if x.strip()],
                "values": _floats(c.get("series1_values", "")),
            }
            out["content"] = str(c.get("insight_body", "") or "")
        elif recipe == "quote":
            att = c.get("attribution")
            out["content"] = f"“{c.get('quote', '')}”" + (f" — {att}" if att else "")
        elif recipe in ("table", "appendix_table"):
            headers = [str(h) for h in c.get("headers") or []]
            rows = c.get("rows") or []
            lines = [" | ".join(headers)] if headers else []
            lines += [" | ".join(str(x) for x in r) for r in rows]
            out["content"] = "\n".join(lines)
        elif recipe in ("image_full", "image_text_2col"):
            out["content"] = str(c.get("body", "") or c.get("caption", "") or "")
            alt = str(c.get("alt", "") or "")
            if alt:
                out["visuals"] = [{"label": alt, "prompt": alt, "caption": alt}]
        else:  # process / timeline / team / pricing / matrix / logo_strip …
            items = c.get("steps") or c.get("members") or c.get("tiers") or c.get("logos") or []
            pts = []
            for it in items:
                if isinstance(it, dict):
                    label = it.get("label") or it.get("name") or it.get("title") or ""
                    detail = it.get("detail") or it.get("role") or it.get("price") or ""
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
