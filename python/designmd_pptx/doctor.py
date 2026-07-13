"""Environment doctor: verify the OfficeCLI toolchain and per-platform agent
skill routing (Claude Code / Codex / Grok) so any agentic AI on this machine
builds pptx through officecli (v1.4)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_OFFICECLI_REMEDY = (
    "install officecli: macOS/Linux `curl -fsSL https://d.officecli.ai/install.sh | bash`; "
    "Windows: download from https://github.com/iOfficeAI/OfficeCLI/releases and add to PATH"
)


def _officecli() -> tuple[bool, str]:
    exe = shutil.which("officecli")
    if not exe:
        return False, _OFFICECLI_REMEDY
    try:
        r = subprocess.run(
            [exe, "--version"], capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace",
        )
        return True, f"v{(r.stdout or '').strip()} ({exe})"
    except OSError as e:
        return False, f"found at {exe} but failed to run: {e}"


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

    ok, msg = _officecli()
    rows.append(("officecli", ok, msg))
    officecli_ok = ok
    ok, msg = _pyyaml()
    rows.append(("PyYAML", ok, msg))
    rows.append(("designmd_pptx", True, f"v{__version__} ({Path(__file__).parent})"))

    ok, msg = _skill(home / ".claude", "officecli-pptx")
    rows.append(("claude: officecli-pptx skill", ok, msg))
    ok, msg = _claude_designmd(home / ".claude")
    rows.append(("claude: designmd layer", ok, msg))

    ok, msg = _skill(home / ".codex", "officecli-pptx")
    if not ok:
        msg = "copy base skills or run scripts/install-codex.ps1"
    rows.append(("codex: officecli-pptx skill", ok, msg))
    ok, msg = _skill(home / ".codex", "officecli-pptx-designmd")
    if not ok:
        msg = "run scripts/install-codex.ps1"
    rows.append(("codex: designmd layer", ok, msg))

    ok, msg = _skill(home / ".grok", "officecli-pptx")
    rows.append(("grok: officecli-pptx skill", ok, msg))
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
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_doctor(strict="--strict" in sys.argv))
