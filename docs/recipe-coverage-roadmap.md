# Full-family recipe coverage roadmap

**Goal:** Cover the *structural roles* represented by a ~400-deck licensed
Infograpify library (local only) — **not** a 1:1 clone of 400 files.

| Metric (local library, 2026-07-15) | Value |
|---|---:|
| Source decks (filename inventory) | 400 |
| Coarse families (`reference` catalog) | 12 |
| Shipped recipes today | 36 |
| Phase 2 premium shortlist (#58) | 10 / 10 |
| Intentional non-goals (asset-heavy) | maps, device mockups, icon packs |

Re-run inventory (safe, filenames only):

```bash
python -m designmd_pptx reference infograpify_ppt_templates --catalog -o .ref-analysis
```

Cluster snapshot used for this roadmap (filenames only, no media):
[`reference-catalog-clusters.json`](reference-catalog-clusters.json).

---

## Coverage model

```
400 files
  → coarse family (filename heuristic)
  → structural subcluster (role)
  → 0..N original recipes (variants = chrome/density, not new files)
```

| Coverage status | Meaning |
|---|---|
| **COVERED** | Dedicated recipe(s) express the role with DESIGN.md tokens |
| **PARTIAL** | Approximated by generic recipes (`feature_cards`, `process`, …) |
| **GAP** | Needs a first-class recipe (or explicit defer) |
| **DEFER** | Asset/license/engine limits — keep as image/reference only |

---

## 1. Coarse family scoreboard

| Infograpify family | n | Shipped recipes | Status | Next recipes (id) |
|---|---:|---|---|---|
| kpi_dashboard | 8 | `kpi_dashboard_grid`, `kpi_row`, `big_number` | COVERED | optional `metric_sparkline_row` |
| narrative_chrome | 7 | `agenda_toc`, `section_opener_numbered`, `cover`, `section_divider` | COVERED | `mission_vision_split` (optional) |
| timeline_roadmap | 20 | `timeline`, `story_timeline`, `roadmap_swimlane` | COVERED / PARTIAL gantt | `gantt_bars` |
| process_flow | 21 | `process`, `funnel_stages` | PARTIAL | `chevron_process`, `cycle_loop`, `pipeline_stages` |
| hierarchy | 6 | `pyramid_levels` | COVERED | optional `iceberg_levels` |
| comparison_matrix | 7 | `comparison_2col`, `matrix_2x2`, `quadrant_matrix_rich`, `vs_scorecard` | COVERED / PARTIAL swot | `swot_2x2` |
| chart_story | 23 | `chart_insight`, `chart_callout_panel` | PARTIAL | `waterfall_insight`, `venn_3set`, `cycle_stats` |
| pricing_table | 6 | `pricing`, `table`, `appendix_table` | COVERED | optional `pricing_highlight_col` |
| org_team | 11 | `team` | PARTIAL | `org_tree`, `persona_card` |
| geo_map | 17 | `image_full`, `image_text_2col` only | DEFER | no first-class map geometry |
| device_mockup | 1 | image recipes only | DEFER | external assets |
| other | 273 | `feature_cards`, `bullets`, domain set | PARTIAL | wave-2/3 clusters below |

---

## 2. Subcluster → recipe map (full library)

Counts from filename re-cluster of the same 400 paths (see snapshot JSON).

### Wave 0 — already shipped (do not reimplement)

| Subcluster | n | Recipes |
|---|---:|---|
| kpi_dashboard | 8 | `kpi_dashboard_grid`, `kpi_row`, `big_number` |
| agenda | 3 | `agenda_toc` |
| timeline / roadmap | 14 | `timeline`, `story_timeline`, `roadmap_swimlane` |
| funnel | 6 | `funnel_stages` |
| process (flow charts) | 6 | `process` |
| pyramid | 6 | `pyramid_levels` |
| comparison / matrix | 4 | `comparison_2col`, `matrix_2x2`, `quadrant_matrix_rich`, `vs_scorecard` |
| pricing | 3 | `pricing` |
| team grid | (in org_team) | `team` |
| narrative openers | (in family) | `cover`, `section_divider`, `section_opener_numbered` |
| academic/medical | n/a | `consort_flow`, `kaplan_meier`, `forest_plot`, `study_design`, `results_table_insight`, `multi_panel_figure` |

### Wave 1 — high leverage GAPs (implement next)

Priority for “full family coverage” of identifiable roles.

| # | Recipe id (proposed) | Geometry | Subcluster / signals | ~files | Rationale |
|---|---|---|---|---:|---|
| 1 | `chevron_process` | structured | process_flow, chevron/arrow language | subset of 21 | #58 planned leftover; very common infographic chrome |
| 2 | `cycle_loop` | structured | cycle diagrams (6+) | 6+ | circular process; not a linear `process` |
| 3 | `waterfall_insight` | structured | waterfall charts | 3+ | chart_story gap; officecli waterfall type + callouts |
| 4 | `venn_overlap` | structured | venn diagrams | 6 | pure geometry; no current recipe |
| 5 | `swot_2x2` | engine/hybrid | SWOT packs | 3 | specialized quadrant labels (S/W/O/T) |
| 6 | `gantt_bars` | structured | gantt packs | 6 | roadmap is swimlane, not true bar/schedule |
| 7 | `org_tree` | structured | organizational charts | 9 | `team` is cards, not reporting lines |
| 8 | `persona_card` | engine | buyer persona | 2+ | single-profile + attributes, not multi-team |
| 9 | `business_canvas` | structured | BMC | 3 | fixed 7–9 block grid |
| 10 | `fishbone_causes` | structured | fishbone (~9 filename hits) | ~9 | root-cause analysis skeleton |
| 11 | `iceberg_levels` | structured | iceberg (~6) | ~6 | above/below waterline hierarchy |
| 12 | `framework_row` | engine | ADKAR/AIDA/value chain/porters | 10+ | labeled stage frameworks as first-class, not generic process |

**Wave 1 target:** ~12 new recipes → process/chart/org/strategy families go COVERED.

### Wave 2 — long-tail *roles* inside “other” / generic_infographic

~172 filenames match `*Infographic*` and ~98 remain weakly classified. Do **not**
make 270 recipes. Cluster by **layout role**:

| # | Recipe id (proposed) | Geometry | Signals (filename / deep-dive) | Approx |
|---|---|---|---|---:|
| 13 | `icon_stat_row` | engine | numeric + icon row demographics/health packs | many |
| 14 | `scale_rating` | engine | smile/likert/rating scales | few |
| 15 | `hub_spoke` | structured | “bullseye”, radial, center hub | few |
| 16 | `before_after_slider` | engine | before/after comparison chrome | few |
| 17 | `calendar_heatmap` | structured | calendar / month grids | few |
| 18 | `case_study_band` | hybrid | case study narrative + KPI strip | few |
| 19 | `okrs_tree` | engine | OKR objective → key results | 1+ |
| 20 | `project_status_rag` | engine | RAG status tables / traffic lights | few |
| 21 | `finance_statement` | structured | budget/forecast tables with insight rail | 4+ |
| 22 | `geo_callout` | structured+image | map *with* callout cards (no basemap ship) | optional |
| 23 | `device_frame` | structured+image | phone/laptop frame slot (user supplies PNG) | optional |

**Wave 2 target:** ~8–11 recipes that absorb most generic_infographic *roles*.  
**Status:** ✅ 12 recipes shipped (`WAVE2_SEQUENCE`).

### Wave 3 — vertical skins, not new geometry

Filename tokens: business, marketing, health, real estate, education, ecology,
sport, SEO, travel, science, fitness, medical, entrepreneurship…

These are **content/theme packs** on top of Wave 0–2 geometry.

| Deliverable | Approach |
|---|---|
| Vertical example deck-specs | `python/examples/content.*.deck.json` using existing recipes |
| Optional DESIGN.md skins | fixtures like `premium-consulting` (original palettes) |
| Compose classifier hints | map keywords → recipes in `compose.py` |

**No new recipe IDs** unless a vertical needs unique geometry.

**Shipped examples:**

| Vertical | Deck-spec | Notes |
|---|---|---|
| business | `python/examples/content.business.deck.json` | icon_stat_row, finance_statement, okrs_tree |
| marketing | `python/examples/content.marketing.deck.json` | pipeline_stages, persona_card, before_after_slider |
| health | `python/examples/content.health.deck.json` | icon_stat_row, scale_rating, project_status_rag |
| education | `python/examples/content.education.deck.json` | framework_row, cycle_loop, okrs_tree |
| finance | `python/examples/content.finance.deck.json` | finance_statement, waterfall_insight, gantt_bars |
| finance skin | `python/fixtures/vertical-finance.DESIGN.md` | original dark data palette |

Compose routes `##` titles containing role keywords (OKR, SWOT, pipeline, …) to Wave 1/2 recipes via `compose._ROLE_TITLE_HINTS`.

### Explicit DEFER (never clone as recipes)

| Cluster | n | Why |
|---|---:|---|
| geo_map basemaps | 17 | Licensed cartography/media; use user images + `image_*` / `geo_callout` |
| device_mockup photo packs | 1 | Stock photography; frame slot only |
| icon libraries | varies | Do not embed vendor icons |
| SmartArt-faithful org art | — | Approximate with `org_tree` shapes, not binary clone |
| Animation-heavy masters | — | Phase 5 / #40 |

---

## 3. Implementation waves (engineering)

| Wave | Recipes (new) | Depends on | Exit criteria |
|---|---:|---|---|
| **1a** (process/chart) | `chevron_process`, `cycle_loop`, `waterfall_insight`, `venn_overlap` | layout contract tests | ✅ shipped |
| **1b** (matrix/plan) | `swot_2x2`, `gantt_bars` | 1a patterns | ✅ shipped |
| **1c** (people/strategy) | `org_tree`, `persona_card`, `business_canvas`, `fishbone_causes`, `iceberg_levels`, `framework_row` | 1a | ✅ shipped (`WAVE1_SEQUENCE`, tests) |
| **2** (long-tail roles) | icon_stat_row … device_frame (12 recipes, incl. `pipeline_stages`, `geo_callout`, `device_frame`) | 1 complete | ✅ shipped (`WAVE2_SEQUENCE`, tests) |
| **3** (verticals) | 0 recipes | wave 1–2 | ✅ shipped: 5 vertical deck-specs + finance DESIGN skin + compose title keywords |

### Per-recipe checklist (same as premium bar)

1. Original geometry (engine | hybrid | structured | fixed) — **one system**
2. `CONTENT_KEYS` + deck validation
3. CJK fit / text budget where text-heavy
4. Unit tests (builder emits ops; contract harness if engine)
5. `reference._suggest_recipes` / compose classifier aware
6. Docs: this roadmap status table flipped to ✅
7. **Never** commit Infograpify bytes or `--include-text` analysis

### Suggested milestone labels

- Wave 1 → issue epic “Full-family coverage W1” (v2.1 or v2.2)
- Wave 2 → follow-on
- Wave 3 → examples only, can ship continuously

---

## 4. Success definition (“all templates covered”)

| Definition | Target | Non-target |
|---|---|---|
| **Structural coverage** | Every coarse family is COVERED or explicit DEFER | 400 file-equal recipes |
| **Subcluster coverage** | Wave 1+2 roles have a recipe or documented alias | One recipe per pptx |
| **Compose path** | Brief keywords map into the expanded catalog | Auto-import of vendor pptx |
| **Agent UX** | ≤ ~55 total recipes (36 + ~12–15) still choosable | 400-way menu |

Rule of thumb: **if two decks share the same content shape and only differ in
icons/colors/industry title → one recipe + DESIGN.md/content, not two recipes.**

---

## 5. Refresh procedure

```bash
# 1) Filename catalog (always safe)
python -m designmd_pptx reference infograpify_ppt_templates --catalog -o .ref-analysis

# 2) Optional deep-dive on a GAP exemplar (redacted; do not commit)
python -m designmd_pptx reference "infograpify_ppt_templates/Venn Diagram 01.pptx" -o .ref-analysis

# 3) Rebuild cluster snapshot for this doc (repo helper; filenames only)
PYTHONPATH=python python scripts/cluster_reference_catalog.py \
  --dir infograpify_ppt_templates -o docs/reference-catalog-clusters.json

# 4) Update status tables in this file when a wave ships
```

---

## 6. Traceability

| Artifact | Role |
|---|---|
| `docs/infograpify-reference.md` | Principles + Phase 2 shortlist history |
| This file | Full-library coverage plan |
| `docs/reference-catalog-clusters.json` | Machine-readable cluster counts/examples |
| `python/designmd_pptx/reference.py` | Family hints + recipe suggestions |
| `python/designmd_pptx/recipes.py` | Shipped builders |
| Local `infograpify_ppt_templates/` | Licensed inputs — **never git** |
