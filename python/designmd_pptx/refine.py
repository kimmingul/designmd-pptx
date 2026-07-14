"""Iterative visual refinement loop (Phase 5 / #19).

Takes a deck-spec (and optional Gate 3 vision findings + natural-language
feedback) and proposes **deterministic deck-spec patches** — split dense
bullet slides, shorten bodies, switch to denser recipes, inject notes —
then optionally re-evaluates a contact sheet for up to N rounds.

Does **not** require OfficeCLI by default: pure JSON transforms + offline
vision heuristics. Live vision models plug in via DESIGNMD_VISION_CMD /
``--vision-cmd`` when a contact sheet is provided.

Typical flow
------------
1. scaffold → apply --screenshot --vision  (optional)
2. refine content.deck.json --feedback "too dense" --rounds 3
3. re-scaffold from refined deck-spec
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from . import vision_gate as VG

# Codes that should drive automatic deck mutations
_DENSITY_CODES = frozenset({
    "density", "overflow", "overlap", "crowded", "tight", "cramped",
})
_CONTRAST_CODES = frozenset({"contrast", "low_contrast", "illegible"})
_ALIGNMENT_CODES = frozenset({"alignment", "misaligned", "layout"})

_NL_DENSITY = re.compile(
    r"(빽빽|밀집|crowded|dense|too\s+much|overflow|cramped|tight|여백|"
    r"spacing|roomy|sparse|넓|space\s+out|split)",
    re.I,
)
_NL_SHORTEN = re.compile(
    r"(짧|shorten|trim|cut|too\s+long|verbose|wordy|줄여|요약)",
    re.I,
)
_NL_SPLIT = re.compile(
    r"(split|나눠|분리|두\s*장|two\s+slides|break\s+up)",
    re.I,
)
_NL_CONTRAST = re.compile(
    r"(대비|contrast|읽기\s*어렵|hard\s+to\s+read|illegible|low\s+contrast)",
    re.I,
)

# Recipes that tolerate fewer list items before looking dense
_LIST_RECIPES = frozenset({
    "bullets", "feature_cards", "process", "timeline", "story_timeline",
    "funnel_stages", "chevron_process", "framework_row", "pipeline_stages",
    "agenda_toc",
})
_TEXT_BODY_KEYS = ("body", "blurb", "insight_body", "quote", "subtitle")


def load_deck(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("slides"), list):
        raise ValueError("deck-spec must be a JSON object with slides[]")
    return data


def write_deck(deck: dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(deck, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def _slide_index(finding: dict[str, Any], n_slides: int) -> list[int]:
    """Resolve finding.slide (1-based) to 0-based indices; None → all content slides."""
    s = finding.get("slide")
    if s is None:
        return list(range(n_slides))
    try:
        i = int(s) - 1
    except (TypeError, ValueError):
        return list(range(n_slides))
    if 0 <= i < n_slides:
        return [i]
    return []


def _list_key(content: dict[str, Any]) -> str | None:
    for k in ("bullets", "items", "steps", "stages", "cards", "entries"):
        if isinstance(content.get(k), list) and content[k]:
            return k
    return None


def _truncate_text(s: str, max_chars: int) -> str:
    s = str(s).strip()
    if len(s) <= max_chars:
        return s
    cut = s[: max_chars - 1].rsplit(" ", 1)[0]
    return (cut or s[: max_chars - 1]) + "…"


def parse_nl_feedback(text: str) -> list[dict[str, Any]]:
    """Turn free-text QA into synthetic vision findings."""
    text = (text or "").strip()
    if not text:
        return []
    findings: list[dict[str, Any]] = []
    if _NL_DENSITY.search(text) or _NL_SPLIT.search(text):
        findings.append({
            "code": "density",
            "severity": "error",
            "message": text,
            "slide": None,
        })
    if _NL_SHORTEN.search(text):
        findings.append({
            "code": "overflow",
            "severity": "error",
            "message": text,
            "slide": None,
        })
    if _NL_CONTRAST.search(text):
        findings.append({
            "code": "contrast",
            "severity": "warn",
            "message": text,
            "slide": None,
        })
    if not findings:
        # Generic: treat as density so the loop still does something useful
        findings.append({
            "code": "density",
            "severity": "warn",
            "message": text,
            "slide": None,
        })
    return findings


def apply_patches(
    deck: dict[str, Any],
    findings: list[dict[str, Any]],
    *,
    max_list_items: int = 4,
    max_body_chars: int = 220,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (new_deck, patch_log) after applying finding-driven mutations.

    Continuations are collected and inserted *after* all index-based patches
    so inserting a slide never shifts later targets mid-pass (adversarial #19).
    """
    out = copy.deepcopy(deck)
    slides = out.get("slides") or []
    if not isinstance(slides, list):
        return out, []
    log: list[dict[str, Any]] = []
    n = len(slides)
    # (after_index, cont_slide) — applied high→low after the main pass
    pending_inserts: list[tuple[int, dict[str, Any]]] = []
    # Track which (slide_index, code_family) already handled to avoid double-patch
    handled: set[tuple[int, str]] = set()

    ordered = sorted(
        findings,
        key=lambda f: 0 if str(f.get("severity")) == "error" else 1,
    )

    for finding in ordered:
        code = str(finding.get("code") or "").lower()
        family = (
            "density" if code in _DENSITY_CODES or code in ("overflow",)
            else "contrast" if code in _CONTRAST_CODES
            else "align" if code in _ALIGNMENT_CODES
            else code
        )
        idxs = _slide_index(finding, n)
        for i in idxs:
            if i >= len(slides):
                continue
            if (i, family) in handled:
                continue
            slide = slides[i]
            if not isinstance(slide, dict):
                continue
            recipe = str(slide.get("recipe") or "")
            content = slide.setdefault("content", {})
            if not isinstance(content, dict):
                continue

            if code in _DENSITY_CODES or code in ("overflow",):
                key = _list_key(content)
                if key:
                    items = list(content[key])
                    if len(items) > max_list_items:
                        head = items[:max_list_items]
                        tail = items[max_list_items:]
                        content[key] = head
                        content["notes"] = (
                            (content.get("notes") or "")
                            + f" [refine: held {len(tail)} overflow items for next slide]"
                        ).strip()
                        cont = copy.deepcopy(slide)
                        cont["id"] = f"{slide.get('id', f's{i}')}-cont"
                        cont_content = dict(cont.get("content") or {})
                        cont_content[key] = tail
                        title = str(cont_content.get("title") or recipe)
                        if "(cont." not in title:
                            cont_content["title"] = f"{title} (cont.)"
                        cont["content"] = cont_content
                        pending_inserts.append((i + 1, cont))
                        handled.add((i, family))
                        log.append({
                            "action": "split_list",
                            "slide": i + 1,
                            "recipe": recipe,
                            "key": key,
                            "kept": len(head),
                            "moved": len(tail),
                            "code": code,
                        })
                        continue
                shortened = False
                for bk in _TEXT_BODY_KEYS:
                    if bk in content and isinstance(content[bk], str):
                        old = content[bk]
                        new = _truncate_text(old, max_body_chars)
                        if new != old:
                            content[bk] = new
                            shortened = True
                if shortened:
                    handled.add((i, family))
                    log.append({
                        "action": "shorten_text",
                        "slide": i + 1,
                        "recipe": recipe,
                        "code": code,
                    })
                    continue
                if recipe == "bullets" and key == "bullets" and len(content.get("bullets") or []) >= 3:
                    cards = [
                        {"title": str(b)[:40], "body": ""}
                        for b in content["bullets"][:4]
                    ]
                    slide["recipe"] = "feature_cards"
                    content["cards"] = cards
                    content.pop("bullets", None)
                    handled.add((i, family))
                    log.append({
                        "action": "recipe_swap",
                        "slide": i + 1,
                        "from": "bullets",
                        "to": "feature_cards",
                        "code": code,
                    })
                    continue

            if code in _CONTRAST_CODES:
                note = content.get("notes") or ""
                hint = " [refine: run a11y --fix-contrast on tokens]"
                if hint.strip() not in note:
                    content["notes"] = (note + hint).strip()
                    handled.add((i, family))
                    log.append({
                        "action": "annotate_contrast",
                        "slide": i + 1,
                        "code": code,
                    })

            if code in _ALIGNMENT_CODES:
                note = content.get("notes") or ""
                hint = " [refine: prefer engine-solved recipe / reduce chrome]"
                if hint.strip() not in note:
                    content["notes"] = (note + hint).strip()
                    handled.add((i, family))
                    log.append({
                        "action": "annotate_alignment",
                        "slide": i + 1,
                        "code": code,
                    })

    # Apply inserts from back to front so indices stay valid
    for after_idx, cont in sorted(pending_inserts, key=lambda t: t[0], reverse=True):
        slides.insert(after_idx, cont)

    out["slides"] = slides
    return out, log


def refine_once(
    deck: dict[str, Any],
    *,
    feedback: str | None = None,
    findings: list[dict[str, Any]] | None = None,
    contact_png: str | Path | None = None,
    vision_plan: str | Path | None = None,
    vision_cmd: str | None = None,
) -> dict[str, Any]:
    """One refinement round. Returns report with refined deck + patches."""
    synth: list[dict[str, Any]] = list(findings or [])
    if feedback:
        synth.extend(parse_nl_feedback(feedback))

    eval_result: dict[str, Any] | None = None
    if contact_png is not None and Path(contact_png).exists():
        eval_result = VG.evaluate_contact_sheet(
            contact_png,
            vision_plan=vision_plan,
            vision_cmd=vision_cmd,
            use_subprocess=bool(vision_cmd) if vision_cmd else None,
            context={"task": "refine_loop", "slide_count": len(deck.get("slides") or [])},
        )
        synth.extend(eval_result.get("findings") or [])

    # Deduplicate by (code, slide, message prefix)
    seen: set[tuple] = set()
    uniq: list[dict[str, Any]] = []
    for f in synth:
        key = (f.get("code"), f.get("slide"), str(f.get("message") or "")[:80])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)

    refined, patches = apply_patches(deck, uniq)
    return {
        "version": 1,
        "findings": uniq,
        "patches": patches,
        "evaluation": eval_result,
        "deck": refined,
        "changed": bool(patches),
    }


def refine_loop(
    deck: dict[str, Any],
    *,
    feedback: str | None = None,
    findings: list[dict[str, Any]] | None = None,
    contact_png: str | Path | None = None,
    vision_plan: str | Path | None = None,
    vision_cmd: str | None = None,
    rounds: int = 3,
) -> dict[str, Any]:
    """Run up to *rounds* refinement passes; stop early if no patches.

    Natural-language feedback is applied on round 1 only (unless re-supplied
    via findings). Contact-sheet evaluation re-runs each round when a path is
    given so later rounds can react to residual issues.
    """
    rounds = max(1, min(5, int(rounds)))
    current = copy.deepcopy(deck)
    history: list[dict[str, Any]] = []
    fb = feedback
    fixed_findings = list(findings or [])

    for r in range(1, rounds + 1):
        report = refine_once(
            current,
            feedback=fb if r == 1 else None,
            findings=fixed_findings if r == 1 else None,
            contact_png=contact_png,
            vision_plan=vision_plan if r == 1 else None,
            # After round 1, re-use evaluation only when contact sheet present;
            # without live re-render, re-running same plan would loop forever —
            # so only NL/findings drive further rounds unless sheet changes.
            vision_cmd=vision_cmd if r == 1 else None,
        )
        # For rounds > 1 without new contact sheet, re-apply residual density
        # heuristics from previous findings that still match long lists.
        if r > 1 and not report["changed"]:
            residual = [
                f for f in (history[-1].get("findings") if history else [])
                if str(f.get("code") or "") in _DENSITY_CODES
            ]
            if residual:
                report = refine_once(current, findings=residual)

        history.append({
            "round": r,
            "patches": report["patches"],
            "findings": report["findings"],
            "changed": report["changed"],
            "evaluation": report.get("evaluation"),
        })
        current = report["deck"]
        if not report["changed"]:
            break
        # Drop plan after first round so we don't re-apply identical forced fails
        fixed_findings = []
        vision_plan = None

    return {
        "version": 1,
        "rounds_run": len(history),
        "history": history,
        "deck": current,
        "changed": any(h["changed"] for h in history),
        "total_patches": sum(len(h["patches"]) for h in history),
    }


def run_refine_to_dir(
    deck_path: str | Path,
    out_dir: str | Path,
    *,
    feedback: str | None = None,
    findings_path: str | Path | None = None,
    contact_png: str | Path | None = None,
    vision_plan: str | Path | None = None,
    vision_cmd: str | None = None,
    rounds: int = 3,
) -> dict[str, Any]:
    """CLI entry: load deck, refine, write refined deck + report."""
    deck = load_deck(deck_path)
    findings = None
    if findings_path:
        raw = json.loads(Path(findings_path).read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("findings"), list):
            findings = raw["findings"]
        elif isinstance(raw, list):
            findings = raw
        else:
            raise ValueError("findings JSON must be a list or {findings:[...]}")

    result = refine_loop(
        deck,
        feedback=feedback,
        findings=findings,
        contact_png=contact_png,
        vision_plan=vision_plan,
        vision_cmd=vision_cmd,
        rounds=rounds,
    )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_deck(result["deck"], out / "content.deck.json")
    report_path = out / "refine.report.json"
    # Don't embed full deck twice in report file body beyond reference
    slim = {
        "version": result["version"],
        "rounds_run": result["rounds_run"],
        "changed": result["changed"],
        "total_patches": result["total_patches"],
        "history": result["history"],
        "source": str(Path(deck_path).name),
        "output": "content.deck.json",
    }
    report_path.write_text(
        json.dumps(slim, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    result["paths"] = {
        "deck": str(out / "content.deck.json"),
        "report": str(report_path),
    }
    return result
