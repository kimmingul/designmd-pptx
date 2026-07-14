# Windows standalone installer (#35)

## Deliverables

| Artifact | Role |
|---|---|
| **`Install-DesignmdPptx.ps1`** | **One-file installer** (primary). Run on any Windows 10+ with PowerShell 5.1+. |
| `Uninstall` via same script (`-Uninstall`) or copied `Uninstall-DesignmdPptx.ps1` | **Uninstall path** |
| `designmd-pptx.iss` + `build-installer.ps1` | Optional **Setup.exe** (Inno Setup 6) GUI wrapper |
| `python/designmd_pptx/win_install.py` | Cross-platform plan/manifest helpers + CLI |

## Quick install (one file)

```powershell
# From a release asset or repo checkout:
powershell -ExecutionPolicy Bypass -File packaging\windows\Install-DesignmdPptx.ps1

# Dry-run (no changes)
powershell -ExecutionPolicy Bypass -File packaging\windows\Install-DesignmdPptx.ps1 -DryRun

# Local checkout wheel/editable instead of PyPI
powershell -ExecutionPolicy Bypass -File packaging\windows\Install-DesignmdPptx.ps1 `
  -PackageSource ".\python"
```

Install root: `%LOCALAPPDATA%\designmd-pptx`

What it does:

1. Ensures Python ≥ 3.10 (existing or `winget install Python.Python.3.12`)
2. Creates an isolated venv and `pip install designmd-pptx`
3. Fetches the **pinned** official OfficeCLI from **officecli-dist**
   (version from `compatibility.json` / script default `0.2.117`)
4. Writes `bin\designmd-pptx.cmd` and appends it to the **user PATH**
5. Writes `install.manifest.json` + uninstall script

## Uninstall

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\Install-DesignmdPptx.ps1 -Uninstall
# after install:
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\designmd-pptx\Uninstall-DesignmdPptx.ps1"
```

Removes the install root and the user PATH entry. Leaves
`%LOCALAPPDATA%\officecli-official` in place (shared with `doctor --install`).

## Optional Setup.exe

On a Windows machine with [Inno Setup 6](https://jrsoftware.org/isinfo.php):

```powershell
pwsh packaging\windows\build-installer.ps1
# → packaging\windows\dist\DesignmdPptx-Setup.exe
```

## Plan without installing

```bash
# any OS
PYTHONPATH=python python -m designmd_pptx windows-install --plan
PYTHONPATH=python python -m designmd_pptx windows-install --plan -o plan.json
```

## Acceptance (#35)

- [x] One-file Windows installer → `Install-DesignmdPptx.ps1`
- [x] Bundles or **fetches** pinned OfficeCLI → officecli-dist pin
- [x] Uninstall path → `-Uninstall` / `Uninstall-DesignmdPptx.ps1` / Inno Uninstall
