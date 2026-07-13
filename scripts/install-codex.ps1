#Requires -Version 5.1
<#
Install designmd-pptx as an OpenAI Codex CLI skill.
Copies the skill + vendored Python toolkit into ~/.codex/skills/ (self-contained)
and the slash command into ~/.codex/prompts/.

Also syncs the base officecli-* skill family from ~/.claude/skills (if present)
so that generic "make me a deck" requests in Codex route through officecli,
not just DESIGN.md-triggered ones. Pass -SkipBaseSkills to opt out.
#>
param(
    [string]$CodexHome = (Join-Path $env:USERPROFILE ".codex"),
    [switch]$SkipBaseSkills
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$skillDst = Join-Path $CodexHome "skills\officecli-pptx-designmd"

New-Item -ItemType Directory -Force $skillDst | Out-Null
Copy-Item (Join-Path $repo "skills\officecli-pptx-designmd\SKILL.md") $skillDst -Force

# Vendor the Python toolkit inside the skill so it is self-contained
robocopy (Join-Path $repo "python") (Join-Path $skillDst "python") /E /XD __pycache__ out /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }

# Optional explicit prompt (invoke with /designmd-pptx or $officecli-pptx-designmd)
$promptDir = Join-Path $CodexHome "prompts"
New-Item -ItemType Directory -Force $promptDir | Out-Null
Copy-Item (Join-Path $repo "commands\designmd-pptx.md") (Join-Path $promptDir "designmd-pptx.md") -Force

# Base officecli skill family: same SKILL.md standard works in Codex.
if (-not $SkipBaseSkills) {
    $claudeSkills = Join-Path $env:USERPROFILE ".claude\skills"
    $baseDirs = @()
    if (Test-Path $claudeSkills) {
        $baseDirs = Get-ChildItem $claudeSkills -Directory -Filter "officecli*" |
            Where-Object { $_.Name -ne "officecli-pptx-designmd" }
    }
    if ($baseDirs.Count -gt 0) {
        foreach ($dir in $baseDirs) {
            $dst = Join-Path $CodexHome "skills\$($dir.Name)"
            robocopy $dir.FullName $dst /E /NFL /NDL /NJH /NJS | Out-Null
            if ($LASTEXITCODE -ge 8) { throw "robocopy failed for $($dir.Name) ($LASTEXITCODE)" }
        }
        Write-Host "Synced $($baseDirs.Count) base officecli skill(s) from ~/.claude/skills"
    } else {
        Write-Warning ("Base officecli-pptx skill not found in ~/.claude/skills — generic deck " +
            "requests in Codex will not route through officecli. Install the officecli skill " +
            "family (https://github.com/iOfficeAI/OfficeCLI) or re-run after installing it in Claude Code.")
    }
}

pip install -r (Join-Path $skillDst "python\requirements.txt")

Write-Host "Installed skill: $skillDst"
Write-Host 'In Codex: type $officecli-pptx-designmd, run /designmd-pptx, or mention DESIGN.md -> PPTX.'
Write-Host 'Verify routing everywhere: python -m designmd_pptx doctor'
