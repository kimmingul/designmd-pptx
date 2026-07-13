"""Proprietary / web font → PowerPoint-safe substitutes."""

from __future__ import annotations

# Order matters: first match wins (substring, case-insensitive).
_SUBSTITUTES: list[tuple[str, str]] = [
    # CJK first — these must match before generic families like "noto sans"
    ("pretendard", "Malgun Gothic"),
    ("noto sans kr", "Malgun Gothic"),
    ("noto serif kr", "Batang"),
    ("noto sans cjk kr", "Malgun Gothic"),
    ("nanum myeongjo", "Batang"),
    ("nanumsquare", "Malgun Gothic"),
    ("nanum", "Malgun Gothic"),
    ("spoqa han sans", "Malgun Gothic"),
    ("apple sd gothic", "Malgun Gothic"),
    ("malgun", "Malgun Gothic"),
    ("gulim", "Gulim"),
    ("dotum", "Dotum"),
    ("batang", "Batang"),
    ("noto sans jp", "Yu Gothic"),
    ("noto serif jp", "Yu Mincho"),
    ("hiragino", "Yu Gothic"),
    ("meiryo", "Meiryo"),
    ("yu gothic", "Yu Gothic"),
    ("noto sans sc", "Microsoft YaHei"),
    ("noto sans tc", "Microsoft JhengHei"),
    ("pingfang", "Microsoft YaHei"),
    ("microsoft yahei", "Microsoft YaHei"),
    ("source han", "Malgun Gothic"),
    ("linear display", "Arial"),
    ("linear text", "Calibri"),
    ("linear mono", "Consolas"),
    ("sf pro display", "Arial"),
    ("sf pro text", "Calibri"),
    ("sf pro", "Arial"),
    ("sf mono", "Consolas"),
    ("geist mono", "Consolas"),
    ("geist sans", "Arial"),
    ("geist", "Arial"),
    ("inter", "Arial"),
    ("ibm plex mono", "Consolas"),
    ("ibm plex sans", "Arial"),
    ("ibm plex", "Arial"),
    ("jetbrains mono", "Consolas"),
    ("fira code", "Consolas"),
    ("source code", "Consolas"),
    ("menlo", "Consolas"),
    ("monaco", "Consolas"),
    ("ui-monospace", "Consolas"),
    ("roboto mono", "Consolas"),
    ("roboto", "Arial"),
    ("helvetica neue", "Arial"),
    ("helvetica", "Arial"),
    ("system-ui", "Calibri"),
    ("-apple-system", "Calibri"),
    ("segoe ui", "Calibri"),
    ("noto sans", "Arial"),
    ("open sans", "Arial"),
    ("lato", "Calibri"),
    ("montserrat", "Arial"),
    ("poppins", "Arial"),
    ("dm sans", "Arial"),
    ("space grotesk", "Arial"),
    ("futura", "Arial"),
    ("avenir", "Calibri"),
    ("proxima", "Arial"),
    ("georgia", "Georgia"),
    ("garamond", "Garamond"),
    ("palatino", "Palatino"),
    ("cambria", "Cambria"),
    ("calibri", "Calibri"),
    ("arial black", "Arial Black"),
    ("arial", "Arial"),
    ("trebuchet", "Trebuchet MS"),
    ("impact", "Impact"),
    ("consolas", "Consolas"),
    ("courier", "Consolas"),
]


def substitute_font(name: str | None, role: str = "body") -> str:
    """Map a DESIGN.md font family string to a PPTX-safe face."""
    if not name or not str(name).strip():
        return "Georgia" if role == "heading" else "Calibri"

    raw = str(name).split(",")[0].strip().strip("\"'")
    low = raw.lower()

    for needle, face in _SUBSTITUTES:
        if needle in low:
            return face

    # Unknown custom name: role-based default (never ship a missing proprietary face).
    return "Arial" if role == "heading" else "Calibri"


def pair_from_typography(typography: dict) -> tuple[str, str, str, list[str]]:
    """
    Return (heading_font, body_font, mono_font, warnings) from DESIGN.md typography.
    """
    warnings: list[str] = []
    heading_src = None
    body_src = None
    mono_src = None

    for key in (
        "display-xl",
        "display-lg",
        "display-md",
        "headline",
        "display",
        "h1",
        "title",
    ):
        node = typography.get(key)
        if isinstance(node, dict) and node.get("fontFamily"):
            heading_src = node["fontFamily"]
            break

    for key in ("body", "body-lg", "body-sm", "text", "paragraph"):
        node = typography.get(key)
        if isinstance(node, dict) and node.get("fontFamily"):
            body_src = node["fontFamily"]
            break

    for key in ("mono", "code", "monospace"):
        node = typography.get(key)
        if isinstance(node, dict) and node.get("fontFamily"):
            mono_src = node["fontFamily"]
            break

    if not heading_src or not body_src:
        for node in typography.values():
            if isinstance(node, dict) and node.get("fontFamily"):
                heading_src = heading_src or node["fontFamily"]
                body_src = body_src or node["fontFamily"]
                break

    heading = substitute_font(heading_src, "heading")
    body = substitute_font(body_src, "body")
    mono = substitute_font(mono_src, "body") if mono_src else "Consolas"

    def _face_name(src: str | None) -> str:
        if not src:
            return ""
        return str(src).split(",")[0].strip().strip("\"'")

    for role, src, face in (
        ("heading", heading_src, heading),
        ("body", body_src, body),
        ("mono", mono_src, mono),
    ):
        raw = _face_name(src)
        if raw and raw.lower() not in face.lower() and face not in raw:
            # proprietary / unmapped → substitute
            if not any(x in raw.lower() for x in ("arial", "calibri", "georgia", "consolas", "cambria")):
                warnings.append(f"font.{role}: '{raw}' → '{face}' (PowerPoint-safe substitute)")

    return heading, body, mono, warnings
