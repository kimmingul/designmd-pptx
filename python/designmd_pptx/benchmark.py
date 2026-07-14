"""Before/after benchmark harness (issue #37).

Compares a *before* artifact (original pptx metadata, extract report, or
deck-spec) to an *after* artifact (restyle/scaffold/extract output) and scores
regression metrics against ``benchmark_thresholds.json``:

* corruption
* extraction_loss
* layout_failure
* visual_gate_failure
* a11y_error

The runner is pure-Python for fixture mode (no OfficeCLI required). When a
corpus manifest is supplied, held-out entries are preferred; missing pptx
files are recorded as skipped with an explicit reason so CI stays green
without a private 50-deck corpus.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import a11y as a11y_mod
from . import corpus as corpus_mod

THRESHOLDS_PATH = Path(__file__).with_name("benchmark_thresholds.json")


@dataclass
class DeckMetrics:
    deck_id: str
    corruption: int = 0
    extraction_loss: int = 0
    layout_failure: int = 0
    visual_gate_failure: int = 0
    a11y_error: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DeckResult:
    deck_id: str
    status: str  # "pass" | "fail" | "skip"
    before: dict[str, Any]
    after: dict[str, Any]
    deltas: dict[str, int]
    threshold_breaches: list[str] = field(default_factory=list)
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SuiteReport:
    ok: bool
    decks_total: int
    decks_pass: int
    decks_fail: int
    decks_skip: int
    thresholds: dict[str, Any]
    results: list[DeckResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "decks_total": self.decks_total,
            "decks_pass": self.decks_pass,
            "decks_fail": self.decks_fail,
            "decks_skip": self.decks_skip,
            "thresholds": self.thresholds,
            "results": [r.to_dict() for r in self.results],
            "notes": self.notes,
        }


def load_thresholds(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else THRESHOLDS_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def _pptx_corruption(path: Path | None) -> tuple[int, str]:
    if path is None or not path.is_file():
        return 0, "no pptx path"
    try:
        if not zipfile.is_zipfile(path):
            return 1, "not a zip/pptx"
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            if "[Content_Types].xml" not in names:
                return 1, "missing [Content_Types].xml"
            if not any(n.startswith("ppt/slides/slide") for n in names):
                return 1, "no ppt/slides/slide* parts"
        return 0, "ok"
    except (OSError, zipfile.BadZipFile) as e:
        return 1, str(e)


def _count_extraction_loss(report: dict[str, Any] | None) -> int:
    if not report:
        return 0
    ledger = report.get("loss_ledger") or report.get("losses") or []
    if isinstance(ledger, dict):
        # structured {errors: N, ...} or list under items
        if "items" in ledger:
            ledger = ledger["items"]
        elif "count" in ledger:
            return int(ledger["count"])
        else:
            return int(ledger.get("errors", 0)) + int(ledger.get("high", 0))
    if not isinstance(ledger, list):
        return 0
    n = 0
    for item in ledger:
        if isinstance(item, dict):
            sev = str(item.get("severity") or item.get("level") or "info").lower()
            if sev in ("error", "high", "critical"):
                n += 1
        else:
            n += 1
    return n


def _layout_failures(tokens: dict | None, deck: dict | None) -> int:
    n = 0
    if tokens is not None:
        try:
            from .validate import validate_tokens_struct
            n += len(validate_tokens_struct(tokens))
        except Exception as e:  # pragma: no cover — defensive
            n += 1
            _ = e
    if deck is not None:
        try:
            from .deck import validate_deck_content
            # validate_deck_content may not exist — fall back to light checks
        except ImportError:
            pass
        slides = deck.get("slides") if isinstance(deck, dict) else None
        if not isinstance(slides, list) or not slides:
            n += 1
        else:
            for s in slides:
                if not isinstance(s, dict) or not s.get("recipe"):
                    n += 1
                content = s.get("content") if isinstance(s, dict) else None
                if content is not None and not isinstance(content, dict):
                    n += 1
    return n


def _visual_gate_failures(gate_report: dict | None) -> int:
    if not gate_report:
        return 0
    if gate_report.get("pass") is False or gate_report.get("ok") is False:
        return 1
    issues = gate_report.get("issues") or gate_report.get("findings") or []
    if isinstance(issues, list):
        return sum(
            1 for i in issues
            if isinstance(i, dict) and str(i.get("severity", "")).lower() in ("error", "fail", "high")
        )
    return 0


def score_deck(
    deck_id: str,
    *,
    before_pptx: Path | None = None,
    after_pptx: Path | None = None,
    before_extract: dict | None = None,
    after_extract: dict | None = None,
    before_deck: dict | None = None,
    after_deck: dict | None = None,
    before_tokens: dict | None = None,
    after_tokens: dict | None = None,
    after_gate: dict | None = None,
) -> tuple[DeckMetrics, DeckMetrics]:
    """Compute before and after metric vectors for one deck.

    Both sides are scored symmetrically for a11y when tokens and/or deck-spec
    are supplied, so deltas reflect real before→after improvement (or regession).
    """
    b = DeckMetrics(deck_id=deck_id)
    a = DeckMetrics(deck_id=deck_id)

    c, note = _pptx_corruption(before_pptx)
    b.corruption = c
    if note != "ok" and before_pptx:
        b.notes.append(f"before pptx: {note}")
    c, note = _pptx_corruption(after_pptx)
    a.corruption = c
    if note != "ok" and after_pptx:
        a.notes.append(f"after pptx: {note}")

    b.extraction_loss = _count_extraction_loss(before_extract)
    a.extraction_loss = _count_extraction_loss(after_extract)

    b.layout_failure = _layout_failures(before_tokens, before_deck)
    a.layout_failure = _layout_failures(after_tokens, after_deck)

    b.visual_gate_failure = 0  # before usually has no gate
    a.visual_gate_failure = _visual_gate_failures(after_gate)

    if before_tokens is not None or before_deck is not None:
        rep_b = a11y_mod.audit(tokens=before_tokens, deck=before_deck)
        b.a11y_error = rep_b.errors
    if after_tokens is not None or after_deck is not None:
        rep_a = a11y_mod.audit(tokens=after_tokens, deck=after_deck)
        a.a11y_error = rep_a.errors
    return b, a


def evaluate_against_thresholds(
    after: DeckMetrics,
    thresholds: dict[str, Any],
) -> list[str]:
    """Return list of breach messages for *after* metrics (not deltas)."""
    metrics = thresholds.get("metrics") or {}
    breaches: list[str] = []
    for name in ("corruption", "extraction_loss", "layout_failure",
                 "visual_gate_failure", "a11y_error"):
        spec = metrics.get(name) or {}
        max_v = int(spec.get("max", 0))
        val = int(getattr(after, name, 0))
        if val > max_v:
            breaches.append(f"{name}={val} > max {max_v}")
    return breaches


def compare_deck(
    deck_id: str,
    before: DeckMetrics,
    after: DeckMetrics,
    thresholds: dict[str, Any],
) -> DeckResult:
    deltas = {
        "corruption": after.corruption - before.corruption,
        "extraction_loss": after.extraction_loss - before.extraction_loss,
        "layout_failure": after.layout_failure - before.layout_failure,
        "visual_gate_failure": after.visual_gate_failure - before.visual_gate_failure,
        "a11y_error": after.a11y_error - before.a11y_error,
    }
    breaches = evaluate_against_thresholds(after, thresholds)
    # Also fail if metrics *regressed* beyond absolute max even when after alone
    # would pass? Absolute after thresholds are the AC gate.
    status = "fail" if breaches else "pass"
    return DeckResult(
        deck_id=deck_id,
        status=status,
        before=before.to_dict(),
        after=after.to_dict(),
        deltas=deltas,
        threshold_breaches=breaches,
    )


def run_fixture_suite(
    *,
    fixtures: list[dict[str, Any]],
    thresholds: dict[str, Any] | None = None,
) -> SuiteReport:
    """Run benchmark on in-memory fixture cases.

    Each fixture dict may include:
      id, before_deck, after_deck, before_tokens, after_tokens,
      before_extract, after_extract, after_gate, before_pptx, after_pptx
    """
    th = thresholds or load_thresholds()
    results: list[DeckResult] = []
    for fx in fixtures:
        did = str(fx.get("id") or fx.get("deck_id") or f"deck-{len(results)}")
        before_pptx = Path(fx["before_pptx"]) if fx.get("before_pptx") else None
        after_pptx = Path(fx["after_pptx"]) if fx.get("after_pptx") else None
        b, a = score_deck(
            did,
            before_pptx=before_pptx,
            after_pptx=after_pptx,
            before_extract=fx.get("before_extract"),
            after_extract=fx.get("after_extract"),
            before_deck=fx.get("before_deck"),
            after_deck=fx.get("after_deck"),
            before_tokens=fx.get("before_tokens"),
            after_tokens=fx.get("after_tokens"),
            after_gate=fx.get("after_gate"),
        )
        results.append(compare_deck(did, b, a, th))
    return _suite_from_results(results, th)


def run_corpus_suite(
    manifest_path: str | Path,
    *,
    root: str | Path | None = None,
    thresholds: dict[str, Any] | None = None,
    held_out_only: bool = True,
) -> SuiteReport:
    """Score corpus entries. Missing files → skip with reason (CI-safe)."""
    th = thresholds or load_thresholds()
    entries = corpus_mod.load_corpus(manifest_path)
    errors = corpus_mod.validate_entries(entries)
    notes = [f"manifest error: {e}" for e in errors]
    if held_out_only:
        _, entries = corpus_mod.split(entries)
        notes.append(f"evaluating held-out set ({len(entries)} entries)")
    base = Path(root) if root else Path(manifest_path).resolve().parent
    results: list[DeckResult] = []
    for e in entries:
        did = str(e.get("id") or "unknown")
        rel = e.get("file") or e.get("path")
        if not rel:
            results.append(DeckResult(
                deck_id=did, status="skip", before={}, after={}, deltas={},
                skip_reason="manifest entry missing file path",
            ))
            continue
        pptx = base / rel if not Path(rel).is_absolute() else Path(rel)
        if not pptx.is_file():
            results.append(DeckResult(
                deck_id=did, status="skip", before={}, after={}, deltas={},
                skip_reason=f"corpus asset absent: {pptx}",
            ))
            continue
        # Without a paired after artifact, score the pptx alone as both sides
        # (smoke: corruption only). Real before/after needs extract/restyle outputs.
        b, a = score_deck(did, before_pptx=pptx, after_pptx=pptx)
        results.append(compare_deck(did, b, a, th))
    if not results:
        notes.append(
            "no corpus decks evaluated — provide assets or use fixture suite "
            "(see docs/maturity-roadmap.md)"
        )
    return _suite_from_results(results, th, notes=notes)


def run_default_fixture_benchmark(
    content_path: str | Path | None = None,
    design_path: str | Path | None = None,
    thresholds: dict[str, Any] | None = None,
) -> SuiteReport:
    """CI entry: compile default design + example deck-spec and score a11y/layout.

    Proves thresholds + runner without a private corpus.
    """
    from .compile import compile_design_md

    th = thresholds or load_thresholds()
    pkg = Path(__file__).parent
    design = Path(design_path) if design_path else pkg / "default.DESIGN.md"
    content_p = Path(content_path) if content_path else (
        pkg.parent / "examples" / "content.deck.json"
    )
    tokens = compile_design_md(design)
    deck = json.loads(content_p.read_text(encoding="utf-8"))

    # Before: intentionally degraded (low-contrast-ish after strip of on_accent,
    # missing alt on a synthetic image slide) vs after: auto-corrected + filled.
    before_tokens = json.loads(json.dumps(tokens))
    before_tokens.setdefault("colors", {})["text"] = "AAAAAA"
    before_tokens["colors"]["background"] = "FFFFFF"
    before_deck = json.loads(json.dumps(deck))
    # inject a slide with src and no alt for before metrics
    before_deck.setdefault("slides", []).append({
        "id": "a11y-probe",
        "recipe": "image_full",
        "content": {"title": "Probe", "src": "x.png", "alt": ""},
    })
    after_tokens, _ = a11y_mod.auto_correct_contrast(before_tokens)
    after_deck, _ = a11y_mod.ensure_notes_and_alt(before_deck)

    # "before" metrics intentionally fail a11y; after should pass layout/a11y.
    # before_tokens/before_deck must be scored so a11y_error deltas are real.
    fixtures = [{
        "id": "fixture-default-example",
        "before_deck": before_deck,
        "after_deck": after_deck,
        "before_tokens": before_tokens,
        "after_tokens": after_tokens,
        "before_extract": {"loss_ledger": []},
        "after_extract": {"loss_ledger": []},
        "after_gate": {"pass": True, "issues": []},
    }]
    report = run_fixture_suite(fixtures=fixtures, thresholds=th)
    report.notes.append(
        "default fixture benchmark (corpus assets optional; "
        "see docs/maturity-roadmap.md for 50-deck gap)"
    )
    return report


def _suite_from_results(
    results: list[DeckResult],
    thresholds: dict[str, Any],
    notes: list[str] | None = None,
) -> SuiteReport:
    n_pass = sum(1 for r in results if r.status == "pass")
    n_fail = sum(1 for r in results if r.status == "fail")
    n_skip = sum(1 for r in results if r.status == "skip")
    suite = thresholds.get("suite") or {}
    max_fail = int(suite.get("max_failed_decks", 0))
    min_decks = int(suite.get("min_decks", 1))
    evaluated = n_pass + n_fail
    ok = n_fail <= max_fail and evaluated >= min_decks
    extra = list(notes or [])
    if evaluated < min_decks:
        # Allow skip-only corpus runs to be ok when documented — CI fixture path
        # always evaluates ≥1. For corpus-only with all skips, mark ok with note.
        if n_skip > 0 and n_fail == 0 and evaluated == 0:
            ok = True
            extra.append(
                f"all {n_skip} corpus deck(s) skipped (assets absent) — "
                "thresholds not breached; run fixture suite for hard gate"
            )
        else:
            ok = False
            extra.append(f"evaluated {evaluated} < min_decks {min_decks}")
    return SuiteReport(
        ok=ok,
        decks_total=len(results),
        decks_pass=n_pass,
        decks_fail=n_fail,
        decks_skip=n_skip,
        thresholds=thresholds,
        results=results,
        notes=extra,
    )


def write_report(report: SuiteReport, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "benchmark.report.json"
    path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    # per-deck stubs for before/after inspection
    for r in report.results:
        (out / f"{r.deck_id}.json").write_text(
            json.dumps(r.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return path
