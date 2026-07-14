"""Extract content from an existing .pptx into a deck-spec draft (v1.2+).

Reverse path: pptx → content.deck.json + extract.report.json + assets/.
Stdlib only (zipfile + ElementTree) — officecli is not required for extraction.
The output is a *draft*: every slide is mapped to the closest recipe pattern
with a confidence score; review the report before scaffolding.

Phase 2 / #12 fidelity
----------------------
- Charts: type + categories + series values when chart XML is readable
- Groups: recursive shape walk (text inside ``p:grpSp`` is recovered)
- SmartArt / diagrams: text fallback + explicit loss-ledger entries
- Animations, embeddings, OLE: recorded in the loss ledger (never silent)
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
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "dgm": "http://schemas.openxmlformats.org/drawingml/2006/diagram",
    "c14": "http://schemas.microsoft.com/office/drawing/2007/8/2/chart",
}

# Accepts unit suffixes (42ms, 1.2k, 3x, 84.2M, 12건) — v1.5
_KPI_RE = re.compile(r"^\s*[~<>≈]?[$€£₩]?\d[\d,.]*\s*[%xX+]?[A-Za-z가-힣]{0,4}(\s|$)")
_QUOTE_CHARS = "\"'“‘«"

# Recipe capacity limits from content.overlay.schema.json — used for warnings,
# never for silent truncation.
_LIMITS = {"process": 5, "timeline": 6, "kpi_row": 4}

# Chart type local-names → officecli / content chart_type strings.
_CHART_TYPE_MAP = {
    "barChart": "bar",
    "bar3DChart": "bar",
    "colChart": "column",
    "lineChart": "line",
    "line3DChart": "line",
    "areaChart": "area",
    "area3DChart": "area",
    "pieChart": "pie",
    "pie3DChart": "pie",
    "doughnutChart": "doughnut",
    "scatterChart": "scatter",
    "bubbleChart": "bubble",
    "radarChart": "radar",
    "surfaceChart": "surface",
    "stockChart": "stock",
    "ofPieChart": "pie",
}


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


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


def _loss(
    kind: str,
    *,
    detail: str,
    recoverable: bool = False,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "kind": kind,
        "detail": detail,
        "recoverable": recoverable,
    }
    if data:
        entry["data"] = data
    return entry


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


def _chart_type(chart_root: ET.Element) -> str:
    plot = chart_root.find(".//c:plotArea", NS)
    if plot is None:
        return "column"
    for child in list(plot):
        local = _local(child.tag)
        if local in _CHART_TYPE_MAP:
            return _CHART_TYPE_MAP[local]
        if local.endswith("Chart") and local not in ("ofPieChart",):
            # unknown *Chart → strip suffix
            base = local[: -len("Chart")].lower() if local.endswith("Chart") else local
            return base or "column"
    return "column"


def _num_ref_values(parent: ET.Element | None) -> list[str]:
    if parent is None:
        return []
    # Prefer cached numbers; fall back to string cache / literal pts.
    pts = parent.findall(".//c:numCache/c:pt", NS)
    if pts:
        out = []
        for pt in sorted(pts, key=lambda e: int(e.get("idx", 0))):
            v = pt.find("c:v", NS)
            out.append((v.text or "").strip() if v is not None else "")
        return out
    pts = parent.findall(".//c:strCache/c:pt", NS)
    if pts:
        out = []
        for pt in sorted(pts, key=lambda e: int(e.get("idx", 0))):
            v = pt.find("c:v", NS)
            out.append((v.text or "").strip() if v is not None else "")
        return out
    return []


def _series_name(ser: ET.Element) -> str:
    tx = ser.find("c:tx", NS)
    if tx is None:
        return ""
    v = tx.find(".//c:v", NS)
    if v is not None and (v.text or "").strip():
        return (v.text or "").strip()
    pts = _num_ref_values(tx)
    return pts[0] if pts else ""


def _parse_chart_part(zf: zipfile.ZipFile, chart_part: str) -> dict[str, Any] | None:
    if chart_part not in zf.namelist():
        return None
    try:
        root = ET.fromstring(zf.read(chart_part))
    except ET.ParseError:
        return None
    chart_type = _chart_type(root)
    cats: list[str] = []
    series: list[dict[str, Any]] = []
    for ser in root.findall(".//c:ser", NS):
        name = _series_name(ser) or f"Series {len(series) + 1}"
        # Categories often live on the first series' cat node.
        cat_vals = _num_ref_values(ser.find("c:cat", NS))
        if cat_vals and not cats:
            cats = cat_vals
        vals = _num_ref_values(ser.find("c:val", NS))
        if not vals:
            vals = _num_ref_values(ser.find("c:yVal", NS))
        series.append({"name": name, "values": vals})
    if not series:
        return {
            "chart_type": chart_type,
            "categories": [],
            "series": [],
            "partial": True,
        }
    return {
        "chart_type": chart_type,
        "categories": cats,
        "series": series,
        "partial": False,
    }


def _walk_shapes(
    tree: ET.Element,
    *,
    in_group: bool = False,
) -> tuple[list[dict[str, Any]], int, int, list[dict[str, Any]]]:
    """Walk spTree / grpSp for text shapes. Returns
    (plain_shapes, connector_count, group_count, losses)."""
    plain: list[dict[str, Any]] = []
    connectors = 0
    groups = 0
    losses: list[dict[str, Any]] = []

    for child in list(tree):
        local = _local(child.tag)
        if local == "cxnSp":
            connectors += 1
            continue
        if local == "grpSp":
            groups += 1
            sub_plain, sub_cxn, sub_grp, sub_loss = _walk_shapes(child, in_group=True)
            plain.extend(sub_plain)
            connectors += sub_cxn
            groups += sub_grp
            losses.extend(sub_loss)
            continue
        if local != "sp":
            continue
        ph = child.find(".//p:nvSpPr/p:nvPr/p:ph", NS)
        ph_type = ph.get("type", "body") if ph is not None else None
        tx = child.find("p:txBody", NS)
        if tx is None:
            continue
        paras = _paragraphs(tx)
        if not paras:
            continue
        x, y, w, h = _geometry(child)
        cnv = child.find(".//p:cNvPr", NS)
        name = cnv.get("name") if cnv is not None else ""
        plain.append({
            "paras": paras,
            "sz": _max_font_size(tx),
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "ph_type": ph_type,
            "in_group": in_group,
            "name": name or "",
        })
    return plain, connectors, groups, losses


def _parse_slide(zf: zipfile.ZipFile, part: str) -> dict[str, Any]:
    root = ET.fromstring(zf.read(part))
    rels = _read_rels(zf, part)
    title: str | None = None
    subtitle: str | None = None
    body: list[str] = []
    tables: list[list[list[str]]] = []
    pictures: list[dict[str, str]] = []
    charts: list[dict[str, Any]] = []
    losses: list[dict[str, Any]] = []
    placeholders: list[dict[str, Any]] = []

    tree = root.find(".//p:cSld/p:spTree", NS)
    if tree is None:
        return {
            "title": None,
            "subtitle": None,
            "body": [],
            "tables": [],
            "pictures": [],
            "shapes": [],
            "connectors": 0,
            "groups": 0,
            "charts": [],
            "losses": [_loss("empty_slide", detail="no spTree")],
            "placeholders": [],
            "has_animation": False,
            "smartart_count": 0,
        }

    # Timing / animation detection
    has_animation = bool(
        root.find(".//p:timing", NS) is not None
        or root.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}timing")
        is not None
    )
    if has_animation:
        losses.append(_loss(
            "animation",
            detail="slide has timing/animation; transitions are not reconstructed",
            recoverable=False,
        ))

    raw_shapes, connectors, groups, walk_losses = _walk_shapes(tree)
    losses.extend(walk_losses)

    plain: list[dict[str, Any]] = []
    for sp in raw_shapes:
        ph_type = sp.get("ph_type")
        paras = sp["paras"]
        if ph_type in ("title", "ctrTitle") and title is None:
            title = " ".join(paras)
            placeholders.append({"type": ph_type, "role": "title", "text": title})
        elif ph_type == "subTitle" and subtitle is None:
            subtitle = " ".join(paras)
            placeholders.append({"type": ph_type, "role": "subtitle", "text": subtitle})
        elif ph_type is None:
            plain.append(sp)
        else:
            body.extend(paras)
            placeholders.append({
                "type": ph_type,
                "role": "body",
                "text": " ".join(paras)[:200],
            })

    if title is None and plain:
        top = max(plain, key=lambda s: s["sz"])
        others = [s["sz"] for s in plain if s is not top]
        if top["sz"] >= 2400 and top["sz"] >= 1.25 * max(others, default=0):
            title = " ".join(top["paras"])
            plain.remove(top)
    for shape in plain:
        body.extend(shape["paras"])
    shapes = plain
    if groups:
        # Informative — not a hard loss; text was recovered via recursive walk.
        losses.append(_loss(
            "group_shapes",
            detail=f"{groups} group(s) expanded; nested transforms not re-applied",
            recoverable=True,
            data={"group_count": groups},
        ))

    smartart_count = 0
    for frame in tree.findall("p:graphicFrame", NS):
        # Tables
        for tbl in frame.findall(".//a:tbl", NS):
            rows = []
            for tr in tbl.findall("a:tr", NS):
                rows.append(
                    ["".join(t.text or "" for t in tc.findall(".//a:t", NS)).strip()
                     for tc in tr.findall("a:tc", NS)]
                )
            if rows:
                tables.append(rows)

        gd = frame.find("a:graphic/a:graphicData", NS)
        uri = (gd.get("uri") if gd is not None else "") or ""

        # Charts
        chart_el = frame.find(".//c:chart", NS)
        if chart_el is not None or "chart" in uri.lower():
            rid = chart_el.get(f"{{{NS['r']}}}id") if chart_el is not None else None
            if not rid and gd is not None:
                # some writers put r:id on graphicData children differently
                for el in gd.iter():
                    rid = el.get(f"{{{NS['r']}}}id")
                    if rid:
                        break
            chart_part = rels.get(rid or "")
            parsed = _parse_chart_part(zf, chart_part) if chart_part else None
            if parsed and parsed.get("series"):
                charts.append(parsed)
            else:
                losses.append(_loss(
                    "chart",
                    detail="chart present but series/categories could not be parsed",
                    recoverable=False,
                    data={"part": chart_part or "", "rid": rid or ""},
                ))
            continue

        # SmartArt / diagrams
        if "diagram" in uri.lower() or frame.find(".//dgm:relIds", NS) is not None:
            smartart_count += 1
            # Collect any visible text still hanging off the frame / related parts.
            texts = [
                "".join(t.text or "" for t in frame.findall(".//a:t", NS)).strip()
            ]
            texts = [t for t in texts if t]
            # Try diagram drawing / data parts via rels on the frame.
            dgm = frame.find(".//dgm:relIds", NS)
            dgm_texts: list[str] = []
            if dgm is not None:
                for attr in ("dm", "lo", "qs", "cs"):
                    # Attributes are r:dm etc. in the r namespace
                    rid = dgm.get(f"{{{NS['r']}}}{attr}") or dgm.get(attr)
                    target = rels.get(rid or "")
                    if target and target in zf.namelist():
                        try:
                            droot = ET.fromstring(zf.read(target))
                        except ET.ParseError:
                            continue
                        for t_el in droot.findall(".//a:t", NS):
                            if t_el.text and t_el.text.strip():
                                dgm_texts.append(t_el.text.strip())
                        # Also plain <dgm:t> style text in some diagrams
                        for t_el in droot.iter():
                            if _local(t_el.tag) in ("t", "val") and t_el.text and t_el.text.strip():
                                if t_el.text.strip() not in dgm_texts:
                                    dgm_texts.append(t_el.text.strip())
            recovered = dgm_texts or texts
            if recovered:
                # Feed into body so classification can use the text as bullets/process.
                body.extend(recovered)
                losses.append(_loss(
                    "smartart",
                    detail="SmartArt/diagram: text recovered, geometry/layout lost",
                    recoverable=True,
                    data={"texts": recovered[:20]},
                ))
            else:
                losses.append(_loss(
                    "smartart",
                    detail="SmartArt/diagram present; no text recovered",
                    recoverable=False,
                ))
            continue

        # OLE / embedded objects
        if "ole" in uri.lower() or "package" in uri.lower():
            losses.append(_loss(
                "embedding",
                detail=f"embedded object (uri={uri[:80]}) not extracted",
                recoverable=False,
            ))

    for pic in tree.findall(".//p:pic", NS):  # include pics nested in groups
        blip = pic.find(".//a:blip", NS)
        if blip is None:
            blip = pic.find(".//p:blipFill/a:blip", NS)
        embed = blip.get(f"{{{NS['r']}}}embed") if blip is not None else None
        media = rels.get(embed or "")
        cnv = pic.find(".//p:cNvPr", NS)
        if cnv is None:
            cnv = pic.find(".//p:nvPicPr/p:cNvPr", NS)
        alt = (cnv.get("descr") or cnv.get("name") or "image") if cnv is not None else "image"
        if media:
            pictures.append({"media": media, "alt": alt})

    # Package-level embeddings referenced from this slide's rels
    for rid, target in rels.items():
        if "/embeddings/" in target or target.startswith("ppt/embeddings/"):
            losses.append(_loss(
                "embedding",
                detail=f"embedded part {target} not expanded",
                recoverable=False,
                data={"rid": rid, "target": target},
            ))

    return {
        "title": title,
        "subtitle": subtitle,
        "body": body,
        "tables": tables,
        "pictures": pictures,
        "shapes": shapes,
        "connectors": connectors,
        "groups": groups,
        "charts": charts,
        "losses": losses,
        "placeholders": placeholders,
        "has_animation": has_animation,
        "smartart_count": smartart_count,
    }


def _classify(
    slide: dict[str, Any], index: int, total: int
) -> tuple[str, dict[str, Any], float, list[str]]:
    """Map extracted slide content to the closest recipe. Returns
    (recipe, content, confidence, warnings)."""
    warnings: list[str] = []
    title = slide["title"] or ""
    body: list[str] = list(slide["body"])

    # Charts → chart_insight (prefer over tables/pictures when chart data exists)
    charts = slide.get("charts") or []
    if charts:
        ch = charts[0]
        if len(charts) > 1:
            warnings.append(f"{len(charts)} charts on slide; only the first was mapped")
        series = ch.get("series") or []
        cats = ch.get("categories") or []
        content: dict[str, Any] = {
            "title": title or "Chart",
            "chart_type": ch.get("chart_type") or "column",
            "categories": ",".join(str(c) for c in cats),
        }
        if series:
            content["series1_name"] = series[0].get("name") or "Series 1"
            content["series1_values"] = ",".join(str(v) for v in series[0].get("values") or [])
        if len(series) > 1:
            content["series2_name"] = series[1].get("name") or "Series 2"
            content["series2_values"] = ",".join(str(v) for v in series[1].get("values") or [])
        if body:
            content["insight_title"] = "Key insight"
            content["insight_body"] = body[0]
            if len(body) > 1:
                warnings.append("extra body text folded into insight notes")
                content["notes"] = " ".join(body[1:])
        if ch.get("partial"):
            warnings.append("chart data partial — verify series/categories")
        conf = 0.85 if series and cats else 0.65
        return "chart_insight", content, conf, warnings

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
                 "src": pic.get("src", ""), "alt": pic.get("alt", "image")},
                0.8,
                warnings,
            )
        return (
            "image_full",
            {"title": title, "src": pic.get("src", ""), "alt": pic.get("alt", "image")},
            0.8,
            warnings,
        )

    # Geometry-based structure recovery (v1.5): connectors + a row of similar
    # boxes = process; 3–4 similar boxes with multi-line text = feature cards.
    # Run before the index-0 cover heuristic so SmartArt/process on slide 1
    # is not collapsed into a cover.
    shapes = slide.get("shapes") or []
    row = _similar_row(shapes)
    if slide.get("connectors", 0) >= 1 and 2 <= len(row) <= 5:
        steps = [" ".join(s["paras"]) for s in row]
        return "process", {"title": title, "steps": steps}, 0.75, warnings
    if 3 <= len(row) <= 4 and all(len(s["paras"]) >= 2 for s in row):
        cards = [{"title": s["paras"][0], "body": " ".join(s["paras"][1:])} for s in row]
        return "feature_cards", {"title": title, "cards": cards}, 0.7, warnings

    # SmartArt text-only recovery often yields a short process-like list.
    if slide.get("smartart_count", 0) and 2 <= len(body) <= 6:
        warnings.append("classified from SmartArt text fallback (geometry lost)")
        return "process", {"title": title, "steps": body[:5]}, 0.55, warnings

    if index == 0:
        sub = slide["subtitle"] or (body[0] if body else "")
        if len(body) > 1:
            warnings.append("cover keeps only the first body line as subtitle")
        return "cover", {"title": title or "Untitled", "subtitle": sub}, 0.7, warnings

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
    if len(kpi_hits) > 4:
        # Cap to kpi_row capacity; remainder is a warning (no silent drop).
        kpis = []
        for p in kpi_hits[:4]:
            m = _KPI_RE.match(p)
            value = p[: m.end()].strip()
            kpis.append({"value": value, "label": p[m.end():].strip() or value})
        warnings.append(
            f"{len(kpi_hits)} KPI-like values found; mapped first 4 to kpi_row "
            "(split remaining onto another slide)"
        )
        return "kpi_row", {"title": title, "kpis": kpis}, 0.5, warnings

    if body and body[0][:1] in _QUOTE_CHARS and len(body) <= 2:
        content = {"quote": body[0].strip(_QUOTE_CHARS + "”’» ")}
        if len(body) == 2:
            content["attribution"] = body[1].lstrip("—- ")
        return "quote", content, 0.6, warnings

    if index == total - 1 and len(body) <= 3 and sum(len(p) for p in body) < 200:
        content = {"title": title or "Next step"}
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
    all_losses: list[dict[str, Any]] = []

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
            # Surface non-recoverable losses as warnings too (agents see them).
            for loss in slide.get("losses") or []:
                if not loss.get("recoverable", False):
                    warnings.append(f"loss:{loss['kind']}: {loss['detail']}")
                elif loss["kind"] in ("smartart", "group_shapes"):
                    warnings.append(f"loss:{loss['kind']}: {loss['detail']}")

            limit = _LIMITS.get(recipe)
            items = (
                content.get("kpis")
                or content.get("steps")
                or content.get("stages")
                or []
            )
            if limit and len(items) > limit:
                warnings.append(f"{recipe} supports at most {limit} items; got {len(items)}")
            if recipe in ("image_full", "image_text_2col") and not content.get("src"):
                warnings.append("image src could not be exported — set it manually")

            slides_spec.append(
                {"id": f"s{idx + 1:02d}-{recipe}", "recipe": recipe, "content": content}
            )
            slide_losses = list(slide.get("losses") or [])
            all_losses.extend(
                {**loss, "slide": idx + 1} for loss in slide_losses
            )
            report_slides.append(
                {
                    "index": idx + 1,
                    "recipe": recipe,
                    "confidence": confidence,
                    "title": slide["title"],
                    "warnings": warnings,
                    "losses": slide_losses,
                    "geometry": {
                        "shapes": len(slide.get("shapes") or []),
                        "groups": slide.get("groups", 0),
                        "connectors": slide.get("connectors", 0),
                        "charts": len(slide.get("charts") or []),
                        "tables": len(slide.get("tables") or []),
                        "pictures": len(slide.get("pictures") or []),
                        "smartart": slide.get("smartart_count", 0),
                        "placeholders": len(slide.get("placeholders") or []),
                    },
                    "placeholders": slide.get("placeholders") or [],
                    "has_animation": bool(slide.get("has_animation")),
                }
            )

    deck = {"version": "1.1", "slides": slides_spec}
    deck_path = out_dir / "content.deck.json"
    deck_path.write_text(
        json.dumps(deck, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Aggregate loss ledger
    by_kind: dict[str, int] = {}
    for loss in all_losses:
        by_kind[loss["kind"]] = by_kind.get(loss["kind"], 0) + 1

    report = {
        "source": str(pptx.name),  # basename only — avoid leaking absolute paths
        "source_path_hint": pptx.name,
        "slides": report_slides,
        "assets": sorted(exported.values()),
        "loss_ledger": {
            "total": len(all_losses),
            "by_kind": by_kind,
            "entries": all_losses,
        },
        "note": (
            "Draft mapping — review recipes/content before scaffold; "
            "asset src paths are relative to this directory. "
            "loss_ledger lists elements that were not fully reconstructed "
            "(charts without data, SmartArt geometry, animations, embeddings)."
        ),
    }
    (out_dir / "extract.report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
