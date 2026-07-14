#Requires -Version 5.1
<#
Install designmd-pptx for OpenAI Codex — OFFICIAL-FIRST (v1.7, issue #29).

Order of operations:
1. Official officecli binary: keep an existing one; else `npm install -g
   officecli`; else download the platform asset from officecli/officecli-dist
   into %LOCALAPPDATA%\officecli (npm's postinstall downloader is known to
   fail on some Windows setups).
2. Official base skill: run the official installer
   (scripts/install-skill.sh via Git Bash), then sync the resulting
   ~/.claude/skills/officecli into ~/.codex/skills. Legacy officecli-* skill
   copying is only a fallback and warns.
3. designmd-pptx extension skill: vendored copy (this repo's own skill).
#>
param(
    [string]$CodexHome = (Join-Path $env:USERPROFILE ".codex"),
    [switch]$SkipBaseSkills
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot

function Test-OfficialBinary([string]$exe) {
    try { return ((& $exe --version) 2>$null | Select-Object -First 1) -like "officecli version*" }
    catch { return $false }
}

# --- 1. official binary -------------------------------------------------------
$officialExe = $null
# NOTE: "officecli-official", never "officecli" — Windows paths are
# case-insensitive and "officecli\" would clobber the legacy "OfficeCLI\" dir.
$pathCmd = Get-Command officecli -ErrorAction SilentlyContinue
$pathCand = if ($pathCmd) { $pathCmd.Source } else { $null }
foreach ($cand in @($pathCand,
                    (Join-Path $env:LOCALAPPDATA "officecli-official\officecli.exe"))) {
    if ($cand -and (Test-Path $cand) -and (Test-OfficialBinary $cand)) { $officialExe = $cand; break }
}
if (-not $officialExe) {
    Write-Host "official officecli not found — trying npm install -g officecli"
    try {
        npm install -g officecli 2>$null | Out-Null
        # native exit codes do NOT throw in PS5.1 — verify explicitly
        $npmShim = Join-Path $env:APPDATA "npm\officecli.cmd"
        if ($LASTEXITCODE -eq 0 -and (Test-Path $npmShim) -and
            (Test-OfficialBinary $npmShim)) { $officialExe = $npmShim }
        elseif ($LASTEXITCODE -ne 0) { Write-Warning "npm install failed (exit $LASTEXITCODE)" }
    } catch {}
}
if (-not $officialExe) {
    Write-Host "npm route unavailable — downloading from officecli/officecli-dist releases"
    $dst = Join-Path $env:LOCALAPPDATA "officecli-official"
    New-Item -ItemType Directory -Force $dst | Out-Null
    try {
        gh release download -R officecli/officecli-dist --pattern "*windows_amd64.tar.gz" `
            --dir $dst --clobber 2>$null
        if ($LASTEXITCODE -ne 0) { throw "gh release download failed (exit $LASTEXITCODE)" }
        $tarball = Get-ChildItem $dst -Filter "officecli_*_windows_amd64.tar.gz" |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        tar -xzf $tarball.FullName -C $dst
        if ($LASTEXITCODE -ne 0) { throw "tar extraction failed (exit $LASTEXITCODE)" }
        if (Test-OfficialBinary (Join-Path $dst "officecli.exe")) {
            $officialExe = Join-Path $dst "officecli.exe"
        }
    } catch {
        Write-Warning ("could not fetch officecli-dist automatically — download " +
            "https://github.com/officecli/officecli-dist/releases manually into $dst")
    }
}
if ($officialExe) {
    Write-Host "official officecli: $officialExe"
} else {
    Write-Warning "official officecli unavailable — the render command will be disabled"
}

# --- 2. official base skill ---------------------------------------------------
if (-not $SkipBaseSkills) {
    $claudeBase = Join-Path $env:USERPROFILE ".claude\skills\officecli"
    $bashCmd = Get-Command bash -ErrorAction SilentlyContinue
    $bash = if ($bashCmd) { $bashCmd.Source } else { $null }
    if ($bash -and -not (Test-Path (Join-Path $claudeBase "SKILL.md"))) {
        Write-Host "running official install-skill.sh (officecli base skill)"
        try {
            & $bash -c "curl -fsSL https://raw.githubusercontent.com/officecli/officecli/main/scripts/install-skill.sh | bash -s -- officecli" | Out-Null
        } catch { Write-Warning "official install-skill.sh failed: $_" }
    }
    if (Test-Path (Join-Path $claudeBase "SKILL.md")) {
        $dst = Join-Path $CodexHome "skills\officecli"
        robocopy $claudeBase $dst /E /NFL /NDL /NJH /NJS | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy failed for base skill ($LASTEXITCODE)" }
        Write-Host "synced official base skill -> $dst"
    } else {
        # legacy fallback only (#25): old officecli-* skill family
        $legacy = Get-ChildItem (Join-Path $env:USERPROFILE ".claude\skills") `
            -Directory -Filter "officecli*" -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -ne "officecli-pptx-designmd" }
        if ($legacy) {
            Write-Warning ("official base skill unavailable — falling back to copying " +
                "$($legacy.Count) LEGACY officecli-* skill(s); re-run once the official " +
                "installer works")
            foreach ($dir in $legacy) {
                robocopy $dir.FullName (Join-Path $CodexHome "skills\$($dir.Name)") /E /NFL /NDL /NJH /NJS | Out-Null
                if ($LASTEXITCODE -ge 8) { throw "robocopy failed for $($dir.Name)" }
            }
        } else {
            Write-Warning "no officecli base skill found (official or legacy)"
        }
    }
}

# --- 3. designmd-pptx extension skill (vendored) ------------------------------
$skillDst = Join-Path $CodexHome "skills\officecli-pptx-designmd"
New-Item -ItemType Directory -Force $skillDst | Out-Null
Copy-Item (Join-Path $repo "skills\officecli-pptx-designmd\SKILL.md") $skillDst -Force
robocopy (Join-Path $repo "python") (Join-Path $skillDst "python") /E /XD __pycache__ out /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }

$promptDir = Join-Path $CodexHome "prompts"
New-Item -ItemType Directory -Force $promptDir | Out-Null
Copy-Item (Join-Path $repo "commands\designmd-pptx.md") (Join-Path $promptDir "designmd-pptx.md") -Force

pip install -r (Join-Path $skillDst "python\requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "pip install failed (exit $LASTEXITCODE) — install PyYAML manually: pip install PyYAML"
}

Write-Host "Installed skill: $skillDst"
Write-Host 'Verify everything: python -m designmd_pptx doctor'
