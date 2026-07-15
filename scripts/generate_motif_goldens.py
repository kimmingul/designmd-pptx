#!/usr/bin/env python3
"""Render each motif to a one-slide deck + contact/screenshot under demo/motifs/.

License-safe: uses synthetic slots only (no vendor content).
Requires legacy OfficeCLI for apply (OFFICECLI_LEGACY_BIN or PATH).

Usage:
  PYTHONPATH=python python scripts/generate_motif_goldens.py
  PYTHONPATH=python python scripts/generate_motif_goldens.py --motifs card_row,step_rail
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from designmd_pptx.apply import apply_sequence  # noqa: E402
from designmd_pptx.compile import compile_design_md  # noqa: E402
from designmd_pptx.motif import list_motifs, render_motif  # noqa: E402


def _sample_slots(motif_id: str) -> dict:
    samples = {
        "sparse_hero": {
            "title": "designmd-pptx",
            "subtitle": "Motif golden — sparse_hero",
            "meta": "v2.1.2",
            "placement": "left",
        },
        "split_hero": {
            "title": "What changes",
            "left": {"title": "Before", "body": ["Drift", "No gates", "Risk"]},
            "right": {"title": "After", "body": ["Tokens", "Gate 3", "Staging-safe"]},
            "name_prefix": "Ba",
        },
        "card_row": {
            "title": "Three promises",
            "cards": [
                {"title": "Exact geometry", "body": "Centimeters and floors."},
                {"title": "Hard gates", "body": "Budgets then contact sheet."},
                {"title": "Agent-safe", "body": "Install only after yes."},
            ],
            "title_name": "FeatTitle",
        },
        "kpi_band": {
            "title": "At a glance",
            "kpis": [
                {"value": "75", "label": "Builders", "chip": ""},
                {"value": "12", "label": "Motifs", "chip": ""},
                {"value": "2", "label": "Backends", "chip": ""},
            ],
        },
        "kpi_hero": {
            "value": "DESIGN.md",
            "label": "Brand contract",
            "context": "One source of truth for tokens and floors.",
        },
        "step_rail": {
            "title": "Pipeline",
            "steps": [
                {"label": "Brief", "detail": "MD"},
                {"label": "Compose", "detail": "Spec"},
                {"label": "Apply", "detail": "PPTX"},
                {"label": "Gate 3", "detail": "QA"},
            ],
            "slide_index": 1,
        },
        "funnel_cascade": {
            "title": "Adoption funnel",
            "stages": [
                {"label": "Aware", "value": "100%"},
                {"label": "Try", "value": "40%"},
                {"label": "Adopt", "value": "18%"},
                {"label": "Expand", "value": "7%"},
            ],
        },
        "matrix_quad": {
            "title": "Where we play",
            "quadrants": [
                {"title": "Invest", "body": "High value, high fit"},
                {"title": "Selective", "body": "High value, low fit"},
                {"title": "Maintain", "body": "Low value, high fit"},
                {"title": "Exit", "body": "Low value, low fit"},
            ],
            "axes": {"x": "Fit →", "y": "Value ↑"},
        },
        "stair_ascent": {
            "title": "Maturity",
            "steps": [
                {"label": "Tokens", "detail": "Floors"},
                {"label": "Fit", "detail": "Budgets"},
                {"label": "Issues", "detail": "Gate"},
                {"label": "Ship", "detail": "Human"},
            ],
        },
        "check_stack": {
            "title": "Hard rules",
            "items": [
                {"label": "Title ≥ 36pt", "done": True},
                {"label": "No font shrink", "done": True},
                {"label": "Content-height body", "done": True},
            ],
        },
        "tile_row": {
            "title": "Pieces",
            "items": [
                {"label": "Compile"},
                {"label": "Compose"},
                {"label": "Apply"},
                {"label": "QA"},
            ],
            "name_prefix": "Tile",
        },
        "section_mark": {
            "number": "02",
            "title": "How it works",
            "blurb": "Motifs carry chrome; DESIGN.md carries brand.",
        },
        "org_cascade": {
            "title": "Delivery org",
            "root": {"name": "Product lead", "role": "Owns outcomes"},
            "reports": [
                {"name": "Design", "role": "Systems"},
                {"name": "Eng", "role": "Platform"},
                {"name": "GTM", "role": "Narrative"},
            ],
        },
        "chevron_flow": {
            "title": "Ship path",
            "steps": [
                {"label": "Brief", "value": "MD"},
                {"label": "Compose", "value": "Spec"},
                {"label": "Apply", "value": "PPTX"},
                {"label": "Gate 3", "value": "Ship"},
            ],
        },
        "hub_orbit": {
            "title": "Loop",
            "hub": "Core",
            "steps": [{"label": s} for s in ("Plan", "Do", "Check", "Act")],
        },
        "pyramid_stack": {
            "title": "Hierarchy",
            "levels": [
                {"label": "Strategy"},
                {"label": "Systems"},
                {"label": "Execution"},
            ],
        },
        "timeline_rail": {
            "title": "Milestones",
            "steps": [
                {"label": "Q1", "detail": "Discover"},
                {"label": "Q2", "detail": "Build"},
                {"label": "Q3", "detail": "Ship"},
                {"label": "Q4", "detail": "Scale"},
            ],
        },
        "pricing_tiers": {
            "title": "Plans",
            "tiers": [
                {"name": "Starter", "price": "$9", "blurb": "Solo"},
                {"name": "Team", "price": "$29", "blurb": "Squad", "featured": True},
                {"name": "Enterprise", "price": "Talk", "blurb": "Scale"},
            ],
        },
        "kpi_grid": {
            "title": "Dashboard",
            "kpis": [
                {"value": "12", "label": "Motifs"},
                {"value": "75", "label": "Recipes"},
                {"value": "13", "label": "Families"},
                {"value": "400", "label": "Ref decks"},
                {"value": "2", "label": "Backends"},
                {"value": "0", "label": "Vendor bytes"},
            ],
        },
        "canvas_bmc": {"title": "Business model"},
        "risk_heat": {"title": "Risk heat"},
        "team_cards": {
            "title": "Team",
            "members": [
                {"name": "Alex", "role": "Eng"},
                {"name": "Sam", "role": "Design"},
                {"name": "Riley", "role": "GTM"},
            ],
        },
        "pillar_band": {
            "title": "Pillars",
            "pillars": [
                {"label": "Legacy"},
                {"label": "Official"},
                {"label": "Offline"},
            ],
        },
        "agenda_list": {
            "title": "Agenda",
            "items": ["Contract", "Motifs", "Gates", "Ask"],
        },
        "close_mark": {
            "title": "Next step",
            "body": "python -m designmd_pptx doctor --ensure",
        },
    }
    base = samples.get(motif_id)
    if base is not None:
        return base
    # Fallback keeps goldens generating even for new catalog ids
    return {"title": motif_id.replace("_", " ").title()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--motifs", default="", help="comma list; default all")
    ap.add_argument(
        "--design",
        type=Path,
        default=ROOT / "demo" / "apple.DESIGN.md",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "demo" / "motifs",
    )
    args = ap.parse_args()
    ids = [x.strip() for x in args.motifs.split(",") if x.strip()] or list_motifs()
    tokens = compile_design_md(args.design)
    args.out.mkdir(parents=True, exist_ok=True)

    force = True
    for mid in ids:
        print(f"→ motif {mid}")
        ops = render_motif(mid, tokens, _sample_slots(mid))
        # Ensure first op is slide
        if not ops or ops[0].get("type") != "slide":
            print(f"  skip {mid}: no slide op")
            continue
        seq_path = args.out / f"{mid}.sequence.json"
        seq_path.write_text(
            json.dumps(ops, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        pptx = args.out / f"{mid}.pptx"
        try:
            apply_sequence(
                pptx, seq_path, create=True, force=force,
                require_clean_issues=False, screenshot=True,
            )
            print(f"  wrote {pptx.name}")
        except Exception as e:
            print(f"  FAIL {mid}: {e}")
            return 1
    print(f"done → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
