# Smoke checklist — designmd-pptx v2.1.2

Post-adversarial (Codex BLOCK → 2.1.2 fixes). Two tracks:

1. **Automated local smoke** (any OS with Python 3.10+) — `scripts/smoke-v2.1.2.sh`
2. **Windows bootstrap smoke** (Windows 10/11 + PowerShell 5.1+) — section B
3. **PowerPoint / LibreOffice animation smoke** — section C

Exit criteria for “production announce ready”:

| Gate | Pass condition |
|---|---|
| A Automated | `scripts/smoke-v2.1.2.sh` exit 0 |
| B Windows | install → doctor → scaffold → uninstall without leftover product root |
| C Animation | animate → open in PPT/LO; transitions present; no repair dialog |

---

## A. Automated local smoke

```bash
# from repo root
./scripts/smoke-v2.1.2.sh
# or:
bash scripts/smoke-v2.1.2.sh
```

Covers:

- version == 2.1.2 + `npm run check` exact equality
- unit suite (or fast subset if `SMOKE_FAST=1`)
- refine multi-slide split stability
- extract `barDir=col` → column
- generative overflow preserve + placement reject
- animation CT_Slide order + force required
- public synthetic suite (`--public-n 30`) with recipe smoke notes
- windows installer structural markers (`windows-install --check-script`)
- VS Code cli.js argv injection resistance (node)

---

## B. Windows bootstrap smoke (manual / VM)

**Host:** clean Windows 10/11 user (no admin required).

```powershell
# 1) Clone or download Install-DesignmdPptx.ps1 from v2.1.2 tag
cd path\to\designmd-pptx
powershell -ExecutionPolicy Bypass -File packaging\windows\Install-DesignmdPptx.ps1 -DryRun

# 2) Real install (network: winget/PyPI/GitHub)
powershell -ExecutionPolicy Bypass -File packaging\windows\Install-DesignmdPptx.ps1

# 3) New terminal — shim on PATH
designmd-pptx --help
designmd-pptx doctor
designmd-pptx scaffold default -o $env:TEMP\dmd-smoke --content python\examples\content.deck.json

# 4) Safe-root guard (must FAIL)
powershell -ExecutionPolicy Bypass -File packaging\windows\Install-DesignmdPptx.ps1 `
  -Uninstall -InstallRoot C:\Windows\Temp\evil
# expect: InstallRoot must be under ...\designmd-pptx

# 5) Uninstall
powershell -ExecutionPolicy Bypass -File packaging\windows\Install-DesignmdPptx.ps1 -Uninstall
# product root gone; officecli-official may remain (documented)
```

Optional integrity:

```powershell
# If you have the expected tarball hash:
$env:DESIGNMD_OFFICECLI_SHA256 = "<sha256 of officecli_0.2.117_windows_amd64.tar.gz>"
powershell -ExecutionPolicy Bypass -File packaging\windows\Install-DesignmdPptx.ps1
```

**Record:** OS build, Python source (existing vs winget), doctor output, any PATH issues.

---

## C. PowerPoint / LibreOffice animation smoke

Requires a materialised `.pptx` (legacy OfficeCLI `apply` or an existing deck).

```bash
# After scaffold --apply (legacy binary) OR any valid deck.pptx:
PYTHONPATH=python python -m designmd_pptx animate path/to/deck.pptx \
  -o /tmp/deck.animated.pptx --entrance fade --transition fade --force

# Inspect OOXML order without Office:
python - <<'PY'
import zipfile
from lxml import etree
from pathlib import Path
p = Path("/tmp/deck.animated.pptx")
with zipfile.ZipFile(p) as z:
    xml = z.read("ppt/slides/slide1.xml")
root = etree.fromstring(xml)
locals_ = [c.tag.split("}")[-1] for c in root]
print(locals_)
assert "transition" in locals_ and "timing" in locals_
assert locals_.index("transition") < locals_.index("timing")
if "extLst" in locals_:
    assert locals_.index("timing") < locals_.index("extLst")
print("order OK")
PY
```

**In PowerPoint / LibreOffice Impress:**

1. Open `deck.animated.pptx` — no repair / “unreadable content” dialog.
2. Slide Show → transitions visible (fade).
3. Select title shape → Animation pane shows entrance effect (or equivalent).
4. Save-as new file succeeds.

**In-place force guard:**

```bash
# must refuse without --force
PYTHONPATH=python python -m designmd_pptx animate deck.pptx -o deck.pptx --entrance fade
# expect: error/notes about --force
```

---

## D. Sign-off template

```text
Date:
Operator:
Commit/tag:
A automated smoke: PASS / FAIL (log: )
B Windows install: PASS / FAIL / SKIP (reason: )
C PPT/LO animation: PASS / FAIL / SKIP (reason: )
Notes:
Announce: YES / NO
```

---

## E. Recorded run (this environment)

```text
Date: 2026-07-15
Operator: agent (macOS Darwin)
Commit/tag: v2.1.2 (b6ba429)
A automated smoke: PASS — bash scripts/smoke-v2.1.2.sh
B Windows install: SKIP — no Windows/pwsh on host (manual VM required)
C PPT/LO animation: PARTIAL — OOXML order verified programmatically
  tags: cSld, clrMapOvr, transition, timing
  officecli/soffice/libreoffice: not on PATH (no real slideshow open)
Codex re-verify (gpt-5.6-sol@high): see .grok/artifacts/verify/codex-gpt-5.6-sol-reverify-v2.1.2.md
Announce: conditional on B+C human sign-off if claiming full production Windows/PPT
```
