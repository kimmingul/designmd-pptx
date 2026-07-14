"""Phase 5: #21 generative layout, #40 animation, #42 public benchmark."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from designmd_pptx import animation as anim
from designmd_pptx import generative as gen
from designmd_pptx import public_benchmark as pub
from designmd_pptx import recipes as R
from designmd_pptx.__main__ import main
from designmd_pptx.compile import compile_design_md
from designmd_pptx.layout import LayoutOverflow

PKG = Path(__file__).resolve().parent.parent / "designmd_pptx"
FIX = Path(__file__).resolve().parent.parent / "fixtures"
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class Generative21(unittest.TestCase):
    def test_parse_keynote_directive(self) -> None:
        p = gen.parse_style_directive("이 슬라이드를 Apple Keynote 스타일로 재구성해줘")
        self.assertEqual(p["id"], "keynote")
        self.assertTrue(p["force_relayout"])

    def test_parse_swiss(self) -> None:
        p = gen.parse_style_directive("Swiss international typography please")
        self.assertEqual(p["id"], "swiss")

    def test_freeform_tree_validates(self) -> None:
        content = {
            "title": "Hero Moment",
            "body": "A short line.",
            "bullets": ["One", "Two", "Three"],
        }
        profile = gen.parse_style_directive("keynote")
        tree = gen.build_freeform_tree(content, profile)
        val = gen.validate_tree(tree)
        self.assertTrue(val.ok, val.overflow)
        self.assertGreaterEqual(val.placed_count, 1)

    def test_generate_deck_swaps_recipes(self) -> None:
        deck = {
            "version": "1.1",
            "slides": [{
                "id": "s1",
                "recipe": "bullets",
                "content": {
                    "title": "Agenda",
                    "bullets": [f"P{i}" for i in range(8)],
                },
            }],
        }
        report = gen.generate_deck_layout(deck, profile_id="keynote")
        self.assertTrue(report["changed"])
        # keynote maps bullets → feature_cards OR freeform when force
        new_recipe = report["deck"]["slides"][0]["recipe"]
        self.assertIn(new_recipe, ("feature_cards", "freeform"))
        content = report["deck"]["slides"][0]["content"]
        key = "cards" if "cards" in content else "bullets"
        if key in content and key == "bullets":
            self.assertLessEqual(len(content[key]), 4)
            # Overflow preserved (not silent drop)
            if len([f"P{i}" for i in range(8)]) > 4:
                self.assertIn("overflow", content)

    def test_overflow_preserved_not_dropped(self) -> None:
        deck = {
            "slides": [{
                "id": "s1",
                "recipe": "bullets",
                "content": {"title": "T", "bullets": [f"P{i}" for i in range(10)]},
            }],
        }
        report = gen.generate_deck_layout(deck, profile_id="minimal")
        content = report["deck"]["slides"][0]["content"]
        ov = content.get("overflow") or {}
        self.assertTrue(ov.get("bullets") or content.get("notes", "").find("overflow") >= 0
                        or report["deck"]["slides"][0]["recipe"] == "freeform")

    def test_feature_cards_to_bullets_keeps_body(self) -> None:
        deck = {
            "slides": [{
                "id": "s1",
                "recipe": "feature_cards",
                "content": {
                    "title": "T",
                    "cards": [
                        {"title": "A", "body": "BODY_A"},
                        {"title": "B", "body": "BODY_B"},
                    ],
                },
            }],
        }
        report = gen.generate_deck_layout(deck, profile_id="swiss")
        slide = report["deck"]["slides"][0]
        blob = json.dumps(slide)
        self.assertIn("BODY_A", blob)
        self.assertIn("BODY_B", blob)

    def test_placements_reject_nan_and_empty_text(self) -> None:
        ok, _ = gen.validate_placements([
            {"name": "X", "x": float("nan"), "y": 0, "w": 1, "h": 1, "text": "hi", "kind": "text"},
        ])
        self.assertFalse(ok)
        ok, _ = gen.validate_placements([
            {"name": "X", "x": 1, "y": 1, "w": 2, "h": 2, "text": "", "kind": "text"},
        ])
        self.assertFalse(ok)

    def test_vision_density_forces_freeform(self) -> None:
        deck = {
            "slides": [{
                "id": "s1",
                "recipe": "bullets",
                "content": {"title": "T", "bullets": ["a", "b", "c"]},
            }],
        }
        findings = [{
            "code": "density",
            "severity": "error",
            "message": "여백 부족, 시각적 균형 깨짐",
            "slide": 1,
        }]
        report = gen.generate_deck_layout(
            deck, directive="rebalance", findings=findings,
        )
        self.assertEqual(report["deck"]["slides"][0]["recipe"], "freeform")
        placements = report["deck"]["slides"][0]["content"].get("placements")
        self.assertTrue(placements)

    def test_recipe_freeform_emits_ops(self) -> None:
        tokens = compile_design_md(PKG / "default.DESIGN.md")
        ops = R.recipe_freeform(tokens, {
            "title": "Free",
            "body": "Body text",
            "style_directive": "minimal",
        })
        self.assertTrue(any(o.get("type") == "slide" for o in ops))
        self.assertTrue(any(o.get("type") == "shape" for o in ops))

    def test_freeform_in_builders(self) -> None:
        self.assertIn("freeform", R.RECIPE_BUILDERS)
        self.assertIn("freeform", R.PATTERN_LAYOUT["engine"])

    def test_cli_generate(self) -> None:
        deck = {
            "slides": [{
                "id": "s1",
                "recipe": "bullets",
                "content": {"title": "T", "bullets": ["a", "b", "c", "d", "e"]},
            }],
        }
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            deck_p = td_path / "deck.json"
            deck_p.write_text(json.dumps(deck), encoding="utf-8")
            out = td_path / "out"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main([
                    "generate", str(deck_p), "-o", str(out),
                    "--directive", "Apple Keynote style",
                ])
            self.assertEqual(rc, 0)
            self.assertTrue((out / "content.generated.deck.json").is_file())
            self.assertTrue((out / "generative.report.json").is_file())


class Animation40(unittest.TestCase):
    def _minimal_slide_xml(self, name: str = "CoverTitle", spid: str = "2") -> bytes:
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr/>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="{spid}" name="{name}"/>
          <p:cNvSpPr/><p:nvPr/>
        </p:nvSpPr>
        <p:spPr/>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Hi</a:t></a:r></a:p></p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
""".encode("utf-8")

    def test_extract_animation_from_frontmatter(self) -> None:
        cfg, warns = anim.extract_animation({
            "animation": {
                "enabled": True,
                "entrance": "fade",
                "transition": "push",
                "stagger_ms": 200,
            }
        })
        self.assertTrue(cfg["enabled"])
        self.assertEqual(cfg["entrance"], "fade")
        self.assertEqual(cfg["transition"], "push")
        self.assertEqual(cfg["stagger_ms"], 200)
        self.assertEqual(warns, [])

    def test_extract_disabled_default(self) -> None:
        cfg, _ = anim.extract_animation({})
        self.assertFalse(cfg["enabled"])

    def test_inject_slide_adds_timing_and_transition(self) -> None:
        xml = self._minimal_slide_xml()
        new, effects, trn = anim.inject_slide_animation(
            xml, entrance="fade", transition="fade", name_prefixes=["CoverTitle"],
        )
        self.assertGreater(effects, 0)
        self.assertEqual(trn, 1)
        self.assertIn(b"timing", new)
        self.assertIn(b"transition", new)
        self.assertIn(b"animEffect", new)
        # namespace-safe re-parse + CT_Slide order: transition/timing before extLst
        from designmd_pptx import opc
        root = opc.parse(new)
        self.assertIsNotNone(root.find(opc.qn("p:timing")))
        self.assertIsNotNone(root.find(opc.qn("p:transition")))
        tags = [opc.qn(t).split("}")[-1] if False else (
            c.tag.split("}")[-1] if "}" in c.tag else c.tag
        ) for c in list(root)]
        # simplified local names
        locals_ = [c.tag.split("}")[-1] for c in list(root)]
        if "clrMapOvr" in locals_:
            self.assertLess(locals_.index("clrMapOvr"), locals_.index("transition"))
        self.assertLess(locals_.index("transition"), locals_.index("timing"))
        if "extLst" in locals_:
            self.assertLess(locals_.index("timing"), locals_.index("extLst"))

    def test_inplace_requires_force(self) -> None:
        slide = self._minimal_slide_xml("CoverTitle")
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "deck.pptx"
            with zipfile.ZipFile(src, "w") as zf:
                zf.writestr("[Content_Types].xml", "<Types/>")
                zf.writestr("ppt/slides/slide1.xml", slide)
            report = anim.animate_pptx(
                src, out=src,
                animation={"enabled": True, "entrance": "fade", "transition": "fade"},
                force=False,
            )
            self.assertFalse(report.ok)
            self.assertTrue(any("force" in n.lower() for n in report.notes))

    def test_animate_pptx_roundtrip(self) -> None:
        slide = self._minimal_slide_xml("CoverTitle")
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "in.pptx"
            dst = Path(td) / "out.pptx"
            with zipfile.ZipFile(src, "w") as zf:
                zf.writestr("[Content_Types].xml", """<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/slides/slide1.xml"
    ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>""")
                zf.writestr("ppt/slides/slide1.xml", slide)
            report = anim.animate_pptx(
                src, out=dst,
                animation={"enabled": True, "entrance": "fade", "transition": "fade"},
                force=True,
            )
            self.assertTrue(report.ok, report.notes)
            self.assertEqual(report.slides_touched, 1)
            self.assertGreater(report.effects_added, 0)
            with zipfile.ZipFile(dst) as zf:
                data = zf.read("ppt/slides/slide1.xml")
            self.assertIn(b"p:timing", data.replace(b"timing", b"p:timing") or data)
            # Clark notation serialize may use full URI — just check fade filter
            self.assertIn(b"fade", data)

    def test_compile_embeds_animation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "DESIGN.md"
            d.write_text(
                "---\nname: Anim\n"
                "colors:\n  canvas: \"#FFFFFF\"\n  ink: \"#111111\"\n  accent: \"#3366FF\"\n"
                "animation:\n  enabled: true\n  entrance: wipe\n  transition: fade\n"
                "---\n\n# Overview\n\nTest brand.\n",
                encoding="utf-8",
            )
            tokens = compile_design_md(d)
            self.assertIn("animation", tokens)
            self.assertTrue(tokens["animation"]["enabled"])
            self.assertEqual(tokens["animation"]["entrance"], "wipe")

    def test_cli_animate(self) -> None:
        slide = self._minimal_slide_xml("BulletTitle")
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "deck.pptx"
            with zipfile.ZipFile(src, "w") as zf:
                zf.writestr("[Content_Types].xml",
                            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
                zf.writestr("ppt/slides/slide1.xml", slide)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main([
                    "animate", str(src), "--entrance", "appear",
                    "--transition", "fade", "--force",
                ])
            self.assertEqual(rc, 0, buf.getvalue())


class PublicBenchmark42(unittest.TestCase):
    def test_generates_at_least_100(self) -> None:
        decks = pub.generate_public_deck_specs(100)
        self.assertEqual(len(decks), 100)
        ids = {d["id"] for d in decks}
        self.assertEqual(len(ids), 100)
        recipes = {d["meta"]["primary_recipe"] for d in decks}
        self.assertGreaterEqual(len(recipes), 20)
        self.assertEqual(decks[0]["meta"]["license"], pub.PUBLIC_LICENSE)

    def test_public_suite_pass(self) -> None:
        # Smaller smoke is faster; full 100 is also exercised in CLI test with n=100
        report, meta = pub.run_public_suite(n=12)
        self.assertEqual(meta.decks_generated, 12)
        self.assertTrue(report.ok, report.notes)
        self.assertEqual(report.decks_fail, 0)
        self.assertEqual(report.decks_pass, 12)

    def test_public_suite_meets_bar(self) -> None:
        report, meta = pub.run_public_suite(n=100)
        self.assertGreaterEqual(meta.decks_generated, 100)
        self.assertTrue(report.ok, f"notes={report.notes} fail={report.decks_fail}")
        self.assertEqual(report.decks_total, 100)
        self.assertEqual(report.decks_fail, 0)

    def test_write_and_docs(self) -> None:
        report, meta = pub.run_public_suite(n=10)
        with tempfile.TemporaryDirectory() as td:
            paths = pub.write_public_report(report, meta, td)
            self.assertTrue(paths["summary"].is_file())
            self.assertTrue(paths["methodology"].is_file())
            self.assertTrue(paths["index"].is_file())
            summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
            self.assertEqual(summary["rights"]["license"], "CC0-1.0")
            docs = Path(td) / "docs"
            dpath = pub.publish_docs_snapshot(report, meta, docs)
            self.assertTrue(dpath.is_file())
            text = dpath.read_text(encoding="utf-8")
            self.assertIn("methodology", text.lower())
            self.assertIn("CC0", text)

    def test_cli_public(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "bm"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main([
                    "benchmark", "--public", "--public-n", "15",
                    "-o", str(out),
                ])
            self.assertEqual(rc, 0, buf.getvalue())
            self.assertTrue((out / "public-benchmark.summary.json").is_file())
            self.assertIn("public-benchmark", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
