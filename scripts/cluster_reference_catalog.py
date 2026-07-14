#!/usr/bin/env python3
"""Filename-only clustering of a local reference deck library.

Safe to run on licensed packs (e.g. infograpify_ppt_templates/): only basenames
are read. Writes a JSON snapshot for docs/recipe-coverage-roadmap.md.

  PYTHONPATH=python python scripts/cluster_reference_catalog.py \
    --dir infograpify_ppt_templates -o docs/reference-catalog-clusters.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Allow running from repo root without installing the package.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "python"))

from designmd_pptx.reference import family_from_name  # noqa: E402
from designmd_pptx.recipes import RECIPE_BUILDERS  # noqa: E402

_SUB: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"waterfall", re.I), "waterfall_chart"),
    (re.compile(r"venn", re.I), "venn"),
    (re.compile(r"cycle|circular", re.I), "cycle_diagram"),
    (re.compile(r"pie\s*chart|donut", re.I), "pie_donut"),
    (re.compile(r"gantt", re.I), "gantt"),
    (re.compile(r"swot", re.I), "swot"),
    (re.compile(r"funnel", re.I), "funnel"),
    (re.compile(r"chevron|arrow\s*process", re.I), "chevron_process"),
    (re.compile(r"pipeline", re.I), "pipeline"),
    (re.compile(r"fishbone|ishikawa", re.I), "fishbone"),
    (re.compile(r"iceberg", re.I), "iceberg"),
    (re.compile(r"adkar|aida", re.I), "marketing_framework"),
    (re.compile(r"value\s*chain|porter", re.I), "value_chain"),
    (re.compile(r"business\s*model|bmc|canvas", re.I), "business_canvas"),
    (re.compile(r"persona|buyer", re.I), "persona"),
    (re.compile(r"org(?:anizational)?", re.I), "org_chart"),
    (re.compile(r"\bteam\b", re.I), "team_grid"),
    (re.compile(r"pricing", re.I), "pricing"),
    (re.compile(r"agenda", re.I), "agenda"),
    (re.compile(r"roadmap", re.I), "roadmap"),
    (re.compile(r"timeline", re.I), "timeline"),
    (re.compile(r"kpi|dashboard", re.I), "kpi_dashboard"),
    (re.compile(r"pyramid|triangle|hierarchy", re.I), "pyramid"),
    (re.compile(r"matrix|2\s*x\s*2|quadrant", re.I), "matrix"),
    (re.compile(r"compar|vs\.?|versus|scorecard", re.I), "comparison"),
    (re.compile(r"process|flow\s*chart", re.I), "process"),
    (re.compile(r"map|geo|world|asia|europe|united\s*states|mind\s*map|mindmap|empathy", re.I), "map_or_mindmap"),
    (re.compile(r"mockup|device", re.I), "device_mockup"),
    (re.compile(r"okrs?|objective", re.I), "okr"),
    (re.compile(r"budget|forecast|finance|financial", re.I), "finance"),
    (re.compile(r"infographic", re.I), "generic_infographic"),
]


def subcluster(name: str) -> str:
    stem = Path(name).stem
    for pat, lab in _SUB:
        if pat.search(stem):
            return lab
    return "unclassified_other"


# Suggested shipped recipes per subcluster (documentation aid).
_RECIPES: dict[str, list[str]] = {
    "waterfall_chart": ["chart_insight", "chart_callout_panel"],
    "venn": [],
    "cycle_diagram": ["process"],
    "pie_donut": ["chart_insight"],
    "gantt": ["roadmap_swimlane", "timeline"],
    "swot": ["matrix_2x2", "quadrant_matrix_rich", "vs_scorecard"],
    "funnel": ["funnel_stages"],
    "chevron_process": ["process"],
    "pipeline": ["process", "funnel_stages"],
    "fishbone": [],
    "iceberg": ["pyramid_levels"],
    "marketing_framework": ["process", "feature_cards"],
    "value_chain": ["process", "feature_cards"],
    "business_canvas": [],
    "persona": ["team", "feature_cards"],
    "org_chart": ["team"],
    "team_grid": ["team"],
    "pricing": ["pricing"],
    "agenda": ["agenda_toc"],
    "roadmap": ["roadmap_swimlane", "story_timeline"],
    "timeline": ["timeline", "story_timeline"],
    "kpi_dashboard": ["kpi_dashboard_grid", "kpi_row", "big_number"],
    "pyramid": ["pyramid_levels"],
    "matrix": ["matrix_2x2", "quadrant_matrix_rich"],
    "comparison": ["comparison_2col", "vs_scorecard"],
    "process": ["process"],
    "map_or_mindmap": ["image_full", "image_text_2col"],
    "device_mockup": ["image_text_2col"],
    "okr": ["kpi_row", "bullets"],
    "finance": ["table", "chart_insight", "kpi_row"],
    "generic_infographic": ["feature_cards", "bullets", "process"],
    "unclassified_other": ["bullets", "feature_cards"],
}


def build(dir_path: Path) -> dict:
    files = sorted(p.name for p in dir_path.glob("*.pptx"))
    fam = Counter(family_from_name(n) for n in files)
    sub = Counter(subcluster(n) for n in files)
    by_sub: dict[str, list[str]] = defaultdict(list)
    for n in files:
        by_sub[subcluster(n)].append(n)
    clusters = {}
    for k, n in sub.most_common():
        recs = _RECIPES.get(k, [])
        have = [r for r in recs if r in RECIPE_BUILDERS]
        if not recs:
            status = "GAP"
        elif k in (
            "map_or_mindmap", "device_mockup", "waterfall_chart", "venn",
            "cycle_diagram", "gantt", "swot", "org_chart", "fishbone",
            "business_canvas", "chevron_process", "iceberg",
        ):
            status = "GAP_OR_WEAK"
        elif k in (
            "funnel", "agenda", "pricing", "pyramid", "kpi_dashboard",
            "timeline", "roadmap", "process", "comparison", "matrix", "team_grid",
        ):
            status = "COVERED"
        else:
            status = "PARTIAL"
        clusters[k] = {
            "count": n,
            "status": status,
            "shipped_recipes": have,
            "examples": by_sub[k][:8],
        }
    return {
        "schema": 1,
        "source_dir": str(dir_path.name),
        "total": len(files),
        "license_note": (
            "Filenames only. Decks are licensed third-party assets and must "
            "not be committed."
        ),
        "coarse_families": dict(fam.most_common()),
        "subclusters": clusters,
        "shipped_recipe_count": len(RECIPE_BUILDERS),
        "shipped_recipes": sorted(RECIPE_BUILDERS),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, required=True, help="Directory of .pptx")
    ap.add_argument("-o", "--out", type=Path, required=True, help="Output JSON")
    args = ap.parse_args(argv)
    if not args.dir.is_dir():
        print(f"error: not a directory: {args.dir}", file=sys.stderr)
        return 2
    data = build(args.dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"Wrote {args.out} ({data['total']} files, "
          f"{len(data['subclusters'])} subclusters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
