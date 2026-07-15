# Thin wrapper: staging-safe apply via designmd_pptx apply (apply_sequence)
# Does NOT delete the destination before validate/issues — staging lives in apply.py
# Requires: officecli + python
$ErrorActionPreference = 'Stop'
$File = Join-Path $PSScriptRoot "Northstar-Board-Flagship.pptx"
$Seq  = Join-Path $PSScriptRoot "recipes\deck.sequence.json"
$Force = @()
if ($env:DESIGNMD_FORCE -eq '1') { $Force = @('--force') }
# designmd-pptx package root is two levels up from out/<brand>/
$PkgRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (Test-Path (Join-Path $PkgRoot "designmd_pptx")) { $env:PYTHONPATH = $PkgRoot }
python -m designmd_pptx apply $File $Seq @Force --screenshot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done: $File"
