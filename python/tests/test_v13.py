"""v1.3 suite — slide master branding + .potx template export."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from designmd_pptx.compile import compile_design_md
from designmd_pptx.master import brand_master, export_potx

try:  # discovery imports test modules top-level; dotted runs need the package path
    from test_v12 import NS_DECL, THEME_XML, _slide, _sp
except ImportError:  # pragma: no cover
    from python.tests.test_v12 import NS_DECL, THEME_XML, _slide, _sp

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

MASTER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f"<p:sldMaster {NS_DECL}>"
    "<p:cSld><p:spTree><p:nvGrpSpPr/><p:grpSpPr/></p:spTree></p:cSld>"
    '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" '
    'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" '
    'accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
    "<p:txStyles>"
    '<p:titleStyle><a:lvl1pPr><a:defRPr sz="4400"/></a:lvl1pPr></p:titleStyle>'
    '<p:bodyStyle><a:lvl1pPr><a:defRPr sz="2800"/></a:lvl1pPr></p:bodyStyle>'
    "<p:otherStyle/></p:txStyles></p:sldMaster>"
)

_CT_NS = 'xmlns="http://schemas.openxmlformats.org/package/2006/content-types"'
_PML = "application/vnd.openxmlformats-officedocument.presentationml"


def _content_types(n_slides: int) -> str:
    overrides = "".join(
        f'<Override PartName="/ppt/slides/slide{i + 1}.xml" '
        f'ContentType="{_PML}.slide+xml"/>'
        for i in range(n_slides)
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types {_CT_NS}>'
        '<Default Extension="rels" ContentType='
        '"application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'<Override PartName="/ppt/presentation.xml" ContentType="{_PML}.presentation.main+xml"/>'
        f'<Override PartName="/ppt/theme/theme1.xml" ContentType='
        '"application/vnd.openxmlformats-officedocument.theme+xml"/>'
        f'<Override PartName="/ppt/slideMasters/slideMaster1.xml" '
        f'ContentType="{_PML}.slideMaster+xml"/>'
        f"{overrides}</Types>"
    )


def make_full_pptx(path: Path, slides: list[str]) -> Path:
    """Minimal pptx with [Content_Types].xml + slideMaster1.xml + theme."""
    n = len(slides)
    rel_ns = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    sld_ids = "".join(f'<p:sldId id="{256 + i}" r:id="rId{i + 2}"/>' for i in range(n))
    pres = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<p:presentation {NS_DECL}>"
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        f"<p:sldIdLst>{sld_ids}</p:sldIdLst></p:presentation>"
    )
    rel_base = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    pres_rels = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {rel_ns}>'
        f'<Relationship Id="rId1" Type="{rel_base}/slideMaster" '
        'Target="slideMasters/slideMaster1.xml"/>'
        + "".join(
            f'<Relationship Id="rId{i + 2}" Type="{rel_base}/slide" '
            f'Target="slides/slide{i + 1}.xml"/>'
            for i in range(n)
        )
        + "</Relationships>"
    )
    root_rels = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {rel_ns}>'
        f'<Relationship Id="rId1" Type="{rel_base}/officeDocument" '
        'Target="ppt/presentation.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types(n))
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("ppt/presentation.xml", pres)
        zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        zf.writestr("ppt/theme/theme1.xml", THEME_XML)
        zf.writestr("ppt/slideMasters/slideMaster1.xml", MASTER_XML)
        for i, xml in enumerate(slides):
            zf.writestr(f"ppt/slides/slide{i + 1}.xml", xml)
    return path


def _read(pptx: Path, part: str) -> str:
    with zipfile.ZipFile(pptx) as zf:
        return zf.read(part).decode("utf-8")


def _names(pptx: Path) -> list[str]:
    with zipfile.ZipFile(pptx) as zf:
        return zf.namelist()


class MasterV13(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        slides = [
            _slide(_sp(["Deck Title"], ph="ctrTitle")),
            _slide(_sp(["Body"], ph="title")),
        ]
        self.pptx = make_full_pptx(self.root / "deck.pptx", slides)
        self.tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_theme_and_master_branding(self) -> None:
        out = self.root / "branded.pptx"
        report = brand_master(self.pptx, self.tokens, out=out)
        theme = _read(out, "ppt/theme/theme1.xml")
        colors = self.tokens["colors"]
        self.assertIn(f'<a:accent1><a:srgbClr val="{colors["accent"]}"/></a:accent1>', theme)
        self.assertIn(f'<a:lt1><a:srgbClr val="{colors["background"]}"/></a:lt1>', theme)
        master = _read(out, "ppt/slideMasters/slideMaster1.xml")
        title_sz = int(self.tokens["type"]["title_pt"]) * 100
        body_sz = int(self.tokens["type"]["body_pt"]) * 100
        self.assertIn(f'<p:titleStyle><a:lvl1pPr><a:defRPr sz="{title_sz}"/>', master)
        self.assertIn(f'<p:bodyStyle><a:lvl1pPr><a:defRPr sz="{body_sz}"/>', master)
        self.assertEqual(report["master_styles"],
                         {"title_pt": self.tokens["type"]["title_pt"],
                          "body_pt": self.tokens["type"]["body_pt"]})

    def test_slides_untouched(self) -> None:
        out = self.root / "branded.pptx"
        brand_master(self.pptx, self.tokens, out=out)
        self.assertEqual(
            _read(self.pptx, "ppt/slides/slide1.xml"),
            _read(out, "ppt/slides/slide1.xml"),
        )

    def test_in_place_requires_force(self) -> None:
        before = self.pptx.read_bytes()
        with self.assertRaises(FileExistsError):
            brand_master(self.pptx, self.tokens)
        self.assertEqual(self.pptx.read_bytes(), before)
        brand_master(self.pptx, self.tokens, force=True)
        self.assertNotEqual(self.pptx.read_bytes(), before)

    def test_report_written(self) -> None:
        out = self.root / "branded.pptx"
        brand_master(self.pptx, self.tokens, out=out)
        data = json.loads(
            out.with_suffix(".master.report.json").read_text(encoding="utf-8")
        )
        self.assertGreaterEqual(len(data["theme_scheme"]), 10)


class PotxV13(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        slides = [_slide(_sp(["One"], ph="title")), _slide(_sp(["Two"], ph="title"))]
        self.pptx = make_full_pptx(self.root / "deck.pptx", slides)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_content_type_flipped(self) -> None:
        potx = self.root / "brand.potx"
        export_potx(self.pptx, potx)
        ct = _read(potx, "[Content_Types].xml")
        self.assertIn(f"{_PML}.template.main+xml", ct)
        self.assertNotIn(f"{_PML}.presentation.main+xml", ct)
        # slides kept by default
        self.assertIn("ppt/slides/slide1.xml", _names(potx))

    def test_empty_strips_slides(self) -> None:
        potx = self.root / "blank.potx"
        export_potx(self.pptx, potx, empty=True)
        names = _names(potx)
        self.assertFalse([n for n in names if n.startswith("ppt/slides/")])
        self.assertNotIn("<p:sldId ", _read(potx, "ppt/presentation.xml"))
        self.assertNotIn('Target="slides/', _read(potx, "ppt/_rels/presentation.xml.rels"))
        self.assertNotIn('PartName="/ppt/slides/', _read(potx, "[Content_Types].xml"))
        # master + theme survive
        self.assertIn("ppt/slideMasters/slideMaster1.xml", names)
        self.assertIn("ppt/theme/theme1.xml", names)

    def test_extension_enforced(self) -> None:
        with self.assertRaises(ValueError):
            export_potx(self.pptx, self.root / "brand.pptx")

    def test_overwrite_requires_force(self) -> None:
        potx = self.root / "brand.potx"
        potx.write_bytes(b"sentinel")
        with self.assertRaises(FileExistsError):
            export_potx(self.pptx, potx)
        self.assertEqual(potx.read_bytes(), b"sentinel")


class CliV13(unittest.TestCase):
    def test_master_potx_only_leaves_source(self) -> None:
        from designmd_pptx.__main__ import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pptx = make_full_pptx(root / "deck.pptx", [_slide(_sp(["T"], ph="title"))])
            before = pptx.read_bytes()
            rc = main([
                "master", str(pptx), str(FIXTURES / "linear.DESIGN.md"),
                "--potx", str(root / "brand.potx"), "--empty-potx",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(pptx.read_bytes(), before)
            self.assertTrue((root / "brand.potx").exists())
            ct = _read(root / "brand.potx", "[Content_Types].xml")
            self.assertIn(f"{_PML}.template.main+xml", ct)

    def test_master_branded_copy(self) -> None:
        from designmd_pptx.__main__ import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pptx = make_full_pptx(root / "deck.pptx", [_slide(_sp(["T"], ph="title"))])
            rc = main([
                "master", str(pptx), str(FIXTURES / "linear.DESIGN.md"),
                "-o", str(root / "branded.pptx"),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue((root / "branded.pptx").exists())


if __name__ == "__main__":
    unittest.main()
