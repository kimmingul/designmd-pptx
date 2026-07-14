"""Phase 2 / #12 — extract fidelity: charts, groups, SmartArt, loss ledger."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from designmd_pptx.extract import extract_pptx

NS_DECL = (
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
    'xmlns:dgm="http://schemas.openxmlformats.org/drawingml/2006/diagram"'
)

THEME_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office">'
    "<a:themeElements><a:clrScheme name=\"Office\">"
    '<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
    '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
    '<a:dk2><a:srgbClr val="44546A"/></a:dk2>'
    '<a:lt2><a:srgbClr val="E7E6E6"/></a:lt2>'
    '<a:accent1><a:srgbClr val="4472C4"/></a:accent1>'
    '<a:accent2><a:srgbClr val="ED7D31"/></a:accent2>'
    '<a:accent3><a:srgbClr val="A5A5A5"/></a:accent3>'
    '<a:accent4><a:srgbClr val="FFC000"/></a:accent4>'
    '<a:accent5><a:srgbClr val="5B9BD5"/></a:accent5>'
    '<a:accent6><a:srgbClr val="70AD47"/></a:accent6>'
    '<a:hlink><a:srgbClr val="0563C1"/></a:hlink>'
    '<a:folHlink><a:srgbClr val="954F72"/></a:folHlink>'
    "</a:clrScheme><a:fontScheme name=\"Office\">"
    '<a:majorFont><a:latin typeface="Calibri"/></a:majorFont>'
    '<a:minorFont><a:latin typeface="Calibri"/></a:minorFont>'
    "</a:fontScheme><a:fmtScheme name=\"Office\"/></a:themeElements></a:theme>"
)

# OOXML group tags: nvGrpSpPr / cNvGrpSpPr
NV_GRP_SP_PR = "nv" + "G" + "r" + "p" + "SpPr"
CNV_GRP_SP_PR = "cNv" + "G" + "r" + "p" + "SpPr"
GRP_SP = "grpSp"
GRP_SP_PR = "grpSpPr"


def _sp(paras, ph=None, *, x=0, y=0, w=2_000_000, h=1_000_000, sz=1800):
    ph_xml = f'<p:ph type="{ph}"/>' if ph else ""
    runs = "".join(
        f'<a:p><a:r><a:rPr sz="{sz}"/><a:t>{t}</a:t></a:r></a:p>' for t in paras
    )
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="shape"/><p:cNvSpPr/>'
        f"<p:nvPr>{ph_xml}</p:nvPr></p:nvSpPr>"
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/>'
        f'<a:ext cx="{w}" cy="{h}"/></a:xfrm></p:spPr>'
        f"<p:txBody><a:bodyPr/>{runs}</p:txBody></p:sp>"
    )


def _grp(*inner):
    return (
        f"<p:{GRP_SP}>"
        f"<p:{NV_GRP_SP_PR}><p:cNvPr id=\"10\" name=\"Group 1\"/>"
        f"<p:{CNV_GRP_SP_PR}/><p:nvPr/></p:{NV_GRP_SP_PR}>"
        f"<p:{GRP_SP_PR}/>"
        + "".join(inner)
        + f"</p:{GRP_SP}>"
    )


def _slide(body, *, timing=False):
    timing_xml = (
        '<p:timing><p:tnLst><p:par><p:cTn id="1"/></p:par></p:tnLst></p:timing>'
        if timing
        else ""
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<p:sld {NS_DECL}><p:cSld><p:spTree>"
        f"{body}</p:spTree></p:cSld>{timing_xml}</p:sld>"
    )


CHART_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <c:chart>
    <c:plotArea>
      <c:barChart>
        <c:ser>
          <c:tx><c:v>Revenue</c:v></c:tx>
          <c:cat>
            <c:strRef><c:strCache>
              <c:pt idx="0"><c:v>Q1</c:v></c:pt>
              <c:pt idx="1"><c:v>Q2</c:v></c:pt>
              <c:pt idx="2"><c:v>Q3</c:v></c:pt>
            </c:strCache></c:strRef>
          </c:cat>
          <c:val>
            <c:numRef><c:numCache>
              <c:pt idx="0"><c:v>10</c:v></c:pt>
              <c:pt idx="1"><c:v>14</c:v></c:pt>
              <c:pt idx="2"><c:v>18</c:v></c:pt>
            </c:numCache></c:numRef>
          </c:val>
        </c:ser>
        <c:ser>
          <c:tx><c:v>Cost</c:v></c:tx>
          <c:val>
            <c:numRef><c:numCache>
              <c:pt idx="0"><c:v>6</c:v></c:pt>
              <c:pt idx="1"><c:v>7</c:v></c:pt>
              <c:pt idx="2"><c:v>8</c:v></c:pt>
            </c:numCache></c:numRef>
          </c:val>
        </c:ser>
      </c:barChart>
    </c:plotArea>
  </c:chart>
</c:chartSpace>
"""


def _chart_frame(rid="rIdChart"):
    return (
        '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="20" name="Chart 1"/>'
        "<p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>"
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">'
        f'<c:chart r:id="{rid}"/>'
        "</a:graphicData></a:graphic></p:graphicFrame>"
    )


def _smartart_frame():
    return (
        '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="30" name="Diagram"/>'
        "<p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>"
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/diagram">'
        '<dgm:relIds r:dm="rIdDm" r:lo="rIdLo" r:qs="rIdQs" r:cs="rIdCs"/>'
        "</a:graphicData></a:graphic></p:graphicFrame>"
    )


DIAGRAM_DATA = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<dgm:dataModel xmlns:dgm="http://schemas.openxmlformats.org/drawingml/2006/diagram"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <dgm:ptLst>
    <dgm:pt><dgm:t><a:r><a:t>Discover</a:t></a:r></dgm:t></dgm:pt>
    <dgm:pt><dgm:t><a:r><a:t>Build</a:t></a:r></dgm:t></dgm:pt>
    <dgm:pt><dgm:t><a:r><a:t>Ship</a:t></a:r></dgm:t></dgm:pt>
  </dgm:ptLst>
</dgm:dataModel>
"""


def _make_pptx(path, slides, *, extra_parts=None):
    n = len(slides)
    sld_ids = "".join(
        f'<p:sldId id="{256 + i}" r:id="rId{i + 1}"/>' for i in range(n)
    )
    pres = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<p:presentation {NS_DECL}><p:sldIdLst>{sld_ids}</p:sldIdLst></p:presentation>"
    )
    rel_ns = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    pres_rels = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<Relationships {rel_ns}>"
        + "".join(
            f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/'
            f'officeDocument/2006/relationships/slide" Target="slides/slide{i + 1}.xml"/>'
            for i in range(n)
        )
        + "</Relationships>"
    )
    root_rels = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<Relationships {rel_ns}>"
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("ppt/presentation.xml", pres)
        zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        zf.writestr("ppt/theme/theme1.xml", THEME_XML)
        for i, (xml, rels) in enumerate(slides):
            zf.writestr(f"ppt/slides/slide{i + 1}.xml", xml)
            if rels:
                zf.writestr(f"ppt/slides/_rels/slide{i + 1}.xml.rels", rels)
        for name, data in (extra_parts or {}).items():
            zf.writestr(name, data)
    return path


def _rels(*pairs):
    rel_ns = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    body = "".join(
        f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
        f'officeDocument/2006/relationships/{typ}" Target="{tgt}"/>'
        for rid, typ, tgt in pairs
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<Relationships {rel_ns}>{body}</Relationships>"
    )


class ExtractFidelity12(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_chart_series_and_categories(self):
        slide = _slide(_sp(["Revenue"], ph="title") + _chart_frame("rIdChart"))
        rels = _rels(("rIdChart", "chart", "../charts/chart1.xml"))
        pptx = _make_pptx(
            self.root / "chart.pptx",
            [(slide, rels)],
            extra_parts={"ppt/charts/chart1.xml": CHART_XML},
        )
        out = self.root / "out-chart"
        report = extract_pptx(pptx, out)
        spec = json.loads((out / "content.deck.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["slides"][0]["recipe"], "chart_insight")
        c = spec["slides"][0]["content"]
        self.assertEqual(c["chart_type"], "bar")
        self.assertEqual(c["categories"], "Q1,Q2,Q3")
        self.assertEqual(c["series1_name"], "Revenue")
        self.assertEqual(c["series1_values"], "10,14,18")
        self.assertEqual(c["series2_name"], "Cost")
        self.assertEqual(c["series2_values"], "6,7,8")
        self.assertEqual(report["slides"][0]["geometry"]["charts"], 1)
        self.assertIn("loss_ledger", report)

    def test_group_nested_text_recovered(self):
        g = _grp(
            _sp(["One", "Body one"], x=100_000, y=1_000_000, w=2_500_000, h=2_000_000),
            _sp(["Two", "Body two"], x=3_000_000, y=1_000_000, w=2_500_000, h=2_000_000),
            _sp(["Three", "Body three"], x=6_000_000, y=1_000_000, w=2_500_000, h=2_000_000),
        )
        self.assertIn(NV_GRP_SP_PR, g)
        slide = _slide(_sp(["Capabilities"], ph="title") + g)
        pptx = _make_pptx(self.root / "group.pptx", [(slide, None)])
        out = self.root / "out-group"
        report = extract_pptx(pptx, out)
        spec = json.loads((out / "content.deck.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["slides"][0]["recipe"], "feature_cards")
        cards = spec["slides"][0]["content"]["cards"]
        self.assertEqual(len(cards), 3)
        self.assertEqual(cards[0]["title"], "One")
        kinds = [e["kind"] for e in report["loss_ledger"]["entries"]]
        self.assertIn("group_shapes", kinds)
        self.assertEqual(report["slides"][0]["geometry"]["groups"], 1)

    def test_smartart_text_fallback_and_ledger(self):
        slide = _slide(_sp(["Process"], ph="title") + _smartart_frame())
        rels = _rels(
            ("rIdDm", "diagramData", "../diagrams/data1.xml"),
            ("rIdLo", "diagramLayout", "../diagrams/layout1.xml"),
            ("rIdQs", "diagramQuickStyle", "../diagrams/quickStyle1.xml"),
            ("rIdCs", "diagramColors", "../diagrams/colors1.xml"),
        )
        empty = (
            '<?xml version="1.0"?><dgm:dataModel '
            'xmlns:dgm="http://schemas.openxmlformats.org/drawingml/2006/diagram"/>'
        )
        pptx = _make_pptx(
            self.root / "smart.pptx",
            [(slide, rels)],
            extra_parts={
                "ppt/diagrams/data1.xml": DIAGRAM_DATA,
                "ppt/diagrams/layout1.xml": empty,
                "ppt/diagrams/quickStyle1.xml": empty,
                "ppt/diagrams/colors1.xml": empty,
            },
        )
        out = self.root / "out-smart"
        report = extract_pptx(pptx, out)
        spec = json.loads((out / "content.deck.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["slides"][0]["recipe"], "process")
        steps = spec["slides"][0]["content"]["steps"]
        self.assertEqual(steps, ["Discover", "Build", "Ship"])
        kinds = [e["kind"] for e in report["loss_ledger"]["entries"]]
        self.assertIn("smartart", kinds)
        smart = [e for e in report["loss_ledger"]["entries"] if e["kind"] == "smartart"][0]
        self.assertTrue(smart["recoverable"])

    def test_animation_loss_ledger(self):
        slide = _slide(_sp(["Title"], ph="title") + _sp(["Body line"]), timing=True)
        pptx = _make_pptx(self.root / "anim.pptx", [(slide, None)])
        out = self.root / "out-anim"
        report = extract_pptx(pptx, out)
        self.assertTrue(report["slides"][0]["has_animation"])
        kinds = [e["kind"] for e in report["loss_ledger"]["entries"]]
        self.assertIn("animation", kinds)
        warns = " ".join(report["slides"][0]["warnings"])
        self.assertIn("animation", warns)

    def test_report_source_is_basename(self):
        slide = _slide(_sp(["Hi"], ph="title"))
        pptx = _make_pptx(self.root / "named-deck.pptx", [(slide, None)])
        report = extract_pptx(pptx, self.root / "out-name")
        self.assertEqual(report["source"], "named-deck.pptx")
        self.assertNotIn(str(self.root), report["source"])


if __name__ == "__main__":
    unittest.main()
