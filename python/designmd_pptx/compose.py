"""Compose (v1.5): markdown brief/outline → deck-spec draft.

Removes the agent's highest-error step — hand-writing content.deck.json.
Give it a plain markdown outline (# title, ## section per slide, lists,
tables, quotes, images) and it selects recipes, shapes the content, splits
oversized lists, and writes content.deck.json + compose.report.json.

Deterministic, stdlib-only. The output is a *draft*: review the report,
adjust recipes/content, then scaffold with any DESIGN.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_KPI_LINE = re.compile(
    r"^([~<>≈]?[$€£₩]?\d[\d,.]*\s*[%xX+]?[A-Za-z가-힣]{0,4})\s*[—–:\-]\s*(.+)$"
)
_TIMELINE_HINT = re.compile(r"(20\d\d|Q[1-4]|H[12]|1?[0-9]월|[A-Z][a-z]{2,8} 20\d\d)")
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_CTA = re.compile(r"^(?:CTA|cta|행동|다음)\s*[:：]\s*(.+)$")
_BULLET = re.compile(r"^\s*[-*•]\s+(.+)$")
_ORDERED = re.compile(r"^\s*\d+[.)]\s+(.+)$")
_MAX_BULLETS = 5


def _split_label_detail(text: str) -> tuple[str, str]:
    for sep in (" — ", " – ", ": ", " - "):
        if sep in text:
            label, detail = text.split(sep, 1)
            return label.strip(), detail.strip()
    return text.strip(), ""


def _parse_sections(md: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Split markdown into a head (H1 + intro) and H2 sections."""
    head: dict[str, Any] = {"title": None, "paras": []}
    sections: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("# ") and not line.startswith("## "):
            head["title"] = line[2:].strip()
            i += 1
            continue
        if line.startswith("## "):
            cur = {"title": line[3:].strip(), "subs": [], "bullets": [], "ordered": [],
                   "paras": [], "quote": None, "table": [], "images": [], "cta": None}
            sections.append(cur)
            i += 1
            continue
        target = cur if cur is not None else None
        if line.startswith("### ") and target is not None:
            target["subs"].append({"title": line[4:].strip(), "paras": []})
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        if target is None:
            if not line.startswith("#"):
                head["paras"].append(line.strip())
            i += 1
            continue
        m = _IMAGE.search(line)
        if m:
            target["images"].append({"alt": m.group(1) or "image", "src": m.group(2)})
            i += 1
            continue
        if line.lstrip().startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quote_lines.append(lines[i].lstrip()[1:].strip())
                i += 1
            target["quote"] = " ".join(q for q in quote_lines if q)
            continue
        if line.lstrip().startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells):
                    continue  # separator row
                target["table"].append(cells)
            continue
        m = _CTA.match(line.strip())
        if m:
            target["cta"] = m.group(1).strip()
            i += 1
            continue
        m = _BULLET.match(line)
        if m:
            target["bullets"].append(m.group(1).strip())
            i += 1
            continue
        m = _ORDERED.match(line)
        if m:
            target["ordered"].append(m.group(1).strip())
            i += 1
            continue
        if target["subs"]:
            target["subs"][-1]["paras"].append(line.strip())
        else:
            target["paras"].append(line.strip())
        i += 1
    return head, sections


def _quote_for(sec: dict[str, Any]) -> list[tuple[str, dict[str, Any], float, list[str]]]:
    """A quote in a section becomes its own slide (even alongside other elements)."""
    if not sec["quote"]:
        return []
    content: dict[str, Any] = {"quote": sec["quote"].strip('"“”\'')}
    att = next(
        (p.lstrip("—–- ") for p in sec["paras"] if p.startswith(("—", "–", "-"))), None
    )
    if att:
        content["attribution"] = att
    return [("quote", content, 0.85, [])]


def _classify_section(
    sec: dict[str, Any], index: int, total: int
) -> list[tuple[str, dict[str, Any], float, list[str]]]:
    """Map one H2 section to one or more slides; co-located quotes get their own."""
    results = _classify_primary(sec, index, total)
    if sec["quote"] and not any(r[0] == "quote" for r in results):
        results = results + _quote_for(sec)
    return results


def _classify_primary(
    sec: dict[str, Any], index: int, total: int
) -> list[tuple[str, dict[str, Any], float, list[str]]]:
    title = sec["title"]
    warnings: list[str] = []

    if sec["table"]:
        rows = sec["table"]
        headers, body = rows[0], rows[1:]
        dense = len(headers) > 6 or len(body) > 8
        recipe = "appendix_table" if dense else "table"
        if len(body) > 14:
            warnings.append(f"table truncat-risk: {len(body)} rows > 14 — split manually")
        content = {"title": title, "headers": headers, "rows": body[:14]}
        notes = [p for p in sec["paras"] if not p.startswith(("—", "–", "-"))]
        if notes:
            content["notes"] = " ".join(notes)
        return [(recipe, content, 0.9, warnings)]

    if sec["images"]:
        img = sec["images"][0]
        if len(sec["images"]) > 1:
            warnings.append("multiple images; only the first was mapped")
        text = "\n".join(sec["bullets"] + sec["paras"])
        if text:
            return [("image_text_2col",
                     {"title": title, "body": text, "src": img["src"], "alt": img["alt"]},
                     0.85, warnings)]
        return [("image_full", {"title": title, "src": img["src"], "alt": img["alt"]},
                 0.85, warnings)]

    if sec["quote"] and not sec["bullets"] and not sec["ordered"]:
        return _quote_for(sec)

    if sec["ordered"]:
        items = sec["ordered"]
        hits = sum(1 for s in items if _TIMELINE_HINT.search(s))
        if 2 <= len(items) <= 6 and hits >= max(1, len(items) // 2):
            steps = [dict(zip(("label", "detail"), _split_label_detail(s))) for s in items]
            return [("timeline", {"title": title, "steps": steps}, 0.75, warnings)]
        if 2 <= len(items) <= 5:
            return [("process", {"title": title, "steps": items}, 0.75, warnings)]
        warnings.append(f"{len(items)} ordered steps exceed process/timeline caps — mapped to bullets")
        return [("bullets", {"title": title, "bullets": items[:_MAX_BULLETS]}, 0.4, warnings)]

    kpi_hits = [(m.group(1).strip(), m.group(2).strip())
                for s in sec["bullets"] if (m := _KPI_LINE.match(s))]
    if len(sec["bullets"]) == 1 and len(kpi_hits) == 1:
        value, label = kpi_hits[0]
        content = {"value": value, "label": label}
        if sec["paras"]:
            content["context"] = " ".join(sec["paras"])
        return [("big_number", content, 0.7, warnings)]
    if 2 <= len(kpi_hits) <= 4 and len(kpi_hits) == len(sec["bullets"]):
        kpis = [{"value": v, "label": l} for v, l in kpi_hits]
        return [("kpi_row", {"title": title, "kpis": kpis}, 0.75, warnings)]

    if len(sec["subs"]) == 2:
        left, right = sec["subs"]
        return [("comparison_2col",
                 {"title": title,
                  "left": {"title": left["title"], "body": " ".join(left["paras"])},
                  "right": {"title": right["title"], "body": " ".join(right["paras"])}},
                 0.7, warnings)]
    if 3 <= len(sec["subs"]) <= 4:
        cards = [{"title": s["title"], "body": " ".join(s["paras"])} for s in sec["subs"]]
        return [("feature_cards", {"title": title, "cards": cards}, 0.7, warnings)]

    if index == total - 1 and (sec["cta"] or sum(len(p) for p in sec["paras"]) < 200):
        content = {"title": title}
        body = " ".join(sec["paras"]) or " ".join(sec["bullets"])
        if body:
            content["body"] = body
        if sec["cta"]:
            content["cta"] = sec["cta"]
        return [("close", content, 0.6, warnings)]

    if not sec["bullets"] and not sec["paras"]:
        return [("section_divider", {"title": title}, 0.6, warnings)]
    if not sec["bullets"] and sec["paras"] and sum(len(p) for p in sec["paras"]) < 140:
        return [("section_divider", {"title": title, "blurb": " ".join(sec["paras"])},
                 0.55, warnings)]

    bullets = sec["bullets"] or sec["paras"]
    if len(bullets) <= _MAX_BULLETS:
        return [("bullets", {"title": title, "bullets": bullets}, 0.5, warnings)]
    # auto-split oversized lists instead of failing downstream caps
    out = []
    for part, start in enumerate(range(0, len(bullets), _MAX_BULLETS)):
        chunk = bullets[start:start + _MAX_BULLETS]
        suffix = "" if part == 0 else f" ({part + 1})"
        out.append(("bullets", {"title": f"{title}{suffix}", "bullets": chunk}, 0.5,
                    ([f"split into {-(-len(bullets) // _MAX_BULLETS)} slides"] if part == 0 else [])))
    return out


def compose_outline(
    brief_md: str | Path,
    out_dir: str | Path,
    *,
    tokens: dict[str, Any] | None = None,
    llm: bool = False,
    style: str | None = None,
    plan: str | Path | None = None,
    llm_cmd: str | None = None,
) -> dict[str, Any]:
    """Compile a markdown brief into content.deck.json + compose.report.json.

    Parameters
    ----------
    llm:
        Opt-in intelligent planner (Phase 3 / #18). Default False keeps the
        fully offline deterministic path. When True, applies
        ``compose_llm.plan_compose`` (plan file / subprocess / offline heuristic).
    style:
        Free-text style directive (e.g. ``"Apple Keynote storytelling"``).
    plan:
        Path to a JSON plan (replay / tests). Implies intelligent path.
    llm_cmd:
        Override ``DESIGNMD_LLM_CMD`` for subprocess planners.
    """
    brief_md = Path(brief_md)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    brief_text = brief_md.read_text(encoding="utf-8")
    head, sections = _parse_sections(brief_text)
    if not head["title"] and not sections:
        raise ValueError(f"{brief_md}: no # title or ## sections found")

    slides: list[dict[str, Any]] = []
    report_slides: list[dict[str, Any]] = []

    cover: dict[str, Any] = {"title": head["title"] or (sections[0]["title"] if sections else "Untitled")}
    if head["paras"]:
        cover["subtitle"] = head["paras"][0]
    slides.append({"id": "s01-cover", "recipe": "cover", "content": cover})
    report_slides.append({"index": 1, "recipe": "cover", "confidence": 0.9,
                          "title": cover["title"], "warnings": []})

    for si, sec in enumerate(sections):
        for recipe, content, confidence, warnings in _classify_section(sec, si, len(sections)):
            n = len(slides) + 1
            slides.append({"id": f"s{n:02d}-{recipe}", "recipe": recipe, "content": content})
            report_slides.append({"index": n, "recipe": recipe, "confidence": confidence,
                                  "title": content.get("title") or content.get("label"),
                                  "warnings": warnings})

    if slides[-1]["recipe"] != "close":
        slides.append({"id": f"s{len(slides) + 1:02d}-close",
                       "recipe": "close", "content": {"title": "Next step"}})
        report_slides.append({"index": len(slides), "recipe": "close", "confidence": 0.4,
                              "title": "Next step",
                              "warnings": ["auto-added close slide — edit its content"]})

    deck = {"version": "1.1", "slides": slides}
    planner_report: dict[str, Any] | None = None
    use_llm = bool(llm or plan or (
        __import__("os").environ.get("DESIGNMD_COMPOSE_LLM", "").strip() in ("1", "true", "yes")
    ))
    if use_llm:
        from .compose_llm import plan_compose

        deck, planner_report = plan_compose(
            deck,
            brief_text=brief_text,
            style=style,
            plan_path=plan,
            tokens=tokens,
            llm_cmd=llm_cmd,
        )
        # Rebuild report_slides from the (possibly revised) deck so agents see
        # the final recipes. Confidence: LLM path bumps base scores slightly.
        report_slides = []
        conf_model = (planner_report or {}).get("confidence_model") or "rules"
        for i, s in enumerate(deck.get("slides") or []):
            base = 0.55
            role = None
            if planner_report and planner_report.get("narrative"):
                for n in planner_report["narrative"]:
                    if n.get("index") == i + 1:
                        role = n.get("role")
                        break
            if conf_model == "llm":
                base = 0.8
            elif planner_report and planner_report.get("accepted"):
                base = 0.65
            report_slides.append({
                "index": i + 1,
                "recipe": s.get("recipe"),
                "confidence": base,
                "title": (s.get("content") or {}).get("title"),
                "role": role,
                "warnings": [],
                "confidence_model": conf_model,
            })

    fit_warnings: list[str] = []
    if tokens is not None:
        from .deck import generate_deck

        try:
            _, _, fit_warnings = generate_deck(tokens, deck, strict=False)
        except ValueError as e:  # structural problem the draft author must fix
            fit_warnings = [str(e)]

    (out_dir / "content.deck.json").write_text(
        json.dumps(deck, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report: dict[str, Any] = {
        "source": str(brief_md.name),  # basename — avoid leaking home paths
        "slides": report_slides,
        "fit_warnings": fit_warnings,
        "note": "Draft — review recipes/content, then scaffold with a DESIGN.md",
    }
    if planner_report is not None:
        report["planner"] = planner_report
        if planner_report.get("accepted"):
            report["note"] += " | planner applied (see report.planner)"
        elif planner_report.get("errors"):
            report["note"] += " | planner rejected plan; deterministic deck kept"
    (out_dir / "compose.report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
