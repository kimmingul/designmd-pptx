# Windows standalone installer (#35)

Non-developer friendly install of **designmd-pptx** + a **pinned official
OfficeCLI** on Windows 10/11 — without requiring a pre-configured Python
dev environment.

## One-file installer (primary)

[`packaging/windows/Install-DesignmdPptx.ps1`](../packaging/windows/Install-DesignmdPptx.ps1)
is a **single PowerShell file** you can download and run:

```powershell
powershell -ExecutionPolicy Bypass -File Install-DesignmdPptx.ps1
powershell -ExecutionPolicy Bypass -File Install-DesignmdPptx.ps1 -DryRun
```

| Flag | Effect |
|---|---|
| `-Uninstall` | Remove install root + user PATH entry |
| `-DryRun` | Print actions only |
| `-SkipOfficeCli` | Skip pinned OfficeCLI download |
| `-SkipPath` | Do not modify user PATH |
| `-PackageSource X` | `designmd-pptx` (default) or local path/wheel |
| `-InstallRoot PATH` | Override `%LOCALAPPDATA%\designmd-pptx` |

### Layout

```
%LOCALAPPDATA%\designmd-pptx\
  venv\                 # isolated Python env
  bin\
    designmd-pptx.cmd   # shim → venv python -m designmd_pptx
    officecli.exe       # copy of pinned official binary
  install.manifest.json
  Uninstall-DesignmdPptx.ps1
  logs\
%LOCALAPPDATA%\officecli-official\
  officecli.exe         # shared with doctor --install
```

### What is pinned

OfficeCLI version comes from
[`python/designmd_pptx/compatibility.json`](../python/designmd_pptx/compatibility.json)
(`official.recommended`). The installer downloads the matching
**officecli-dist** Windows amd64 tarball (same source as
`doctor --install`).

Legacy shape-level OfficeCLI is **not** auto-installed (rolling upstream;
still required for scaffold/apply precision — `doctor` prints the URL).

## Uninstall path

```powershell
# Same one-file script
powershell -ExecutionPolicy Bypass -File Install-DesignmdPptx.ps1 -Uninstall

# After install
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\designmd-pptx\Uninstall-DesignmdPptx.ps1"
```

Removes the product root and the user PATH entry. Leaves
`officecli-official` in place so other tools keep working.

## Optional Setup.exe (Inno Setup)

On a Windows build agent with [Inno Setup 6](https://jrsoftware.org/isinfo.php):

```powershell
pwsh packaging\windows\build-installer.ps1
# → packaging\windows\dist\DesignmdPptx-Setup.exe
```

The Setup.exe is a thin GUI wrapper: it extracts the one-file script and runs
it; uninstall calls `-Uninstall`. Privileges: **per-user** (`lowest`).

## Plan / CI checks (any OS)

```bash
PYTHONPATH=python python -m designmd_pptx windows-install --plan
PYTHONPATH=python python -m designmd_pptx windows-install --check-script
PYTHONPATH=python python -m designmd_pptx windows-install --json -o plan.json
```

## Acceptance criteria

| Criterion | Evidence |
|---|---|
| One-file Windows installer | `Install-DesignmdPptx.ps1` |
| Bundles or fetches pinned OfficeCLI | officecli-dist URL from pin + extract to LocalAppData |
| Uninstall path | `-Uninstall` / `Uninstall-DesignmdPptx.ps1` / Inno `[UninstallRun]` |

See also [install.md](install.md) (pip + doctor) and
[packaging/windows/README.md](../packaging/windows/README.md).
