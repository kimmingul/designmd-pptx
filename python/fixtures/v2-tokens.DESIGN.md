---
name: V2 Demo
colors:
  primary: "#3B82F6"
  canvas: "#FFFFFF"
  ink: "#0F172A"
  accent: "#3B82F6"
  success: "#10B981"
composition:
  whitespace_density: spacious
  title_placement: left
charts:
  default_style: minimal
  series_colors: ["#3B82F6", "#10B981", "bogus", "#EF4444"]
tables:
  header_style: underline
  cell_padding_cm: 0.25
  stripe: false
images:
  crop_mode: fit
  placement: right
master:
  footer: "Confidential — V2 Demo"
  page_number: true
  navigation: false
---

## Overview

A deck exercising the v2 design-token sections (issue #11): composition, charts,
tables, images, and master. `bogus` in `series_colors` is intentionally invalid
and should be dropped with a warning.
