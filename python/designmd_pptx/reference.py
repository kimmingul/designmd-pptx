"""License-safe structural analysis of reference .pptx decks (Phase 2 / #59).

Infograpify and other premium templates are **local references only**. This
module never exports media, never writes the source package, and by default
redacts all visible text to length / role statistics so analysis JSON is safe
to inspect and (when redacted) safe to commit.

What is measured
----------------
- package inventory (slide count, charts, tables, pictures, groups, SmartArt)
- theme scheme colors + major/minor fonts
- per-slide geometry fingerprints (shape counts, grid hints, density)
- heuristic mapping to existing designmd-pptx recipe families

What is *not* produced
----------------------
- original .pptx / .potx bytes
- embedded images or fonts
- full slide copy (text content is redacted unless ``include_text=True``)
"""

from __future__ import annotations

import json
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "dgm": "http://schemas.openxmlformats.org/drawingml/2006/diagram",
}

# EMU helpers (Office uses English Metric Units).
_EMU_PER_CM = 360_000.0
_SLIDE_W_EMU_DEFAULT = 12_192_000  # 13.333" widescreen
_SLIDE_H_EMU_DEFAULT = 6_858_000   # 7.5"

# Map loose filename tokens → designmd recipe / premium pattern families.
# Keep in sync with docs/recipe-coverage-roadmap.md coarse families.
_FAMILY_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"kpi|dashboard", re.I), "kpi_dashboard"),
    (re.compile(r"timeline|roadmap|gantt", re.I), "timeline_roadmap"),
    (re.compile(
        r"process|flow|funnel|pipeline|value\s*chain|adkar|aida|fishbone|ishikawa",
        re.I,
    ), "process_flow"),
    (re.compile(r"pyramid|triangle|hierarchy|iceberg", re.I), "hierarchy"),
    (re.compile(r"org(?:anizational)?|team|persona", re.I), "org_team"),
    (re.compile(r"pricing|table", re.I), "pricing_table"),
    (re.compile(r"compar|vs\.?|versus|swot|matrix|2\s*x\s*2", re.I), "comparison_matrix"),
    (re.compile(r"agenda|cover|intro|profile|mission|vision", re.I), "narrative_chrome"),
    (re.compile(r"chart|pie|waterfall|venn|cycle|circle", re.I), "chart_story"),
    (re.compile(r"business\s*model|canvas|bmc", re.I), "strategy_canvas"),
    (re.compile(r"map|geo|world|asia|europe|united\s*states|mind\s*map|mindmap", re.I), "geo_map"),
    (re.compile(r"mockup|device", re.I), "device_mockup"),
]


def _read_rels(zf: zipfile.ZipFile, part: str) -> dict[str, str]:
    base = part.rsplit("/", 1)[0] if "/" in part else ""
    rels_path = f"{base}/_rels/{part.rsplit('/', 1)[-1]}.rels"
    if rels_path not in zf.namelist():
        return {}
    root = ET.fromstring(zf.read(rels_path))
    out: dict[str, str] = {}
    for rel in root.findall("rel:Relationship", NS):
        target = rel.get("Target", "")
        if target.startswith("../"):
            parent = base.rsplit("/", 1)[0] if "/" in base else ""
            target = f"{parent}/{target[3:]}" if parent else target[3:]
        elif not target.startswith("/"):
            target = f"{base}/{target}" if base else target
        out[rel.get("Id", "")] = target.lstrip("/")
    return out


def _slide_parts(zf: zipfile.ZipFile) -> list[str]:
    pres = "ppt/presentation.xml"
    if pres not in zf.namelist():
        raise ValueError("not a pptx: missing ppt/presentation.xml")
    rels = _read_rels(zf, pres)
    root = ET.fromstring(zf.read(pres))
    parts: list[str] = []
    for sld in root.findall(".//p:sldIdLst/p:sldId", NS):
        rid = sld.get(f"{{{NS['r']}}}id")
        target = rels.get(rid or "")
        if target:
            parts.append(target)
    return parts


def _sld_sz(zf: zipfile.ZipFile) -> tuple[int, int]:
    root = ET.fromstring(zf.read("ppt/presentation.xml"))
    sz = root.find("p:sldSz", NS)
    if sz is None:
        return _SLIDE_W_EMU_DEFAULT, _SLIDE_H_EMU_DEFAULT
    return int(sz.get("cx", _SLIDE_W_EMU_DEFAULT)), int(sz.get("cy", _SLIDE_H_EMU_DEFAULT))


def _theme_part(zf: zipfile.ZipFile) -> str | None:
    for name in zf.namelist():
        if re.match(r"ppt/theme/theme\d*\.xml$", name):
            return name
    return None


def _scheme_colors(theme: ET.Element) -> dict[str, str]:
    out: dict[str, str] = {}
    scheme = theme.find(".//a:clrScheme", NS)
    if scheme is None:
        return out
    for child in list(scheme):
        tag = child.tag.rsplit("}", 1)[-1]
        srgb = child.find("a:srgbClr", NS)
        if srgb is not None and srgb.get("val"):
            out[tag] = srgb.get("val", "").upper()
            continue
        sysc = child.find("a:sysClr", NS)
        if sysc is not None and sysc.get("lastClr"):
            out[tag] = sysc.get("lastClr", "").upper()
    return out


def _theme_fonts(theme: ET.Element) -> dict[str, str]:
    out: dict[str, str] = {}
    major = theme.find(".//a:fontScheme/a:majorFont/a:latin", NS)
    minor = theme.find(".//a:fontScheme/a:minorFont/a:latin", NS)
    if major is not None and major.get("typeface"):
        out["major"] = major.get("typeface", "")
    if minor is not None and minor.get("typeface"):
        out["minor"] = minor.get("typeface", "")
    return out


def _emu_cm(n: int) -> float:
    return round(n / _EMU_PER_CM, 3)


def _geometry(el: ET.Element) -> tuple[int, int, int, int]:
    xfrm = el.find(".//a:xfrm", NS)
    if xfrm is None:
        return 0, 0, 0, 0
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    x = int(off.get("x", 0)) if off is not None else 0
    y = int(off.get("y", 0)) if off is not None else 0
    w = int(ext.get("cx", 0)) if ext is not None else 0
    h = int(ext.get("cy", 0)) if ext is not None else 0
    return x, y, w, h


def _text_stats(tx_body: ET.Element | None) -> dict[str, Any]:
    if tx_body is None:
        return {"chars": 0, "paras": 0, "max_sz_pt": 0}
    paras = 0
    chars = 0
    sizes: list[int] = []
    for p in tx_body.findall("a:p", NS):
        text = "".join(t.text or "" for t in p.findall(".//a:t", NS)).strip()
        if text:
            paras += 1
            chars += len(text)
        for rpr in p.findall(".//a:rPr", NS):
            if rpr.get("sz"):
                sizes.append(int(rpr.get("sz", 0)))
    return {
        "chars": chars,
        "paras": paras,
        "max_sz_pt": (max(sizes) // 100) if sizes else 0,
    }


def _preset(sp: ET.Element) -> str | None:
    prst = sp.find(".//a:prstGeom", NS)
    return prst.get("prst") if prst is not None else None


def _fill_hex(sp: ET.Element) -> str | None:
    srgb = sp.find(".//a:solidFill/a:srgbClr", NS)
    if srgb is not None and srgb.get("val"):
        return srgb.get("val", "").upper()
    scheme = sp.find(".//a:solidFill/a:schemeClr", NS)
    if scheme is not None and scheme.get("val"):
        return f"scheme:{scheme.get('val')}"
    return None


def _analyze_slide(
    zf: zipfile.ZipFile,
    part: str,
    *,
    slide_w: int,
    slide_h: int,
    include_text: bool,
) -> dict[str, Any]:
    root = ET.fromstring(zf.read(part))
    rels = _read_rels(zf, part)
    tree = root.find(".//p:cSld/p:spTree", NS)
    counts = Counter(
        {
            "shapes": 0,
            "connectors": 0,
            "pictures": 0,
            "groups": 0,
            "tables": 0,
            "charts": 0,
            "smartart": 0,
            "text_boxes": 0,
        }
    )
    presets: Counter[str] = Counter()
    fills: Counter[str] = Counter()
    fonts: Counter[str] = Counter()
    boxes: list[dict[str, Any]] = []
    text_chars = 0
    text_paras = 0
    sample_text: list[str] = []

    if tree is None:
        return {
            "part": part,
            "counts": dict(counts),
            "density": {},
            "layout_hints": [],
        }

    counts["connectors"] = len(tree.findall("p:cxnSp", NS))
    counts["groups"] = len(tree.findall("p:grpSp", NS))
    counts["pictures"] = len(tree.findall("p:pic", NS))

    for gf in tree.findall("p:graphicFrame", NS):
        if gf.find(".//a:tbl", NS) is not None:
            counts["tables"] += 1
        uri = ""
        gd = gf.find("a:graphic/a:graphicData", NS)
        if gd is not None:
            uri = gd.get("uri") or ""
        if "chart" in uri:
            counts["charts"] += 1
        if "diagram" in uri or gf.find(".//dgm:relIds", NS) is not None:
            counts["smartart"] += 1

    for sp in tree.findall("p:sp", NS):
        counts["shapes"] += 1
        prst = _preset(sp) or "custom"
        presets[prst] += 1
        fill = _fill_hex(sp)
        if fill:
            fills[fill] += 1
        x, y, w, h = _geometry(sp)
        tx = sp.find("p:txBody", NS)
        stats = _text_stats(tx)
        if stats["paras"]:
            counts["text_boxes"] += 1
            text_chars += stats["chars"]
            text_paras += stats["paras"]
        for latin in sp.findall(".//a:latin", NS):
            tf = latin.get("typeface")
            if tf and not tf.startswith("+"):
                fonts[tf] += 1
        if include_text and tx is not None:
            for p in tx.findall("a:p", NS):
                t = "".join(n.text or "" for n in p.findall(".//a:t", NS)).strip()
                if t and len(sample_text) < 6:
                    sample_text.append(t[:120])
        if w > 0 and h > 0:
            boxes.append(
                {
                    "x_cm": _emu_cm(x),
                    "y_cm": _emu_cm(y),
                    "w_cm": _emu_cm(w),
                    "h_cm": _emu_cm(h),
                    "preset": prst,
                    "max_sz_pt": stats["max_sz_pt"],
                    "paras": stats["paras"],
                }
            )

    # Density / margin estimate from outermost boxes.
    dens: dict[str, Any] = {
        "text_chars": text_chars,
        "text_paras": text_paras,
        "shape_count": counts["shapes"] + counts["pictures"] + counts["groups"],
    }
    if boxes:
        min_x = min(b["x_cm"] for b in boxes)
        min_y = min(b["y_cm"] for b in boxes)
        max_r = max(b["x_cm"] + b["w_cm"] for b in boxes)
        max_b = max(b["y_cm"] + b["h_cm"] for b in boxes)
        sw = _emu_cm(slide_w)
        sh = _emu_cm(slide_h)
        dens.update(
            {
                "margin_left_cm": round(min_x, 2),
                "margin_top_cm": round(min_y, 2),
                "margin_right_cm": round(max(0.0, sw - max_r), 2),
                "margin_bottom_cm": round(max(0.0, sh - max_b), 2),
                "content_width_cm": round(max_r - min_x, 2),
                "content_height_cm": round(max_b - min_y, 2),
            }
        )

    hints = _layout_hints(boxes, counts)
    out: dict[str, Any] = {
        "part": Path(part).name,
        "counts": dict(counts),
        "presets": dict(presets.most_common(12)),
        "fills_top": dict(fills.most_common(8)),
        "fonts": dict(fonts.most_common(6)),
        "density": dens,
        "layout_hints": hints,
        "box_count": len(boxes),
    }
    if include_text and sample_text:
        out["text_samples_redacted"] = False
        out["text_samples"] = sample_text
    else:
        out["text_samples_redacted"] = True
    return out


def _layout_hints(boxes: list[dict[str, Any]], counts: Counter) -> list[str]:
    hints: list[str] = []
    if counts["charts"]:
        hints.append("has_chart")
    if counts["tables"]:
        hints.append("has_table")
    if counts["smartart"]:
        hints.append("has_smartart")
    if counts["connectors"] >= 1:
        hints.append("has_connectors")
    if counts["groups"] >= 2:
        hints.append("heavy_grouping")
    if counts["pictures"] >= 3:
        hints.append("image_heavy")

    text_boxes = [b for b in boxes if b["paras"] > 0 and b["w_cm"] > 1]
    if len(text_boxes) >= 3:
        # similar-height row → card grid
        by_y: dict[int, list] = {}
        for b in text_boxes:
            key = int(round(b["y_cm"] * 2))  # 0.5cm bins
            by_y.setdefault(key, []).append(b)
        best = max(by_y.values(), key=len)
        if len(best) >= 3:
            widths = sorted(b["w_cm"] for b in best)
            med = widths[len(widths) // 2]
            similar = [b for b in best if abs(b["w_cm"] - med) <= 0.35 * med]
            if len(similar) >= 3:
                hints.append(f"card_row_{len(similar)}")
        # KPI-like: short text + large type
        kpi_like = [b for b in text_boxes if b["max_sz_pt"] >= 28 and b["paras"] <= 3]
        if len(kpi_like) >= 3:
            hints.append(f"kpi_band_{len(kpi_like)}")
        # 2×2 matrix
        if 4 <= len(text_boxes) <= 6:
            xs = sorted({round(b["x_cm"], 1) for b in text_boxes})
            ys = sorted({round(b["y_cm"], 1) for b in text_boxes})
            if len(xs) >= 2 and len(ys) >= 2:
                hints.append("matrix_like")
    if counts["shapes"] <= 4 and counts["text_boxes"] <= 2:
        hints.append("sparse_hero")
    return hints


def family_from_name(name: str) -> str:
    stem = Path(name).stem
    for pat, family in _FAMILY_HINTS:
        if pat.search(stem):
            return family
    return "other"


def analyze_pptx(
    pptx: str | Path,
    *,
    include_text: bool = False,
    max_slides: int | None = None,
) -> dict[str, Any]:
    """Return a structural report for one reference deck.

    Parameters
    ----------
    include_text:
        When False (default), no slide text is included — only counts and
        geometry. Turn on only for local interactive study; do not commit.
    max_slides:
        Optional cap for very large decks (analysis still reports total count).
    """
    pptx = Path(pptx)
    if not pptx.is_file():
        raise FileNotFoundError(pptx)

    with zipfile.ZipFile(pptx) as zf:
        parts = _slide_parts(zf)
        slide_w, slide_h = _sld_sz(zf)
        theme_name = _theme_part(zf)
        theme_colors: dict[str, str] = {}
        theme_fonts: dict[str, str] = {}
        if theme_name and theme_name in zf.namelist():
            theme = ET.fromstring(zf.read(theme_name))
            theme_colors = _scheme_colors(theme)
            theme_fonts = _theme_fonts(theme)

        names = zf.namelist()
        package = {
            "parts": len(names),
            "slide_count": len(parts),
            "has_notes": any(n.startswith("ppt/notesSlides/") for n in names),
            "has_charts": any("/charts/" in n for n in names),
            "has_embeddings": any(n.startswith("ppt/embeddings/") for n in names),
            "has_diagrams": any(n.startswith("ppt/diagrams/") for n in names),
            "media_files": sum(1 for n in names if n.startswith("ppt/media/")),
        }

        limit = len(parts) if max_slides is None else min(len(parts), max_slides)
        slides = [
            _analyze_slide(
                zf,
                parts[i],
                slide_w=slide_w,
                slide_h=slide_h,
                include_text=include_text,
            )
            for i in range(limit)
        ]

    # Aggregate
    agg_counts: Counter[str] = Counter()
    agg_hints: Counter[str] = Counter()
    margins_l: list[float] = []
    margins_t: list[float] = []
    for s in slides:
        agg_counts.update(s.get("counts") or {})
        for h in s.get("layout_hints") or []:
            agg_hints[h] += 1
            base = re.sub(r"_\d+$", "", h)
            if base != h:
                agg_hints[base] += 1
        d = s.get("density") or {}
        if "margin_left_cm" in d:
            margins_l.append(float(d["margin_left_cm"]))
            margins_t.append(float(d["margin_top_cm"]))

    return {
        "schema": 1,
        "source": {
            "filename": pptx.name,
            "family_hint": family_from_name(pptx.name),
            # basename only — never absolute path (avoids leaking home dirs)
        },
        "license_note": (
            "Structural analysis only. Do not commit original .pptx. "
            "Default output redacts slide text."
        ),
        "text_included": bool(include_text),
        "slide_size_cm": {
            "width": _emu_cm(slide_w),
            "height": _emu_cm(slide_h),
        },
        "package": package,
        "theme": {"colors": theme_colors, "fonts": theme_fonts},
        "aggregate": {
            "counts": dict(agg_counts),
            "layout_hints": dict(agg_hints.most_common(24)),
            "median_margin_left_cm": (
                round(sorted(margins_l)[len(margins_l) // 2], 2) if margins_l else None
            ),
            "median_margin_top_cm": (
                round(sorted(margins_t)[len(margins_t) // 2], 2) if margins_t else None
            ),
            "slides_analyzed": len(slides),
            "slides_total": package["slide_count"],
        },
        "slides": slides,
        "recipe_suggestions": _suggest_recipes(agg_hints, family_from_name(pptx.name)),
    }


def _suggest_recipes(hints: Counter[str], family: str) -> list[str]:
    """Map structural signals → existing or planned designmd patterns.

    Planned IDs match docs/recipe-coverage-roadmap.md Wave 1–2 (not yet all
    shipped). ``planned:`` prefix marks unimplemented suggestions.
    """
    existing = {
        "kpi_dashboard": ["kpi_dashboard_grid", "kpi_row", "big_number", "chart_insight"],
        "timeline_roadmap": [
            "timeline", "story_timeline", "roadmap_swimlane", "gantt_bars",
        ],
        "process_flow": [
            "process", "funnel_stages", "chevron_process", "cycle_loop",
            "fishbone_causes", "framework_row", "pipeline_stages", "feature_cards",
        ],
        "hierarchy": ["pyramid_levels", "iceberg_levels", "feature_cards"],
        "org_team": ["team", "org_tree", "persona_card", "feature_cards"],
        "pricing_table": ["pricing", "table", "comparison_2col"],
        "comparison_matrix": [
            "comparison_2col", "matrix_2x2", "quadrant_matrix_rich",
            "vs_scorecard", "swot_2x2",
        ],
        "narrative_chrome": [
            "cover", "section_divider", "agenda_toc", "section_opener_numbered",
        ],
        "chart_story": [
            "chart_insight", "chart_callout_panel", "waterfall_insight",
            "venn_overlap", "big_number",
        ],
        "strategy_canvas": ["business_canvas", "feature_cards", "table"],
        "geo_map": ["geo_callout", "image_full", "image_text_2col"],
        "device_mockup": ["device_frame", "image_text_2col", "image_full"],
        "other": [
            "feature_cards", "bullets", "icon_stat_row", "scale_rating",
            "hub_spoke", "before_after_slider", "calendar_heatmap",
            "case_study_band", "okrs_tree", "project_status_rag",
            "finance_statement", "pipeline_stages",
        ],
    }
    # Full-family coverage roadmap (Wave 1 / Wave 2) — keep names stable.
    # Wave 1–2 IDs are shipped — remaining planned are Wave 3 optional / future.
    planned = {
        "kpi_dashboard": ["metric_sparkline_row"],
        "timeline_roadmap": [],
        "process_flow": [],
        "hierarchy": [],
        "org_team": [],
        "comparison_matrix": [],
        "narrative_chrome": ["mission_vision_split"],
        "chart_story": ["cycle_stats"],
        "strategy_canvas": [],
        "geo_map": [],  # geo_callout shipped (user basemap only)
        "device_mockup": [],  # device_frame shipped (user screenshot only)
        "other": [],  # Wave 2 long-tail roles shipped
    }
    sug = list(existing.get(family, existing["other"]))
    for p in planned.get(family, []):
        if p not in sug and f"planned:{p}" not in sug:
            # Only mark as planned if not already a shipped builder.
            from .recipes import RECIPE_BUILDERS
            if p in RECIPE_BUILDERS:
                if p not in sug:
                    sug.append(p)
            else:
                sug.append(f"planned:{p}")
    if hints.get("card_row") or any(k.startswith("card_row_") for k in hints):
        if "feature_cards" not in sug:
            sug.insert(0, "feature_cards")
    if hints.get("kpi_band") or any(k.startswith("kpi_band_") for k in hints):
        if "kpi_row" not in sug:
            sug.insert(0, "kpi_row")
    if hints.get("matrix_like"):
        if "matrix_2x2" not in sug:
            sug.append("matrix_2x2")
    if hints.get("has_chart"):
        if "chart_insight" not in sug:
            sug.append("chart_insight")
    return sug


def analyze_tree(
    root: str | Path,
    *,
    include_text: bool = False,
    max_slides: int | None = 12,
    glob: str = "*.pptx",
) -> dict[str, Any]:
    """Analyze every matching deck under ``root`` (redacted by default)."""
    root = Path(root)
    files = sorted(root.glob(glob)) if root.is_dir() else [root]
    decks: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    families: Counter[str] = Counter()
    for f in files:
        if not f.is_file() or f.suffix.lower() != ".pptx":
            continue
        try:
            rep = analyze_pptx(f, include_text=include_text, max_slides=max_slides)
            # Drop per-slide detail in tree mode to keep the index small;
            # full reports are written one-file-at-a-time by the CLI.
            summary = {
                "filename": rep["source"]["filename"],
                "family_hint": rep["source"]["family_hint"],
                "slide_count": rep["package"]["slide_count"],
                "theme": rep["theme"],
                "aggregate": {
                    k: rep["aggregate"][k]
                    for k in (
                        "counts",
                        "layout_hints",
                        "median_margin_left_cm",
                        "median_margin_top_cm",
                        "slides_analyzed",
                        "slides_total",
                    )
                },
                "recipe_suggestions": rep["recipe_suggestions"],
            }
            decks.append(summary)
            families[rep["source"]["family_hint"]] += 1
        except Exception as exc:  # noqa: BLE001 — collect & continue
            errors.append({"filename": f.name, "error": str(exc)})

    return {
        "schema": 1,
        "root_name": root.name,
        "deck_count": len(decks),
        "families": dict(families.most_common()),
        "errors": errors,
        "decks": decks,
        "license_note": (
            "Index of structural summaries only. Original templates must stay "
            "gitignored (infograpify_ppt_templates/). Never force-add .pptx."
        ),
    }


def write_report(report: dict[str, Any], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def catalog_filenames(root: str | Path) -> dict[str, Any]:
    """Filename-only catalog (safe): families + counts, no package open required."""
    root = Path(root)
    files = sorted(p.name for p in root.glob("*.pptx"))
    families: Counter[str] = Counter(family_from_name(n) for n in files)
    by_family: dict[str, list[str]] = {}
    for n in files:
        by_family.setdefault(family_from_name(n), []).append(n)
    return {
        "schema": 1,
        "total": len(files),
        "families": dict(families.most_common()),
        "by_family": {k: sorted(v) for k, v in sorted(by_family.items())},
        "license_note": (
            "Filenames only. The decks themselves are licensed third-party "
            "assets and must not be committed."
        ),
    }
