"""CLI: python -m designmd_pptx <command> ..."""

from __future__ import annotations

import argparse
import json
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
                "python -m designmd_pptx apply $File $Seq @Force",
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
                'python -m designmd_pptx apply "$FILE" "$SEQ" ${FORCE[@]+"${FORCE[@]}"}',
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
    from .extract import extract_pptx

    report = extract_pptx(args.pptx, args.out, export_media=not args.no_media)
    print(f"Wrote {Path(args.out) / 'content.deck.json'}")
    print(f"Wrote {Path(args.out) / 'extract.report.json'}")
    for s in report["slides"]:
        flags = f" — {'; '.join(s['warnings'])}" if s.get("warnings") else ""
        print(f"  slide {s['index']:>2}: {s['recipe']} (confidence {s['confidence']}){flags}")
    if report.get("assets"):
        print(f"assets: {len(report['assets'])} exported")
    print("Review the draft, then: python -m designmd_pptx scaffold DESIGN.md "
          f"--content {Path(args.out) / 'content.deck.json'}")
    return 0


def cmd_restyle(args: argparse.Namespace) -> int:
    """Restyle an existing pptx with brand tokens (theme + explicit values)."""
    import os

    from .restyle import restyle_pptx

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

    report = restyle_pptx(
        args.pptx,
        tokens,
        out=args.out,
        force=force,
        explicit_colors=not args.no_explicit_colors,
        explicit_fonts=not args.no_explicit_fonts,
        color_map=color_map,
    )
    print(f"Restyled → {report['dest']}")
    if report["theme_scheme"]:
        print(f"  theme scheme: {len(report['theme_scheme'])} slots remapped")
    if report["theme_fonts"]:
        print(f"  theme fonts: {report['theme_fonts']}")
    if report["colors"]:
        n = sum(v["count"] for v in report["colors"].values())
        print(f"  explicit colors: {len(report['colors'])} distinct → {n} replacements")
    if report["fonts"]:
        n = sum(v["count"] for v in report["fonts"].values())
        print(f"  explicit fonts: {len(report['fonts'])} distinct → {n} replacements")
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

    if args.potx and not args.out and not force:
        # potx-only mode: brand a throwaway copy, never touch the source
        with tempfile.TemporaryDirectory() as tmp:
            branded = Path(tmp) / "branded.pptx"
            report = brand_master(args.pptx, tokens, out=branded)
            export_potx(branded, args.potx, force=force, empty=args.empty_potx)
    else:
        report = brand_master(args.pptx, tokens, out=args.out, force=force)
        print(f"Branded master → {report['dest']}")
        if args.potx:
            export_potx(report["dest"], args.potx, force=force, empty=args.empty_potx)

    if report["theme_scheme"]:
        print(f"  theme scheme: {len(report['theme_scheme'])} slots remapped")
    if report["theme_fonts"]:
        print(f"  theme fonts: {report['theme_fonts']}")
    if report["master_styles"]:
        print(f"  master type scale: {report['master_styles']}")
    if args.potx:
        print(f"Template → {args.potx}{' (slides stripped)' if args.empty_potx else ''}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from .doctor import run_doctor

    return run_doctor(strict=bool(args.strict))


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
        help="After apply, emit a whole-deck contact-sheet PNG (officecli view "
        "screenshot --grid) for Gate 3 visual QA",
    )
    a.set_defaults(func=cmd_apply)

    e = sub.add_parser(
        "extract",
        help="Existing .pptx → content.deck.json draft (+ report, assets) for re-scaffold",
    )
    e.add_argument("pptx", type=Path, help="Source .pptx to extract")
    e.add_argument("-o", "--out", default="extracted", help="Output directory")
    e.add_argument("--no-media", action="store_true", help="Do not export embedded images")
    e.set_defaults(func=cmd_extract)

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
    y.add_argument("--no-explicit-colors", action="store_true",
                   help="Only remap the theme scheme, not per-shape srgbClr values")
    y.add_argument("--no-explicit-fonts", action="store_true",
                   help="Only remap theme fonts, not per-run typefaces")
    y.add_argument("--map", action="append", default=None, metavar="OLDHEX=NEWHEX",
                   help="Pin an explicit color mapping (repeatable)")
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
                   help="Strip all slides from the .potx so it opens blank")
    m.add_argument("--brand", default=None)
    m.add_argument("--force", action="store_true", help="Overwrite destination")
    m.set_defaults(func=cmd_master)

    d = sub.add_parser(
        "doctor",
        help="Verify officecli + per-platform agent skill routing (Claude/Codex/Grok)",
    )
    d.add_argument("--strict", action="store_true",
                   help="Exit non-zero when officecli is missing")
    d.set_defaults(func=cmd_doctor)

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
