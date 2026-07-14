---
name: officecli-pptx-designmd
description: "designmd-pptx v2.0: compile awesome-design-md / Stitch DESIGN.md into officecli PPTX tokens, ordered decks, staging-safe apply; compose markdown briefs into deck-specs; constraint-based layout engine with density adaptation for text-heavy patterns; extract existing pptx into a deck-spec draft (geometry-aware); restyle existing pptx with brand tokens (font-role aware); brand slide masters/layouts and export pruned .potx templates; a11y WCAG gate; before/after benchmark; doctor --install (officecli-dist pin); 20+ slide patterns; CJK-aware text-fit validation; Gate 3 screenshot gating; render quick drafts via the official officecli agent-bridge. Trigger on DESIGN.md, getdesign.md, brand design for slides, deck outline, restyle deck, modernize slides, slide master, potx template, /designmd-pptx, /officecli-pptx-designmd."
---

# officecli-pptx-designmd (v2.0)

## Locate the toolkit

Resolve the **Python package root** — first match wins:

1. `$env:DESIGNMD_PPTX_ROOT/python` — explicit override (project wins for edits)
2. `$env:CLAUDE_PLUGIN_ROOT/python` — Claude Code plugin install
3. `<this skill dir>/python` — Codex self-contained install (`~/.codex/skills/officecli-pptx-designmd/`)
4. `<this skill dir>/../../python` — repo checkout (`skills/officecli-pptx-designmd/`)
5. `<this skill dir>/../../../python` — Grok layout (`.grok/skills/officecli-pptx-designmd/`)
6. `~/.grok/installed-plugins/designmd-pptx-local/python` — Grok local install
7. project-local `./designmd-pptx/python`

Set for CLI:

```powershell
$env:PYTHONPATH = "<resolved python root>"
pip install -r "<resolved python root>\requirements.txt"
```

## Hard rules

1. Compile DESIGN.md → tokens (provenance + css_vars + warnings).
2. Prefer **deck-spec** (ordered, repeatable recipes). Don't hand-write it from
   prose — run `compose` on a markdown outline first, then edit the draft.
3. Floors: title ≥36pt, body ≥18pt, micro 12–16 for KPI chips only.
4. No silent truncation — item caps AND text length are validated (CJK-aware
   width budgets; Korean/Japanese/Chinese glyphs count wider). Text-heavy
   patterns (bullets, feature_cards, comparison_2col, image_text_2col) solve
   their geometry with the layout engine: comfortable density first, compact
   (tighter spacing, fonts floored at title 36 / body 18) as fallback, then a
   hard shorten-or-split failure. Fix content, don't shrink fonts.
5. `image_full` / `image_text_2col`: `alt` required when `src` set.
6. Process uses **glued connectors** (`/slide[N]/shape[@name=…]`).
7. Overwrite only with `--force` / `DESIGNMD_FORCE=1` (staging-safe via `apply_sequence`).
8. QA: validate → view issues (incl. low_contrast) → **Gate 3**: apply with
   `--screenshot` (renders from staging BEFORE the destination is replaced;
   `--gate3` makes a failed render abort the write). Optional **vision QA**
   (`--vision` / hard `--gate3-vision`, writes `.gate3.json`; offline heuristic
   always, `DESIGNMD_VISION_CMD` for a real vision model). Visually inspect the
   contact sheet; fix and re-apply until clean.
9. No brand DESIGN.md? Pass the literal `default` as the design argument —
   the bundled neutral house style keeps the design floor.
10. officecli missing or routing unclear? Run `python -m designmd_pptx doctor`
   and follow the printed remedies before continuing. For a version-locked
   official OfficeCLI pin: `doctor --install --dry-run` then `doctor --install`
   (reads `compatibility.json`; legacy binary remains a manual download).
11. Licensed premium templates (Infograpify, etc.) are **local reference only** —
    keep under `infograpify_ppt_templates/` (gitignored). Never commit originals
    or force-add ignored `.pptx`. Analyze with `reference` (text redacted by
    default); ship only original tokens/recipes. See `docs/infograpify-reference.md`.

## Commands

```powershell
$env:PYTHONPATH = "<python root>"
python -m designmd_pptx scaffold path\to\DESIGN.md -o out\brand --content <python root>\examples\content.deck.json
python -m designmd_pptx apply --force out\brand\deck.pptx out\brand\recipes\deck.sequence.json
# or thin wrapper after scaffold:
$env:DESIGNMD_FORCE=1; .\out\brand\apply.ps1
```

```text
python -m designmd_pptx compile DESIGN.md -o tokens.slide.json --slide-md SLIDE-DESIGN.md
python -m designmd_pptx recipes tokens.slide.json -o recipes/ --content content.deck.json
python -m designmd_pptx scaffold DESIGN.md -o out/brand --content content.deck.json [--apply --force]
python -m designmd_pptx apply [--force] dest.pptx recipes/deck.sequence.json
python -m designmd_pptx extract old.pptx -o extracted/          # v1.2: pptx → deck-spec draft
python -m designmd_pptx restyle old.pptx DESIGN.md -o new.pptx  # v1.2: rebrand existing deck
python -m designmd_pptx master deck.pptx DESIGN.md --potx brand.potx [--empty-potx]  # v1.3
python -m designmd_pptx scaffold default -o out/deck --content deck.json --apply --force --screenshot  # v1.4
python -m designmd_pptx doctor            # v1.4: verify officecli + skill routing
python -m designmd_pptx doctor --install --dry-run  # #34: version-locked install plan
python -m designmd_pptx doctor --install            # #34: pin official officecli + PyYAML
python -m designmd_pptx a11y --design default --content content.deck.json --show-order  # #39
python -m designmd_pptx a11y --tokens tokens.json --deck deck.json --fix-contrast --generate-missing
python -m designmd_pptx benchmark -o benchmark-out  # #37 fixture thresholds
python -m designmd_pptx refine content.deck.json -o refined --feedback "too dense" --rounds 3  # #19
# after refine: scaffold again from refined/content.deck.json
python -m designmd_pptx compose brief.md -o composed/ --design default   # v1.5: outline → deck-spec
python -m designmd_pptx compose brief.md -o composed/ --llm --style "Keynote storytelling"  # Phase 3 / #18 opt-in planner
python -m designmd_pptx render brief.md -o out/draft.pptx --design default  # v1.7: quick draft via official agent-bridge
python -m designmd_pptx reference infograpify_ppt_templates --catalog -o .ref-analysis  # Phase 2: license-safe structure inventory
python -m designmd_pptx reference path\to\licensed.pptx -o .ref-analysis               # Phase 2: redacted geometry/theme report
```

## Backends (v1.7)

Two OfficeCLI generations, one contract (`docs/officecli-backends.md`):

- **Precision path** (scaffold/apply/restyle/master/extract) → legacy
  shape-level binary. DESIGN.md-exact geometry, glued connectors, Gate 3.
- **Draft path** (`render`) → official `officecli` agent-bridge
  (JSON-RPC 2.0, capability-first: `initialize` → `capabilities/get` →
  `office.render`). Outline-level fidelity; `--design` carries brand colors
  and fonts into the bridge theme, including the CJK font slot.

Pick by need: precise brand deck → compose → scaffold; quick draft to react
to → render. `doctor` shows which backends this machine has.

## Authoring flow (v1.5)

1. Write a markdown **brief**: `# deck title`, one `## section` per slide;
   lists, `1.` steps, tables, `> quotes`, `![alt](img)`, `CTA: …` lines.
   Value bullets like `84.2 — ARR` become KPI cards; a single one becomes
   a big_number hero; dated steps become a timeline; two `###` subsections
   become comparison_2col; oversized bullet lists auto-split.
2. `compose brief.md -o composed/ --design <brand|default>` → review
   `compose.report.json` (confidence + fit warnings), edit the draft.
3. `scaffold <DESIGN.md|default> --content composed/content.deck.json --apply --force --screenshot --gate3`
4. Inspect the contact sheet (Gate 3), fix, re-apply.

## Existing decks (v1.2)

Two paths to modernize an existing .pptx — pick by how much change is wanted:

- **Full re-layout**: `extract old.pptx -o extracted/` maps each slide to the
  closest recipe (confidence + warnings + **loss_ledger** in `extract.report.json`,
  images exported to `assets/`). Charts recover type/series/categories; SmartArt
  falls back to text; groups are expanded; animations/embeddings are listed as
  losses (never silent). **Review the draft** — fix low-confidence mappings, set
  missing `src` — then `scaffold DESIGN.md --content extracted/content.deck.json`.
- **Brand-only restyle**: `restyle old.pptx DESIGN.md -o new.pptx` keeps layout
  untouched; remaps theme scheme + fonts, explicit srgbClr → nearest brand color,
  explicit typefaces → brand fonts. `--no-explicit-colors` / `--no-explicit-fonts`
  for theme-only; `--map OLDHEX=NEWHEX` to pin mappings. In-place needs `--force`
  (staging-safe, same guarantee as apply). Check the `.restyle.report.json`.

## Slide master & templates (v1.3)

`master deck.pptx DESIGN.md [-o branded.pptx] [--potx brand.potx] [--empty-potx] [--layouts]`
brands the theme (scheme + fonts) and master type scale so slides the user adds
later in PowerPoint inherit the brand; slide content is untouched. `--layouts`
also rebrands slideLayouts: explicit colors that exactly match an old theme
slot get that slot's new brand color (unmatched colors are left alone and
reported — safer than nearest-color snapping). `--potx` exports a PowerPoint
template; `--empty-potx` strips slides AND garbage-collects media that no
surviving part references. With `--potx` alone the source pptx is never
modified. Run after `apply` to deliver a deck whose file doubles as a template.

## Patterns

cover · section_divider · **section_opener_numbered** · **agenda_toc** · kpi_row · **kpi_dashboard_grid** · **big_number** · feature_cards · **pricing** · bullets · quote · comparison_2col · **matrix_2x2** · **quadrant_matrix_rich** · **vs_scorecard** · timeline · **story_timeline** · process · **funnel_stages** · **roadmap_swimlane** · **pyramid_levels** · table · **appendix_table** · chart_insight · **chart_callout_panel** (any officecli chartType: column/bar/line/pie/area/waterfall/funnel/…) · **team** · **logo_strip** · image_full · image_text_2col · close

**Academic / medical (#10):** **consort_flow** · **kaplan_meier** · **forest_plot** · **study_design** · **results_table_insight** · **multi_panel_figure** — example deck-spec: `python/examples/content.medical.deck.json`

**Wave 1 full-family:** **chevron_process** · **cycle_loop** · **waterfall_insight** · **venn_overlap** · **swot_2x2** · **gantt_bars** · **org_tree** · **persona_card** · **business_canvas** · **fishbone_causes** · **iceberg_levels** · **framework_row**

**Wave 2 long-tail:** **icon_stat_row** · **scale_rating** · **hub_spoke** · **before_after_slider** · **calendar_heatmap** · **case_study_band** · **okrs_tree** · **project_status_rag** · **finance_statement** · **pipeline_stages** · **geo_callout** · **device_frame** (user media only for map/device)

**Wave 3 verticals:** `python/examples/content.{business,marketing,health,education,finance}.deck.json` — see `docs/recipe-coverage-roadmap.md`

## Colors

hex, rgb/hsl, oklch (approx), color-mix, var(--token), linear-gradient (2-stop officecli form).

## Requires

- Python 3.10+ with PyYAML (`pip install -r <python root>/requirements.txt`)
- Optional, for materializing `.pptx`: legacy shape-level binary
  ([iOfficeAI/OfficeCLI releases](https://github.com/iOfficeAI/OfficeCLI/releases))
  for scaffold/apply, and/or official [officecli](https://github.com/officecli/officecli)
  ≥ 0.2.117 for the `render` command (agent-bridge). `doctor` reports both.
