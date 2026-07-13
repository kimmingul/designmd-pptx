"""v1.5 suite — compose, text-fit + CJK, new recipes, Gate 3 gating,
extract structure recovery, restyle font roles."""

from __future__ import annotations

import inspect
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from designmd_pptx.__main__ import build_parser, main
from designmd_pptx.apply import apply_sequence
from designmd_pptx.compile import compile_design_md
from designmd_pptx.compose import compose_outline
from designmd_pptx.deck import generate_deck
from designmd_pptx.extract import extract_pptx
from designmd_pptx.fit import text_units
from designmd_pptx.fonts import substitute_font
from designmd_pptx.restyle import restyle_pptx

try:
    from test_v12 import NS_DECL, _slide, _sp, make_pptx
except ImportError:  # pragma: no cover
    from python.tests.test_v12 import NS_DECL, _slide, _sp, make_pptx

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

BRIEF = """# FY26 전략 보고

3개년 성장 전략과 투자 우선순위

## 핵심 지표

- 84.2 — ARR (USD millions)
- 118% — 순매출유지율

## 매출 하이라이트

- 42% — 전년 대비 매출 성장

EMEA 신규 출시가 성장을 견인했습니다.

## 실행 프로세스

1. 브리프
2. 디자인
3. 빌드

## 분기 실적

| 분기 | 매출 |
|------|------|
| Q1   | 42   |

> "속도가 곧 전략이다"

— CEO

## 논의 사항

- 항목 하나
- 항목 둘
- 항목 셋
- 항목 넷
- 항목 다섯
- 항목 여섯

## 다음 단계

승인해 주세요.

CTA: 승인
"""


class FitV15(unittest.TestCase):
    def setUp(self) -> None:
        self.tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def test_cjk_wider_than_latin(self) -> None:
        self.assertGreater(text_units("가나다라"), text_units("abcd"))

    def test_long_bullet_rejected_strict(self) -> None:
        spec = {"version": "1.1", "slides": [
            {"id": "b", "recipe": "bullets",
             "content": {"title": "T", "bullets": ["x" * 400]}},
        ]}
        with self.assertRaisesRegex(ValueError, "does not fit"):
            generate_deck(self.tokens, spec)

    def test_reasonable_korean_fits(self) -> None:
        spec = {"version": "1.1", "slides": [
            {"id": "b", "recipe": "bullets",
             "content": {"title": "분기 실적", "bullets": ["매출이 계획을 18% 초과 달성"]}},
        ]}
        ops, _, warns = generate_deck(self.tokens, spec)
        self.assertTrue(ops)
        self.assertFalse([w for w in warns if "fit" in w])

    def test_cjk_font_substitution(self) -> None:
        self.assertEqual(substitute_font("Pretendard"), "Malgun Gothic")
        self.assertEqual(substitute_font("Noto Sans KR"), "Malgun Gothic")
        self.assertEqual(substitute_font("Noto Sans"), "Arial")  # non-KR unchanged


class NewRecipesV15(unittest.TestCase):
    def setUp(self) -> None:
        self.tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")

    def test_all_new_recipes_generate_ops(self) -> None:
        spec = {"version": "1.1", "slides": [
            {"id": "bn", "recipe": "big_number",
             "content": {"value": "118%", "label": "NRR", "context": "Up from 104%"}},
            {"id": "mx", "recipe": "matrix_2x2",
             "content": {"title": "Map", "quadrants": [{"title": "A", "body": "x"}] * 4,
                         "axes": {"x": "Growth", "y": "Share"}}},
            {"id": "tm", "recipe": "team",
             "content": {"title": "Team", "members": [
                 {"name": "Kim Min-Gul", "role": "CEO", "blurb": "PK"},
                 {"name": "Jane Doe", "role": "CTO", "blurb": "Compilers"}]}},
            {"id": "lg", "recipe": "logo_strip",
             "content": {"title": "Customers", "logos": ["Acme", "Globex"]}},
            {"id": "pr", "recipe": "pricing",
             "content": {"title": "Plans", "tiers": [
                 {"name": "Free", "price": "$0", "features": ["A"]},
                 {"name": "Pro", "price": "$29", "features": ["B"], "highlight": True}]}},
            {"id": "ap", "recipe": "appendix_table",
             "content": {"title": "Data", "headers": ["A", "B"], "rows": [["1", "2"]] * 10}},
        ]}
        ops, deck, warns = generate_deck(self.tokens, spec)
        self.assertEqual(len(deck["slides"]), 6)
        self.assertGreater(len(ops), 30)
        self.assertFalse(warns)

    def test_chart_type_passthrough_single_series(self) -> None:
        spec = {"version": "1.1", "slides": [
            {"id": "c", "recipe": "chart_insight",
             "content": {"title": "Mix", "chart_type": "pie",
                         "categories": "A,B", "series1_values": "5,3"}},
        ]}
        ops, _, _ = generate_deck(self.tokens, spec)
        chart = next(o for o in ops if o.get("type") == "chart")["props"]
        self.assertEqual(chart["chartType"], "pie")
        self.assertNotIn("series2.name", chart)

    def test_new_caps_enforced(self) -> None:
        spec = {"version": "1.1", "slides": [
            {"id": "pr", "recipe": "pricing",
             "content": {"tiers": [{"name": str(i), "price": "$1"} for i in range(4)]}},
        ]}
        with self.assertRaises(ValueError):
            generate_deck(self.tokens, spec)


class ComposeV15(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        brief = root / "brief.md"
        brief.write_text(BRIEF, encoding="utf-8")
        tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")
        cls.report = compose_outline(brief, root / "out", tokens=tokens)
        cls.spec = json.loads((root / "out" / "content.deck.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_recipe_mapping(self) -> None:
        recipes = [s["recipe"] for s in self.spec["slides"]]
        self.assertEqual(
            recipes,
            ["cover", "kpi_row", "big_number", "process", "table",
             "quote", "bullets", "bullets", "close"],
        )

    def test_cover_and_cta(self) -> None:
        self.assertEqual(self.spec["slides"][0]["content"]["title"], "FY26 전략 보고")
        self.assertEqual(self.spec["slides"][-1]["content"]["cta"], "승인")

    def test_quote_attribution_next_to_table(self) -> None:
        quote = next(s for s in self.spec["slides"] if s["recipe"] == "quote")
        self.assertEqual(quote["content"]["attribution"], "CEO")

    def test_bullets_autosplit(self) -> None:
        bullets = [s for s in self.spec["slides"] if s["recipe"] == "bullets"]
        self.assertEqual(len(bullets), 2)
        self.assertLessEqual(len(bullets[0]["content"]["bullets"]), 5)

    def test_spec_feeds_generate_deck(self) -> None:
        tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")
        ops, deck, _ = generate_deck(tokens, self.spec, strict=False)
        self.assertEqual(len(deck["slides"]), len(self.spec["slides"]))
        self.assertGreater(len(ops), 20)

    def test_no_fit_warnings(self) -> None:
        self.assertFalse(self.report["fit_warnings"])


class Gate3V15(unittest.TestCase):
    def test_apply_has_gate3(self) -> None:
        params = inspect.signature(apply_sequence).parameters
        self.assertIn("gate3", params)

    def test_parsers_accept_gate3(self) -> None:
        args = build_parser().parse_args(["apply", "a.pptx", "s.json", "--gate3"])
        self.assertTrue(args.gate3)
        args = build_parser().parse_args(["scaffold", "default", "--apply", "--gate3"])
        self.assertTrue(args.gate3)

    def test_wrappers_include_screenshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc = main(["scaffold", "default", "-o", tmp])
            self.assertEqual(rc, 0)
            ps1 = (Path(tmp) / "apply.ps1").read_text(encoding="utf-8")
            sh = (Path(tmp) / "apply.sh").read_text(encoding="utf-8")
            self.assertIn("--screenshot", ps1)
            self.assertIn("--screenshot", sh)


def _sp_geo(paras: list[str], x: int, y: int, w: int, h: int, sz: int) -> str:
    runs = "".join(
        f'<a:p><a:r><a:rPr lang="en-US" sz="{sz}"/><a:t>{t}</a:t></a:r></a:p>'
        for t in paras
    )
    return (
        '<p:sp><p:nvSpPr><p:cNvPr id="3" name="box"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm></p:spPr>'
        f"<p:txBody><a:bodyPr/>{runs}</p:txBody></p:sp>"
    )


def _connector() -> str:
    return (
        '<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="9" name="conn"/><p:cNvCxnSpPr/>'
        "<p:nvPr/></p:nvCxnSpPr><p:spPr/></p:cxnSp>"
    )


class ExtractStructureV15(unittest.TestCase):
    def _extract(self, slides: list[str]) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pptx = make_pptx(root / "d.pptx", slides)
            extract_pptx(pptx, root / "x")
            spec = json.loads((root / "x" / "content.deck.json").read_text(encoding="utf-8"))
            return spec["slides"]

    def test_connectors_become_process(self) -> None:
        boxes = "".join(
            _sp_geo([f"Step {i + 1}"], x=1_000_000 + i * 3_000_000, y=5_000_000,
                    w=2_500_000, h=1_500_000, sz=1800)
            for i in range(4)
        )
        slides = [
            _slide(_sp(["Cover"], ph="ctrTitle")),
            _slide(_sp(["How we ship"], ph="title") + boxes + _connector()),
        ]
        out = self._extract(slides)
        self.assertEqual(out[1]["recipe"], "process")
        self.assertEqual(out[1]["content"]["steps"],
                         ["Step 1", "Step 2", "Step 3", "Step 4"])

    def test_even_boxes_become_cards(self) -> None:
        boxes = "".join(
            _sp_geo([f"Card {i + 1}", "Body text for the card"],
                    x=1_000_000 + i * 4_000_000, y=5_000_000,
                    w=3_500_000, h=4_000_000, sz=1800)
            for i in range(3)
        )
        slides = [
            _slide(_sp(["Cover"], ph="ctrTitle")),
            _slide(_sp(["Features"], ph="title") + boxes),
        ]
        out = self._extract(slides)
        self.assertEqual(out[1]["recipe"], "feature_cards")
        self.assertEqual(len(out[1]["content"]["cards"]), 3)
        self.assertEqual(out[1]["content"]["cards"][0]["title"], "Card 1")

    def test_huge_numeric_becomes_big_number(self) -> None:
        slides = [
            _slide(_sp(["Cover"], ph="ctrTitle")),
            _slide(
                _sp(["Net revenue retention"], ph="title")
                + _sp_geo(["118%"], x=4_000_000, y=4_000_000,
                          w=20_000_000, h=5_000_000, sz=9600)
            ),
        ]
        out = self._extract(slides)
        self.assertEqual(out[1]["recipe"], "big_number")
        self.assertEqual(out[1]["content"]["value"], "118%")

    def test_unit_suffix_kpi_detected(self) -> None:
        slides = [
            _slide(_sp(["Cover"], ph="ctrTitle")),
            _slide(_sp(["Latency"], ph="title") + _sp(["42ms p50", "310ms p99"])),
        ]
        out = self._extract(slides)
        self.assertEqual(out[1]["recipe"], "kpi_row")


class RestyleFontRolesV15(unittest.TestCase):
    def test_heading_size_keeps_heading_font(self) -> None:
        heading_run = (
            '<a:rPr lang="en-US" sz="3600"><a:latin typeface="Custom Display"/></a:rPr>'
        )
        body_run = (
            '<a:rPr lang="en-US" sz="1800"><a:latin typeface="Custom Text"/></a:rPr>'
        )
        slide = _slide(
            "<p:sp><p:nvSpPr><p:cNvPr id=\"2\" name=\"s\"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>"
            "<p:spPr/><p:txBody><a:bodyPr/>"
            f"<a:p><a:r>{heading_run}<a:t>Title</a:t></a:r></a:p>"
            f"<a:p><a:r>{body_run}<a:t>Body</a:t></a:r></a:p>"
            "</p:txBody></p:sp>"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pptx = make_pptx(root / "d.pptx", [slide])
            tokens = compile_design_md(FIXTURES / "linear.DESIGN.md")
            out = root / "restyled.pptx"
            restyle_pptx(pptx, tokens, out=out)
            with zipfile.ZipFile(out) as zf:
                xml = zf.read("ppt/slides/slide1.xml").decode("utf-8")
            heading = tokens["type"]["heading_font"]
            body = tokens["type"]["body_font"]
            self.assertIn(f'sz="3600"><a:latin typeface="{heading}"', xml)
            self.assertIn(f'sz="1800"><a:latin typeface="{body}"', xml)
            self.assertNotIn("Custom Display", xml)
            self.assertNotIn("Custom Text", xml)


if __name__ == "__main__":
    unittest.main()
