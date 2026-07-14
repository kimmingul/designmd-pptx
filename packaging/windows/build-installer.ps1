#Requires -Version 5.1
<#
Build the optional DesignmdPptx-Setup.exe (Inno Setup) for #35.

Requires Inno Setup 6+ on the build machine (ISCC.exe on PATH or
$env:INNO_SETUP_HOME). When ISCC is missing, validates the one-file
Install-DesignmdPptx.ps1 and exits 0 with a note — CI can still gate on
structure without producing a binary on non-Windows agents.
#>
param(
    [switch]$RequireExe
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$iss = Join-Path $here "designmd-pptx.iss"
$ps1 = Join-Path $here "Install-DesignmdPptx.ps1"
$info = Join-Path $here "INSTALL-INFO.txt"

foreach ($f in @($iss, $ps1, $info)) {
    if (-not (Test-Path $f)) { throw "missing $f" }
}

# Structural checks on the one-file installer
$raw = Get-Content $ps1 -Raw
foreach ($needle in @("-Uninstall", "officecli-dist", "install.manifest.json", "LOCALAPPDATA", "designmd-pptx")) {
    if ($raw -notmatch [regex]::Escape($needle)) {
        throw "Install-DesignmdPptx.ps1 missing required content: $needle"
    }
}
Write-Host "OK one-file installer: $ps1"

$iscc = $null
if ($env:INNO_SETUP_HOME) {
    $cand = Join-Path $env:INNO_SETUP_HOME "ISCC.exe"
    if (Test-Path $cand) { $iscc = $cand }
}
if (-not $iscc) {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { $iscc = $cmd.Source }
}
if (-not $iscc) {
    foreach ($p in @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )) {
        if ($p -and (Test-Path $p)) { $iscc = $p; break }
    }
}

if (-not $iscc) {
    $msg = "ISCC.exe not found — skipping Setup.exe build (one-file .ps1 remains the supported installer)"
    if ($RequireExe) { throw $msg }
    Write-Warning $msg
    exit 0
}

Write-Host "Building with $iscc"
& $iscc $iss
if ($LASTEXITCODE -ne 0) { throw "ISCC failed: $LASTEXITCODE" }
$out = Join-Path $here "dist\DesignmdPptx-Setup.exe"
if (-not (Test-Path $out)) { throw "expected output missing: $out" }
Write-Host "OK $out"
