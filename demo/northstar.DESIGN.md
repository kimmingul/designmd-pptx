---
version: alpha
name: Northstar-Board-Flagship
description: "Series B board showcase — deep indigo stage, multi-hue accent system (violet / cyan / magenta / lime / amber). Original tokens, not a vendor template. Tuned for a colorful 20-slide motif narrative."

colors:
  # Stage — deep indigo, not pure black (reads richer under color chrome)
  canvas: "#0B0B1A"
  surface-1: "#16162E"
  surface-2: "#22224A"
  # Primary action / hero accent
  primary: "#7C5CFF"
  on-primary: "#FFFFFF"
  ink: "#F4F2FF"
  ink-muted: "#A8A3C7"
  hairline: "#3A3570"
  # Semantic (used by RAG / risk / success)
  semantic-success: "#3DDC97"
  semantic-danger: "#FF4D6D"
  semantic-warning: "#FFB020"
  # Optional cover gradient (officecli start-end-angle)
  gradient: "0B0B1A-2A145A-135"

typography:
  # Use pt (not px) so sizes map 1:1 into PowerPoint points.
  display-xl:
    fontFamily: "Helvetica Neue, Arial, sans-serif"
    fontSize: 48pt
    fontWeight: 700
  headline:
    fontFamily: "Helvetica Neue, Arial, sans-serif"
    fontSize: 36pt
    fontWeight: 600
  body:
    fontFamily: "Helvetica Neue, Arial, sans-serif"
    fontSize: 18pt
  caption:
    fontFamily: "Helvetica Neue, Arial, sans-serif"
    fontSize: 14pt

rounded:
  md: 14px
  lg: 20px

spacing:
  md: 24px
  lg: 36px

composition:
  whitespace_density: spacious
  title_placement: left

charts:
  default_style: modern
  # Multi-hue series — also mapped into chart_series1/2/3 for motif chrome
  series_colors:
    - "#7C5CFF"   # violet
    - "#22D3EE"   # cyan
    - "#F472B6"   # pink
    - "#3DDC97"   # mint
    - "#FFB020"   # amber
    - "#60A5FA"   # sky
---

## Overview

**Northstar AI** board narrative with a **colorful motif chrome** system:
violet primary, cyan / pink / mint / amber series for cards, steps, KPIs,
and heat. Surfaces stay deep indigo so type stays readable. Short titles,
few cards, intentional empty space.
