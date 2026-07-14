---
version: alpha
name: Premium-Consulting
description: "Original premium consulting aesthetic for Phase 2 visual excellence. Inspired by structural principles from licensed reference research (card bands, KPI scale, compact dashboard density) — not a copy of any vendor template."

colors:
  canvas: "#0B1220"
  surface-1: "#141C2B"
  surface-2: "#1C2740"
  primary: "#3B82F6"
  on-primary: "#FFFFFF"
  ink: "#F8FAFC"
  ink-muted: "#94A3B8"
  hairline: "#243047"
  semantic-success: "#22C55E"
  semantic-danger: "#F43F5E"
  semantic-warning: "#F59E0B"

typography:
  display-xl:
    fontFamily: Arial, sans-serif
    fontSize: 56px
    fontWeight: 700
  headline:
    fontFamily: Arial, sans-serif
    fontSize: 32px
    fontWeight: 600
  body:
    fontFamily: Calibri, sans-serif
    fontSize: 16px
  caption:
    fontFamily: Calibri, sans-serif
    fontSize: 12px

rounded:
  md: 10px
  lg: 14px

spacing:
  md: 14px
  lg: 20px

composition:
  whitespace_density: compact
  title_placement: top

charts:
  default_style: modern
  series_colors:
    - "#3B82F6"
    - "#22C55E"
    - "#F59E0B"
    - "#A78BFA"
    - "#F43F5E"

tables:
  header_style: filled
  cell_padding_cm: 0.12
  stripe: true

images:
  crop_mode: fill
  placement: auto

master:
  footer: ""
  page_number: true
  navigation: false
---

## Overview

Dark-canvas, single blue accent, compact density. Tuned for executive KPI
dashboards, roadmaps, and comparison scorecards. Pair with Phase 2 premium
recipes (`kpi_dashboard_grid`, `story_timeline`, …) as they land.

## Usage

```bash
python -m designmd_pptx scaffold python/fixtures/premium-consulting.DESIGN.md \
  -o out/premium --content python/examples/content.deck.json
```

When no OfficeCLI is available, compile-only still validates tokens:

```bash
python -m designmd_pptx compile python/fixtures/premium-consulting.DESIGN.md -o out/premium-tokens.json
```
