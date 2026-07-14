# Infograpify reference analysis (Phase 2 / #59)

**License-safe design research** for elevating designmd-pptx visual quality.
Original Infograpify `.pptx` files are **local references only** and must never
be committed. This document records **principles, token mappings, and planned
patterns** derived from structural analysis — not copies of vendor slides.

## Hard rules (contributors)

1. Keep licensed decks under `infograpify_ppt_templates/` (gitignored) or any
   path **outside** the repo. Never `git add -f` a `.pptx` from a commercial pack.
2. Analyze with the redacting CLI (default). Do **not** commit reports produced
   with `--include-text`.
3. Ship only **original** code: DESIGN.md tokens, recipes, layout rules, and
   synthetic fixtures. Do not paste vendor shapes, icons, or stock photography.
4. Local analysis artifacts go to `.ref-analysis/` (gitignored).

```bash
# Filename inventory only (safest)
python -m designmd_pptx reference infograpify_ppt_templates --catalog -o .ref-analysis

# Structural report for one deck (text redacted)
python -m designmd_pptx reference "infograpify_ppt_templates/KPI Dashboard.pptx" -o .ref-analysis

# Batch index (summaries, still redacted)
python -m designmd_pptx reference infograpify_ppt_templates -o .ref-analysis --max-slides 12
```

## Workflow (repeatable)

```
licensed .pptx (local)
        │
        ▼
 designmd-pptx reference   ──►  .ref-analysis/*.json   (geometry, theme, hints)
        │
        ▼
 docs/infograpify-reference.md   ──►  design principles (this file)
        │
        ▼
 original DESIGN.md + recipes   ──►  scaffold / master --potx / Gate 3
        │
        ▼
 never commit originals; only tokens, code, synthetic examples
```

| Step | Command / artifact | Commit? |
|---|---|---|
| 1. Inventory | `reference --catalog` → family histogram | principles only |
| 2. Deep dive | `reference <deck>.pptx` → layout hints + theme | no (`.ref-analysis/`) |
| 3. Encode | tokens in DESIGN.md, recipes in `recipes.py` | yes (original) |
| 4. Master | `master deck.pptx DESIGN.md --potx brand.potx --empty-potx` | potx only if **you** authored it |
| 5. QA | CJK fit + Gate 3 contact sheet | screenshots of **our** output ok |

## Catalog snapshot (local library)

Measured on a licensed local library of **400** decks
(`infograpify_ppt_templates/`, not in git). Filename → family heuristic only:

| Family | Count | designmd today | Premium gap (#58) |
|---|---:|---|---|
| other (long-tail verticals) | 273 | bullets / feature_cards | selective later |
| chart_story | 23 | chart_insight, big_number | `chart_callout_panel`, waterfall insight |
| process_flow | 21 | process, timeline | `funnel_stages`, `chevron_process` |
| timeline_roadmap | 20 | timeline | `story_timeline`, `roadmap_swimlane` |
| geo_map | 17 | image_* | defer (asset-heavy) |
| org_team | 11 | team | richer org tree (SmartArt → groups) |
| kpi_dashboard | 8 | kpi_row, big_number | **`kpi_dashboard_grid`** (priority) |
| narrative_chrome | 7 | cover, section_divider | `agenda_toc`, numbered openers |
| comparison_matrix | 7 | comparison_2col, matrix_2x2 | `quadrant_matrix_rich`, scorecard |
| pricing_table | 6 | pricing, table | multi-tier highlight column |
| hierarchy | 6 | feature_cards | `pyramid_levels` |
| device_mockup | 1 | image_text_2col | defer |

## Structural principles (from priority decks)

Deep-analyzed (redacted) samples included: KPI dashboard packs, Timeline,
Process / Funnel, Pricing tables, Matrix analysis, Agenda, Product roadmap,
Org charts, Pyramid, Business Model Canvas, Waterfall charts.

### 1. Composition & rhythm

- **Card rows of 3–4** dominate product/process storytelling (`card_row_3` /
  `card_row_4` hints). Our engine-solved `feature_cards` / `pricing` already
  target this; premium work should vary **chrome** (accent bars, index discs,
  hairline separators) rather than inventing a second grid system.
- **KPI bands** (large type, short labels, 3–8 metrics) co-occur with charts on
  dashboards. Current `kpi_row` (max 4) is necessary but not sufficient for
  multi-row dashboards → planned `kpi_dashboard_grid`.
- **Heavy grouping** is the norm (shapes nested in `p:grpSp`). Extract fidelity
  (#12) must surface groups; recipes should prefer flat, engine-solved trees
  with optional post-solve markers (same pattern as timeline dots / team avatars).
- **Sparse heroes** (few shapes, large type) alternate with dense analytical
  slides — narrative pacing for `compose` / LLM planner (#18) later.

### 2. Color systems (token mapping, not copy)

Vendor packs often ship the **Office theme shell** (Calibri + generic accents)
and paint **per-shape srgb** for brand color. For designmd-pptx:

| Principle | DESIGN.md / tokens mapping |
|---|---|
| One dominant accent + neutrals | `colors.primary`, `ink`, `canvas`, `surface-1/2` |
| Semantic series stay distinct | restyle default: theme-only; `--map-colors` opt-in (#13) |
| Dashboard multi-series | `charts.series_colors` (schema v2) |
| Success / risk never collapsed | `semantic-success`, `semantic-danger` |

**Do not** hardcode a vendor accent hex as “the Infograpify brand.” Encode
**roles** (primary / muted / surface / chart series).

Recommended **consulting-premium** starting palette (original, for fixtures):

```yaml
colors:
  canvas: "#0B1220"          # optional dark-first dashboards
  surface-1: "#141C2B"
  surface-2: "#1C2740"
  primary: "#3B82F6"
  ink: "#F8FAFC"
  ink-muted: "#94A3B8"
  hairline: "#243047"
  semantic-success: "#22C55E"
  semantic-danger: "#F43F5E"
```

Light boardroom variant stays on the bundled `default` house style, with denser
`composition.whitespace_density: compact` for dashboard recipes.

### 3. Typography

- Theme fonts in samples are mostly **Calibri / Calibri Light** (template default),
  not a distinctive brand face — quality comes from **scale ladder + weight**,
  not the typeface name.
- KPI numerals sit at **display** sizes; labels at caption. Map to:
  `display-xl` / `headline` / `body` / `caption` (existing type tokens).
- CJK decks must keep the designmd rule: **shorten or split, never font-shrink**
  past the readability floor (geometry contract ≥10pt).

### 4. Chart & data storytelling

- KPI packs: **charts on most slides** + metric callouts (not chart-only).
- Roadmaps / matrices: **tables + connectors** more than native charts.
- Org charts: **SmartArt** common → extract loss-ledger (#12) must record
  SmartArt; recipes should use **grouped cards + connectors**, not re-emit SmartArt.

### 5. Whitespace density

Measured content margins vary widely (heroes with large empty regions vs edge-to-
edge canvases). Schema v2 already has:

```yaml
composition:
  whitespace_density: comfortable   # comfortable | compact | spacious
  title_placement: top              # top | left | center
```

Premium dashboard recipes should default to **`compact`**; section openers to
**`spacious`**.

## Priority pattern shortlist for #58

Implement as **original** recipes (engine or structured), not template clones.
Target **8–10** patterns; first wave below.

| # | Pattern id | Geometry system | Primary reference families | Acceptance notes |
|---|---|---|---|---|
| 1 | `kpi_dashboard_grid` | engine | kpi_dashboard | 2×N metric tiles + optional chart slot; CJK fit |
| 2 | `agenda_toc` | fixed / engine | narrative_chrome | numbered TOC, 5–12 items, continuation |
| 3 | `story_timeline` | engine | timeline_roadmap | richer than `timeline` (era bands / milestones) |
| 4 | `funnel_stages` | structured | process_flow | 3–6 stages, decreasing width metaphor via cards |
| 5 | `roadmap_swimlane` | structured | timeline_roadmap | rows × quarters; table-backed ok |
| 6 | `quadrant_matrix_rich` | engine | comparison_matrix | labeled axes + cell titles (beyond 2×2 titles) |
| 7 | `pyramid_levels` | structured | hierarchy | 3–5 levels, center stack |
| 8 | `vs_scorecard` | engine | comparison_matrix | 2-column criteria scores |
| 9 | `chart_callout_panel` | structured | chart_story | chart + 3 callout bullets |
| 10 | `section_opener_numbered` | fixed | narrative_chrome | large index + title (section_divider upgrade) |

Domain patterns from #10 (CONSORT, KM, forest plot) stay on the academic track;
they may reuse hierarchy / process geometry.

## Premium master template (#59 acceptance)

Original fixture: [`python/fixtures/premium-consulting.DESIGN.md`](../python/fixtures/premium-consulting.DESIGN.md).

```bash
# 1) Scaffold a neutral deck with the premium tokens
export PYTHONPATH=python
python -m designmd_pptx scaffold python/fixtures/premium-consulting.DESIGN.md \
  -o out/premium-master --content python/examples/content.deck.json

# 2) After materializing a .pptx (OfficeCLI legacy), brand master + empty .potx
python -m designmd_pptx master out/premium-master/deck.pptx \
  python/fixtures/premium-consulting.DESIGN.md \
  --potx out/premium-consulting.potx --empty-potx --layouts --force
```

The `.potx` is **our** branded shell (tokens + master), not a redistributed
vendor template. Gate 3 on any demo deck built from these tokens before claiming
visual quality.

## Linkage to other Phase 2 issues

| Issue | Role |
|---|---|
| **#59** (this doc + `reference` CLI) | Workflow + principles |
| **#58** | Implement the shortlist above |
| **#12** | Extract fidelity / loss ledger (groups, charts, SmartArt) — needed so reference decks can be studied via extract as well as `reference` |
| **#10** | Academic / medical patterns (parallel track) |

## What “done” means for #59

- [x] `designmd-pptx reference` CLI (redacted structural analysis)
- [x] `.gitignore`: `infograpify_ppt_templates/`, `.ref-analysis/`
- [x] This document (principles, token mapping, shortlist, contributor rules)
- [x] Original premium DESIGN.md fixture for master / scaffold
- [ ] First wave recipes (#58) with CJK + Gate 3 on **generated** decks
- [ ] Contributor note mirrored in `CONTRIBUTING.md` / skill hard rules

---

*Analysis tooling is stdlib + package XML parsing only. It never uploads decks
or depends on OfficeCLI.*
