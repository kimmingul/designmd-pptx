#Requires -Version 5.1
<#
Install designmd-pptx as an OpenAI Codex CLI skill.
Copies the skill + vendored Python toolkit into ~/.codex/skills/ (self-contained)
and the slash command into ~/.codex/prompts/.
#>
param([string]$CodexHome = (Join-Path $env:USERPROFILE ".codex"))

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

pip install -r (Join-Path $skillDst "python\requirements.txt")

Write-Host "Installed skill: $skillDst"
Write-Host "In Codex: type `$officecli-pptx-designmd, run /designmd-pptx, or mention DESIGN.md -> PPTX."
