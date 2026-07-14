"""Public 100+ deck benchmark suite (Phase 5 / #42).

Ships a **license-clean synthetic public corpus** (≥100 deck-specs) that
exercises every catalog recipe across multiple design themes, plus the
before/after harness from ``benchmark.py``. Real private corpus assets remain
optional (see docs/corpus.md); this module satisfies the public publication
bar without redistributing third-party decks.

Rights
------
All fixtures generated here are original content produced by designmd-pptx
(CC0-equivalent for benchmark purposes). No anonymized customer decks are
included. Methodology and summarized results live in
``docs/public-benchmark.md`` and are regenerated via::

    python -m designmd_pptx benchmark --public -o public-benchmark-out
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import a11y as a11y_mod
from . import benchmark as bench
from . import recipes as recipes_mod
from .compile import compile_design_md

PUBLIC_LICENSE = "CC0-1.0"
PUBLIC_CORPUS_VERSION = "1.0.0"
MIN_PUBLIC_DECKS = 100

# Design themes used to diversify the synthetic corpus
_THEMES = (
    "default",
    "light",
    "dark-contrast",
    "dense-consulting",
    "airy-keynote",
)

# Narrative templates for synthetic content
_TITLES = (
    "Quarterly Outlook",
    "Product Strategy",
    "Customer Insights",
    "Platform Roadmap",
    "Risk Review",
    "Growth Plan",
    "Ops Health",
    "Research Findings",
    "Launch Readiness",
    "Budget Narrative",
)


@dataclass
class PublicSuiteMeta:
    version: str = PUBLIC_CORPUS_VERSION
    license: str = PUBLIC_LICENSE
    decks_requested: int = MIN_PUBLIC_DECKS
    decks_generated: int = 0
    recipes_covered: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    recipe_build_ok: int = 0
    recipe_build_fail: int = 0
    methodology: str = (
        "Synthetic deck-spec a11y + recipe-builder smoke suite (CC0). "
        "Does NOT download private decks, render PPTX, or run live Gate 3. "
        "Each fixture: degraded before tokens/deck → a11y auto-correct after; "
        "primary recipe is materialised via RECIPE_BUILDERS (ops emitted). "
        "OfficeCLI apply/screenshot is out of band for this public harness."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _catalog_recipes() -> list[str]:
    seq = list(getattr(recipes_mod, "CATALOG_SEQUENCE", None) or recipes_mod.CORE_SEQUENCE)
    # ensure freeform is in the public suite once generative ships
    if "freeform" not in seq:
        seq = list(seq) + ["freeform"]
    return seq


def _content_for_recipe(recipe: str, deck_i: int, theme: str) -> dict[str, Any]:
    """Deterministic minimal-valid content per recipe family."""
    title = _TITLES[deck_i % len(_TITLES)]
    tag = f"{theme}-{recipe}"
    base = {"title": f"{title}: {recipe}", "meta": tag}

    if recipe in ("cover", "close", "section_divider"):
        return {**base, "subtitle": f"Public benchmark fixture · {theme}", "meta": tag}
    if recipe in ("bullets", "agenda_toc"):
        return {
            **base,
            "bullets": [f"Point {j + 1} for {recipe}" for j in range(4)],
        }
    if recipe in ("feature_cards", "framework_row"):
        return {
            **base,
            "cards": [
                {"title": f"Card {j + 1}", "body": f"Body {j + 1}"}
                for j in range(3)
            ],
        }
    if recipe in ("kpi_row",):
        return {
            **base,
            "kpis": [
                {"label": "NPS", "value": "72"},
                {"label": "ARR", "value": "$12M"},
                {"label": "NRR", "value": "118%"},
            ],
        }
    if recipe in ("process", "timeline", "story_timeline", "chevron_process",
                  "funnel_stages", "pipeline_stages"):
        return {
            **base,
            "steps": [
                {"title": f"Step {j + 1}", "body": f"Detail {j + 1}"}
                for j in range(4)
            ],
            "stages": [f"Stage {j + 1}" for j in range(4)],
            "entries": [
                {"date": f"2026-0{j + 1}", "title": f"Milestone {j + 1}"}
                for j in range(4)
            ],
        }
    if recipe in ("comparison_2col", "image_text_2col"):
        return {
            **base,
            "left_title": "Before",
            "right_title": "After",
            "left_bullets": ["A", "B"],
            "right_bullets": ["C", "D"],
            "body": "Narrative body for two-column layouts.",
            "src": "placeholder.png",
            "alt": "Decorative placeholder for public benchmark",
        }
    if recipe in ("table",):
        return {
            **base,
            "headers": ["Metric", "Q1", "Q2"],
            "rows": [["Revenue", "10", "12"], ["Cost", "4", "5"]],
        }
    if recipe in ("quote",):
        return {**base, "quote": "Public benchmark quote fixture.", "attribution": "designmd-pptx"}
    if recipe in ("chart_insight",):
        return {
            **base,
            "insight_title": "Insight",
            "insight_body": "Synthetic chart insight for public benchmark.",
            "series": [{"name": "A", "values": [1, 2, 3]}],
        }
    if recipe in ("image_full",):
        return {
            **base,
            "src": "placeholder.png",
            "alt": "Full-bleed placeholder image for public benchmark",
        }
    if recipe == "freeform":
        return {
            **base,
            "body": "Freeform generative layout fixture.",
            "bullets": ["Alpha", "Beta", "Gamma"],
            "style_directive": "minimal keynote",
        }
    # Domain / wave recipes — generous defaults
    return {
        **base,
        "body": f"Synthetic body for {recipe}",
        "bullets": [f"Item {j + 1}" for j in range(3)],
        "items": [f"Item {j + 1}" for j in range(3)],
        "cards": [{"title": f"C{j}", "body": f"B{j}"} for j in range(3)],
        "subtitle": tag,
    }


def generate_public_deck_specs(
    n: int = MIN_PUBLIC_DECKS,
    *,
    themes: tuple[str, ...] | list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build ≥n synthetic deck-specs covering the recipe catalog."""
    recipes = _catalog_recipes()
    themes = tuple(themes or _THEMES)
    decks: list[dict[str, Any]] = []
    i = 0
    # Round-robin recipes × themes until n
    while len(decks) < n:
        recipe = recipes[i % len(recipes)]
        theme = themes[i % len(themes)]
        deck_id = f"pub-{len(decks):03d}-{theme}-{recipe}"
        # stable short hash for reproducibility notes
        digest = hashlib.sha256(deck_id.encode()).hexdigest()[:12]
        content = _content_for_recipe(recipe, i, theme)
        # multi-slide mini deck for realism (cover + target + close)
        slides = [
            {
                "id": f"{deck_id}-cover",
                "recipe": "cover",
                "content": {
                    "title": content.get("title") or recipe,
                    "subtitle": f"Public suite · {theme}",
                    "meta": digest,
                },
            },
            {
                "id": f"{deck_id}-main",
                "recipe": recipe,
                "content": content,
            },
            {
                "id": f"{deck_id}-close",
                "recipe": "close",
                "content": {
                    "title": "Thank you",
                    "body": f"Fixture {deck_id}",
                    "meta": digest,
                },
            },
        ]
        decks.append({
            "id": deck_id,
            "version": "1.1",
            "meta": {
                "public_benchmark": True,
                "license": PUBLIC_LICENSE,
                "theme": theme,
                "primary_recipe": recipe,
                "digest": digest,
            },
            "slides": slides,
        })
        i += 1
    return decks


def _degrade_for_before(deck: dict[str, Any], tokens: dict[str, Any]) -> tuple[dict, dict]:
    """Intentional before-side quality issues for delta scoring."""
    before_tokens = json.loads(json.dumps(tokens))
    before_tokens.setdefault("colors", {})["text"] = "AAAAAA"
    before_tokens["colors"]["background"] = "FFFFFF"
    before_deck = json.loads(json.dumps(deck))
    # strip alt on image-like slides
    for s in before_deck.get("slides") or []:
        if not isinstance(s, dict):
            continue
        c = s.get("content")
        if isinstance(c, dict) and c.get("src") and "alt" in c:
            c["alt"] = ""
    return before_deck, before_tokens


def _materialize_primary(
    tokens: dict[str, Any],
    deck: dict[str, Any],
) -> tuple[int, list[str]]:
    """Invoke RECIPE_BUILDERS for each slide. Returns (layout_failures, notes)."""
    from . import recipes as recipes_mod

    failures = 0
    notes: list[str] = []
    builders = recipes_mod.RECIPE_BUILDERS
    for s in deck.get("slides") or []:
        if not isinstance(s, dict):
            failures += 1
            continue
        recipe = str(s.get("recipe") or "")
        content = s.get("content") if isinstance(s.get("content"), dict) else {}
        builder = builders.get(recipe)
        if builder is None:
            failures += 1
            notes.append(f"unknown recipe {recipe!r}")
            continue
        try:
            ops = builder(tokens, content)
            if not isinstance(ops, list) or not ops:
                failures += 1
                notes.append(f"{recipe}: empty ops")
            elif not any(o.get("type") == "slide" for o in ops if isinstance(o, dict)):
                failures += 1
                notes.append(f"{recipe}: no slide op")
        except Exception as e:  # noqa: BLE001 — record builder failure as layout metric
            failures += 1
            notes.append(f"{recipe}: {type(e).__name__}: {e}")
    return failures, notes


def build_public_fixtures(
    n: int = MIN_PUBLIC_DECKS,
    *,
    design_path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], PublicSuiteMeta]:
    """Compile tokens once and build fixture dicts for run_fixture_suite.

    Honesty note (adversarial #42): this is a **synthetic deck-spec + recipe
    builder smoke** suite, not a rendered-PPTX corpus. Gate 3 is offline
    structural (no contact sheet unless provided).
    """
    pkg = Path(__file__).parent
    design = Path(design_path) if design_path else pkg / "default.DESIGN.md"
    tokens = compile_design_md(design)
    decks = generate_public_deck_specs(n)
    fixtures: list[dict[str, Any]] = []
    recipes_seen: set[str] = set()
    themes_seen: set[str] = set()
    build_ok = 0
    build_fail = 0

    for deck in decks:
        did = str(deck["id"])
        meta = deck.get("meta") or {}
        recipes_seen.add(str(meta.get("primary_recipe") or ""))
        themes_seen.add(str(meta.get("theme") or ""))
        before_deck, before_tokens = _degrade_for_before(deck, tokens)
        after_tokens, _ = a11y_mod.auto_correct_contrast(before_tokens)
        after_deck, _ = a11y_mod.ensure_notes_and_alt(before_deck)

        # Recipe materialisation smoke on the *after* deck
        layout_fail, build_notes = _materialize_primary(after_tokens, after_deck)
        if layout_fail:
            build_fail += 1
        else:
            build_ok += 1

        # Offline gate: pass only when recipe smoke succeeded (not hard-coded)
        after_gate = {
            "pass": layout_fail == 0,
            "provider": "recipe_smoke",
            "issues": [
                {"severity": "error", "code": "recipe_build", "message": n}
                for n in build_notes
            ],
        }
        fixtures.append({
            "id": did,
            "before_deck": before_deck,
            "after_deck": after_deck,
            "before_tokens": before_tokens,
            "after_tokens": after_tokens,
            # No real extract — ledger empty is honest for synthetic fixtures
            "before_extract": {"loss_ledger": [], "note": "synthetic: no pptx extract"},
            "after_extract": {"loss_ledger": [], "note": "synthetic: no pptx extract"},
            "after_gate": after_gate,
            # Inject layout_failure via a synthetic after metric path:
            # score_deck uses layout_failures(tokens, deck) — we also stash
            # builder failures into after_deck meta for audit.
            "_layout_builder_failures": layout_fail,
        })
        if layout_fail and isinstance(after_deck.get("meta"), dict):
            after_deck["meta"]["layout_builder_failures"] = layout_fail
            after_deck["meta"]["layout_builder_notes"] = build_notes[:8]

    meta_out = PublicSuiteMeta(
        decks_requested=n,
        decks_generated=len(fixtures),
        recipes_covered=sorted(r for r in recipes_seen if r),
        themes=sorted(themes_seen),
        recipe_build_ok=build_ok,
        recipe_build_fail=build_fail,
    )
    return fixtures, meta_out


def run_public_suite(
    *,
    n: int = MIN_PUBLIC_DECKS,
    design_path: str | Path | None = None,
    thresholds: dict[str, Any] | None = None,
) -> tuple[bench.SuiteReport, PublicSuiteMeta]:
    """Run the ≥100 deck public synthetic suite. Returns (suite_report, meta)."""
    fixtures, meta = build_public_fixtures(n, design_path=design_path)
    th = thresholds or bench.load_thresholds()
    report = bench.run_fixture_suite(fixtures=fixtures, thresholds=th)
    # Fold recipe-builder failures into suite status (layout_failure may be 0
    # if deck-spec is well-formed but builder raised).
    extra_fail = 0
    for fx, result in zip(fixtures, report.results):
        bf = int(fx.get("_layout_builder_failures") or 0)
        if bf and result.status == "pass":
            result.status = "fail"
            result.threshold_breaches = list(result.threshold_breaches) + [
                f"recipe_builder_failures={bf}"
            ]
            extra_fail += 1
    if extra_fail:
        report.decks_fail += extra_fail
        report.decks_pass = max(0, report.decks_pass - extra_fail)
        report.ok = False
    report.notes.append(
        f"public synthetic suite v{meta.version} license={meta.license} "
        f"decks={meta.decks_generated} recipes={len(meta.recipes_covered)} "
        f"recipe_build_ok={meta.recipe_build_ok} fail={meta.recipe_build_fail}"
    )
    report.notes.append(meta.methodology)
    report.notes.append(
        "NOT a rendered-PPTX corpus: no OfficeCLI apply/screenshot in this harness"
    )
    if meta.decks_generated < MIN_PUBLIC_DECKS and n >= MIN_PUBLIC_DECKS:
        report.notes.append(
            f"WARNING: generated {meta.decks_generated} < {MIN_PUBLIC_DECKS} "
            "public-deck target"
        )
        report.ok = False
    return report, meta


def write_public_report(
    report: bench.SuiteReport,
    meta: PublicSuiteMeta,
    out_dir: str | Path,
) -> dict[str, Path]:
    """Write suite report + methodology summary + corpus index."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["benchmark"] = bench.write_report(report, out)

    summary = {
        "schema": 1,
        "kind": "public-benchmark-summary",
        "meta": meta.to_dict(),
        "suite": {
            "ok": report.ok,
            "decks_total": report.decks_total,
            "decks_pass": report.decks_pass,
            "decks_fail": report.decks_fail,
            "decks_skip": report.decks_skip,
        },
        "thresholds": report.thresholds,
        "notes": report.notes,
        "failures": [
            {
                "deck_id": r.deck_id,
                "breaches": r.threshold_breaches,
                "deltas": r.deltas,
            }
            for r in report.results
            if r.status == "fail"
        ],
        "pass_rate": (
            report.decks_pass / report.decks_total if report.decks_total else 0.0
        ),
        "rights": {
            "license": PUBLIC_LICENSE,
            "statement": (
                "All decks in this suite are synthetic fixtures generated by "
                "designmd-pptx. No third-party or customer content is included. "
                "Private corpus decks (docs/corpus.md) are separate and gitignored."
            ),
        },
    }
    sp = out / "public-benchmark.summary.json"
    sp.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["summary"] = sp

    # Compact corpus index (ids only — full decks are large)
    index = {
        "schema": 1,
        "version": meta.version,
        "license": meta.license,
        "count": meta.decks_generated,
        "recipes_covered": meta.recipes_covered,
        "themes": meta.themes,
        "deck_ids": [r.deck_id for r in report.results],
    }
    ip = out / "public-corpus.index.json"
    ip.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["index"] = ip

    # Human-readable methodology snapshot (also published under docs/)
    md = out / "METHODOLOGY.md"
    md.write_text(_methodology_markdown(report, meta, summary), encoding="utf-8")
    paths["methodology"] = md
    return paths


def _methodology_markdown(
    report: bench.SuiteReport,
    meta: PublicSuiteMeta,
    summary: dict[str, Any],
) -> str:
    fail_lines = "\n".join(
        f"- `{f['deck_id']}`: {', '.join(f['breaches'])}"
        for f in summary.get("failures") or []
    ) or "_None_"
    recipes = ", ".join(f"`{r}`" for r in meta.recipes_covered[:40])
    if len(meta.recipes_covered) > 40:
        recipes += f", … (+{len(meta.recipes_covered) - 40} more)"
    return f"""# Public benchmark methodology (v{meta.version})

## Rights

- **License:** {meta.license}
- **Content:** 100% synthetic deck-specs generated by `designmd-pptx.public_benchmark`.
- **No** customer, partner, or scraped decks. Private corpus admission remains
  documented in [corpus.md](corpus.md) and is out of band for this publication.

## What we measure

Each fixture is scored **before → after** with
`python/designmd_pptx/benchmark_thresholds.json`:

| Metric | Max allowed (after) |
|---|---|
| corruption | 0 |
| extraction_loss | 5 |
| layout_failure | 0 |
| visual_gate_failure | 0 |
| a11y_error | 0 |

**Before** side intentionally weakens contrast and strips image `alt`.
**After** side runs `a11y.auto_correct_contrast` + `ensure_notes_and_alt`.

## Corpus construction

- Target size: **≥ {MIN_PUBLIC_DECKS}** decks (this run: **{meta.decks_generated}**)
- Themes: {', '.join(meta.themes)}
- Recipes covered ({len(meta.recipes_covered)}): {recipes}
- Each deck: cover + primary recipe + close (3 slides)
- Deterministic ids: `pub-NNN-{{theme}}-{{recipe}}`

## Results (this run)

| | |
|---|---|
| Status | **{"PASS" if report.ok else "FAIL"}** |
| Pass | {report.decks_pass} |
| Fail | {report.decks_fail} |
| Skip | {report.decks_skip} |
| Total | {report.decks_total} |
| Pass rate | {summary.get("pass_rate", 0):.1%} |

### Failures

{fail_lines}

## How to reproduce

```bash
PYTHONPATH=python python -m designmd_pptx benchmark --public -o public-benchmark-out
# optional size override:
PYTHONPATH=python python -m designmd_pptx benchmark --public --public-n 120 -o out
```

Machine-readable artifacts: `public-benchmark.summary.json`,
`public-corpus.index.json`, `benchmark.report.json`.
"""


def publish_docs_snapshot(
    report: bench.SuiteReport,
    meta: PublicSuiteMeta,
    docs_dir: str | Path,
) -> Path:
    """Write/update docs/public-benchmark.md with latest summarized results."""
    docs = Path(docs_dir)
    docs.mkdir(parents=True, exist_ok=True)
    summary = {
        "failures": [
            {"deck_id": r.deck_id, "breaches": r.threshold_breaches}
            for r in report.results if r.status == "fail"
        ],
        "pass_rate": report.decks_pass / report.decks_total if report.decks_total else 0.0,
    }
    path = docs / "public-benchmark.md"
    path.write_text(_methodology_markdown(report, meta, summary), encoding="utf-8")
    return path
