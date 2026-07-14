#Requires -Version 5.1
<#
.SYNOPSIS
  One-file Windows installer for designmd-pptx (#35).

.DESCRIPTION
  Per-user install under %LOCALAPPDATA%\designmd-pptx:
    - Python 3.10+ (existing or winget)
    - Isolated venv + pip install designmd-pptx
    - Pinned official OfficeCLI from officecli-dist (compatibility.json pin)
    - bin\designmd-pptx.cmd shim + optional User PATH
    - install.manifest.json + Uninstall-DesignmdPptx.ps1

  This script IS the one-file installer. Optional GUI wrapper:
    packaging/windows/designmd-pptx.iss  → DesignmdPptx-Setup.exe (Inno Setup)

.PARAMETER Uninstall
  Remove the install root, PATH entry, and related files.

.PARAMETER DryRun
  Print the plan without changing the system.

.PARAMETER SkipOfficeCli
  Do not download the pinned OfficeCLI.

.PARAMETER SkipPath
  Do not modify the user PATH.

.PARAMETER PackageSource
  pip package name/version (default: designmd-pptx) or a local path (dir/wheel).

.PARAMETER InstallRoot
  Override install root (default: %LOCALAPPDATA%\designmd-pptx).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File Install-DesignmdPptx.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File Install-DesignmdPptx.ps1 -Uninstall
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Uninstall,
    [switch]$DryRun,
    [switch]$SkipOfficeCli,
    [switch]$SkipPath,
    # Pin package by default (adversarial #35) — override with -PackageSource for editable installs
    [string]$PackageSource = "designmd-pptx==2.1.2",
    [string]$InstallRoot = "",
    [string]$OfficeCliPin = "",  # empty → read from embedded default / env
    [string]$OfficeCliSha256 = "",  # optional expected SHA-256 of the tarball
    [string]$PythonMin = "3.10"
)

$ErrorActionPreference = "Stop"
$ProductName = "designmd-pptx"
# Keep in sync with python/designmd_pptx/compatibility.json official.recommended
$DefaultOfficeCliPin = "0.2.117"
$DefaultLocalRoot = Join-Path $env:LOCALAPPDATA $ProductName

if (-not $InstallRoot) {
    $InstallRoot = $DefaultLocalRoot
}
# Guard: install/uninstall root must live under LocalAppData\designmd-pptx
# (or explicit subpath). Blocks recursive delete of arbitrary trees.
function Assert-SafeInstallRoot([string]$root) {
    $full = [System.IO.Path]::GetFullPath($root)
    $allowed = [System.IO.Path]::GetFullPath($DefaultLocalRoot)
    if (-not ($full.Equals($allowed, [System.StringComparison]::OrdinalIgnoreCase) -or
              $full.StartsWith($allowed + [IO.Path]::DirectorySeparatorChar,
                               [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "InstallRoot must be under $allowed (got $full). Refusing unsafe path."
    }
}
Assert-SafeInstallRoot $InstallRoot
$BinDir     = Join-Path $InstallRoot "bin"
$VenvDir    = Join-Path $InstallRoot "venv"
$Manifest   = Join-Path $InstallRoot "install.manifest.json"
$UninstallPs1 = Join-Path $InstallRoot "Uninstall-DesignmdPptx.ps1"
$ShimCmd    = Join-Path $BinDir "designmd-pptx.cmd"
$LogDir     = Join-Path $InstallRoot "logs"
$OfficialDir = Join-Path $env:LOCALAPPDATA "officecli-official"

function Write-Step([string]$msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "    OK  $msg" -ForegroundColor Green }
function Write-Info([string]$msg) { Write-Host "    ..  $msg" }

function Get-OfficeCliPin {
    if ($OfficeCliPin) { return $OfficeCliPin.TrimStart('v') }
    if ($env:DESIGNMD_OFFICECLI_PIN) { return $env:DESIGNMD_OFFICECLI_PIN.TrimStart('v') }
    return $DefaultOfficeCliPin
}

function Get-OfficeCliUrl([string]$pin) {
    # officecli-dist: officecli_<ver>_windows_amd64.tar.gz
    $ver = $pin.TrimStart('v')
    return "https://github.com/officecli/officecli-dist/releases/download/v$ver/officecli_${ver}_windows_amd64.tar.gz"
}

function Test-PythonOk([string]$exe) {
    if (-not $exe -or -not (Test-Path $exe)) { return $false }
    try {
        $out = & $exe -c "import sys; print('%d.%d'%sys.version_info[:2])" 2>$null
        if (-not $out) { return $false }
        $parts = $out.Trim().Split('.')
        $minParts = $PythonMin.Split('.')
        $maj = [int]$parts[0]; $min = [int]$parts[1]
        $reqMaj = [int]$minParts[0]; $reqMin = [int]$minParts[1]
        return ($maj -gt $reqMaj) -or ($maj -eq $reqMaj -and $min -ge $reqMin)
    } catch { return $false }
}

function Find-Python {
    $candidates = @()
    foreach ($cmd in @("py", "python", "python3")) {
        $g = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($g) { $candidates += $g.Source }
    }
    # py launcher with version
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $listed = & py -0p 2>$null
            if ($listed) {
                foreach ($line in ($listed -split "`n")) {
                    if ($line -match '(\S+\.exe)\s*$') { $candidates += $Matches[1] }
                }
            }
        } catch {}
    }
    foreach ($c in $candidates) {
        if (Test-PythonOk $c) { return $c }
        # try py -3.12 style
    }
    if ($py) {
        foreach ($v in @("3.12", "3.11", "3.10")) {
            try {
                $exe = & py "-$v" -c "import sys; print(sys.executable)" 2>$null
                if ($exe -and (Test-PythonOk $exe.Trim())) { return $exe.Trim() }
            } catch {}
        }
    }
    return $null
}

function Ensure-Python {
    $found = Find-Python
    if ($found) {
        Write-Ok "Python found: $found"
        return $found
    }
    Write-Step "Python >= $PythonMin not found — trying winget"
    if ($DryRun) {
        Write-Info "dry-run: would winget install Python.Python.3.12"
        return "python"
    }
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "Python $PythonMin+ required. Install from https://www.python.org/downloads/ and re-run."
    }
    & winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget install Python failed (exit $LASTEXITCODE)"
    }
    # Refresh PATH for current process
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
    $found = Find-Python
    if (-not $found) {
        throw "Python installed via winget but not yet on PATH — open a new terminal and re-run the installer."
    }
    Write-Ok "Python installed: $found"
    return $found
}

function New-Venv([string]$pythonExe) {
    Write-Step "Create venv → $VenvDir"
    if ($DryRun) { Write-Info "dry-run: $pythonExe -m venv $VenvDir"; return }
    if (Test-Path $VenvDir) {
        Write-Info "venv exists — reusing"
    } else {
        & $pythonExe -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
    }
    Write-Ok $VenvDir
}

function Get-VenvPython {
    $p = Join-Path $VenvDir "Scripts\python.exe"
    if (-not (Test-Path $p) -and -not $DryRun) { throw "venv python missing: $p" }
    return $p
}

function Install-Package {
    $py = Get-VenvPython
    Write-Step "pip install $PackageSource"
    if ($DryRun) { Write-Info "dry-run: $py -m pip install $PackageSource"; return }
    & $py -m pip install -U pip
    & $py -m pip install $PackageSource
    if ($LASTEXITCODE -ne 0) { throw "pip install failed for $PackageSource" }
    # Prefer doctor --install when package is importable
    try {
        & $py -m designmd_pptx doctor --install 2>&1 | ForEach-Object { Write-Info "$_" }
    } catch {
        Write-Info "doctor --install skipped/failed (will still fetch OfficeCLI pin): $_"
    }
    Write-Ok "package installed"
}

function Install-OfficeCliPin {
    if ($SkipOfficeCli) { Write-Info "SkipOfficeCli — not fetching OfficeCLI"; return $null }
    $pin = Get-OfficeCliPin
    $url = Get-OfficeCliUrl $pin
    Write-Step "Pinned OfficeCLI $pin"
    Write-Info $url
    if ($DryRun) { Write-Info "dry-run: download + extract to $OfficialDir and $BinDir"; return $url }

    New-Item -ItemType Directory -Force $OfficialDir | Out-Null
    New-Item -ItemType Directory -Force $BinDir | Out-Null
    New-Item -ItemType Directory -Force $LogDir | Out-Null
    $tmp = Join-Path $env:TEMP "designmd-officecli-$pin.tgz"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing
    } catch {
        throw "Failed to download OfficeCLI pin from $url : $_"
    }
    if (-not (Test-Path $tmp) -or ((Get-Item $tmp).Length -lt 64)) {
        throw "Download too small or missing: $tmp"
    }
    $expectSha = if ($OfficeCliSha256) { $OfficeCliSha256 } else { $env:DESIGNMD_OFFICECLI_SHA256 }
    if ($expectSha) {
        $hash = (Get-FileHash -Algorithm SHA256 -Path $tmp).Hash.ToLowerInvariant()
        if ($hash -ne $expectSha.ToLowerInvariant()) {
            throw "OfficeCLI tarball SHA-256 mismatch: got $hash expected $expectSha"
        }
        Write-Ok "SHA-256 verified"
    } elseif ($env:DESIGNMD_REQUIRE_OFFICECLI_SHA -eq "1") {
        throw "DESIGNMD_REQUIRE_OFFICECLI_SHA=1 but no -OfficeCliSha256 / DESIGNMD_OFFICECLI_SHA256 provided"
    } else {
        Write-Host "    WARN pin URL only — set DESIGNMD_OFFICECLI_SHA256 for supply-chain verify" -ForegroundColor Yellow
    }
    # tar is available on Windows 10+; extract only under our temp root (path safety)
    $extract = Join-Path $env:TEMP "designmd-officecli-extract-$pin"
    if (Test-Path $extract) { Remove-Item -Recurse -Force $extract }
    New-Item -ItemType Directory -Force $extract | Out-Null
    tar -xzf $tmp -C $extract
    $extractFull = [System.IO.Path]::GetFullPath($extract)
    $exe = Get-ChildItem -Path $extract -Recurse -Filter "officecli.exe" -ErrorAction SilentlyContinue |
        Where-Object {
            $p = [System.IO.Path]::GetFullPath($_.FullName)
            $p.StartsWith($extractFull, [System.StringComparison]::OrdinalIgnoreCase)
        } |
        Select-Object -First 1
    if (-not $exe) {
        throw "Archive has no officecli.exe under extract root (refusing ambiguous officecli* matches)"
    }
    # Reject zip-slip / path traversal outside extract root
    $exeFull = [System.IO.Path]::GetFullPath($exe.FullName)
    if (-not $exeFull.StartsWith($extractFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing officecli path outside extract root: $exeFull"
    }
    $destOfficial = Join-Path $OfficialDir "officecli.exe"
    $destBin = Join-Path $BinDir "officecli.exe"
    Copy-Item -Force $exe.FullName $destOfficial
    Copy-Item -Force $exe.FullName $destBin
    $env:OFFICECLI_BRIDGE_BIN = $destOfficial
    Write-Ok "$destOfficial"
    return $destOfficial
}

function Write-Shim {
    Write-Step "Write CLI shim $ShimCmd"
    if ($DryRun) { Write-Info "dry-run: write shim"; return }
    New-Item -ItemType Directory -Force $BinDir | Out-Null
    $py = Get-VenvPython
    $content = @"
@echo off
REM designmd-pptx shim — generated by Install-DesignmdPptx.ps1
"$py" -m designmd_pptx %*
"@
    Set-Content -Path $ShimCmd -Value $content -Encoding ASCII
    Write-Ok $ShimCmd
}

function Add-UserPath {
    if ($SkipPath) { Write-Info "SkipPath — PATH unchanged"; return $false }
    Write-Step "Ensure user PATH contains $BinDir"
    if ($DryRun) { Write-Info "dry-run: append to HKCU Path"; return $true }
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $userPath) { $userPath = "" }
    $parts = $userPath -split ';' | Where-Object { $_ -and $_.Trim() -ne '' }
    $norm = $BinDir.TrimEnd('\')
    foreach ($p in $parts) {
        if ($p.TrimEnd('\') -ieq $norm) {
            Write-Info "already on PATH"
            return $false
        }
    }
    $newPath = if ($userPath.Trim()) { "$userPath;$BinDir" } else { $BinDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $env:Path = "$env:Path;$BinDir"
    Write-Ok "PATH updated (new terminals pick this up)"
    return $true
}

function Write-ManifestFile([string]$pythonExe, [string]$officecliPath, [bool]$pathModified) {
    Write-Step "Write manifest + uninstall script"
    $pin = Get-OfficeCliPin
    $url = Get-OfficeCliUrl $pin
    $installedAt = (Get-Date).ToUniversalTime().ToString("o")
    $pkgVer = "unknown"
    if (-not $DryRun) {
        try {
            $pkgVer = & (Get-VenvPython) -c "from designmd_pptx import __version__; print(__version__)" 2>$null
            if (-not $pkgVer) { $pkgVer = "unknown" } else { $pkgVer = $pkgVer.Trim() }
        } catch { $pkgVer = "unknown" }
    }
    $manifestObj = [ordered]@{
        schema       = 1
        product      = $ProductName
        version      = $pkgVer
        installed_at = $installedAt
        publisher    = "designmd-pptx contributors"
        paths        = [ordered]@{
            root          = $InstallRoot
            bin_dir       = $BinDir
            venv_dir      = $VenvDir
            manifest      = $Manifest
            uninstall_ps1 = $UninstallPs1
            shim_cmd      = $ShimCmd
            log_dir       = $LogDir
        }
        python_exe   = $pythonExe
        officecli    = [ordered]@{
            pin        = $pin
            version    = $pin
            path       = $officecliPath
            source_url = $url
        }
        path_modified = $pathModified
        uninstall    = [ordered]@{
            command = "powershell -ExecutionPolicy Bypass -File `"$UninstallPs1`""
            removes = @($InstallRoot, "User PATH entry for bin_dir (if path_modified)")
        }
    }
    if ($DryRun) {
        Write-Info "dry-run: would write $Manifest"
        return
    }
    New-Item -ItemType Directory -Force $InstallRoot | Out-Null
    $json = $manifestObj | ConvertTo-Json -Depth 6
    Set-Content -Path $Manifest -Value $json -Encoding UTF8
    # Self-copy as uninstall entry (this file supports -Uninstall)
    $self = $MyInvocation.MyCommand.Path
    if ($self -and (Test-Path $self)) {
        Copy-Item -Force $self $UninstallPs1
    } else {
        # When dot-sourced / wrapped by Inno, write a tiny uninstaller that re-invokes Install with -Uninstall
        $boot = @"
#Requires -Version 5.1
param()
`$here = Split-Path -Parent `$MyInvocation.MyCommand.Path
`$installer = Join-Path `$here 'Install-DesignmdPptx.ps1'
if (Test-Path `$installer) {
  & `$installer -Uninstall
} else {
  # inline minimal uninstall
  `$root = `$here
  if (Test-Path `$root) { Remove-Item -Recurse -Force `$root }
}
"@
        Set-Content -Path $UninstallPs1 -Value $boot -Encoding UTF8
    }
    Write-Ok $Manifest
    Write-Ok $UninstallPs1
}

function Remove-UserPathEntry {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $userPath) { return }
    $norm = $BinDir.TrimEnd('\')
    $parts = $userPath -split ';' | Where-Object {
        $_ -and ($_.TrimEnd('\') -ine $norm)
    }
    $newPath = ($parts -join ';')
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Ok "removed $BinDir from user PATH"
}

function Invoke-Uninstall {
    Write-Step "Uninstall $ProductName from $InstallRoot"
    Assert-SafeInstallRoot $InstallRoot
    if ($DryRun) {
        Write-Info "dry-run: remove $InstallRoot and PATH entry"
        return
    }
    $pathModified = $false
    if (-not (Test-Path $Manifest)) {
        throw "Refusing uninstall: $Manifest missing (not a designmd-pptx install root)"
    }
    try {
        $m = Get-Content $Manifest -Raw | ConvertFrom-Json
    } catch {
        throw "Refusing uninstall: manifest is not valid JSON: $_"
    }
    if (-not $m.product -or $m.product -ne $ProductName) {
        throw "Refusing uninstall: manifest product is '$($m.product)' (want $ProductName)"
    }
    if ($m.paths -and $m.paths.root) {
        $manifestRoot = [System.IO.Path]::GetFullPath([string]$m.paths.root)
        $wantRoot = [System.IO.Path]::GetFullPath($InstallRoot)
        if (-not $manifestRoot.Equals($wantRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing uninstall: manifest root $manifestRoot != InstallRoot $wantRoot"
        }
    }
    $pathModified = [bool]$m.path_modified
    if ($pathModified -or -not $SkipPath) {
        Remove-UserPathEntry
    }
    if (Test-Path $InstallRoot) {
        Remove-Item -Recurse -Force $InstallRoot
        Write-Ok "removed $InstallRoot"
    } else {
        Write-Info "install root already absent"
    }
    # Do NOT remove %LOCALAPPDATA%\officecli-official — may be shared with doctor --install
    Write-Host ""
    Write-Host "Uninstall complete. Official OfficeCLI under officecli-official was left in place." -ForegroundColor Yellow
    Write-Host "Remove it manually if desired: $OfficialDir"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
Write-Host "designmd-pptx Windows installer (#35)" -ForegroundColor White
Write-Host "  root: $InstallRoot"
Write-Host "  pin:  $(Get-OfficeCliPin)"
if ($DryRun) { Write-Host "  mode: DRY-RUN" -ForegroundColor Yellow }

if ($Uninstall) {
    Invoke-Uninstall
    exit 0
}

$python = Ensure-Python
New-Venv $python
Install-Package
$ocli = Install-OfficeCliPin
Write-Shim
$pathMod = Add-UserPath
Write-ManifestFile -pythonExe $python -officecliPath $ocli -pathModified $pathMod

Write-Host ""
Write-Host "Install complete." -ForegroundColor Green
Write-Host "  shim:      $ShimCmd"
Write-Host "  uninstall: powershell -ExecutionPolicy Bypass -File `"$UninstallPs1`""
Write-Host "  or:        powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Uninstall"
Write-Host ""
Write-Host "Open a new terminal, then:"
Write-Host "  designmd-pptx doctor"
Write-Host "  designmd-pptx scaffold default -o demo --content <deck.json>"
exit 0
