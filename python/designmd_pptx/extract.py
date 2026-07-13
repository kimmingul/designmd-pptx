"""Extract content from an existing .pptx into a deck-spec draft (v1.2).

Reverse path: pptx → content.deck.json + extract.report.json + assets/.
Stdlib only (zipfile + ElementTree) — officecli is not required for extraction.
The output is a *draft*: every slide is mapped to the closest recipe pattern
with a confidence score; review the report before scaffolding.
"""

from __future__ import annotations

import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

# Accepts unit suffixes (42ms, 1.2k, 3x, 84.2M, 12건) — v1.5
_KPI_RE = re.compile(r"^\s*[~<>≈]?[$€£₩]?\d[\d,.]*\s*[%xX+]?[A-Za-z가-힣]{0,4}(\s|$)")
_QUOTE_CHARS = "\"'“‘«"

# Recipe capacity limits from content.overlay.schema.json — used for warnings,
# never for silent truncation.
_LIMITS = {"process": 5, "timeline": 6, "kpi_row": 4}


def _read_rels(zf: zipfile.ZipFile, part: str) -> dict[str, str]:
    """Return rId → target (resolved against the part's directory)."""
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
    """Ordered slide part names from presentation.xml sldIdLst."""
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


def _paragraphs(tx_body: ET.Element) -> list[str]:
    paras: list[str] = []
    for p in tx_body.findall("a:p", NS):
        text = "".join(t.text or "" for t in p.findall(".//a:t", NS)).strip()
        if text:
            paras.append(text)
    return paras


def _max_font_size(tx_body: ET.Element) -> int:
    """Largest run font size in hundredths of a point (0 when inherited)."""
    sizes = [
        int(rpr.get("sz", 0))
        for rpr in tx_body.findall(".//a:rPr", NS)
        if rpr.get("sz")
    ]
    return max(sizes, default=0)


def _geometry(sp: ET.Element) -> tuple[int, int, int, int]:
    """(x, y, w, h) in EMU from spPr/xfrm; zeros when unpositioned."""
    xfrm = sp.find(".//a:xfrm", NS)
    if xfrm is None:
        return 0, 0, 0, 0
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    x = int(off.get("x", 0)) if off is not None else 0
    y = int(off.get("y", 0)) if off is not None else 0
    w = int(ext.get("cx", 0)) if ext is not None else 0
    h = int(ext.get("cy", 0)) if ext is not None else 0
    return x, y, w, h


def _similar_row(shapes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Largest group of text boxes sharing a baseline y and similar width —
    the geometry signature of process steps / card grids."""
    boxes = [s for s in shapes if s["w"] > 0 and s["paras"]]
    if len(boxes) < 2:
        return []
    y_tol = 700_000  # ~1.9cm of the 19.05cm slide height
    groups: list[list[dict[str, Any]]] = []
    for box in sorted(boxes, key=lambda s: s["y"]):
        for g in groups:
            if abs(g[0]["y"] - box["y"]) <= y_tol:
                g.append(box)
                break
        else:
            groups.append([box])
    best = max(groups, key=len)
    if len(best) < 2:
        return []
    widths = sorted(s["w"] for s in best)
    median_w = widths[len(widths) // 2]
    row = [s for s in best if median_w and abs(s["w"] - median_w) <= 0.35 * median_w]
    return sorted(row, key=lambda s: s["x"]) if len(row) >= 2 else []


def _parse_slide(zf: zipfile.ZipFile, part: str) -> dict[str, Any]:
    root = ET.fromstring(zf.read(part))
    rels = _read_rels(zf, part)
    title: str | None = None
    subtitle: str | None = None
    body: list[str] = []
    tables: list[list[list[str]]] = []
    pictures: list[dict[str, str]] = []

    tree = root.find(".//p:cSld/p:spTree", NS)
    if tree is None:
        return {"title": None, "subtitle": None, "body": [], "tables": [],
                "pictures": [], "shapes": [], "connectors": 0}

    connectors = len(tree.findall("p:cxnSp", NS))

    plain: list[dict[str, Any]] = []  # non-placeholder text shapes, in order
    for sp in tree.findall("p:sp", NS):
        ph = sp.find(".//p:nvSpPr/p:nvPr/p:ph", NS)
        ph_type = ph.get("type", "body") if ph is not None else None
        tx = sp.find("p:txBody", NS)
        if tx is None:
            continue
        paras = _paragraphs(tx)
        if not paras:
            continue
        if ph_type in ("title", "ctrTitle") and title is None:
            title = " ".join(paras)
        elif ph_type == "subTitle" and subtitle is None:
            subtitle = " ".join(paras)
        elif ph_type is None:
            x, y, w, h = _geometry(sp)
            plain.append({"paras": paras, "sz": _max_font_size(tx),
                          "x": x, "y": y, "w": w, "h": h})
        else:
            body.extend(paras)

    # No title placeholder (common in generated/hand-drawn decks): promote the
    # clearly-largest plain text shape (≥24pt and ≥1.25× the runner-up) to title.
    if title is None and plain:
        top = max(plain, key=lambda s: s["sz"])
        others = [s["sz"] for s in plain if s is not top]
        if top["sz"] >= 2400 and top["sz"] >= 1.25 * max(others, default=0):
            title = " ".join(top["paras"])
            plain.remove(top)
    for shape in plain:
        body.extend(shape["paras"])
    shapes = plain

    for frame in tree.findall("p:graphicFrame", NS):
        for tbl in frame.findall(".//a:tbl", NS):
            rows = []
            for tr in tbl.findall("a:tr", NS):
                rows.append(
                    ["".join(t.text or "" for t in tc.findall(".//a:t", NS)).strip()
                     for tc in tr.findall("a:tc", NS)]
                )
            if rows:
                tables.append(rows)

    for pic in tree.findall("p:pic", NS):
        blip = pic.find(".//p:blipFill/a:blip", NS)
        embed = blip.get(f"{{{NS['r']}}}embed") if blip is not None else None
        media = rels.get(embed or "")
        cnv = pic.find(".//p:nvPicPr/p:cNvPr", NS)
        alt = (cnv.get("descr") or cnv.get("name") or "image") if cnv is not None else "image"
        if media:
            pictures.append({"media": media, "alt": alt})

    return {"title": title, "subtitle": subtitle, "body": body,
            "tables": tables, "pictures": pictures,
            "shapes": shapes, "connectors": connectors}


def _classify(
    slide: dict[str, Any], index: int, total: int
) -> tuple[str, dict[str, Any], float, list[str]]:
    """Map extracted slide content to the closest recipe. Returns
    (recipe, content, confidence, warnings)."""
    warnings: list[str] = []
    title = slide["title"] or ""
    body: list[str] = slide["body"]

    if slide["tables"]:
        rows = slide["tables"][0]
        if len(slide["tables"]) > 1:
            warnings.append("multiple tables on slide; only the first was mapped")
        content = {"title": title, "headers": rows[0], "rows": rows[1:]}
        if body:
            content["notes"] = " ".join(body)
        return "table", content, 0.9, warnings

    if slide["pictures"]:
        pic = slide["pictures"][0]
        if len(slide["pictures"]) > 1:
            warnings.append("multiple pictures on slide; only the first was mapped")
        if body:
            return (
                "image_text_2col",
                {"title": title, "body": "\n".join(body),
                 "src": pic["src"], "alt": pic["alt"]},
                0.8,
                warnings,
            )
        return (
            "image_full",
            {"title": title, "src": pic["src"], "alt": pic["alt"]},
            0.8,
            warnings,
        )

    if index == 0:
        sub = slide["subtitle"] or (body[0] if body else "")
        if len(body) > 1:
            warnings.append("cover keeps only the first body line as subtitle")
        return "cover", {"title": title or "Untitled", "subtitle": sub}, 0.7, warnings

    # Geometry-based structure recovery (v1.5): connectors + a row of similar
    # boxes = process; 3–4 similar boxes with multi-line text = feature cards.
    shapes = slide.get("shapes") or []
    row = _similar_row(shapes)
    if slide.get("connectors", 0) >= 1 and 2 <= len(row) <= 5:
        steps = [" ".join(s["paras"]) for s in row]
        return "process", {"title": title, "steps": steps}, 0.75, warnings
    if 3 <= len(row) <= 4 and all(len(s["paras"]) >= 2 for s in row):
        cards = [{"title": s["paras"][0], "body": " ".join(s["paras"][1:])} for s in row]
        return "feature_cards", {"title": title, "cards": cards}, 0.7, warnings

    # A single dominant huge numeric = big_number hero slide.
    huge = [s for s in shapes if s["sz"] >= 5400 and s["paras"]]
    if len(huge) == 1 and _KPI_RE.match(huge[0]["paras"][0]):
        value = huge[0]["paras"][0]
        rest = [p for p in body if p != value]
        content = {"value": value, "label": title or (rest[0] if rest else "")}
        if rest and title:
            content["context"] = rest[0]
        return "big_number", content, 0.7, warnings

    kpi_hits = [p for p in body if _KPI_RE.match(p) and len(p) <= 40]
    if 2 <= len(kpi_hits) <= 4 and len(kpi_hits) >= max(2, len(body) - 1):
        kpis = []
        for p in kpi_hits:
            m = _KPI_RE.match(p)
            value = p[: m.end()].strip()
            kpis.append({"value": value, "label": p[m.end():].strip() or value})
        return "kpi_row", {"title": title, "kpis": kpis}, 0.6, warnings

    if body and body[0][:1] in _QUOTE_CHARS and len(body) <= 2:
        content = {"quote": body[0].strip(_QUOTE_CHARS + "”’» ")}
        if len(body) == 2:
            content["attribution"] = body[1].lstrip("—- ")
        return "quote", content, 0.6, warnings

    if index == total - 1 and len(body) <= 3 and sum(len(p) for p in body) < 200:
        content: dict[str, Any] = {"title": title or "Next step"}
        if len(body) >= 2 and len(body[-1]) < 40:
            content["body"] = " ".join(body[:-1])
            content["cta"] = body[-1]
        elif body:
            content["body"] = " ".join(body)
        return "close", content, 0.5, warnings

    if len(body) <= 1 and sum(len(p) for p in body) < 140:
        content = {"title": title or "Section"}
        if body:
            content["blurb"] = body[0]
        return "section_divider", content, 0.5, warnings

    # Strip bullet glyphs baked into the source text — the bullets recipe
    # re-adds its own markers, so keeping them would double up.
    cleaned = [re.sub(r"^[•▪◦‣·*]\s*|^-\s+", "", p) for p in body]
    return "bullets", {"title": title, "bullets": cleaned}, 0.4, warnings


def extract_pptx(
    pptx: str | Path,
    out_dir: str | Path,
    *,
    export_media: bool = True,
) -> dict[str, Any]:
    """Extract pptx → deck-spec draft. Writes content.deck.json,
    extract.report.json, and assets/ under out_dir. Returns the report."""
    pptx = Path(pptx)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    assets = out_dir / "assets"

    slides_spec: list[dict[str, Any]] = []
    report_slides: list[dict[str, Any]] = []
    exported: dict[str, str] = {}

    with zipfile.ZipFile(pptx) as zf:
        parts = _slide_parts(zf)
        if not parts:
            raise ValueError(f"{pptx}: no slides found")
        for idx, part in enumerate(parts):
            slide = _parse_slide(zf, part)
            media_warnings: list[str] = []
            for pic in slide["pictures"]:
                media = pic["media"]
                if export_media and media in zf.namelist():
                    if media not in exported:
                        assets.mkdir(parents=True, exist_ok=True)
                        name = Path(media).name
                        if (assets / name).exists() and media not in exported.values():
                            name = f"{idx + 1:02d}-{name}"
                        (assets / name).write_bytes(zf.read(media))
                        exported[media] = f"assets/{name}"
                    pic["src"] = exported[media]
                else:
                    pic["src"] = ""
                    if export_media:
                        media_warnings.append(f"media part {media} not found in package")

            recipe, content, confidence, warnings = _classify(slide, idx, len(parts))
            warnings.extend(media_warnings)
            limit = _LIMITS.get(recipe)
            items = content.get("kpis") or content.get("steps") or []
            if limit and len(items) > limit:
                warnings.append(f"{recipe} supports at most {limit} items; got {len(items)}")
            if recipe in ("image_full", "image_text_2col") and not content.get("src"):
                warnings.append("image src could not be exported — set it manually")

            slides_spec.append(
                {"id": f"s{idx + 1:02d}-{recipe}", "recipe": recipe, "content": content}
            )
            report_slides.append(
                {
                    "index": idx + 1,
                    "recipe": recipe,
                    "confidence": confidence,
                    "title": slide["title"],
                    "warnings": warnings,
                }
            )

    deck = {"version": "1.1", "slides": slides_spec}
    deck_path = out_dir / "content.deck.json"
    deck_path.write_text(
        json.dumps(deck, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    report = {
        "source": str(pptx),
        "slides": report_slides,
        "assets": sorted(exported.values()),
        "note": (
            "Draft mapping — review recipes/content before scaffold; "
            "asset src paths are relative to this directory"
        ),
    }
    (out_dir / "extract.report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
