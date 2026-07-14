"""Windows standalone installer planning & manifest (Phase 5 / #35).

The **one-file** installer that end-users run is
``packaging/windows/Install-DesignmdPptx.ps1`` (optionally wrapped by Inno
Setup into ``DesignmdPptx-Setup.exe``). This module is the **cross-platform
source of truth** for:

* install root paths (LocalAppData layout)
* pin resolution from ``compatibility.json``
* install plan steps (Python, package, OfficeCLI pin, PATH, uninstall)
* install.manifest.json schema read/write/validate
* dry-run plan rendering for ``designmd-pptx windows-install --plan``

No network or Windows-only APIs are required here — unit tests run on
macOS/Linux CI. The PowerShell script executes the plan on Windows.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import __version__ as PKG_VERSION
from . import compat
from . import doctor as doctor_mod

MANIFEST_SCHEMA = 1
MANIFEST_NAME = "install.manifest.json"
PRODUCT_NAME = "designmd-pptx"
DEFAULT_PUBLISHER = "designmd-pptx contributors"


@dataclass
class InstallPaths:
    """Canonical per-user install layout on Windows (also used for docs/tests)."""
    root: Path
    bin_dir: Path
    venv_dir: Path
    manifest: Path
    uninstall_ps1: Path
    shim_cmd: Path
    log_dir: Path

    def to_dict(self) -> dict[str, str]:
        return {k: str(v) for k, v in asdict(self).items()}


@dataclass
class PlanStep:
    id: str
    title: str
    action: str  # ensure_python | create_venv | pip_install | officecli_pin | path | shortcuts | write_manifest | uninstall
    detail: str
    required: bool = True
    downloads: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InstallPlan:
    product: str
    version: str
    officecli_pin: str
    officecli_url: str
    paths: dict[str, str]
    steps: list[PlanStep] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    uninstall_command: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "product": self.product,
            "version": self.version,
            "officecli_pin": self.officecli_pin,
            "officecli_url": self.officecli_url,
            "paths": self.paths,
            "steps": [s.to_dict() for s in self.steps],
            "notes": self.notes,
            "uninstall_command": self.uninstall_command,
        }


def default_install_root(*, home: Path | None = None, local_appdata: str | None = None) -> Path:
    """``%LOCALAPPDATA%\\designmd-pptx`` on Windows; XDG-ish fallback elsewhere."""
    if local_appdata:
        return Path(local_appdata) / PRODUCT_NAME
    env_la = os.environ.get("LOCALAPPDATA")
    if env_la:
        return Path(env_la) / PRODUCT_NAME
    h = home or Path.home()
    if os.name == "nt" or platform.system().lower() == "windows":
        return h / "AppData" / "Local" / PRODUCT_NAME
    # Non-Windows: still define a stable path for plan/docs/tests
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / PRODUCT_NAME
    return h / ".local" / "share" / PRODUCT_NAME


def resolve_paths(root: str | Path | None = None, **kwargs: Any) -> InstallPaths:
    r = Path(root) if root else default_install_root(**kwargs)
    return InstallPaths(
        root=r,
        bin_dir=r / "bin",
        venv_dir=r / "venv",
        manifest=r / MANIFEST_NAME,
        uninstall_ps1=r / "Uninstall-DesignmdPptx.ps1",
        shim_cmd=r / "bin" / "designmd-pptx.cmd",
        log_dir=r / "logs",
    )


def officecli_pin() -> str:
    spec = compat.spec_for("official")
    return str(spec.get("recommended") or spec.get("min") or "0.2.117").lstrip("v")


def officecli_windows_url(version: str | None = None, arch: str = "amd64") -> str:
    """Pinned officecli-dist asset URL for Windows (fetched by the installer)."""
    ver = (version or officecli_pin()).lstrip("v")
    # officecli-dist naming: officecli_<ver>_windows_<arch>.tar.gz
    # doctor.dist_asset_url uses platform triple; force windows for the installer plan
    triple = f"windows_{arch}"
    return doctor_mod.dist_asset_url(ver, triple=triple)


def build_install_plan(
    *,
    root: str | Path | None = None,
    package_source: str = "pip",  # pip | path:./
    skip_officecli: bool = False,
    skip_path: bool = False,
    python_min: str = "3.10",
) -> InstallPlan:
    """Deterministic install plan for the one-file Windows installer."""
    paths = resolve_paths(root)
    pin = officecli_pin()
    url = officecli_windows_url(pin)
    steps: list[PlanStep] = [
        PlanStep(
            id="ensure_python",
            title=f"Python ≥ {python_min}",
            action="ensure_python",
            detail=(
                f"Use existing `py -{python_min}` / python3 on PATH, else "
                f"`winget install Python.Python.3.12` (user scope)"
            ),
            downloads="Python from winget (only if missing)",
        ),
        PlanStep(
            id="create_venv",
            title="Isolated virtualenv",
            action="create_venv",
            detail=f"python -m venv {paths.venv_dir}",
        ),
        PlanStep(
            id="pip_install",
            title="Install designmd-pptx package",
            action="pip_install",
            detail=(
                f"{paths.venv_dir}/Scripts/pip install -U pip; "
                + (
                    f"pip install designmd-pptx=={PKG_VERSION}"
                    if package_source in ("pip", f"designmd-pptx=={PKG_VERSION}")
                    else f"pip install {package_source}"
                )
            ),
            downloads=(
                f"designmd-pptx=={PKG_VERSION} from PyPI (pinned)"
                if package_source in ("pip", f"designmd-pptx=={PKG_VERSION}")
                else f"package source {package_source}"
            ),
        ),
    ]
    if not skip_officecli:
        steps.append(PlanStep(
            id="officecli_pin",
            title=f"Pinned official OfficeCLI {pin}",
            action="officecli_pin",
            detail=(
                f"Download {url} → extract officecli.exe to "
                f"{paths.bin_dir} and %LOCALAPPDATA%\\officecli-official\\"
            ),
            downloads=url,
        ))
    steps.append(PlanStep(
        id="shim",
        title="CLI shim",
        action="write_shim",
        detail=f"Write {paths.shim_cmd} → venv python -m designmd_pptx",
    ))
    if not skip_path:
        steps.append(PlanStep(
            id="user_path",
            title="User PATH",
            action="path",
            detail=f"Append {paths.bin_dir} to HKCU Environment Path (idempotent)",
        ))
    steps.append(PlanStep(
        id="write_manifest",
        title="Install manifest + uninstall script",
        action="write_manifest",
        detail=f"Write {paths.manifest} and copy Uninstall-DesignmdPptx.ps1",
    ))

    notes = [
        "One-file entrypoint: packaging/windows/Install-DesignmdPptx.ps1",
        "Optional GUI wrapper: packaging/windows/designmd-pptx.iss (Inno Setup → Setup.exe)",
        "Uninstall: Install-DesignmdPptx.ps1 -Uninstall  OR  Uninstall-DesignmdPptx.ps1",
        "Legacy shape-level OfficeCLI remains manual (not auto-bundled).",
        f"Package version: {PKG_VERSION}",
    ]
    uninstall = (
        f'powershell -ExecutionPolicy Bypass -File '
        f'"{paths.uninstall_ps1}"'
    )
    return InstallPlan(
        product=PRODUCT_NAME,
        version=PKG_VERSION,
        officecli_pin=pin,
        officecli_url=url,
        paths=paths.to_dict(),
        steps=steps,
        notes=notes,
        uninstall_command=uninstall,
    )


def new_manifest(
    plan: InstallPlan,
    *,
    installed_at: str,
    python_exe: str,
    package_version: str | None = None,
    officecli_version: str | None = None,
    officecli_path: str | None = None,
    path_modified: bool = False,
) -> dict[str, Any]:
    """Build install.manifest.json content."""
    return {
        "schema": MANIFEST_SCHEMA,
        "product": plan.product,
        "version": package_version or plan.version,
        "installed_at": installed_at,
        "publisher": DEFAULT_PUBLISHER,
        "paths": plan.paths,
        "python_exe": python_exe,
        "officecli": {
            "pin": plan.officecli_pin,
            "version": officecli_version or plan.officecli_pin,
            "path": officecli_path,
            "source_url": plan.officecli_url,
        },
        "path_modified": path_modified,
        "uninstall": {
            "command": plan.uninstall_command,
            "removes": [
                plan.paths["root"],
                "User PATH entry for bin_dir (if path_modified)",
            ],
        },
    }


def validate_manifest(data: Any) -> list[str]:
    """Return list of structural errors (empty = ok)."""
    errs: list[str] = []
    if not isinstance(data, dict):
        return ["manifest must be a JSON object"]
    if data.get("schema") != MANIFEST_SCHEMA:
        errs.append(f"schema must be {MANIFEST_SCHEMA}")
    for key in ("product", "version", "installed_at", "paths", "uninstall"):
        if key not in data:
            errs.append(f"missing required field: {key}")
    paths = data.get("paths")
    if isinstance(paths, dict):
        for k in ("root", "bin_dir", "manifest", "uninstall_ps1"):
            if k not in paths:
                errs.append(f"paths missing: {k}")
    elif paths is not None:
        errs.append("paths must be an object")
    un = data.get("uninstall")
    if isinstance(un, dict):
        if not un.get("command"):
            errs.append("uninstall.command required")
    elif un is not None:
        errs.append("uninstall must be an object")
    return errs


def write_manifest(path: str | Path, data: dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def load_manifest(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errs = validate_manifest(data)
    if errs:
        raise ValueError("invalid install manifest:\n- " + "\n- ".join(errs))
    return data


def render_plan_text(plan: InstallPlan) -> str:
    lines = [
        f"# {plan.product} Windows install plan v{plan.version}",
        f"OfficeCLI pin: {plan.officecli_pin}",
        f"OfficeCLI URL: {plan.officecli_url}",
        f"Install root: {plan.paths.get('root')}",
        "",
        "## Steps",
    ]
    for i, s in enumerate(plan.steps, 1):
        req = "required" if s.required else "optional"
        lines.append(f"{i}. [{s.id}] {s.title} ({req})")
        lines.append(f"   action: {s.action}")
        lines.append(f"   {s.detail}")
        if s.downloads:
            lines.append(f"   downloads: {s.downloads}")
    lines += ["", "## Uninstall", plan.uninstall_command, "", "## Notes"]
    lines.extend(f"- {n}" for n in plan.notes)
    return "\n".join(lines) + "\n"


def installer_script_path(repo_root: str | Path | None = None) -> Path:
    """Locate the one-file PowerShell installer relative to the package or repo."""
    # Prefer repo layout when developing from checkout
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "packaging" / "windows" / "Install-DesignmdPptx.ps1",
        here.parents[1] / "packaging" / "windows" / "Install-DesignmdPptx.ps1",
    ]
    if repo_root:
        candidates.insert(0, Path(repo_root) / "packaging" / "windows" / "Install-DesignmdPptx.ps1")
    for c in candidates:
        if c.is_file():
            return c
    return candidates[0]


def assert_installer_present(repo_root: str | Path | None = None) -> Path:
    p = installer_script_path(repo_root)
    if not p.is_file():
        raise FileNotFoundError(f"Windows installer missing: {p}")
    return p
