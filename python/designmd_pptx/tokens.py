"""Slide token model, contrast floors, type floors, provenance."""

from __future__ import annotations

import colorsys
import re
from typing import Any, Literal

from .colors_parse import collect_css_vars, normalize_color_value, parse_gradient

# Standard 16:9 widescreen used by officecli-pptx skill
CANVAS_W_CM = 33.87
CANVAS_H_CM = 19.05
MARGIN_CM = 1.27
GAP_CM = 0.76

# officecli-pptx deliverable floors
TITLE_PT_MIN = 36
BODY_PT_MIN = 18
SECTION_PT_MIN = 20
KPI_PT_DEFAULT = 60
CAPTION_PT_MAX = 12
# Chips / KPI sublabels: officecli-pptx allows ≤5-word KPI sublabels below 18pt
MICRO_PT_DEFAULT = 14
MICRO_PT_MIN = 12
MICRO_PT_MAX = 16

SourceKind = Literal["sourced", "heuristic", "fallback"]

# Brand-neutral fallbacks — NEVER another product's signature hex (no Linear lavender).
NEUTRAL = {
    "background_light": "FFFFFF",
    "background_dark": "121212",
    "surface_light": "F5F7FA",
    "surface_dark": "1E1E1E",
    "surface_elevated_light": "EEEEEE",
    "surface_elevated_dark": "2A2A2A",
    "accent": "4A5568",  # neutral slate
    "text_light_bg": "333333",
    "text_dark_bg": "F5F5F5",
    "muted_light_bg": "6B7B8D",
    "muted_dark_bg": "A0A6B0",
    "hairline_light": "D0D5DD",
    "hairline_dark": "3A3A3A",
    "success": "2F9E44",
    "risk": "C92A2A",
}


def normalize_hex(
    value: Any,
    *,
    var_map: dict[str, str] | None = None,
    diagnostics: list[str] | None = None,
    path: str = "color",
) -> str | None:
    """Return RRGGBB uppercase without #, or None. Accepts #hex, rgb(), hsl(), oklch, vars."""
    return normalize_color_value(
        value, var_map=var_map, diagnostics=diagnostics, path=path
    )


def hex_brightness(hex6: str) -> float:
    """Relative luminance proxy 0–100 (perceived brightness)."""
    r = int(hex6[0:2], 16) / 255.0
    g = int(hex6[2:4], 16) / 255.0
    b = int(hex6[4:6], 16) / 255.0

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return L * 100.0


def is_dark(hex6: str, threshold: float = 30.0) -> bool:
    return hex_brightness(hex6) < threshold


def hex_saturation(hex6: str) -> float:
    r = int(hex6[0:2], 16) / 255.0
    g = int(hex6[2:4], 16) / 255.0
    b = int(hex6[4:6], 16) / 255.0
    _h, s, _v = colorsys.rgb_to_hsv(r, g, b)
    return s


def shift_hex(hex6: str, *, sat_scale: float = 0.45, val_delta: float = 0.18) -> str:
    """Derive a secondary chart color from accent (desaturate + lift/dim)."""
    r = int(hex6[0:2], 16) / 255.0
    g = int(hex6[2:4], 16) / 255.0
    b = int(hex6[4:6], 16) / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = max(0.0, min(1.0, s * sat_scale))
    if is_dark(hex6):
        v = min(1.0, v + val_delta)
    else:
        v = max(0.15, v - val_delta * 0.5)
    rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
    return f"{int(rr * 255):02X}{int(gg * 255):02X}{int(bb * 255):02X}"


def contrast_text_on(fill_hex: str, preferred: str | None = None) -> str:
    """
    Pick a readable text color for a solid fill.
    Dark fills (<30% brightness) → light text; else dark text.
    """
    fill = normalize_hex(fill_hex) or "FFFFFF"
    if is_dark(fill):
        pref = normalize_hex(preferred)
        if pref and hex_brightness(pref) >= 80:
            return pref
        return "FFFFFF"
    pref = normalize_hex(preferred)
    if pref and hex_brightness(pref) <= 45:
        return pref
    return "333333"


def parse_length(value: Any) -> tuple[float, str] | None:
    """
    Parse a CSS-ish length. Returns (number, unit) where unit is 'px'|'pt'|'raw'.
    'raw' means unitless number — treated as px for DESIGN.md fontSize (Stitch convention).
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value), "raw"
    s = str(value).strip().lower()
    m = re.match(r"^([\d.]+)\s*px$", s)
    if m:
        return float(m.group(1)), "px"
    m = re.match(r"^([\d.]+)\s*pt$", s)
    if m:
        return float(m.group(1)), "pt"
    m = re.match(r"^([\d.]+)\s*rem$", s)
    if m:
        return float(m.group(1)) * 16.0, "px"
    try:
        return float(s), "raw"
    except ValueError:
        return None


def parse_px(value: Any) -> float | None:
    """Legacy helper: numeric magnitude only (prefer to_pt)."""
    parsed = parse_length(value)
    return parsed[0] if parsed else None


def to_pt(value: Any) -> float | None:
    """Unit-aware conversion to PowerPoint points."""
    parsed = parse_length(value)
    if not parsed:
        return None
    n, unit = parsed
    if unit == "pt":
        return n
    # px, rem→px, and unitless DESIGN.md fontSize: CSS px @ 96dpi → pt
    return n * 0.75


def px_to_pt(px: float) -> float:
    """CSS px → approximate PPT pt (96dpi: 1px = 0.75pt)."""
    return px * 0.75


def floor_title_pt(pt: float | None) -> int:
    if pt is None:
        return 40
    return max(TITLE_PT_MIN, int(round(pt)))


def floor_body_pt(pt: float | None) -> int:
    if pt is None:
        return BODY_PT_MIN
    return max(BODY_PT_MIN, int(round(pt)))


def pick_color_raw(colors: dict, *keys: str) -> Any | None:
    lower_map = {str(k).lower(): v for k, v in colors.items()}
    for k in keys:
        if k in colors:
            return colors[k]
        if k.lower() in lower_map:
            return lower_map[k.lower()]
    return None


def pick_color(
    colors: dict,
    *keys: str,
    var_map: dict[str, str] | None = None,
    diagnostics: list[str] | None = None,
) -> str | None:
    for k in keys:
        if k in colors:
            h = normalize_hex(
                colors[k], var_map=var_map, diagnostics=diagnostics, path=f"colors.{k}"
            )
            if h:
                return h
    lower_map = {str(k).lower(): v for k, v in colors.items()}
    for k in keys:
        if k.lower() in lower_map:
            h = normalize_hex(
                lower_map[k.lower()],
                var_map=var_map,
                diagnostics=diagnostics,
                path=f"colors.{k}",
            )
            if h:
                return h
    return None


def all_hex_from_colors(
    colors: dict,
    *,
    var_map: dict[str, str] | None = None,
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for k, v in colors.items():
        h = normalize_hex(v, var_map=var_map)
        if h:
            out.append((str(k), h))
    return out


def heuristic_roles(
    colors: dict,
    *,
    var_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    When synonym keys miss, assign roles by geometry in color space:
    darkest → canvas candidate, lightest → ink-on-dark or inverse,
    most saturated → accent.
    """
    pairs = all_hex_from_colors(colors, var_map=var_map)
    if not pairs:
        return {}
    by_bright = sorted(pairs, key=lambda kv: hex_brightness(kv[1]))
    by_sat = sorted(pairs, key=lambda kv: hex_saturation(kv[1]), reverse=True)
    roles: dict[str, str] = {}
    darkest = by_bright[0][1]
    lightest = by_bright[-1][1]
    roles["canvas"] = darkest
    roles["ink"] = lightest if is_dark(darkest) else darkest
    # accent: most saturated that isn't nearly pure gray
    for _k, h in by_sat:
        if hex_saturation(h) >= 0.12 and h not in (darkest,):
            roles["primary"] = h
            break
    if "primary" not in roles and by_sat:
        roles["primary"] = by_sat[0][1]
    # mid surfaces: second-darkest if available
    if len(by_bright) >= 2:
        roles["surface-1"] = by_bright[1][1]
    return roles


def _record(
    provenance: dict[str, str],
    role: str,
    value: str,
    source: SourceKind,
) -> str:
    provenance[role] = source
    return value


def extract_semantic_colors(
    colors: dict,
    *,
    body: str = "",
    var_map: dict[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, str], list[str], dict[str, Any]]:
    """
    Collapse DESIGN.md color soup into a minimal slide palette.

    Returns (palette, provenance, warnings, extras).
    provenance values: sourced | heuristic | fallback | derived | resolved_var
    extras may include background_gradient (officecli form).
    """
    warnings: list[str] = []
    provenance: dict[str, str] = {}
    diag: list[str] = []
    vmap = var_map if var_map is not None else collect_css_vars(colors, body)

    def pc(*keys: str) -> str | None:
        return pick_color(colors, *keys, var_map=vmap, diagnostics=diag)

    background = pc("canvas", "background", "bg", "page", "surface-0", "bg-canvas")
    surface = pc("surface-1", "surface1", "card", "panel", "elevated", "bg-level-1")
    surface_elevated = pc("surface-2", "surface2", "surface-3", "bg-level-2", "bg-level-3")
    accent = pc("primary", "brand", "accent", "brand-primary", "cta", "brand-color")
    text = pc("ink", "text", "foreground", "fg", "on-canvas", "on-background", "text-primary")
    # Do NOT include "secondary" — often a chromatic brand secondary, not muted text
    muted = pc("ink-muted", "ink-subtle", "muted", "text-muted", "ink-tertiary", "text-secondary")
    on_accent = pc("on-primary", "on-accent", "primary-foreground")
    hairline = pc("hairline", "border", "hairline-strong", "line", "divider", "border-color")
    success = pc("semantic-success", "success", "positive", "green")
    risk = pc("semantic-danger", "danger", "error", "risk", "negative")
    _inverse = pc("inverse-canvas", "inverse")

    # Heuristic fill for missing roles
    heur = heuristic_roles(colors, var_map=vmap) if colors else {}
    if not background and "canvas" in heur:
        background = heur["canvas"]
        provenance["background"] = "heuristic"
        warnings.append("background: assigned via luminance heuristic (no canvas/background key)")
    if not accent and "primary" in heur:
        accent = heur["primary"]
        provenance["accent"] = "heuristic"
        warnings.append("accent: assigned via saturation heuristic (no primary/accent key)")
    if not text and "ink" in heur:
        text = heur["ink"]
        provenance["text_source"] = "heuristic"
        warnings.append("text: assigned via luminance heuristic (no ink/text key)")
    if not surface and "surface-1" in heur:
        surface = heur["surface-1"]
        provenance["surface"] = "heuristic"
        warnings.append("surface: assigned via luminance heuristic")

    # Neutral fallbacks
    if background:
        if "background" not in provenance:
            provenance["background"] = "sourced"
    else:
        background = NEUTRAL["background_light"]
        provenance["background"] = "fallback"
        warnings.append("background: neutral fallback (FFFFFF) — DESIGN.md had no canvas color")

    dark = is_dark(background)

    if surface:
        if "surface" not in provenance:
            provenance["surface"] = "sourced"
    else:
        surface = NEUTRAL["surface_dark"] if dark else NEUTRAL["surface_light"]
        provenance["surface"] = "fallback"
        warnings.append(f"surface: neutral fallback ({surface})")

    if surface_elevated:
        provenance["surface_elevated"] = "sourced"
    else:
        surface_elevated = (
            NEUTRAL["surface_elevated_dark"] if dark else NEUTRAL["surface_elevated_light"]
        )
        provenance["surface_elevated"] = "fallback"

    if accent:
        if "accent" not in provenance:
            provenance["accent"] = "sourced"
    else:
        accent = NEUTRAL["accent"]
        provenance["accent"] = "fallback"
        warnings.append("accent: neutral slate fallback — no primary/accent in DESIGN.md")

    if text:
        if "text_source" not in provenance:
            provenance["text_source"] = "sourced"
    else:
        text = NEUTRAL["text_dark_bg"] if dark else NEUTRAL["text_light_bg"]
        provenance["text_source"] = "fallback"
        warnings.append("text: neutral fallback")

    if muted:
        provenance["muted"] = "sourced"
    else:
        muted = NEUTRAL["muted_dark_bg"] if dark else NEUTRAL["muted_light_bg"]
        provenance["muted"] = "fallback"

    if on_accent:
        provenance["on_accent"] = "sourced"
        on_accent_val = on_accent
    else:
        on_accent_val = contrast_text_on(accent)
        provenance["on_accent"] = "fallback"

    if hairline:
        provenance["hairline"] = "sourced"
    else:
        hairline = NEUTRAL["hairline_dark"] if dark else NEUTRAL["hairline_light"]
        provenance["hairline"] = "fallback"

    if success:
        provenance["success"] = "sourced"
    else:
        success = NEUTRAL["success"]
        provenance["success"] = "fallback"
        warnings.append("success: neutral fallback (no semantic-success key)")

    if risk:
        provenance["risk"] = "sourced"
    else:
        risk = NEUTRAL["risk"]
        provenance["risk"] = "fallback"
        warnings.append("risk: neutral fallback (no danger/error key)")

    # Content slides share brand canvas (dark-first brands stay dark).
    content_bg = background
    provenance["content_background"] = provenance["background"]

    text_on_bg = contrast_text_on(background, text)
    text_on_surface = contrast_text_on(surface, text)
    text_on_content = contrast_text_on(content_bg, text)
    provenance["text"] = "derived"
    provenance["text_on_surface"] = "derived"
    provenance["text_on_content"] = "derived"

    muted_on_bg = muted
    if abs(hex_brightness(muted_on_bg) - hex_brightness(background)) <= 25:
        muted_on_bg = NEUTRAL["muted_dark_bg"] if dark else NEUTRAL["muted_light_bg"]
        provenance["muted"] = "fallback"
        warnings.append("muted: contrast-corrected against background")
    if dark and hex_brightness(muted_on_bg) < 40:
        muted_on_bg = NEUTRAL["muted_dark_bg"]
    if not dark and hex_brightness(muted_on_bg) > 70:
        muted_on_bg = NEUTRAL["muted_light_bg"]

    series2 = shift_hex(accent)
    # Ensure series2 differs enough from series1 and bg
    if abs(hex_brightness(series2) - hex_brightness(accent)) < 8:
        series2 = shift_hex(accent, sat_scale=0.35, val_delta=0.28)
    if abs(hex_brightness(series2) - hex_brightness(content_bg)) < 12:
        series2 = NEUTRAL["muted_dark_bg"] if not dark else "CADCFC"
        warnings.append("chart_series2: adjusted for contrast vs content background")
    provenance["chart_series1"] = provenance.get("accent", "sourced")
    provenance["chart_series2"] = "derived"
    provenance["chart_series3"] = provenance.get("success", "fallback")

    # Optional brand gradient for covers (officecli: start-end-angle)
    gradient_raw = pick_color_raw(colors, "gradient", "background-gradient", "hero-gradient")
    gdiag: list[str] = []
    background_gradient = (
        parse_gradient(gradient_raw, var_map=vmap, diagnostics=gdiag) if gradient_raw else None
    )
    warnings.extend(gdiag)
    if background_gradient:
        provenance["background_gradient"] = "sourced"
    else:
        background_gradient = None

    # mark resolved_var when diagnostics mention var resolution success paths
    for d in diag:
        if "unresolved" in d or "approximated" in d or "fallback" in d or "color-mix" in d or "oklch" in d:
            warnings.append(d)
        elif "->" in d:
            warnings.append(d)

    palette = {
        "background": background,
        "content_background": content_bg,
        "surface": surface,
        "surface_elevated": surface_elevated,
        "accent": accent,
        "on_accent": on_accent_val,
        "text": text_on_bg,
        "text_on_surface": text_on_surface,
        "text_on_content": text_on_content,
        "muted": muted_on_bg,
        "hairline": hairline,
        "success": success,
        "risk": risk,
        "chart_series1": accent,
        "chart_series2": series2,
        "chart_series3": success,
    }
    extras = {"background_gradient": background_gradient}
    return palette, provenance, warnings, extras


def extract_type_sizes(typography: dict) -> tuple[dict[str, int], list[str]]:
    warnings: list[str] = []

    def size_for(*keys: str) -> float | None:
        for k in keys:
            node = typography.get(k)
            if isinstance(node, dict):
                pt = to_pt(node.get("fontSize"))
                if pt is not None:
                    return pt
            elif node is not None:
                pt = to_pt(node)
                if pt is not None:
                    return pt
        return None

    display = size_for("display-xl", "display-lg", "display-md", "display", "h1")
    headline = size_for("headline", "card-title", "h2", "title")
    body = size_for("body-lg", "body", "body-sm", "text")
    caption = size_for("caption", "eyebrow", "label")
    button = size_for("button")

    if display is None and not typography:
        warnings.append("typography: empty — using officecli floors only")

    cover = floor_title_pt(display if display is not None else 44)
    cover = min(cover, 52)
    title = floor_title_pt(headline if headline is not None else 40)
    title = min(title, 44)
    body_pt = floor_body_pt(body if body is not None else BODY_PT_MIN)
    body_pt = min(body_pt, 22)
    caption_pt = int(round(caption)) if caption is not None else CAPTION_PT_MAX
    caption_pt = max(10, min(CAPTION_PT_MAX, caption_pt))
    # micro: chips / KPI sublabels — allowed slightly under body floor (officecli KPI exception)
    micro_src = button if button is not None else (caption if caption is not None else MICRO_PT_DEFAULT)
    micro_pt = int(round(micro_src))
    micro_pt = max(MICRO_PT_MIN, min(MICRO_PT_MAX, micro_pt))
    section = max(SECTION_PT_MIN, min(28, title - 8))

    return {
        "cover_pt": cover,
        "title_pt": title,
        "section_pt": section,
        "body_pt": body_pt,
        "caption_pt": caption_pt,
        "micro_pt": micro_pt,
        "kpi_pt": KPI_PT_DEFAULT,
    }, warnings


def motif_from_atmosphere(colors: dict[str, str], description: str = "") -> str:
    bg = colors["background"]
    if is_dark(bg):
        return "hairline-card-on-dark"
    if description and "editorial" in description.lower():
        return "serif-editorial-band"
    return "solid-surface-cards"


DROPPED_WEB_CONCERNS = [
    "hover",
    "focus",
    "breakpoints",
    "responsive",
    "nav",
    "inputs",
    "forms",
    "touch-targets",
    "scroll",
    "z-index-stacking-beyond-shapes",
    "css-gradients-as-background-unless-officecli-gradient-prop",
]
