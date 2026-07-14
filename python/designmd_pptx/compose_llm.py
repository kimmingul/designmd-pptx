"""Opt-in intelligent compose planner (Phase 3 / #18).

Default ``compose`` stays fully offline and deterministic. This module is only
used when the caller opts in (``--llm`` / ``DESIGNMD_COMPOSE_LLM=1``).

Providers
---------
1. **plan file** (``--plan path.json``) — apply a pre-authored plan (tests +
   replay). Schema validated; unknown recipes rejected.
2. **subprocess LLM** (``DESIGNMD_LLM_CMD``) — run an external command that
   reads a JSON request on stdin and writes a plan JSON on stdout. No SDK
   hard-dep; agents wire Claude/Codex/Grok themselves.
3. **offline narrative heuristic** — no network: re-tags narrative roles,
   optional style-biased recipe upgrades, confidence bumps. Always available
   as the zero-config ``--llm`` fallback.

Every plan is forced through the same deck validators as hand-written specs
(``normalize_deck_spec`` + ``validate_deck_content_caps`` + optional fit).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from . import recipes as R
from .deck import normalize_deck_spec, validate_deck_content_caps

# Narrative roles for pacing analysis (report + optional reordering hints).
NARRATIVE_ROLES = (
    "introduction",
    "context",
    "data",
    "insight",
    "decision",
    "conclusion",
)

_STYLE_HINTS: dict[str, list[str]] = {
    "keynote": ["big_number", "section_opener_numbered", "quote", "feature_cards"],
    "apple": ["big_number", "section_opener_numbered", "quote", "image_full"],
    "consulting": ["kpi_dashboard_grid", "agenda_toc", "comparison_2col", "process"],
    "mckinsey": ["kpi_row", "matrix_2x2", "process", "comparison_2col"],
    "academic": ["consort_flow", "study_design", "results_table_insight", "table"],
    "medical": ["consort_flow", "kaplan_meier", "forest_plot", "results_table_insight"],
    "story": ["story_timeline", "section_opener_numbered", "quote", "big_number"],
    "data": ["kpi_dashboard_grid", "chart_insight", "chart_callout_panel", "table"],
}


def _role_for_recipe(recipe: str, index: int, total: int) -> str:
    if recipe == "cover" or index == 0:
        return "introduction"
    if recipe in ("close",) or index >= total - 1:
        return "conclusion"
    if recipe in (
        "kpi_row", "kpi_dashboard_grid", "big_number", "table", "appendix_table",
        "chart_insight", "chart_callout_panel", "kaplan_meier", "forest_plot",
        "results_table_insight", "consort_flow",
    ):
        return "data"
    if recipe in ("quote", "comparison_2col", "vs_scorecard", "matrix_2x2",
                  "quadrant_matrix_rich"):
        return "insight"
    if recipe in ("process", "timeline", "story_timeline", "funnel_stages",
                  "roadmap_swimlane", "study_design"):
        return "context"
    if recipe in ("section_divider", "section_opener_numbered", "agenda_toc"):
        return "introduction" if index < total // 3 else "context"
    if recipe in ("feature_cards", "bullets", "pricing", "team"):
        return "context"
    return "context"


def _style_tokens(style: str | None) -> list[str]:
    if not style:
        return []
    s = style.lower()
    hits: list[str] = []
    for key, recipes in _STYLE_HINTS.items():
        if key in s:
            hits.extend(recipes)
    return hits


def annotate_narrative(deck: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach narrative role + pacing notes to each slide (report helper)."""
    slides = deck.get("slides") or []
    total = len(slides)
    out: list[dict[str, Any]] = []
    for i, s in enumerate(slides):
        recipe = str(s.get("recipe") or "")
        role = _role_for_recipe(recipe, i, total)
        out.append({
            "index": i + 1,
            "id": s.get("id"),
            "recipe": recipe,
            "role": role,
            "title": (s.get("content") or {}).get("title"),
        })
    return out


def _pacing_score(roles: list[str]) -> dict[str, Any]:
    """Heuristic narrative-flow score in 0..1."""
    if not roles:
        return {"score": 0.0, "notes": ["empty deck"]}
    notes: list[str] = []
    score = 0.6
    if roles[0] == "introduction":
        score += 0.15
    else:
        notes.append("deck does not open with introduction-class recipe")
    if roles[-1] == "conclusion":
        score += 0.15
    else:
        notes.append("deck does not close with conclusion-class recipe")
    if "data" in roles:
        score += 0.05
    else:
        notes.append("no data-class slides (kpi/chart/table)")
    if "insight" in roles:
        score += 0.05
    # Prefer data before final conclusion
    if "data" in roles and "conclusion" in roles:
        if roles.index("data") < len(roles) - 1:
            score += 0.05
    return {"score": round(min(1.0, score), 2), "notes": notes}


def apply_plan(
    base_deck: dict[str, Any],
    plan: dict[str, Any],
    *,
    tokens: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Merge a planner plan into a base deck. Returns (deck, apply_report).

    Plan schema (subset):
      {
        "version": 1,
        "style": "...",
        "slides": [ {"recipe", "content", "id?", "confidence?", "role?"}, ... ]
          OR "ops": [ {"op":"set_recipe","index":N,"recipe":"..."},
                      {"op":"set_content","index":N,"content":{...}},
                      {"op":"reorder","order":[0,2,1,...]} ]
      }
    """
    report: dict[str, Any] = {
        "mode": "plan",
        "accepted": False,
        "errors": [],
        "warnings": [],
        "source": plan.get("source") or "plan",
    }
    if not isinstance(plan, dict):
        report["errors"].append("plan must be a JSON object")
        return base_deck, report

    # Full replacement path
    if isinstance(plan.get("slides"), list) and plan["slides"]:
        candidate = {"version": plan.get("version") or base_deck.get("version") or "1.1",
                     "slides": plan["slides"]}
    else:
        candidate = json.loads(json.dumps(base_deck))  # deep copy via json
        slides = list(candidate.get("slides") or [])
        for op in plan.get("ops") or []:
            if not isinstance(op, dict):
                report["warnings"].append(f"skip non-object op: {op!r}")
                continue
            kind = op.get("op")
            if kind == "reorder":
                order = op.get("order") or []
                if (
                    isinstance(order, list)
                    and len(order) == len(slides)
                    and sorted(order) == list(range(len(slides)))
                ):
                    slides = [slides[i] for i in order]
                else:
                    report["errors"].append("reorder op has invalid order")
            elif kind == "set_recipe":
                idx = int(op.get("index", -1))
                recipe = str(op.get("recipe") or "")
                recipe = R.RECIPE_ALIASES.get(recipe, recipe)
                if not (0 <= idx < len(slides)):
                    report["errors"].append(f"set_recipe index out of range: {idx}")
                elif recipe not in R.RECIPE_BUILDERS:
                    report["errors"].append(f"unknown recipe in plan: {recipe}")
                else:
                    slides[idx]["recipe"] = recipe
                    if op.get("content") is not None:
                        slides[idx]["content"] = op["content"]
            elif kind == "set_content":
                idx = int(op.get("index", -1))
                if not (0 <= idx < len(slides)):
                    report["errors"].append(f"set_content index out of range: {idx}")
                elif not isinstance(op.get("content"), dict):
                    report["errors"].append("set_content requires content object")
                else:
                    slides[idx]["content"] = op["content"]
            elif kind == "boost_confidence":
                # report-only op — ignored for deck body
                pass
            else:
                report["warnings"].append(f"unknown plan op: {kind!r}")
        candidate["slides"] = slides

    if report["errors"]:
        return base_deck, report

    # Same validators as hand-authored deck-specs
    try:
        deck, norm_warns = normalize_deck_spec(candidate)
    except ValueError as e:
        report["errors"].append(f"normalize failed: {e}")
        return base_deck, report
    report["warnings"].extend(norm_warns)
    cap_errs = validate_deck_content_caps(deck)
    if cap_errs:
        report["errors"].extend(cap_errs)
        return base_deck, report

    if tokens is not None:
        from .deck import generate_deck

        try:
            _, _, fit_warns = generate_deck(tokens, deck, strict=False)
            report["fit_warnings"] = fit_warns
        except ValueError as e:
            report["errors"].append(f"fit/generate failed: {e}")
            return base_deck, report

    report["accepted"] = True
    report["narrative"] = annotate_narrative(deck)
    roles = [n["role"] for n in report["narrative"]]
    report["pacing"] = _pacing_score(roles)
    return deck, report


def offline_narrative_plan(
    base_deck: dict[str, Any],
    *,
    style: str | None = None,
    brief_text: str = "",
) -> dict[str, Any]:
    """Zero-network planner: narrative tags + light style-biased recipe swaps."""
    style_recipes = _style_tokens(style) + _style_tokens(brief_text)
    ops: list[dict[str, Any]] = []
    slides = base_deck.get("slides") or []
    for i, s in enumerate(slides):
        recipe = str(s.get("recipe") or "")
        content = dict(s.get("content") or {})
        title = str(content.get("title") or "").lower()
        # Style-biased upgrades that stay schema-safe
        if recipe == "kpi_row" and "kpi_dashboard_grid" in style_recipes:
            kpis = content.get("kpis") or []
            if isinstance(kpis, list) and len(kpis) >= 4:
                ops.append({
                    "op": "set_recipe",
                    "index": i,
                    "recipe": "kpi_dashboard_grid",
                    "content": content,
                    "reason": "style prefers multi-row KPI dashboard",
                })
        if recipe == "section_divider" and "section_opener_numbered" in style_recipes:
            ops.append({
                "op": "set_recipe",
                "index": i,
                "recipe": "section_opener_numbered",
                "content": {
                    "number": content.get("number") or f"{i:02d}",
                    "title": content.get("title") or "Section",
                    "blurb": content.get("blurb") or "",
                },
                "reason": "style prefers numbered section openers",
            })
        if recipe == "timeline" and "story_timeline" in style_recipes:
            steps = content.get("steps") or []
            if isinstance(steps, list) and len(steps) >= 2:
                ops.append({
                    "op": "set_recipe",
                    "index": i,
                    "recipe": "story_timeline",
                    "content": content,
                    "reason": "style prefers story timeline chrome",
                })
        if recipe == "chart_insight" and "chart_callout_panel" in style_recipes:
            ops.append({
                "op": "set_recipe",
                "index": i,
                "recipe": "chart_callout_panel",
                "content": {
                    **content,
                    "callouts": content.get("callouts") or [
                        content.get("insight_body") or content.get("insight") or "Key takeaway",
                        "What drives the shape of the data",
                        "Decision this enables",
                    ],
                },
                "reason": "style prefers chart + callout storytelling",
            })
        if recipe == "bullets" and any(k in title for k in ("agenda", "agenda", "목차", "outline")):
            items = content.get("bullets") or content.get("items") or []
            if isinstance(items, list) and len(items) >= 5:
                ops.append({
                    "op": "set_recipe",
                    "index": i,
                    "recipe": "agenda_toc",
                    "content": {
                        "title": content.get("title") or "Agenda",
                        "items": [{"label": str(x)} for x in items[:12]],
                    },
                    "reason": "agenda-like bullets → agenda_toc",
                })
    return {
        "version": 1,
        "source": "offline_narrative",
        "style": style or "",
        "ops": ops,
        "notes": [
            "offline planner: no network call; set DESIGNMD_LLM_CMD for external LLM",
        ],
    }


def run_subprocess_planner(
    request: dict[str, Any],
    *,
    cmd: str | None = None,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """Invoke an external planner. ``cmd`` is a shell string (stdin JSON → stdout JSON)."""
    cmd = cmd or os.environ.get("DESIGNMD_LLM_CMD") or ""
    if not cmd.strip():
        raise ValueError("DESIGNMD_LLM_CMD is not set")
    payload = json.dumps(request, ensure_ascii=False).encode("utf-8")
    proc = subprocess.run(
        cmd,
        input=payload,
        capture_output=True,
        shell=True,
        timeout=timeout_s,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or b"").decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"LLM planner failed (rc={proc.returncode}): {err}")
    text = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    if not text:
        raise RuntimeError("LLM planner returned empty stdout")
    # Allow models to wrap JSON in fences
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    plan = json.loads(text)
    if not isinstance(plan, dict):
        raise RuntimeError("LLM planner stdout must be a JSON object")
    plan.setdefault("source", "subprocess_llm")
    return plan


def plan_compose(
    base_deck: dict[str, Any],
    *,
    brief_text: str = "",
    style: str | None = None,
    plan_path: str | Path | None = None,
    use_subprocess: bool | None = None,
    tokens: dict[str, Any] | None = None,
    llm_cmd: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Produce a validated deck from base + optional LLM/plan/heuristic.

    Returns (deck, planner_report). On planner failure, returns base_deck with
    errors recorded (never raises for heuristic path).
    """
    report: dict[str, Any] = {
        "enabled": True,
        "provider": None,
        "accepted": False,
        "errors": [],
        "warnings": [],
    }

    plan: dict[str, Any] | None = None
    if plan_path is not None:
        p = Path(plan_path)
        plan = json.loads(p.read_text(encoding="utf-8"))
        report["provider"] = "plan_file"
        report["plan_path"] = p.name
    else:
        want_sub = use_subprocess
        if want_sub is None:
            want_sub = bool(llm_cmd or os.environ.get("DESIGNMD_LLM_CMD"))
        if want_sub:
            request = {
                "version": 1,
                "task": "compose_plan",
                "style": style or "",
                "brief": brief_text[:12000],
                "base_deck": base_deck,
                "allowed_recipes": sorted(R.RECIPE_BUILDERS.keys()),
                "instructions": (
                    "Return JSON with either slides:[{recipe,content}] replacing the "
                    "deck, or ops:[{op,index,recipe,content}|{op:reorder,order:[...]}]. "
                    "Only use allowed_recipes. Prefer introduction→data→insight→conclusion."
                ),
            }
            try:
                plan = run_subprocess_planner(request, cmd=llm_cmd)
                report["provider"] = "subprocess_llm"
            except Exception as e:  # noqa: BLE001 — fall back offline
                report["warnings"].append(f"subprocess planner failed: {e}; using offline heuristic")
                plan = offline_narrative_plan(base_deck, style=style, brief_text=brief_text)
                report["provider"] = "offline_narrative_fallback"
        else:
            plan = offline_narrative_plan(base_deck, style=style, brief_text=brief_text)
            report["provider"] = "offline_narrative"

    prior_warnings = list(report.get("warnings") or [])
    deck, apply_rep = apply_plan(base_deck, plan or {}, tokens=tokens)
    # Merge apply report without clobbering provider / prior warnings
    for k, v in apply_rep.items():
        if k in ("mode",):
            continue
        if k == "warnings":
            report["warnings"] = prior_warnings + list(v or [])
        elif k == "errors":
            report["errors"] = list(report.get("errors") or []) + list(v or [])
        else:
            report[k] = v
    report["plan_ops"] = len((plan or {}).get("ops") or [])
    report["plan_notes"] = (plan or {}).get("notes") or []
    if not report.get("narrative"):
        report["narrative"] = annotate_narrative(deck)
        report["pacing"] = _pacing_score([n["role"] for n in report["narrative"]])
    # Upgrade confidences in a side channel for the compose report
    report["confidence_model"] = (
        "llm" if report.get("provider") == "subprocess_llm" else "heuristic+rules"
    )
    return deck, report
