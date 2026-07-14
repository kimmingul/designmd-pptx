"""CLI: python -m designmd_pptx <command> ..."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .compile import assert_content_valid, assert_tokens_valid, compile_design_md, write_tokens
from .deck import generate_deck
from .recipes import generate_all_recipes, write_deck_sequence, write_recipes, write_slide_design_md

_DEFAULT_DESIGN = Path(__file__).parent / "default.DESIGN.md"


def _resolve_design(p: str | Path) -> Path:
    """Accept the literal `default` as the bundled neutral house style."""
    if str(p).strip().lower() in ("default", "@default"):
        return _DEFAULT_DESIGN
    return Path(p)


def cmd_compile(args: argparse.Namespace) -> int:
    tokens = compile_design_md(_resolve_design(args.design_md), brand=args.brand)
    strict = not getattr(args, "no_strict", False)
    errs = assert_tokens_valid(tokens, strict=strict)
    if errs and not strict:
        for e in errs:
            print(f"warning: {e}")
    out = Path(args.out)
    if out.suffix.lower() != ".json":
        out = out / "tokens.slide.json"
    write_tokens(tokens, out)
    print(f"Wrote {out}")
    if tokens.get("warnings"):
        print(f"warnings: {len(tokens['warnings'])}")
        for w in tokens["warnings"][:12]:
            print(f"  - {w}")
    if args.slide_md:
        md = Path(args.slide_md)
        write_slide_design_md(tokens, md)
        print(f"Wrote {md}")
    return 0


def cmd_recipes(args: argparse.Namespace) -> int:
    tokens = json.loads(Path(args.tokens).read_text(encoding="utf-8"))
    content_map = None
    if args.content:
        content_map = json.loads(Path(args.content).read_text(encoding="utf-8"))
    ops, deck, warnings = generate_deck(
        tokens, content_map, strict=not getattr(args, "no_strict", False)
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    seq = write_deck_sequence(ops, out)
    print(f"Wrote {seq} ({len(deck['slides'])} slides, {len(ops)} ops)")
    if getattr(args, "catalog", False):
        recipes = generate_all_recipes(tokens, content_map, validate=False, catalog=True)
        for p in write_recipes(recipes, out):
            print(f"Wrote {p}")
    for w in warnings:
        print(f"warning: {w}")
    (out / "deck.spec.json").write_text(
        json.dumps(deck, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {out / 'deck.spec.json'}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Staging-safe materialization entry point used by apply.ps1 / apply.sh."""
    from .apply import apply_sequence

    force = bool(args.force)
    # DESIGNMD_FORCE=1 is an alternate force signal for shell wrappers
    import os

    if os.environ.get("DESIGNMD_FORCE") == "1":
        force = True
    apply_sequence(
        args.pptx,
        args.sequence,
        create=True,
        force=force,
        require_clean_issues=not bool(getattr(args, "no_issues_gate", False)),
        screenshot=bool(getattr(args, "screenshot", False)),
        gate3=bool(getattr(args, "gate3", False)),
        vision=bool(getattr(args, "vision", False)),
        vision_fail=bool(getattr(args, "gate3_vision", False)),
        vision_plan=getattr(args, "vision_plan", None),
        vision_cmd=getattr(args, "vision_cmd", None),
    )
    return 0


def cmd_scaffold(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    tokens = compile_design_md(_resolve_design(args.design_md), brand=args.brand)
    assert_tokens_valid(tokens, strict=not args.no_strict)
    tokens_path = out_dir / "tokens.slide.json"
    write_tokens(tokens, tokens_path)
    print(f"Wrote {tokens_path}")
    if tokens.get("warnings"):
        print(f"compiler warnings: {len(tokens['warnings'])}")

    slide_md = out_dir / "SLIDE-DESIGN.md"
    write_slide_design_md(tokens, slide_md)
    print(f"Wrote {slide_md}")

    content_map = None
    if args.content:
        content_map = json.loads(Path(args.content).read_text(encoding="utf-8"))
    elif args.title or args.subtitle:
        content_map = {
            "version": "1.0",
            "slides": [
                {
                    "id": "cover",
                    "recipe": "cover",
                    "content": {
                        "title": args.title or "Presentation Title",
                        "subtitle": args.subtitle or tokens.get("brand", ""),
                        "meta": args.meta or "designmd-pptx scaffold",
                    },
                },
                {
                    "id": "close",
                    "recipe": "close",
                    "content": {
                        "title": args.title or "Next step",
                        "body": args.subtitle or "One clear ask.",
                        "cta": "Continue",
                    },
                },
            ],
        }

    ops, deck, deck_warnings = generate_deck(
        tokens, content_map, strict=not args.no_strict
    )
    recipe_dir = out_dir / "recipes"
    recipe_dir.mkdir(parents=True, exist_ok=True)
    seq_path = write_deck_sequence(ops, recipe_dir)
    print(f"Wrote {seq_path} ({len(deck['slides'])} slides)")
    (recipe_dir / "deck.spec.json").write_text(
        json.dumps(deck, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {recipe_dir / 'deck.spec.json'}")
    if getattr(args, "catalog", True):
        recipes = generate_all_recipes(tokens, content_map, validate=False, catalog=True)
        for p in write_recipes(recipes, recipe_dir):
            print(f"Wrote {p}")
    for w in deck_warnings:
        print(f"warning: {w}")

    # Thin wrappers — all materialization goes through apply_sequence (staging-safe)
    pptx_name = args.pptx or f"{_safe_name(tokens.get('brand', 'deck'))}.pptx"
    ps1 = out_dir / "apply.ps1"
    ps1.write_text(
        "\n".join(
            [
                "# Thin wrapper: staging-safe apply via designmd_pptx apply (apply_sequence)",
                "# Does NOT delete the destination before validate/issues — staging lives in apply.py",
                "# Requires: officecli + python",
                "$ErrorActionPreference = 'Stop'",
                f'$File = Join-Path $PSScriptRoot "{pptx_name}"',
                f'$Seq  = Join-Path $PSScriptRoot "recipes\\deck.sequence.json"',
                "$Force = @()",
                "if ($env:DESIGNMD_FORCE -eq '1') { $Force = @('--force') }",
                "# designmd-pptx package root is two levels up from out/<brand>/",
                '$PkgRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path',
                'if (Test-Path (Join-Path $PkgRoot "designmd_pptx")) { $env:PYTHONPATH = $PkgRoot }',
                "python -m designmd_pptx apply $File $Seq @Force --screenshot",
                'if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }',
                'Write-Host "Done: $File"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {ps1}")

    sh = out_dir / "apply.sh"
    sh.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "# Thin wrapper: staging-safe apply via designmd_pptx.apply_sequence",
                "set -euo pipefail",
                'ROOT="$(cd "$(dirname "$0")" && pwd)"',
                f'FILE="$ROOT/{pptx_name}"',
                'SEQ="$ROOT/recipes/deck.sequence.json"',
                'FORCE=()',
                'if [[ "${DESIGNMD_FORCE:-}" == "1" ]]; then FORCE=(--force); fi',
                'PKG="$(cd "$ROOT/../.." && pwd)"',
                'if [[ -d "$PKG/designmd_pptx" ]]; then export PYTHONPATH="$PKG${PYTHONPATH:+:$PYTHONPATH}"; fi',
                'python -m designmd_pptx apply "$FILE" "$SEQ" ${FORCE[@]+"${FORCE[@]}"} --screenshot',
                'echo "Done: $FILE"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {sh}")

    if args.apply:
        from .apply import apply_sequence

        apply_sequence(
            out_dir / pptx_name,
            recipe_dir / "deck.sequence.json",
            create=True,
            force=bool(getattr(args, "force", False)),
            require_clean_issues=True,
            screenshot=bool(getattr(args, "screenshot", False)),
            gate3=bool(getattr(args, "gate3", False)),
            vision=bool(getattr(args, "vision", False)),
            vision_fail=bool(getattr(args, "gate3_vision", False)),
            vision_plan=getattr(args, "vision_plan", None),
            vision_cmd=getattr(args, "vision_cmd", None),
        )

    print("")
    print("Scaffold complete.")
    print(f"  tokens:  {tokens_path}")
    print(f"  design:  {slide_md}")
    print(f"  recipes: {recipe_dir}")
    print(f"  apply:   {ps1.name} / {sh.name}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    """Existing pptx → content.deck.json draft + report + assets/."""
    from .extract import extract_pptx, is_licensed_reference_path

    # --no-media always wins; otherwise None lets extract apply the license fence
    # (media off under infograpify_ppt_templates/). --force-media opts back in.
    export_media: bool | None
    if getattr(args, "no_media", False):
        export_media = False
    elif getattr(args, "force_media", False):
        export_media = True
    else:
        export_media = None

    if is_licensed_reference_path(args.pptx) and export_media is not False:
        print(
            "warning: source looks like a licensed commercial pack — "
            "prefer `reference` for structural study; media export is "
            + ("ON (--force-media)" if export_media else "OFF (license fence)"),
            file=sys.stderr,
        )

    report = extract_pptx(args.pptx, args.out, export_media=export_media)
    print(f"Wrote {Path(args.out) / 'content.deck.json'}")
    print(f"Wrote {Path(args.out) / 'extract.report.json'}")
    for s in report["slides"]:
        flags = f" — {'; '.join(s['warnings'])}" if s.get("warnings") else ""
        print(f"  slide {s['index']:>2}: {s['recipe']} (confidence {s['confidence']}){flags}")
    if report.get("assets"):
        print(f"assets: {len(report['assets'])} exported")
    if report.get("licensed_source"):
        print(
            "note: licensed source detected — do not commit extracted assets; "
            "use `python -m designmd_pptx reference` for license-safe analysis"
        )
    print("Review the draft, then: python -m designmd_pptx scaffold DESIGN.md "
          f"--content {Path(args.out) / 'content.deck.json'}")
    return 0


def cmd_reference(args: argparse.Namespace) -> int:
    """License-safe structural analysis of premium reference decks (Phase 2 / #59).

    Default output redacts slide text and never exports media. Original .pptx
    files must remain gitignored (infograpify_ppt_templates/).
    """
    from .reference import (
        analyze_pptx,
        analyze_tree,
        catalog_filenames,
        write_report,
    )

    src = Path(args.path)
    out = Path(args.out) if args.out else Path(".ref-analysis")
    include_text = bool(args.include_text)
    if include_text:
        print(
            "warning: --include-text embeds slide wording; do NOT commit the report",
            file=sys.stderr,
        )

    if args.catalog:
        if not src.is_dir():
            print(f"error: --catalog needs a directory, got {src}", file=sys.stderr)
            return 2
        report = catalog_filenames(src)
        path = write_report(report, out / "catalog.json")
        print(f"Wrote {path} ({report['total']} decks, {len(report['families'])} families)")
        for fam, n in list(report["families"].items())[:16]:
            print(f"  {fam}: {n}")
        return 0

    if src.is_dir():
        report = analyze_tree(
            src,
            include_text=include_text,
            max_slides=args.max_slides,
        )
        path = write_report(report, out / "index.json")
        print(
            f"Wrote {path} — {report['deck_count']} decks, "
            f"{len(report.get('errors') or [])} errors"
        )
        for fam, n in list(report.get("families", {}).items())[:12]:
            print(f"  {fam}: {n}")
        if report.get("errors"):
            for e in report["errors"][:8]:
                print(f"  error: {e['filename']}: {e['error']}")
        print(
            "License: originals stay local/gitignored; only structural JSON is written."
        )
        return 0 if not report.get("errors") else 0  # soft-fail on per-deck errors

    report = analyze_pptx(
        src,
        include_text=include_text,
        max_slides=args.max_slides,
    )
    stem = re.sub(r"[^\w.\-]+", "_", src.stem)[:80]
    path = write_report(report, out / f"{stem}.json")
    print(f"Wrote {path}")
    print(
        f"  family={report['source']['family_hint']}  "
        f"slides={report['package']['slide_count']}  "
        f"analyzed={report['aggregate']['slides_analyzed']}"
    )
    print(f"  theme fonts: {report['theme'].get('fonts')}")
    print(f"  suggestions: {', '.join(report['recipe_suggestions'][:8])}")
    hints = report["aggregate"].get("layout_hints") or {}
    if hints:
        top = ", ".join(f"{k}×{v}" for k, v in list(hints.items())[:8])
        print(f"  hints: {top}")
    return 0


def cmd_restyle(args: argparse.Namespace) -> int:
    """Restyle an existing pptx with brand tokens (theme + explicit values)."""
    import os

    from .restyle import restyle_pptx, restyle_preview

    design = _resolve_design(args.design)
    if design.suffix.lower() == ".json":
        tokens = json.loads(design.read_text(encoding="utf-8"))
    else:
        tokens = compile_design_md(design, brand=args.brand)
        errs = assert_tokens_valid(tokens, strict=False)
        for e in errs:
            print(f"warning: {e}")

    force = bool(args.force) or os.environ.get("DESIGNMD_FORCE") == "1"
    color_map = {}
    for pair in args.map or []:
        old, _, new = pair.partition("=")
        if len(old) != 6 or len(new) != 6:
            raise ValueError(f"--map expects OLDHEX=NEWHEX, got: {pair}")
        color_map[old] = new

    kwargs = dict(explicit_colors=bool(args.map_colors),
                  explicit_fonts=not args.no_explicit_fonts, color_map=color_map)

    if args.preview:
        report = restyle_preview(args.pptx, tokens, **kwargs)
        print(f"Restyle preview (no changes written) → {report['source']}")
    else:
        report = restyle_pptx(args.pptx, tokens, out=args.out, force=force, **kwargs)
        print(f"Restyled → {report['dest']}")
    if report["theme_scheme"]:
        print(f"  theme scheme: {len(report['theme_scheme'])} slots remapped")
    if report["theme_fonts"]:
        print(f"  theme fonts: {report['theme_fonts']}")
    if report["colors"]:
        n = sum(v["count"] for v in report["colors"].values())
        print(f"  explicit colors: {len(report['colors'])} distinct → {n} replacements")
    if report.get("colors_preserved"):
        n = sum(v["count"] for v in report["colors_preserved"].values())
        print(f"  semantic colors preserved: {len(report['colors_preserved'])} "
              f"distinct → {n} occurrences (use --map to remap)")
    if report["fonts"]:
        n = sum(v["count"] for v in report["fonts"].values())
        print(f"  explicit fonts: {len(report['fonts'])} distinct → {n} replacements")
    if not args.map_colors and not args.preview:
        print("  (theme-only by default; pass --map-colors to snap explicit colors)")
    return 0


def cmd_master(args: argparse.Namespace) -> int:
    """Brand theme + slide master; optionally export a .potx template."""
    import os
    import tempfile

    from .master import brand_master, export_potx

    design = _resolve_design(args.design)
    if design.suffix.lower() == ".json":
        tokens = json.loads(design.read_text(encoding="utf-8"))
    else:
        tokens = compile_design_md(design, brand=args.brand)
        errs = assert_tokens_valid(tokens, strict=False)
        for e in errs:
            print(f"warning: {e}")

    force = bool(args.force) or os.environ.get("DESIGNMD_FORCE") == "1"

    potx_stats: dict = {}
    if args.potx and not args.out and not force:
        # potx-only mode: brand a throwaway copy, never touch the source
        with tempfile.TemporaryDirectory() as tmp:
            branded = Path(tmp) / "branded.pptx"
            report = brand_master(args.pptx, tokens, out=branded, layouts=args.layouts)
            export_potx(branded, args.potx, force=force, empty=args.empty_potx,
                        stats=potx_stats)
    else:
        report = brand_master(args.pptx, tokens, out=args.out, force=force,
                              layouts=args.layouts)
        print(f"Branded master → {report['dest']}")
        if args.potx:
            export_potx(report["dest"], args.potx, force=force, empty=args.empty_potx,
                        stats=potx_stats)

    if report["theme_scheme"]:
        print(f"  theme scheme: {len(report['theme_scheme'])} slots remapped")
    if report["theme_fonts"]:
        print(f"  theme fonts: {report['theme_fonts']}")
    if report["master_styles"]:
        print(f"  master type scale: {report['master_styles']}")
    if report.get("layout_colors"):
        n = sum(v["count"] for v in report["layout_colors"].values())
        print(f"  layout colors: {len(report['layout_colors'])} distinct → {n} replacements")
    if args.potx:
        print(f"Template → {args.potx}{' (slides stripped)' if args.empty_potx else ''}")
        if potx_stats.get("pruned_media"):
            print(f"  pruned {len(potx_stats['pruned_media'])} unreferenced media part(s)")
    return 0


def cmd_compose(args: argparse.Namespace) -> int:
    """Markdown brief/outline → deck-spec draft (recipe selection + content)."""
    from .compose import compose_outline

    tokens = None
    if args.design:
        tokens = compile_design_md(_resolve_design(args.design), brand=args.brand)
    report = compose_outline(
        args.brief,
        args.out,
        tokens=tokens,
        llm=bool(getattr(args, "llm", False)),
        style=getattr(args, "style", None),
        plan=getattr(args, "plan", None),
        llm_cmd=getattr(args, "llm_cmd", None),
    )
    print(f"Wrote {Path(args.out) / 'content.deck.json'}")
    print(f"Wrote {Path(args.out) / 'compose.report.json'}")
    for s in report["slides"]:
        role = f" [{s['role']}]" if s.get("role") else ""
        flags = f" — {'; '.join(s['warnings'])}" if s.get("warnings") else ""
        print(
            f"  slide {s['index']:>2}: {s['recipe']}{role} "
            f"(confidence {s['confidence']}){flags}"
        )
    planner = report.get("planner") or {}
    if planner:
        print(
            f"planner: provider={planner.get('provider')} "
            f"accepted={planner.get('accepted')} "
            f"pacing={((planner.get('pacing') or {}).get('score'))}"
        )
        for e in planner.get("errors") or []:
            print(f"planner error: {e}")
        for w in planner.get("warnings") or []:
            print(f"planner warning: {w}")
    for w in report.get("fit_warnings") or []:
        print(f"fit warning: {w}")
    print("Review the draft, then: python -m designmd_pptx scaffold <DESIGN.md|default> "
          f"--content {Path(args.out) / 'content.deck.json'}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    """Outline → deck via the official agent-bridge (office.render).

    Quick-draft path: outline-level fidelity only. For DESIGN.md-precise
    decks use compose → scaffold (legacy shape-level backend)."""
    import os
    import tempfile

    from .backend import (AgentBridgeBackend, deck_to_render_payload,
                          tokens_to_bridge_theme)
    from .deck import normalize_deck_spec

    src = Path(args.source)
    if src.suffix.lower() == ".json":
        deck_obj = json.loads(src.read_text(encoding="utf-8"))
    else:
        from .compose import compose_outline

        with tempfile.TemporaryDirectory() as tmp:
            compose_outline(src, tmp)
            deck_obj = json.loads(
                (Path(tmp) / "content.deck.json").read_text(encoding="utf-8")
            )
    deck, _ = normalize_deck_spec(deck_obj)
    theme = None
    if args.design:
        tokens = compile_design_md(_resolve_design(args.design), brand=None)
        theme = tokens_to_bridge_theme(tokens)
    payload = deck_to_render_payload(
        deck, title=args.title, style_preset=args.style, theme=theme
    )

    out = Path(args.out)
    force = bool(args.force) or os.environ.get("DESIGNMD_FORCE") == "1"
    if out.exists() and not force:
        raise FileExistsError(f"{out} already exists. Pass --force to overwrite.")

    bridge = AgentBridgeBackend()
    try:
        result = bridge.render_pptx(payload, out, enable_images=bool(args.images))
    finally:
        bridge.close()
    print(f"Rendered → {out}")
    status = result.get("status") or result.get("state") or "done"
    print(f"  bridge result: {status} ({len(payload['slides'])} slides, "
          f"images={'on' if args.images else 'off'})")
    print("  note: outline-level fidelity — use scaffold for DESIGN.md-precise decks")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from .doctor import run_doctor, run_install

    if getattr(args, "install", False):
        return run_install(dry_run=bool(getattr(args, "dry_run", False)))
    return run_doctor(strict=bool(args.strict))


def cmd_anonymize(args: argparse.Namespace) -> int:
    """Strip PII/metadata from a .pptx for corpus admission (#36)."""
    import os

    from .anonymize import anonymize_pptx

    force = bool(args.force) or os.environ.get("DESIGNMD_FORCE") == "1"
    report = anonymize_pptx(
        args.pptx, out=args.out, force=force, redact_text=bool(args.redact_text))
    print(f"Anonymized → {report['dest']}")
    if report["core_fields"]:
        print(f"  core.xml fields scrubbed: {sorted(set(report['core_fields']))}")
    if report["app_fields"]:
        print(f"  app.xml fields scrubbed: {sorted(set(report['app_fields']))}")
    if report["custom_props_dropped"]:
        print(f"  custom properties dropped: {report['custom_props_dropped']}")
    if report["comment_authors"]:
        print(f"  comment authors anonymized: {report['comment_authors']}")
    if report["redact_text"]:
        print(f"  text runs redacted: {report['text_runs_redacted']}")
    if report["unparsed"]:
        print(f"  warning: {len(report['unparsed'])} unparseable part(s) left as-is")
    return 0


def cmd_corpus(args: argparse.Namespace) -> int:
    """Validate a corpus manifest and report the train/held-out split (#36)."""
    from . import corpus

    entries = corpus.load_corpus(args.manifest)
    errors = corpus.validate_entries(entries)
    for e in errors:
        print(f"error: {e}")
    s = corpus.stats(entries)
    print(f"corpus: {s['total']} decks — {s['train']} train / {s['held_out']} held-out")
    print(f"  licenses: {', '.join(s['licenses']) or '(none)'}")
    print(f"  sources:  {', '.join(s['sources']) or '(none)'}")
    return 1 if errors else 0


def cmd_a11y(args: argparse.Namespace) -> int:
    """WCAG contrast, reading order, alt/notes audit (#39)."""
    from . import a11y as a11y_mod

    tokens = None
    deck = None
    if args.tokens:
        tokens = a11y_mod.load_json(args.tokens)
    if args.deck:
        deck = a11y_mod.load_json(args.deck)
    if tokens is None and deck is None:
        # Convenience: compile design + load content when provided
        if args.design:
            from .compile import compile_design_md
            tokens = compile_design_md(_resolve_design(args.design))
        if args.content:
            deck = a11y_mod.load_json(args.content)
    if tokens is None and deck is None:
        print("error: provide --tokens and/or --deck (or --design / --content)",
              file=sys.stderr)
        return 2

    report = a11y_mod.audit(
        tokens=tokens,
        deck=deck,
        level=args.level,
        require_notes=bool(args.require_notes),
        auto_correct=bool(args.fix_contrast),
        generate_missing=bool(args.generate_missing),
    )
    out = Path(args.out) if args.out else None
    if out:
        a11y_mod.write_report(report, out)
        print(f"Wrote {out}")
        if report.corrected and args.write_corrected:
            corr_dir = out.parent
            if report.corrected.get("tokens"):
                tp = corr_dir / "tokens.a11y.json"
                tp.write_text(
                    json.dumps(report.corrected["tokens"], indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
                print(f"Wrote {tp}")
            if report.corrected.get("deck"):
                dp = corr_dir / "content.a11y.deck.json"
                dp.write_text(
                    json.dumps(report.corrected["deck"], indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
                print(f"Wrote {dp}")

    mark = "PASS" if report.ok else "FAIL"
    print(f"a11y {mark}: {report.errors} error(s), {report.warnings} warning(s)")
    for f in report.findings:
        print(f"  [{f.severity}] {f.code}: {f.message}"
              + (f" ({f.path})" if f.path else ""))
    if report.reading_order and args.show_order:
        print(f"reading order ({len(report.reading_order)} nodes):")
        for n in report.reading_order[:40]:
            print(f"  [{n.get('reading_index')}] {n.get('slide_id')}/"
                  f"{n.get('role')}: {n.get('text', '')[:60]}")
    return 0 if report.ok else 1


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Before/after regression harness (#37)."""
    from . import benchmark as bench

    th = bench.load_thresholds(args.thresholds) if args.thresholds else bench.load_thresholds()
    if args.manifest:
        report = bench.run_corpus_suite(
            args.manifest,
            root=args.root,
            thresholds=th,
            held_out_only=not bool(args.all_entries),
        )
    else:
        report = bench.run_default_fixture_benchmark(
            content_path=args.content,
            design_path=args.design,
            thresholds=th,
        )
    out = Path(args.out) if args.out else Path("benchmark-out")
    path = bench.write_report(report, out)
    print(f"Wrote {path}")
    mark = "PASS" if report.ok else "FAIL"
    print(f"benchmark {mark}: pass={report.decks_pass} fail={report.decks_fail} "
          f"skip={report.decks_skip} total={report.decks_total}")
    for n in report.notes:
        print(f"  note: {n}")
    for r in report.results:
        if r.status == "skip":
            print(f"  skip  {r.deck_id}: {r.skip_reason}")
        elif r.status == "fail":
            print(f"  FAIL  {r.deck_id}: {', '.join(r.threshold_breaches)}")
            print(f"        deltas={r.deltas}")
        else:
            print(f"  pass  {r.deck_id}: deltas={r.deltas}")
    return 0 if report.ok else 1


def _safe_name(s: str) -> str:
    out = []
    for ch in s:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch in " .":
            out.append("-")
    name = "".join(out).strip("-") or "deck"
    return name[:64]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="designmd_pptx",
        description="Compile awesome-design-md DESIGN.md into officecli PPTX tokens & recipes",
    )
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("compile", help="DESIGN.md → tokens.slide.json")
    c.add_argument("design_md", type=Path)
    c.add_argument("-o", "--out", default="tokens.slide.json")
    c.add_argument("--brand", default=None)
    c.add_argument("--slide-md", default=None, help="Also write SLIDE-DESIGN.md path")
    c.add_argument("--no-strict", action="store_true", help="Do not fail on schema errors")
    c.set_defaults(func=cmd_compile)

    r = sub.add_parser("recipes", help="tokens.slide.json → recipe JSON files")
    r.add_argument("tokens", type=Path)
    r.add_argument("-o", "--out", default="recipes")
    r.add_argument("--content", type=Path, default=None, help="Deck-spec or flat content JSON")
    r.add_argument("--catalog", action="store_true", help="Also write per-recipe JSON files")
    r.add_argument("--no-strict", action="store_true")
    r.set_defaults(func=cmd_recipes)

    s = sub.add_parser("scaffold", help="compile + recipes + apply scripts in one shot")
    s.add_argument("design_md", type=Path)
    s.add_argument("-o", "--out", default="out")
    s.add_argument("--brand", default=None)
    s.add_argument("--title", default=None)
    s.add_argument("--subtitle", default=None)
    s.add_argument("--meta", default=None)
    s.add_argument("--pptx", default=None, help="Output pptx filename inside -o")
    s.add_argument("--content", type=Path, default=None)
    s.add_argument("--apply", action="store_true", help="Run officecli after scaffold")
    s.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing pptx when using --apply",
    )
    s.add_argument("--no-strict", action="store_true", help="Relax schema/content validation")
    s.add_argument(
        "--screenshot",
        action="store_true",
        help="With --apply: emit a Gate 3 contact-sheet PNG for visual QA",
    )
    s.add_argument(
        "--gate3",
        action="store_true",
        help="With --apply: the contact sheet must render before the pptx is written",
    )
    s.add_argument(
        "--vision",
        action="store_true",
        help="With --apply: evaluate contact sheet (offline + optional DESIGNMD_VISION_CMD)",
    )
    s.add_argument(
        "--gate3-vision",
        action="store_true",
        help="Hard vision QA gate: fail apply if evaluation pass=false (implies screenshot)",
    )
    s.add_argument(
        "--vision-plan",
        type=Path,
        default=None,
        help="JSON evaluation plan/result for replay (tests)",
    )
    s.add_argument(
        "--vision-cmd",
        default=None,
        help="Shell vision evaluator (stdin JSON → stdout eval). Overrides DESIGNMD_VISION_CMD",
    )
    s.set_defaults(func=cmd_scaffold)

    a = sub.add_parser(
        "apply",
        help="Materialize deck.sequence.json → pptx (staging-safe; requires --force to overwrite)",
    )
    a.add_argument("pptx", type=Path, help="Destination .pptx path")
    a.add_argument("sequence", type=Path, help="recipes/deck.sequence.json")
    a.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing pptx via staging (never delete dest until validate+issues pass)",
    )
    a.add_argument(
        "--no-issues-gate",
        action="store_true",
        help="Do not fail when view issues reports problems",
    )
    a.add_argument(
        "--screenshot",
        action="store_true",
        help="Emit a whole-deck contact-sheet PNG (officecli view screenshot --grid) "
        "for Gate 3 visual QA — rendered from staging before the destination is replaced",
    )
    a.add_argument(
        "--gate3",
        action="store_true",
        help="Hard gate: the contact sheet must render successfully or the "
        "destination is left untouched (implies --screenshot)",
    )
    a.add_argument(
        "--vision",
        action="store_true",
        help="Evaluate contact sheet quality (offline heuristic + optional vision cmd)",
    )
    a.add_argument(
        "--gate3-vision",
        action="store_true",
        dest="gate3_vision",
        help="Hard vision QA: abort apply when evaluation pass=false "
        "(implies screenshot; writes .gate3.json)",
    )
    a.add_argument(
        "--vision-plan",
        type=Path,
        default=None,
        help="JSON evaluation to merge/replay (tests + offline CI)",
    )
    a.add_argument(
        "--vision-cmd",
        default=None,
        help="Shell vision evaluator (stdin JSON → stdout eval JSON)",
    )
    a.set_defaults(func=cmd_apply)

    e = sub.add_parser(
        "extract",
        help="Existing .pptx → content.deck.json draft (+ report, assets) for re-scaffold",
    )
    e.add_argument("pptx", type=Path, help="Source .pptx to extract")
    e.add_argument("-o", "--out", default="extracted", help="Output directory")
    e.add_argument("--no-media", action="store_true", help="Do not export embedded images")
    e.add_argument(
        "--force-media",
        action="store_true",
        help="Export embedded images even when the source path looks like a "
        "licensed commercial pack (infograpify_ppt_templates/). Default is to "
        "skip media for those paths — prefer `reference` for structural study.",
    )
    e.set_defaults(func=cmd_extract)

    ref = sub.add_parser(
        "reference",
        help="License-safe structural analysis of premium reference .pptx "
        "(theme/geometry/hints only; default redacts text; never commits originals)",
    )
    ref.add_argument(
        "path",
        type=Path,
        help="A .pptx file or a directory of reference decks "
        "(e.g. infograpify_ppt_templates/)",
    )
    ref.add_argument(
        "-o",
        "--out",
        default=".ref-analysis",
        help="Output directory for JSON reports (default: .ref-analysis/, gitignored)",
    )
    ref.add_argument(
        "--catalog",
        action="store_true",
        help="Filename-only family catalog (no package open; safest inventory)",
    )
    ref.add_argument(
        "--include-text",
        action="store_true",
        help="Include short text samples (local study only — do not commit)",
    )
    ref.add_argument(
        "--max-slides",
        type=int,
        default=12,
        help="Per-deck slide cap for deep analysis (default 12; catalog ignores this)",
    )
    ref.set_defaults(func=cmd_reference)

    y = sub.add_parser(
        "restyle",
        help="Restyle an existing .pptx with DESIGN.md tokens (theme scheme/fonts "
        "+ explicit colors/fonts; staging-safe, --force to overwrite)",
    )
    y.add_argument("pptx", type=Path, help="Source .pptx")
    y.add_argument("design", type=Path, help="DESIGN.md or tokens.slide.json")
    y.add_argument("-o", "--out", type=Path, default=None,
                   help="Output .pptx (omit to restyle in place, requires --force)")
    y.add_argument("--brand", default=None)
    y.add_argument("--force", action="store_true", help="Overwrite destination")
    y.add_argument("--map-colors", action="store_true",
                   help="Opt in to remapping per-shape srgbClr values to the nearest "
                   "brand color (hue-aware — off-hue semantic colors are preserved). "
                   "Default is theme-only, which never collapses series/semantic colors")
    y.add_argument("--no-explicit-fonts", action="store_true",
                   help="Only remap theme fonts, not per-run typefaces")
    y.add_argument("--map", action="append", default=None, metavar="OLDHEX=NEWHEX",
                   help="Pin an explicit color mapping — always applied (repeatable)")
    y.add_argument("--preview", action="store_true",
                   help="Print the mapping report without writing anything")
    y.set_defaults(func=cmd_restyle)

    m = sub.add_parser(
        "master",
        help="Brand theme + slide master with DESIGN.md tokens (new PowerPoint "
        "slides inherit the brand); optionally export a .potx template",
    )
    m.add_argument("pptx", type=Path, help="Source .pptx")
    m.add_argument("design", type=Path, help="DESIGN.md or tokens.slide.json")
    m.add_argument("-o", "--out", type=Path, default=None,
                   help="Branded .pptx output (omit with --potx for template-only; "
                   "omit entirely to brand in place, requires --force)")
    m.add_argument("--potx", type=Path, default=None,
                   help="Also export a .potx template at this path")
    m.add_argument("--empty-potx", action="store_true",
                   help="Strip all slides from the .potx so it opens blank "
                   "(also garbage-collects media no surviving part references)")
    m.add_argument("--layouts", action="store_true",
                   help="Also snap explicit slideLayout colors to the brand palette")
    m.add_argument("--brand", default=None)
    m.add_argument("--force", action="store_true", help="Overwrite destination")
    m.set_defaults(func=cmd_master)

    o = sub.add_parser(
        "compose",
        help="Markdown brief/outline → content.deck.json draft (recipe selection, "
        "auto-split, fit warnings)",
    )
    o.add_argument("brief", type=Path, help="Markdown outline: # title, ## per slide")
    o.add_argument("-o", "--out", default="composed", help="Output directory")
    o.add_argument("--design", default=None,
                   help="DESIGN.md / tokens / 'default' — adds text-fit warnings to the report")
    o.add_argument("--brand", default=None)
    o.add_argument(
        "--llm",
        action="store_true",
        help="Opt-in intelligent planner (Phase 3 / #18). Default offline path is "
        "unchanged. Without DESIGNMD_LLM_CMD uses a narrative heuristic; set the "
        "env (or --llm-cmd) for a real LLM subprocess. Also: DESIGNMD_COMPOSE_LLM=1",
    )
    o.add_argument(
        "--style",
        default=None,
        help="Style / storytelling directive for the planner "
        '(e.g. "Apple Keynote storytelling", "medical conference")',
    )
    o.add_argument(
        "--plan",
        type=Path,
        default=None,
        help="Apply a JSON plan file (replay/tests). Validated through the same "
        "deck caps as hand-written specs",
    )
    o.add_argument(
        "--llm-cmd",
        default=None,
        help="Shell command for subprocess planner (stdin JSON request → stdout plan). "
        "Overrides DESIGNMD_LLM_CMD",
    )
    o.set_defaults(func=cmd_compose)

    n = sub.add_parser(
        "render",
        help="Outline → deck via the official officecli agent-bridge "
        "(office.render; quick drafts — use scaffold for precision)",
    )
    n.add_argument("source", type=Path, help="brief.md or content.deck.json")
    n.add_argument("-o", "--out", type=Path, required=True, help="Output .pptx")
    n.add_argument("--title", default=None)
    n.add_argument("--style", default="business", help="stylePreset (default: business)")
    n.add_argument("--design", default=None,
                   help="DESIGN.md / tokens / 'default' — brand colors+fonts "
                   "carry into the bridge theme (incl. CJK font slot)")
    n.add_argument("--images", action="store_true",
                   help="Enable hosted image generation (account credits)")
    n.add_argument("--force", action="store_true", help="Overwrite existing output")
    n.set_defaults(func=cmd_render)

    d = sub.add_parser(
        "doctor",
        help="Verify officecli + per-platform agent skill routing (Claude/Codex/Grok); "
             "optional --install pins official OfficeCLI from compatibility.json",
    )
    d.add_argument("--strict", action="store_true",
                   help="Exit non-zero when officecli is missing")
    d.add_argument("--install", action="store_true",
                   help="Explicitly install/repair auto-installable deps "
                        "(official officecli@pin from compatibility.json, PyYAML); "
                        "prints every download/command; legacy remains manual")
    d.add_argument("--dry-run", action="store_true",
                   help="With --install: print the version-locked plan without running it")
    d.set_defaults(func=cmd_doctor)

    z = sub.add_parser(
        "anonymize",
        help="Strip author/org/custom metadata + comment authorship from a .pptx "
        "for validation-corpus admission (staging-safe; --force to overwrite)",
    )
    z.add_argument("pptx", type=Path, help="Source .pptx to anonymize")
    z.add_argument("-o", "--out", type=Path, default=None,
                   help="Output .pptx (omit to anonymize in place, requires --force)")
    z.add_argument("--redact-text", action="store_true",
                   help="Also length-preserve-blank visible slide text (for highly "
                   "sensitive decks; layout/structure preserved)")
    z.add_argument("--force", action="store_true", help="Overwrite destination")
    z.set_defaults(func=cmd_anonymize)

    cp = sub.add_parser(
        "corpus",
        help="Validate a corpus manifest and report the train / held-out split",
    )
    cp.add_argument("manifest", type=Path, help="corpus.manifest.json")
    cp.set_defaults(func=cmd_corpus)

    ay = sub.add_parser(
        "a11y",
        help="WCAG contrast + reading order + alt/notes audit (issue #39); "
             "fails before output is treated as clean when errors remain",
    )
    ay.add_argument("--tokens", type=Path, default=None, help="tokens.slide.json")
    ay.add_argument("--deck", type=Path, default=None, help="content.deck.json / deck-spec")
    ay.add_argument("--design", type=Path, default=None,
                    help="DESIGN.md or 'default' (compiled when --tokens omitted)")
    ay.add_argument("--content", type=Path, default=None,
                    help="content.deck.json (used when --deck omitted)")
    ay.add_argument("--level", default="AA", choices=["AA", "AAA"],
                    help="WCAG contrast level (default AA)")
    ay.add_argument("--require-notes", action="store_true",
                    help="Treat missing speaker notes on narrative recipes as errors")
    ay.add_argument("--fix-contrast", action="store_true",
                    help="Opt-in: snap failing foreground token colors to readable ones")
    ay.add_argument("--generate-missing", action="store_true",
                    help="Opt-in: fill missing alt/notes with deterministic placeholders")
    ay.add_argument("--show-order", action="store_true",
                    help="Print deterministic reading-order nodes")
    ay.add_argument("-o", "--out", type=Path, default=None,
                    help="Write structured a11y.report.json")
    ay.add_argument("--write-corrected", action="store_true",
                    help="With --out, also write tokens.a11y.json / content.a11y.deck.json")
    ay.set_defaults(func=cmd_a11y)

    bm = sub.add_parser(
        "benchmark",
        help="Before/after regression harness with explicit thresholds (issue #37)",
    )
    bm.add_argument("--manifest", type=Path, default=None,
                    help="corpus.manifest.json (held-out by default); omit for fixture suite")
    bm.add_argument("--root", type=Path, default=None,
                    help="Root for relative corpus file paths")
    bm.add_argument("--all-entries", action="store_true",
                    help="With --manifest, score train+held-out (default: held-out only)")
    bm.add_argument("--design", type=Path, default=None,
                    help="Fixture mode: DESIGN.md (default: bundled default)")
    bm.add_argument("--content", type=Path, default=None,
                    help="Fixture mode: content.deck.json")
    bm.add_argument("--thresholds", type=Path, default=None,
                    help="Override benchmark_thresholds.json")
    bm.add_argument("-o", "--out", type=Path, default=Path("benchmark-out"),
                    help="Output directory for reports (default: benchmark-out)")
    bm.set_defaults(func=cmd_benchmark)

    return p


def main(argv: list[str] | None = None) -> int:
    # Legacy consoles (e.g. cp949) can't encode em-dashes etc. from deck content;
    # degrade to replacement chars instead of crashing the summary print.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, OSError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
