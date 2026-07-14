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

# Wave 1–2 role keywords in section titles → recipe ids (order matters).
_ROLE_TITLE_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(okr|okrs|objectives?\s+and\s+key\s+results)\b", re.I), "okrs_tree"),
    (re.compile(r"\b(rag|status\s+report|project\s+status|traffic\s+light)\b", re.I),
     "project_status_rag"),
    (re.compile(r"\b(swot)\b", re.I), "swot_2x2"),
    (re.compile(r"\b(gantt|schedule|timeline\s+bar)\b", re.I), "gantt_bars"),
    (re.compile(r"\b(waterfall|bridge\s+chart|variance\s+bridge)\b", re.I),
     "waterfall_insight"),
    (re.compile(r"\b(venn|overlap\s+sets?)\b", re.I), "venn_overlap"),
    (re.compile(r"\b(pipeline|funnel\s+sales|conversion\s+pipeline)\b", re.I),
     "pipeline_stages"),
    (re.compile(r"\b(before\s*/?\s*after|before\s+and\s+after)\b", re.I),
     "before_after_slider"),
    (re.compile(r"\b(case\s+study|customer\s+story)\b", re.I), "case_study_band"),
    (re.compile(r"\b(persona|buyer\s+persona)\b", re.I), "persona_card"),
    (re.compile(r"\b(business\s+model\s+canvas|bmc)\b", re.I), "business_canvas"),
    (re.compile(r"\b(fishbone|ishikawa|root\s+cause)\b", re.I), "fishbone_causes"),
    (re.compile(r"\b(iceberg)\b", re.I), "iceberg_levels"),
    (re.compile(r"\b(adkar|aida|value\s+chain)\b", re.I), "framework_row"),
    (re.compile(r"\b(likert|rating\s+scale|nps\s+scale|smile\s+scale)\b", re.I),
     "scale_rating"),
    (re.compile(r"\b(heatmap|calendar|activity\s+grid)\b", re.I), "calendar_heatmap"),
    (re.compile(r"\b(org\s+chart|organization|reporting\s+line)\b", re.I), "org_tree"),
    (re.compile(r"\b(chevron|arrow\s+process)\b", re.I), "chevron_process"),
    (re.compile(r"\b(cycle|pdca|loop)\b", re.I), "cycle_loop"),
    (re.compile(r"\b(finance|p&l|budget|forecast)\b", re.I), "finance_statement"),
    (re.compile(r"\b(at\s+a\s+glance|stat\s+row|icon\s+stats?)\b", re.I), "icon_stat_row"),
    (re.compile(r"\b(hub\s+and\s+spoke|bullseye|radial)\b", re.I), "hub_spoke"),
    # Wave 4 Infograpify long-tail
    (re.compile(r"\b(mind\s*map|mindmap)\b", re.I), "mindmap_branches"),
    (re.compile(r"\b(customer\s+journey|user\s+journey|journey\s+map)\b", re.I),
     "journey_stages"),
    (re.compile(r"\b(pestle|pestel|pest\b)\b", re.I), "pestle_grid"),
    (re.compile(r"\b(raci|responsibility\s+matrix)\b", re.I), "raci_matrix"),
    (re.compile(r"\b(balanced\s+scorecard|bsc)\b", re.I), "scorecard_balanced"),
    (re.compile(r"\b(hexagon|honeycomb|hex\s+cluster)\b", re.I), "hex_cluster"),
    (re.compile(r"\b(puzzle|jigsaw)\b", re.I), "puzzle_pieces"),
    (re.compile(r"\b(pillar|pillars)\b", re.I), "pillar_columns"),
    (re.compile(r"\b(stair|stairs|maturity\s+model|ascent)\b", re.I), "stairs_ascent"),
    (re.compile(r"\b(checklist|launch\s+readiness)\b", re.I), "checklist_board"),
    (re.compile(r"\b(empathy\s+map)\b", re.I), "empathy_map_quad"),
    (re.compile(r"\b(risk\s+matrix|risk\s+heat|heat\s*map\s+risk)\b", re.I),
     "risk_heat_matrix"),
    (re.compile(r"\b(circle\s+segment|donut\s+legend|ring\s+chart)\b", re.I),
     "circle_segments"),
    (re.compile(r"\b(mission|vision|purpose)\b", re.I), "mission_vision_split"),
]


def _role_from_title(title: str) -> str | None:
    for pat, recipe in _ROLE_TITLE_HINTS:
        if pat.search(title or ""):
            return recipe
    return None


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

    # Wave 1–2: explicit role keywords in ## titles win over generic heuristics.
    role = _role_from_title(title)
    if role:
        content: dict[str, Any] = {"title": title}
        if sec["bullets"]:
            if role in ("icon_stat_row", "pipeline_stages", "framework_row",
                        "chevron_process", "cycle_loop", "hub_spoke"):
                stats = []
                for s in sec["bullets"]:
                    m = _KPI_LINE.match(s)
                    if m:
                        stats.append({
                            "value": m.group(1).strip(),
                            "label": m.group(2).strip(),
                        })
                    else:
                        lab, det = _split_label_detail(s)
                        stats.append({"label": lab, "value": det, "detail": det})
                content["stats"] = stats
                content["stages"] = stats
                content["steps"] = stats
                content["items"] = sec["bullets"]
            elif role in ("okrs_tree",):
                content["objective"] = sec["paras"][0] if sec["paras"] else title
                content["key_results"] = [
                    {"label": a, "detail": b} for a, b in
                    (_split_label_detail(s) for s in sec["bullets"])
                ]
            elif role in ("before_after_slider",):
                if len(sec["subs"]) >= 2:
                    content["before"] = {
                        "title": sec["subs"][0]["title"],
                        "body": " ".join(sec["subs"][0]["paras"]) or "\n".join(
                            sec["subs"][0].get("bullets") or []),
                    }
                    content["after"] = {
                        "title": sec["subs"][1]["title"],
                        "body": " ".join(sec["subs"][1]["paras"]) or "\n".join(
                            sec["subs"][1].get("bullets") or []),
                    }
                else:
                    mid = max(1, len(sec["bullets"]) // 2)
                    content["before"] = {"title": "Before", "body": "\n".join(sec["bullets"][:mid])}
                    content["after"] = {"title": "After", "body": "\n".join(sec["bullets"][mid:])}
            elif role in ("project_status_rag",):
                content["rows"] = [
                    {"name": a, "note": b, "status": "amber"}
                    for a, b in (_split_label_detail(s) for s in sec["bullets"])
                ]
            elif role in ("finance_statement",) and sec["table"]:
                rows = sec["table"]
                content["headers"], content["rows"] = rows[0], rows[1:12]
            elif role in ("case_study_band", "persona_card"):
                content["body"] = " ".join(sec["paras"]) or "\n".join(sec["bullets"])
                content["attrs"] = sec["bullets"]
                content["customer"] = title
            elif sec["bullets"]:
                content["bullets"] = sec["bullets"]
                content["steps"] = sec["bullets"]
            if sec["paras"] and "body" not in content and role != "okrs_tree":
                content.setdefault("body", " ".join(sec["paras"]))
            return [(role, content, 0.8, warnings)]

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
