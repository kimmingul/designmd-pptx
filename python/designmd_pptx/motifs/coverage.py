"""Infograpify → motif coverage map (license-safe structural collapse).

400 local Infograpify decks are **not** cloned 1:1. Filename/family analysis
(`.ref-analysis/catalog.json`, `index.json`) collapses them into **owned**
motifs + recipe wrappers. Vendor shapes/media never ship.

``RECIPE_TO_MOTIF`` is the source of truth: every registered recipe maps to
exactly one motif id. Custom builders live in ``motif.py`` /
``motifs.structural``; remaining recipes are exposed via recipe adapters so
``render_motif`` can render the full catalog.
"""

from __future__ import annotations

# Infograpify family_hint → motif ids (structural coverage)
FAMILY_MOTIFS: dict[str, list[str]] = {
    "narrative_chrome": [
        "sparse_hero", "section_mark", "section_wash", "agenda_list",
        "close_mark", "quote_mark", "split_hero",
    ],
    "kpi_dashboard": [
        "kpi_band", "kpi_hero", "kpi_grid", "stat_row", "chart_panel",
    ],
    "process_flow": [
        "step_rail", "funnel_cascade", "chevron_flow", "hub_orbit",
        "pipeline_rail", "journey_path", "stair_ascent", "fishbone_spine",
        "framework_bar",
    ],
    "timeline_roadmap": [
        "timeline_rail", "swimlane_roadmap", "gantt_track",
    ],
    "hierarchy": [
        "pyramid_stack", "iceberg_depth", "pillar_band", "org_cascade",
        "okr_tree",
    ],
    "org_team": [
        "org_cascade", "team_cards", "persona_split",
    ],
    "comparison_matrix": [
        "matrix_quad", "rich_matrix", "split_hero", "vs_columns",
        "risk_heat", "raci_grid",
    ],
    "pricing_table": [
        "pricing_tiers", "data_table", "card_row",
    ],
    "strategy_canvas": [
        "canvas_bmc", "pestle_cells", "scorecard_grid",
    ],
    "chart_story": [
        "chart_panel", "venn_duo", "ring_segments", "waterfall_bars",
    ],
    "geo_map": [
        "geo_pins", "mindmap_radial", "empathy_quad",
    ],
    "device_mockup": [
        "device_chrome",
    ],
    "other": [
        "card_row", "bullet_stack", "tile_row", "check_stack", "hex_honey",
        "calendar_grid", "case_band", "rag_status", "finance_grid",
        "scale_meter", "logo_band", "image_stage", "consort_spine",
        "forest_ci", "km_curve", "study_box", "multi_panel", "freeform_stage",
    ],
}

# Every recipe → one motif (primary chrome grammar)
RECIPE_TO_MOTIF: dict[str, str] = {
    # narrative
    "cover": "sparse_hero",
    "section_divider": "section_wash",
    "section_opener_numbered": "section_mark",
    "agenda_toc": "agenda_list",
    "close": "close_mark",
    "quote": "quote_mark",
    "bullets": "bullet_stack",
    "mission_vision_split": "split_hero",
    "before_after_slider": "split_hero",
    "comparison_2col": "split_hero",
    # kpi / metrics
    "kpi_row": "kpi_band",
    "kpi_dashboard_grid": "kpi_grid",
    "big_number": "kpi_hero",
    "icon_stat_row": "stat_row",
    "scale_rating": "scale_meter",
    # process
    "process": "step_rail",
    "funnel_stages": "funnel_cascade",
    "chevron_process": "chevron_flow",
    "cycle_loop": "hub_orbit",
    "hub_spoke": "hub_orbit",
    "pipeline_stages": "pipeline_rail",
    "journey_stages": "journey_path",
    "stairs_ascent": "stair_ascent",
    "fishbone_causes": "fishbone_spine",
    "framework_row": "framework_bar",
    # timeline
    "timeline": "timeline_rail",
    "story_timeline": "timeline_rail",
    "roadmap_swimlane": "swimlane_roadmap",
    "gantt_bars": "gantt_track",
    # hierarchy / org
    "pyramid_levels": "pyramid_stack",
    "iceberg_levels": "iceberg_depth",
    "pillar_columns": "pillar_band",
    "org_tree": "org_cascade",
    "okrs_tree": "okr_tree",
    "team": "team_cards",
    "persona_card": "persona_split",
    # matrix / compare
    "matrix_2x2": "matrix_quad",
    "swot_2x2": "matrix_quad",
    "quadrant_matrix_rich": "rich_matrix",
    "vs_scorecard": "vs_columns",
    "risk_heat_matrix": "risk_heat",
    "raci_matrix": "raci_grid",
    "empathy_map_quad": "empathy_quad",
    # cards / tiles
    "feature_cards": "card_row",
    "puzzle_pieces": "tile_row",
    "checklist_board": "check_stack",
    "hex_cluster": "hex_honey",
    "pricing": "pricing_tiers",
    # strategy
    "business_canvas": "canvas_bmc",
    "pestle_grid": "pestle_cells",
    "scorecard_balanced": "scorecard_grid",
    # chart / data
    "chart_insight": "chart_panel",
    "chart_callout_panel": "chart_panel",
    "waterfall_insight": "waterfall_bars",
    "venn_overlap": "venn_duo",
    "circle_segments": "ring_segments",
    "table": "data_table",
    "appendix_table": "data_table",
    "results_table_insight": "data_table",
    "finance_statement": "finance_grid",
    # long-tail
    "mindmap_branches": "mindmap_radial",
    "calendar_heatmap": "calendar_grid",
    "case_study_band": "case_band",
    "project_status_rag": "rag_status",
    "geo_callout": "geo_pins",
    "device_frame": "device_chrome",
    "logo_strip": "logo_band",
    "image_full": "image_stage",
    "image_text_2col": "image_stage",
    "consort_flow": "consort_spine",
    "forest_plot": "forest_ci",
    "kaplan_meier": "km_curve",
    "study_design": "study_box",
    "multi_panel_figure": "multi_panel",
    "freeform": "freeform_stage",
}

# Motifs with dedicated builders in motif.py / motifs.structural
CUSTOM_MOTIF_IDS: frozenset[str] = frozenset({
    "sparse_hero", "split_hero", "card_row", "kpi_band", "kpi_hero",
    "step_rail", "funnel_cascade", "matrix_quad", "stair_ascent",
    "check_stack", "tile_row", "section_mark", "org_cascade", "chevron_flow",
    # structural pack
    "hub_orbit", "pyramid_stack", "iceberg_depth", "pillar_band",
    "timeline_rail", "swimlane_roadmap", "gantt_track", "pipeline_rail",
    "journey_path", "team_cards", "persona_split", "pricing_tiers",
    "kpi_grid", "stat_row", "scale_meter", "agenda_list", "quote_mark",
    "bullet_stack", "close_mark", "section_wash", "canvas_bmc",
    "pestle_cells", "scorecard_grid", "risk_heat", "raci_grid",
    "empathy_quad", "hex_honey", "mindmap_radial", "venn_duo",
    "ring_segments", "fishbone_spine", "framework_bar", "vs_columns",
    "rich_matrix", "okr_tree", "case_band", "rag_status", "calendar_grid",
    "logo_band", "geo_pins", "device_chrome",
})

# Motifs that delegate to recipe implementation (complex chart/table/domain)
RECIPE_BACKED_MOTIFS: dict[str, str] = {
    "chart_panel": "chart_insight",
    "waterfall_bars": "waterfall_insight",
    "data_table": "table",
    "finance_grid": "finance_statement",
    "image_stage": "image_text_2col",
    "consort_spine": "consort_flow",
    "forest_ci": "forest_plot",
    "km_curve": "kaplan_meier",
    "study_box": "study_design",
    "multi_panel": "multi_panel_figure",
    "freeform_stage": "freeform",
}


def all_motif_ids() -> list[str]:
    ids = set(RECIPE_TO_MOTIF.values())
    for mids in FAMILY_MOTIFS.values():
        ids.update(mids)
    ids.update(CUSTOM_MOTIF_IDS)
    ids.update(RECIPE_BACKED_MOTIFS)
    return sorted(ids)


def motif_catalog_entries() -> list[dict]:
    """Build catalog motif records from the coverage map."""
    reverse: dict[str, list[str]] = {}
    for recipe, mid in RECIPE_TO_MOTIF.items():
        reverse.setdefault(mid, []).append(recipe)

    family_of: dict[str, list[str]] = {}
    for fam, mids in FAMILY_MOTIFS.items():
        for mid in mids:
            family_of.setdefault(mid, []).append(fam)

    role_guess = {
        "sparse_hero": "cover_hero",
        "section_mark": "section_opener",
        "section_wash": "section_divider",
        "kpi_band": "metric_band",
        "kpi_hero": "single_metric_hero",
        "kpi_grid": "metric_dashboard",
        "step_rail": "process_steps",
        "funnel_cascade": "funnel",
        "chevron_flow": "chevron_process",
        "hub_orbit": "cycle_hub",
        "org_cascade": "org_hierarchy",
        "matrix_quad": "2x2_matrix",
        "timeline_rail": "timeline",
        "pyramid_stack": "pyramid",
        "card_row": "card_row_n",
    }

    entries = []
    for mid in all_motif_ids():
        recipes = reverse.get(mid) or (
            [RECIPE_BACKED_MOTIFS[mid]] if mid in RECIPE_BACKED_MOTIFS else []
        )
        entries.append({
            "id": mid,
            "role": role_guess.get(mid, mid),
            "ref_hints": [],
            "infograpify_families": family_of.get(mid, ["other"]),
            "slots": ["title", "…"],
            "chrome": ["stage_metrics"],
            "recipes": recipes,
            "builder": (
                "custom" if mid in CUSTOM_MOTIF_IDS
                else "recipe_adapter" if mid in RECIPE_BACKED_MOTIFS
                else "custom"
            ),
        })
    return entries
