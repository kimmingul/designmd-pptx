"""Parse CSS-like colors → RRGGBB or officecli gradient strings (v1.1)."""

from __future__ import annotations

import colorsys
import math
import re
from typing import Any


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return (
        f"{int(round(clamp01(r) * 255)):02X}"
        f"{int(round(clamp01(g) * 255)):02X}"
        f"{int(round(clamp01(b) * 255)):02X}"
    )


def parse_number_component(s: str, *, percent_of: float = 255.0) -> float | None:
    s = s.strip()
    if s.endswith("%"):
        try:
            return clamp01(float(s[:-1]) / 100.0)
        except ValueError:
            return None
    try:
        v = float(s)
    except ValueError:
        return None
    if percent_of == 255.0 and v > 1.0:
        return clamp01(v / 255.0)
    if percent_of == 1.0 and v > 1.0 and not s.endswith("%"):
        # bare 50 in hsl sat often means 50%
        if v <= 100:
            return clamp01(v / 100.0)
    return clamp01(v)


def _parse_hue_to_turn(h: str) -> float | None:
    h = h.strip().lower()
    try:
        if h.endswith("turn"):
            return float(h[:-4]) % 1.0
        if h.endswith("rad"):
            return (float(h[:-3]) / (2 * math.pi)) % 1.0
        if h.endswith("deg"):
            return (float(h[:-3]) % 360) / 360.0
        return (float(h) % 360) / 360.0
    except ValueError:
        return None


def oklch_to_srgb(L: float, C: float, h_deg: float) -> tuple[float, float, float]:
    """
    Approximate OKLCH → sRGB (CSS Color 4). Not bit-identical to all browsers;
    good enough for slide brand tokens. Returns linear-ish sRGB 0–1 after clip.
    """
    h = math.radians(h_deg)
    a = C * math.cos(h)
    b = C * math.sin(h)
    # OKLab → LMS
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l = l_ * l_ * l_
    m = m_ * m_ * m_
    s = s_ * s_ * s_
    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    def compand(c: float) -> float:
        c = max(0.0, min(1.0, c))
        if c <= 0.0031308:
            return 12.92 * c
        return 1.055 * (c ** (1 / 2.4)) - 0.055

    return compand(r), compand(g), compand(bl)


def collect_css_vars(
    colors: dict[str, Any] | None = None,
    body: str = "",
) -> dict[str, str]:
    """
    Build --name → raw value map from DESIGN.md colors + CSS custom properties in body.

    Explicit `--token` keys win. Semantic keys (primary, canvas, …) are exposed as
    `--primary` only when that name is not already defined — avoids
    canvas: var(--canvas) overwriting --canvas: #hex and creating a cycle.
    """
    out: dict[str, str] = {}
    if colors:
        # Pass 1: explicit custom properties
        for k, v in colors.items():
            key = str(k).strip()
            if key.startswith("--"):
                out[key] = str(v).strip()
        # Pass 2: semantic aliases without clobbering explicit --tokens
        for k, v in colors.items():
            key = str(k).strip()
            if key.startswith("--"):
                continue
            raw = str(v).strip()
            # Skip pure self-var indirection as alias source (useless / cyclic)
            if re.fullmatch(rf"var\(\s*--{re.escape(key)}\s*(?:,[^)]+)?\)", raw, re.I):
                continue
            for alias in (f"--{key}", f"--color-{key}"):
                if alias not in out:
                    out[alias] = raw
    if body:
        for m in re.finditer(
            r"(--[a-zA-Z0-9_-]+)\s*:\s*([^;}\n]+)",
            body,
        ):
            name = m.group(1)
            # body custom props fill gaps only (frontmatter wins)
            if name not in out:
                out[name] = m.group(2).strip()
    return out


def resolve_var_reference(
    value: str,
    var_map: dict[str, str],
    *,
    diagnostics: list[str] | None = None,
    depth: int = 0,
    path: str = "color",
) -> str | None:
    """
    Resolve var(--name) and var(--name, fallback). Returns resolved raw string or None.
    """
    if diagnostics is None:
        diagnostics = []
    if depth > 12:
        diagnostics.append(f"{path}: CSS var resolution depth exceeded (cycle?)")
        return None
    s = value.strip()
    # var(--name) or var(--name, fallback)
    m = re.fullmatch(
        r"var\(\s*(--[a-zA-Z0-9_-]+)\s*(?:,\s*(.+))?\s*\)",
        s,
        re.I | re.S,
    )
    if not m:
        return s
    name = m.group(1)
    fallback = m.group(2)
    if name in var_map:
        nxt = var_map[name].strip()
        # self-reference cycle: var(--x) where --x is var(--x)
        if re.fullmatch(rf"var\(\s*{re.escape(name)}\s*(?:,[^)]+)?\)", nxt, re.I):
            diagnostics.append(f"{path}: cyclic CSS variable {name}")
            if fallback is not None:
                return resolve_var_reference(
                    fallback.strip(),
                    var_map,
                    diagnostics=diagnostics,
                    depth=depth + 1,
                    path=f"{path}->{name}-fallback",
                )
            return None
        return resolve_var_reference(
            nxt,
            var_map,
            diagnostics=diagnostics,
            depth=depth + 1,
            path=f"{path}->{name}",
        )
    if fallback is not None:
        diagnostics.append(f"{path}: unresolved {name}, using fallback")
        return resolve_var_reference(
            fallback.strip(),
            var_map,
            diagnostics=diagnostics,
            depth=depth + 1,
            path=f"{path}->{name}-fallback",
        )
    diagnostics.append(f"{path}: unresolved CSS variable {name} (no fallback)")
    return None


_NAMED = {
    "white": "FFFFFF",
    "black": "000000",
    "transparent": "FFFFFF",
    "red": "FF0000",
    "green": "008000",
    "blue": "0000FF",
    "gray": "808080",
    "grey": "808080",
}


def _split_top_level(s: str, sep: str = ",") -> list[str]:
    """Split on sep not inside parentheses."""
    parts: list[str] = []
    depth = 0
    cur: list[str] = []
    for ch in s:
        if ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            cur.append(ch)
        elif ch == sep and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur).strip())
    return [p for p in parts if p]


def _extract_function_args(s: str, fname: str) -> str | None:
    """Return inside of fname(...) with nested paren support."""
    m = re.search(rf"{fname}\s*\(", s, re.I)
    if not m:
        return None
    i = m.end()
    depth = 1
    start = i
    while i < len(s) and depth:
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return s[start : i - 1]


def parse_css_color(
    value: Any,
    *,
    var_map: dict[str, str] | None = None,
    diagnostics: list[str] | None = None,
    path: str = "color",
) -> str | None:
    """
    Return RRGGBB uppercase without #, or None.
    Supports: #RGB/#RRGGBB/#RRGGBBAA, rgb/rgba (comma or space), hsl/hsla,
    oklch(), color-mix(in srgb, ...), var(--x) / var(--x, fallback), named colors.
    """
    if diagnostics is None:
        diagnostics = []
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.startswith("{"):
        return None

    if var_map is not None or s.lower().startswith("var("):
        resolved = resolve_var_reference(
            s, var_map or {}, diagnostics=diagnostics, path=path
        )
        if resolved is None:
            return None
        if resolved != s:
            return parse_css_color(
                resolved, var_map=var_map, diagnostics=diagnostics, path=path
            )
        s = resolved

    named = _NAMED.get(s.lower())
    if named:
        return named

    # hex
    if s.startswith("#"):
        h = s[1:]
        if re.fullmatch(r"[0-9A-Fa-f]{3}", h):
            return "".join(c * 2 for c in h).upper()
        if re.fullmatch(r"[0-9A-Fa-f]{4}", h):
            return "".join(c * 2 for c in h[:3]).upper()
        if re.fullmatch(r"[0-9A-Fa-f]{6}", h):
            return h.upper()
        if re.fullmatch(r"[0-9A-Fa-f]{8}", h):
            return h[:6].upper()
        return None

    if re.fullmatch(r"[0-9A-Fa-f]{6}", s):
        return s.upper()
    if re.fullmatch(r"[0-9A-Fa-f]{3}", s):
        return "".join(c * 2 for c in s).upper()

    low = re.sub(r"\s+", " ", s.lower().strip())

    # color-mix(in srgb, c1 p%, c2)
    mix_inner = _extract_function_args(s, "color-mix")
    if mix_inner is not None:
        mix_low = re.sub(r"\s+", " ", mix_inner.strip())
        mm = re.match(
            r"in\s+(?:srgb|srgb-linear|display-p3)\s*,\s*(.+)$",
            mix_low,
            re.I,
        )
        if mm:
            parts = _split_top_level(mm.group(1))
            if len(parts) >= 2:

                def split_color_pct(part: str) -> tuple[str, float | None]:
                    pm = re.match(r"(.+?)\s+(\d+(?:\.\d+)?)%\s*$", part.strip())
                    if pm:
                        return pm.group(1).strip(), float(pm.group(2)) / 100.0
                    return part.strip(), None

                c1s, p1 = split_color_pct(parts[0])
                c2s, p2 = split_color_pct(parts[1])
                if p1 is None and p2 is None:
                    p1, p2 = 0.5, 0.5
                elif p1 is None and p2 is not None:
                    p1 = 1.0 - p2
                elif p2 is None and p1 is not None:
                    p2 = 1.0 - p1
                h1 = parse_css_color(
                    c1s, var_map=var_map, diagnostics=diagnostics, path=path
                )
                h2 = parse_css_color(
                    c2s, var_map=var_map, diagnostics=diagnostics, path=path
                )
                if h1 and h2 and p1 is not None:
                    t = p1
                    r = (int(h1[0:2], 16) * t + int(h2[0:2], 16) * (1 - t)) / 255.0
                    g = (int(h1[2:4], 16) * t + int(h2[2:4], 16) * (1 - t)) / 255.0
                    b = (int(h1[4:6], 16) * t + int(h2[4:6], 16) * (1 - t)) / 255.0
                    diagnostics.append(f"{path}: color-mix approximated in sRGB")
                    return rgb_to_hex(r, g, b)
        diagnostics.append(f"{path}: unparseable color-mix()")
        return None

    # oklch(L C H) or oklch(L C H / a)
    oklch_inner = _extract_function_args(s, "oklch")
    if oklch_inner is not None:
        m = re.fullmatch(
            r"\s*([\d.]+%?)\s+([\d.]+%?)\s+([-\d.]+(?:deg|rad|turn)?)\s*(?:/\s*[\d.%]+)?\s*",
            oklch_inner.replace(",", " "),
        )
        if m:
            L_raw = m.group(1)
            C_raw = m.group(2)
            H_raw = m.group(3)
            try:
                L = float(L_raw[:-1]) / 100.0 if L_raw.endswith("%") else float(L_raw)
                if L > 1.0:
                    L = L / 100.0
                C = float(C_raw[:-1]) / 100.0 if C_raw.endswith("%") else float(C_raw)
                ht = _parse_hue_to_turn(H_raw)
                if ht is None:
                    return None
                r, g, b = oklch_to_srgb(L, C, ht * 360.0)
                diagnostics.append(
                    f"{path}: oklch approximated to sRGB (not browser-identical)"
                )
                return rgb_to_hex(r, g, b)
            except ValueError:
                return None

    # rgb comma form
    compact = low.replace(" ", "")
    m = re.fullmatch(
        r"rgba?\((\d+%?|\d*\.?\d+%?),(\d+%?|\d*\.?\d+%?),(\d+%?|\d*\.?\d+%?)(?:,[\d.%]+)?\)",
        compact,
    )
    if m:
        r = parse_number_component(m.group(1))
        g = parse_number_component(m.group(2))
        b = parse_number_component(m.group(3))
        if None not in (r, g, b):
            return rgb_to_hex(r, g, b)  # type: ignore[arg-type]

    # rgb space / slash form: rgb(255 0 0 / 0.5)
    m = re.fullmatch(
        r"rgba?\(\s*(\d+%?|\d*\.?\d+%?)\s+(\d+%?|\d*\.?\d+%?)\s+(\d+%?|\d*\.?\d+%?)(?:\s*/\s*[\d.%]+)?\s*\)",
        low,
    )
    if m:
        r = parse_number_component(m.group(1))
        g = parse_number_component(m.group(2))
        b = parse_number_component(m.group(3))
        if None not in (r, g, b):
            return rgb_to_hex(r, g, b)  # type: ignore[arg-type]

    # hsl comma
    m = re.fullmatch(
        r"hsla?\(([-\d.]+(?:deg|rad|turn)?),(\d+%?|\d*\.?\d+%?),(\d+%?|\d*\.?\d+%?)(?:,[\d.%]+)?\)",
        compact,
    )
    if m:
        ht = _parse_hue_to_turn(m.group(1))
        sat = parse_number_component(m.group(2), percent_of=1.0)
        lig = parse_number_component(m.group(3), percent_of=1.0)
        if ht is None or sat is None or lig is None:
            return None
        r, g, b = colorsys.hls_to_rgb(ht, lig, sat)
        return rgb_to_hex(r, g, b)

    # hsl space form
    m = re.fullmatch(
        r"hsla?\(\s*([-\d.]+(?:deg|rad|turn)?)\s+(\d+%?|\d*\.?\d+%?)\s+(\d+%?|\d*\.?\d+%?)(?:\s*/\s*[\d.%]+)?\s*\)",
        low,
    )
    if m:
        ht = _parse_hue_to_turn(m.group(1))
        sat = parse_number_component(m.group(2), percent_of=1.0)
        lig = parse_number_component(m.group(3), percent_of=1.0)
        if ht is None or sat is None or lig is None:
            return None
        r, g, b = colorsys.hls_to_rgb(ht, lig, sat)
        return rgb_to_hex(r, g, b)

    return None


def parse_gradient(
    value: Any,
    *,
    var_map: dict[str, str] | None = None,
    diagnostics: list[str] | None = None,
) -> str | None:
    """
    Parse linear-gradient → officecli RRGGBB-RRGGBB-ANGLE.
    Multi-stop (>2 colors): uses first and last stop + warning.
    radial/conic: explicit diagnostic, returns None.
    """
    if diagnostics is None:
        diagnostics = []
    if value is None:
        return None
    s = str(value).strip()
    bare = s.replace("#", "")
    if re.fullmatch(r"[0-9A-Fa-f]{6}-[0-9A-Fa-f]{6}-\d{1,3}", bare, re.I):
        parts = bare.split("-")
        return f"{parts[0].upper()}-{parts[1].upper()}-{parts[2]}"

    if re.search(r"(radial|conic)-gradient\s*\(", s, re.I):
        diagnostics.append(
            "gradient: radial/conic-gradient not supported by officecli 2-stop linear; dropped"
        )
        return None

    inner = _extract_function_args(s, "linear-gradient")
    if inner is not None:
        # angle
        angle = 180
        am = re.match(r"\s*([-\d.]+)(deg|rad|turn)?\s*,\s*", inner, re.I)
        rest = inner
        if am:
            unit = (am.group(2) or "deg").lower()
            try:
                av = float(am.group(1))
                if unit == "rad":
                    angle = int(round(math.degrees(av))) % 360
                elif unit == "turn":
                    angle = int(round(av * 360)) % 360
                else:
                    angle = int(round(av)) % 360
            except ValueError:
                angle = 180
            rest = inner[am.end() :]
        stops = _split_top_level(rest)
        colors: list[str] = []
        for stop in stops:
            cm = re.match(r"(.+?)(?:\s+[\d.]+%)?$", stop.strip())
            raw = cm.group(1).strip() if cm else stop
            hx = parse_css_color(raw, var_map=var_map, diagnostics=diagnostics)
            if hx:
                colors.append(hx)
        if len(colors) >= 2:
            if len(colors) > 2:
                diagnostics.append(
                    f"gradient: multi-stop linear ({len(colors)} stops) → first/last only for officecli"
                )
            return f"{colors[0]}-{colors[-1]}-{angle}"
        diagnostics.append("gradient: linear-gradient needs ≥2 parseable color stops")
        return None

    m = re.search(
        r"(#[0-9A-Fa-f]{3,8}|rgb[a]?\([^)]+\)|oklch\([^)]+\)|var\([^)]+\))"
        r"\s*(?:→|->|to)\s*"
        r"(#[0-9A-Fa-f]{3,8}|rgb[a]?\([^)]+\)|oklch\([^)]+\)|var\([^)]+\))",
        s,
        re.I,
    )
    if m:
        c1 = parse_css_color(m.group(1), var_map=var_map, diagnostics=diagnostics)
        c2 = parse_css_color(m.group(2), var_map=var_map, diagnostics=diagnostics)
        if c1 and c2:
            return f"{c1}-{c2}-180"

    return None


def normalize_color_value(
    value: Any,
    *,
    var_map: dict[str, str] | None = None,
    diagnostics: list[str] | None = None,
    path: str = "color",
) -> str | None:
    """Solid RRGGBB only."""
    return parse_css_color(value, var_map=var_map, diagnostics=diagnostics, path=path)
