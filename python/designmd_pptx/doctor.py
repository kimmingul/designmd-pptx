"""Environment doctor (v1.7+ — issues #25/#26/#34): capability-first verification
of BOTH OfficeCLI generations plus per-platform agent skill routing
(Claude Code / Codex / Grok).

``doctor --install`` (issue #34) is an explicit, transparent installer that
pins the official OfficeCLI to the version in ``compatibility.json`` (#8).
Both generations install a binary named `officecli`, so everything here is
identified by probing, never by name — see docs/officecli-backends.md."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import compat
from .backend import (AgentBridgeBackend, BackendUnavailable,
                      LegacyBatchBackend, find_binaries)

_LEGACY_REMEDY = (
    "install the legacy shape-level binary from "
    "https://github.com/iOfficeAI/OfficeCLI/releases (or set "
    "OFFICECLI_LEGACY_BIN) — required by scaffold/apply/restyle/master; "
    "not auto-installable via doctor --install"
)
_OFFICIAL_REMEDY = (
    "run `python -m designmd_pptx doctor --install` (pins the official "
    "officecli from compatibility.json) — or set OFFICECLI_BRIDGE_BIN; "
    "fallback download: https://github.com/officecli/officecli-dist/releases"
)

# Injected by tests; production uses subprocess.run.
_RUN_INSTALL: Callable[..., subprocess.CompletedProcess] | None = None


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
        detail += f" — upgrade: doctor --install  (or {spec['install']})"
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
        return False, "pip install PyYAML  (or: doctor --install)"


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


# ---------------------------------------------------------------------------
# doctor --install (issue #34)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InstallStep:
    """One transparent install / guidance action."""

    id: str
    title: str
    kind: str  # "run" | "manual" | "skip"
    argv: tuple[str, ...]  # empty for manual/skip
    display: str  # shell-ish form printed to the user
    reason: str
    downloads: str  # what package / URL this pulls


def _official_install_argv(spec: dict) -> tuple[str, ...]:
    """Prefer parsing the manifest install string; fall back to recommended pin."""
    install = (spec.get("install") or "").strip()
    if install:
        # e.g. "npm install -g officecli@0.2.117"
        parts = install.split()
        if parts:
            return tuple(parts)
    pinned = spec.get("recommended") or spec.get("min") or "0.2.117"
    return ("npm", "install", "-g", f"officecli@{pinned}")


def _official_needs_install() -> tuple[bool, str]:
    """(needed, reason) for the official pin from compatibility.json."""
    exe = find_binaries().get("official")
    spec = compat.spec_for("official")
    pinned = spec.get("recommended") or spec.get("min") or "?"
    if not exe:
        return True, f"official officecli not found — will install pinned {pinned}"
    _, ver = _run(exe, "--version")
    level, why = compat.classify_support("official", ver)
    if level == compat.TOO_OLD:
        return True, f"installed {ver or '?'} is {why} — upgrade to pinned {pinned}"
    if level == compat.UNKNOWN:
        return True, f"could not parse version from {ver!r} — reinstall pinned {pinned}"
    # OK or UNTESTED_NEWER: leave alone (don't downgrade a newer build)
    return False, f"already present ({ver}) — {_SUPPORT_TAG[level]} [{why}]"


def _pyyaml_needs_install() -> tuple[bool, str]:
    ok, msg = _pyyaml()
    if ok:
        return False, "already importable"
    return True, "PyYAML not importable"


def plan_install() -> list[InstallStep]:
    """Build the explicit install plan from current probes + compatibility.json.

    Never silent: every step is listed even when skipped. Legacy is always
    manual (rolling/unversioned upstream; no safe npm pin).
    """
    steps: list[InstallStep] = []
    spec = compat.spec_for("official")
    pinned = spec.get("recommended") or spec.get("min") or "?"
    argv = _official_install_argv(spec)
    need, reason = _official_needs_install()
    npm = shutil.which("npm")
    if need and not npm:
        steps.append(InstallStep(
            id="official",
            title="official officecli (agent-bridge)",
            kind="manual",
            argv=(),
            display=spec.get("install") or " ".join(argv),
            reason=(
                f"{reason}; npm not on PATH — install Node/npm, then re-run, "
                f"or download from https://github.com/officecli/officecli-dist/releases "
                f"(or set OFFICECLI_BRIDGE_BIN)"
            ),
            downloads=f"officecli@{pinned} (npm registry) or officecli-dist release asset",
        ))
    elif need:
        steps.append(InstallStep(
            id="official",
            title="official officecli (agent-bridge)",
            kind="run",
            argv=argv,
            display=" ".join(argv),
            reason=reason,
            downloads=f"officecli@{pinned} from the npm registry (global)",
        ))
    else:
        steps.append(InstallStep(
            id="official",
            title="official officecli (agent-bridge)",
            kind="skip",
            argv=(),
            display=" ".join(argv),
            reason=reason,
            downloads=f"officecli@{pinned} (not downloaded — already ok)",
        ))

    need_y, reason_y = _pyyaml_needs_install()
    pip_argv = (sys.executable, "-m", "pip", "install", "PyYAML")
    if need_y:
        steps.append(InstallStep(
            id="pyyaml",
            title="PyYAML",
            kind="run",
            argv=pip_argv,
            display=" ".join(pip_argv),
            reason=reason_y,
            downloads="PyYAML from PyPI",
        ))
    else:
        steps.append(InstallStep(
            id="pyyaml",
            title="PyYAML",
            kind="skip",
            argv=(),
            display=" ".join(pip_argv),
            reason=reason_y,
            downloads="PyYAML (not downloaded — already importable)",
        ))

    leg_ok, leg_msg = _legacy()
    steps.append(InstallStep(
        id="legacy",
        title="legacy officecli (shape-level)",
        kind="manual" if not leg_ok else "skip",
        argv=(),
        display=(
            "download from https://github.com/iOfficeAI/OfficeCLI/releases "
            "and set OFFICECLI_LEGACY_BIN if not on PATH"
        ),
        reason=leg_msg if not leg_ok else f"present — {leg_msg}",
        downloads=(
            "iOfficeAI/OfficeCLI release asset (manual; not version-pinned)"
            if not leg_ok
            else "none (legacy binary already available)"
        ),
    ))
    return steps


def _execute_step(step: InstallStep, *, dry_run: bool) -> tuple[bool, str]:
    """Run one install step. Returns (ok, detail)."""
    if step.kind == "skip":
        return True, f"skip — {step.reason}"
    if step.kind == "manual":
        return False, f"manual — {step.reason}"
    assert step.kind == "run" and step.argv
    if dry_run:
        return True, f"dry-run — would run: {step.display}"
    runner = _RUN_INSTALL or subprocess.run
    try:
        r = runner(
            list(step.argv),
            capture_output=True,
            text=True,
            timeout=int(os.environ.get("DESIGNMD_INSTALL_TIMEOUT", "300")),
            encoding="utf-8",
            errors="replace",
        )
    except OSError as e:
        return False, f"failed to spawn: {e}"
    except subprocess.TimeoutExpired:
        return False, "timed out"
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    tail = "\n".join(out.splitlines()[-8:]) if out else "(no output)"
    if r.returncode != 0:
        return False, f"exit {r.returncode}\n{tail}"
    return True, f"ok\n{tail}" if tail != "(no output)" else "ok"


def run_install(*, dry_run: bool = False) -> int:
    """Execute (or dry-run) the install plan. Returns 0 when every *run*
    step succeeded and no *manual* steps remain required; non-zero otherwise.
    Skips never fail the exit code.
    """
    steps = plan_install()
    print("doctor --install plan (compatibility.json pin)")
    print(f"  dry-run: {'yes' if dry_run else 'no'}")
    off = compat.spec_for("official")
    print(f"  official pin: min={off.get('min')} recommended={off.get('recommended')} "
          f"max_tested={off.get('max_tested')}")
    print()

    failures = 0
    manuals = 0
    ran = 0
    for i, step in enumerate(steps, 1):
        print(f"[{i}/{len(steps)}] {step.title}  ({step.kind})")
        print(f"  reason:    {step.reason}")
        print(f"  downloads: {step.downloads}")
        print(f"  command:   {step.display}")
        ok, detail = _execute_step(step, dry_run=dry_run)
        for line in detail.splitlines() or [detail]:
            print(f"  → {line}")
        print()
        if step.kind == "run":
            ran += 1
            if not ok:
                failures += 1
        elif step.kind == "manual":
            manuals += 1

    if dry_run:
        print("dry-run complete — re-run without --dry-run to apply")
        # dry-run never fails for unexecuted run steps; manuals still noted
        return 0 if failures == 0 else 1

    if failures:
        print(f"{failures} install step(s) failed — see output above")
        print("repair: fix network/npm/pip, then re-run doctor --install")
        return 1
    if manuals:
        print(f"{manuals} step(s) need manual action (legacy binary / missing npm)")
        print("repair: follow the printed URLs, then re-run doctor")
        return 1
    if ran:
        print(f"{ran} step(s) applied — re-probing environment…")
    else:
        print("nothing to install — environment already satisfies auto-installable deps")
    print()
    return run_doctor(strict=False)


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
        print("tip: `python -m designmd_pptx doctor --install --dry-run` "
              "shows the version-locked OfficeCLI install plan")
    else:
        print("\nall checks passed — pptx requests route through officecli on every platform")
    if strict and not officecli_ok:
        return 1  # the shape-level pipeline is the hard requirement
    return 0


if __name__ == "__main__":  # pragma: no cover
    argv = sys.argv[1:]
    if "--install" in argv:
        raise SystemExit(run_install(dry_run="--dry-run" in argv))
    raise SystemExit(run_doctor(strict="--strict" in sys.argv))
