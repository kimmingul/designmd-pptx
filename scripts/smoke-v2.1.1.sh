#!/usr/bin/env bash
# Automated smoke for designmd-pptx v2.1.2 (any OS with Python 3.10+).
# Usage: bash scripts/smoke-v2.1.2.sh
#        SMOKE_FAST=1 bash scripts/smoke-v2.1.2.sh   # skip full unit suite
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/python${PYTHONPATH:+:$PYTHONPATH}"
fail=0
pass() { echo "  PASS  $*"; }
bad()  { echo "  FAIL  $*"; fail=1; }

echo "== designmd-pptx smoke v2.1.2 =="
echo "root: $ROOT"

# ── version ──────────────────────────────────────────────────────────────
VER=$(python -c "from designmd_pptx import __version__; print(__version__)")
[[ "$VER" == "2.1.2" ]] && pass "version $VER" || bad "version $VER (want 2.1.2)"

# ── npm check (exact equality) ───────────────────────────────────────────
if command -v npm >/dev/null 2>&1; then
  if npm run check >/tmp/dmd-smoke-npm.txt 2>&1; then
    pass "npm run check"
  else
    bad "npm run check (see /tmp/dmd-smoke-npm.txt)"
  fi
else
  echo "  skip  npm not installed"
fi

# ── unit tests ───────────────────────────────────────────────────────────
if [[ "${SMOKE_FAST:-}" == "1" ]]; then
  if python -m unittest \
      python.tests.test_phase5_21_40_42 \
      python.tests.test_refine \
      python.tests.test_vscode_extension \
      python.tests.test_windows_installer \
      -q 2>/tmp/dmd-smoke-unit.txt; then
    pass "unit (fast subset)"
  else
    bad "unit fast subset (see /tmp/dmd-smoke-unit.txt)"
  fi
else
  if python -m unittest discover -s python/tests -q 2>/tmp/dmd-smoke-unit.txt; then
    pass "unit full suite"
  else
    bad "unit suite (see /tmp/dmd-smoke-unit.txt)"
  fi
fi

# ── refine multi-slide ───────────────────────────────────────────────────
python - <<'PY' || bad "refine multi-slide"
from designmd_pptx import refine
deck = {"slides": [
  {"id": "s1", "recipe": "bullets", "content": {"title": "A", "bullets": [f"a{i}" for i in range(8)]}},
  {"id": "s2", "recipe": "bullets", "content": {"title": "B", "bullets": [f"b{i}" for i in range(8)]}},
]}
out, log = refine.apply_patches(deck, [{"code": "density", "severity": "error", "message": "x", "slide": None}], max_list_items=4)
assert len(out["slides"]) == 4, out
s2 = next(s for s in out["slides"] if s["id"] == "s2")
assert len(s2["content"]["bullets"]) == 4
print("refine ok")
PY
pass "refine multi-slide split"

# ── extract barDir ───────────────────────────────────────────────────────
python - <<'PY' || bad "barDir"
from xml.etree import ElementTree as ET
from designmd_pptx.extract import _chart_type
xml = '''<?xml version="1.0"?>
<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">
  <c:chart><c:plotArea><c:barChart><c:barDir val="col"/></c:barChart></c:plotArea></c:chart>
</c:chartSpace>'''
assert _chart_type(ET.fromstring(xml)) == "column"
print("barDir ok")
PY
pass "extract barDir=col → column"

# ── generative overflow + placement reject ───────────────────────────────
python - <<'PY' || bad "generative"
from designmd_pptx import generative as g
from designmd_pptx import layout as L
deck = {"slides": [{"id": "s1", "recipe": "bullets",
  "content": {"title": "T", "bullets": [f"P{i}" for i in range(10)]}}]}
r = g.generate_deck_layout(deck, profile_id="minimal")
c = r["deck"]["slides"][0]["content"]
assert c.get("overflow") or "overflow" in (c.get("notes") or "") or r["deck"]["slides"][0]["recipe"] == "freeform"
ok, why = g.validate_placements([{"name": "X", "x": -99, "y": 0, "w": 1, "h": 1}])
assert not ok, why
print("generative ok")
PY
pass "generative overflow + placement validate"

# ── animation order + force ──────────────────────────────────────────────
python - <<'PY' || bad "animation"
import zipfile, tempfile
from pathlib import Path
from designmd_pptx import animation as anim
from designmd_pptx import opc

slide = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr/>
    <p:sp><p:nvSpPr><p:cNvPr id="2" name="CoverTitle"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
      <p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Hi</a:t></a:r></a:p></p:txBody>
    </p:sp>
  </p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>'''
new, eff, tr = anim.inject_slide_animation(slide, entrance="fade", transition="fade", name_prefixes=["CoverTitle"])
assert eff > 0 and tr == 1
root = opc.parse(new)
locals_ = [c.tag.split("}")[-1] for c in list(root)]
assert locals_.index("clrMapOvr") < locals_.index("transition")
assert locals_.index("transition") < locals_.index("timing")
td = tempfile.mkdtemp()
src = Path(td) / "d.pptx"
with zipfile.ZipFile(src, "w") as zf:
    zf.writestr("[Content_Types].xml", "<Types/>")
    zf.writestr("ppt/slides/slide1.xml", slide)
rep = anim.animate_pptx(src, out=src, animation={"enabled": True, "entrance": "fade"}, force=False)
assert not rep.ok and any("force" in n.lower() for n in rep.notes)
print("animation ok", locals_)
PY
pass "animation order + force"

# ── public synthetic suite ───────────────────────────────────────────────
if PYTHONPATH=python python -m designmd_pptx benchmark --public --public-n 30 -o /tmp/dmd-pb-smoke \
    >/tmp/dmd-smoke-pb.txt 2>&1; then
  if grep -q "recipe_build" /tmp/dmd-smoke-pb.txt || grep -q "synthetic" /tmp/dmd-smoke-pb.txt; then
    pass "public synthetic suite n=30"
  else
    bad "public suite missing honesty notes (see /tmp/dmd-smoke-pb.txt)"
  fi
else
  bad "public suite (see /tmp/dmd-smoke-pb.txt)"
fi

# ── windows installer structural ─────────────────────────────────────────
if PYTHONPATH=python python -m designmd_pptx windows-install --check-script >/tmp/dmd-smoke-win.txt 2>&1; then
  pass "windows-install --check-script"
else
  bad "windows-install --check-script"
fi
grep -q 'designmd-pptx==2.1.2' packaging/windows/Install-DesignmdPptx.ps1 \
  && pass "installer package pin 2.1.2" || bad "installer pin missing"
grep -q 'Assert-SafeInstallRoot' packaging/windows/Install-DesignmdPptx.ps1 \
  && pass "installer safe root" || bad "safe root missing"

# ── vscode argv injection ────────────────────────────────────────────────
if command -v node >/dev/null 2>&1; then
  node -e '
const { resolveCli, hasShellMeta } = require("./editor/vscode/cli.js");
const r = resolveCli({ workspaceRoot: process.cwd(), pythonPath: "python3",
  args: ["refine", "deck.json", "--feedback", "$(id); rm -rf /"] });
const fb = r.argv[r.argv.indexOf("--feedback")+1];
if (fb !== "$(id); rm -rf /") { console.error("argv corrupted", fb); process.exit(1); }
if (!hasShellMeta(fb)) process.exit(2);
if (!Array.isArray(r.argv)) process.exit(3);
console.log("ok");
' && pass "vscode argv injection resistance" || bad "vscode argv"
else
  echo "  skip  node not installed"
fi

echo
if [[ $fail -eq 0 ]]; then
  echo "SMOKE PASS (automated track A)"
  exit 0
else
  echo "SMOKE FAIL — see messages above"
  exit 1
fi
