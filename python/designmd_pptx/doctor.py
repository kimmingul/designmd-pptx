"""Environment doctor (v1.7 — issues #25/#26): capability-first verification
of BOTH OfficeCLI generations plus per-platform agent skill routing
(Claude Code / Codex / Grok).

Both generations install a binary named `officecli`, so everything here is
identified by probing, never by name — see docs/officecli-backends.md."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from . import compat
from .backend import (AgentBridgeBackend, BackendUnavailable,
                      LegacyBatchBackend, find_binaries)

_LEGACY_REMEDY = (
    "install the legacy shape-level binary from "
    "https://github.com/iOfficeAI/OfficeCLI/releases (or set "
    "OFFICECLI_LEGACY_BIN) — required by scaffold/apply/restyle/master"
)
_OFFICIAL_REMEDY = (
    "install the official officecli: `npm install -g officecli` "
    "(fallback: download from https://github.com/officecli/officecli-dist/"
    "releases, or set OFFICECLI_BRIDGE_BIN) — enables the render command"
)


def _run(exe: str, *args: str, timeout: int = 30) -> tuple[int, str]:
    try:
        r = subprocess.run(
            [exe, *args], capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except OSError as e:
        return 1, str(e)


def _legacy() -> tuple[bool, str]:
    be = LegacyBatchBackend()
    if not be.available():
        return False, _LEGACY_REMEDY
    try:
        be.require("create", "batch", "validate", "view")
    except BackendUnavailable as e:
        return False, str(e)
    _, ver = _run(be.exe, "--version")
    return True, f"v{ver} ({be.exe}) — shape-level pipeline ready"


_SUPPORT_TAG = {
    compat.OK: "supported",
    compat.TOO_OLD: "TOO OLD",
    compat.UNTESTED_NEWER: "untested (newer)",
    compat.UNKNOWN: "version unreadable",
}


def _official() -> tuple[bool, str]:
    exe = find_binaries().get("official")
    if not exe:
        return False, _OFFICIAL_REMEDY
    _, ver = _run(exe, "--version")
    level, why = compat.classify_support("official", ver)
    spec = compat.spec_for("official")
    rc, status = _run(exe, "config", "status")
    note = status.splitlines()[0][:80] if rc == 0 and status else "config status n/a"
    # Too-old is the only version state that fails the check — a newer,
    # untested build is reported but still usable.
    ok = level != compat.TOO_OLD
    detail = (f"{ver} ({exe}) — {_SUPPORT_TAG[level]} "
              f"[{why}; pinned {spec['recommended']}]; {note}")
    if level == compat.TOO_OLD:
        detail += f" — upgrade: {spec['install']}"
    return ok, detail


def _bridge() -> tuple[bool, str]:
    bridge = AgentBridgeBackend()
    if not bridge.available():
        return False, "official binary missing — render command unavailable"
    try:
        pptx = bridge.pptx_generation()
        tool = pptx.get("preferred_tool", "office.render")
        return True, f"capabilities/get ok — document_generation.pptx via {tool}"
    except BackendUnavailable as e:
        return False, f"agent-bridge probe failed: {str(e)[:120]}"
    finally:
        bridge.close()


def _env_check_script() -> tuple[bool, str]:
    script = Path.home() / ".claude" / "skills" / "officecli" / "check-officecli-env.sh"
    if not script.exists():
        return True, "official check-officecli-env.sh not installed (skipped)"
    bash = shutil.which("bash")
    if not bash:
        return True, f"{script.name} present but bash unavailable (skipped)"
    rc, out = _run(bash, str(script), timeout=60)
    tail = out.splitlines()[-1][:100] if out else ""
    return rc == 0, f"{script.name}: {'ok' if rc == 0 else 'FAILED'} — {tail}"


def _pyyaml() -> tuple[bool, str]:
    try:
        import yaml  # noqa: F401

        return True, "importable"
    except ImportError:
        return False, "pip install PyYAML"


def _skill(home: Path, *names: str) -> tuple[bool, str]:
    for name in names:
        for base in (home / "skills",):
            if (base / name / "SKILL.md").exists():
                return True, str(base / name)
    return False, "not installed"


def _claude_designmd(claude: Path) -> tuple[bool, str]:
    hit, msg = _skill(claude, "officecli-pptx-designmd")
    if hit:
        return hit, msg
    plugins = claude / "plugins"
    if plugins.exists():
        for p in plugins.rglob("designmd-pptx*"):
            if p.is_dir():
                return True, str(p)
    return False, (
        "in Claude Code run: /plugin marketplace add kimmingul/designmd-pptx "
        "then /plugin install designmd-pptx@designmd-pptx"
    )


def run_doctor(*, strict: bool = False) -> int:
    from . import __version__

    home = Path.home()
    rows: list[tuple[str, bool, str]] = []

    ok, msg = _legacy()
    rows.append(("officecli (legacy, shape-level)", ok, msg))
    officecli_ok = ok
    ok, msg = _official()
    rows.append(("officecli (official, agent-bridge)", ok, msg))
    if ok:
        ok2, msg2 = _bridge()
        rows.append(("agent-bridge capabilities", ok2, msg2))
    ok, msg = _env_check_script()
    rows.append(("official env check", ok, msg))
    ok, msg = _pyyaml()
    rows.append(("PyYAML", ok, msg))
    rows.append(("designmd_pptx", True, f"v{__version__} ({Path(__file__).parent})"))

    # base skill: official `officecli` first (#25), legacy officecli-pptx fallback
    ok, msg = _skill(home / ".claude", "officecli", "officecli-pptx")
    rows.append(("claude: officecli base skill", ok, msg))
    ok, msg = _claude_designmd(home / ".claude")
    rows.append(("claude: designmd layer", ok, msg))

    ok, msg = _skill(home / ".codex", "officecli", "officecli-pptx")
    if not ok:
        msg = "run scripts/install-codex.ps1 (official installer first)"
    rows.append(("codex: officecli base skill", ok, msg))
    ok, msg = _skill(home / ".codex", "officecli-pptx-designmd")
    if not ok:
        msg = "run scripts/install-codex.ps1"
    rows.append(("codex: designmd layer", ok, msg))

    ok, msg = _skill(home / ".grok", "officecli", "officecli-pptx")
    rows.append(("grok: officecli base skill", ok, msg))
    ok, msg = _skill(home / ".grok", "officecli-pptx-designmd")
    if not ok and (home / ".grok" / "installed-plugins").exists():
        hits = [p for p in (home / ".grok" / "installed-plugins").glob("designmd-pptx*")]
        if hits:
            ok, msg = True, str(hits[0])
    rows.append(("grok: designmd layer", ok, msg))

    failures = 0
    for label, ok, msg in rows:
        mark = "ok  " if ok else "MISS"
        if not ok:
            failures += 1
        print(f"  {mark}  {label}: {msg}")

    if failures:
        print(f"\n{failures} item(s) missing — remedies above")
    else:
        print("\nall checks passed — pptx requests route through officecli on every platform")
    if strict and not officecli_ok:
        return 1  # the shape-level pipeline is the hard requirement
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_doctor(strict="--strict" in sys.argv))
