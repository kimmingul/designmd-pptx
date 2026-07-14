"""Accessibility checks for DESIGN.md tokens + deck-specs (issue #39).

Pure, OfficeCLI-free checks so unit tests exercise the real path without a
binary:

* WCAG 2.x relative-luminance contrast ratios on brand token pairs
* Deterministic reading-order assignment (top→bottom, left→right)
* Alt-text / speaker-notes coverage on image-bearing and narrative slides
* Structured report with ``ok`` / findings; opt-in contrast auto-correct

Failures are meant to be inspected **before** treating scaffold/apply output
as clean. See ``python -m designmd_pptx a11y``.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .tokens import contrast_text_on, hex_brightness, normalize_hex

# WCAG 2.1 AA for normal text; large text is 3.0 — we apply the normal floor
# to body/title brand pairs so generated decks stay readable.
WCAG_AA_NORMAL = 4.5
WCAG_AA_LARGE = 3.0
WCAG_AAA_NORMAL = 7.0

# Token color pairs checked as (fg_key, bg_key, min_ratio, label)
_DEFAULT_PAIRS: list[tuple[str, str, float, str]] = [
    ("text", "background", WCAG_AA_NORMAL, "body text on background"),
    ("text", "content_background", WCAG_AA_NORMAL, "body text on content bg"),
    ("text", "surface", WCAG_AA_NORMAL, "body text on surface"),
    ("muted", "background", WCAG_AA_LARGE, "muted text on background"),
    ("on_accent", "accent", WCAG_AA_NORMAL, "text on accent"),
]

# Recipes that carry images / logos and must have alt when src is set
_IMAGE_RECIPES = frozenset({"image_full", "image_text_2col", "logo_strip", "multi_panel_figure"})
# Recipes where speaker notes are recommended for narrative delivery
_NOTES_RECIPES = frozenset({
    "cover", "section_divider", "section_opener_numbered", "close",
    "chart_insight", "chart_callout_panel", "quote", "big_number",
    "process", "timeline", "story_timeline", "consort_flow", "study_design",
})


@dataclass
class Finding:
    code: str
    severity: str  # "error" | "warning"
    message: str
    path: str = ""
    ratio: float | None = None
    fix: str | None = None


@dataclass
class A11yReport:
    ok: bool
    errors: int
    warnings: int
    findings: list[Finding] = field(default_factory=list)
    reading_order: list[dict[str, Any]] = field(default_factory=list)
    corrected: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def relative_luminance(hex6: str) -> float:
    """WCAG relative luminance (0..1) for an RRGGBB hex string."""
    h = normalize_hex(hex6)
    if not h:
        return 0.0
    # hex_brightness already applies sRGB linearization and returns 0..100
    return hex_brightness(h) / 100.0


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """WCAG contrast ratio between two colors (always ≥ 1.0)."""
    l1 = relative_luminance(fg_hex)
    l2 = relative_luminance(bg_hex)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def check_token_contrast(
    tokens: dict[str, Any],
    *,
    pairs: list[tuple[str, str, float, str]] | None = None,
    level: str = "AA",
) -> list[Finding]:
    """Check brand token color pairs against WCAG floors."""
    colors = tokens.get("colors") or {}
    if not isinstance(colors, dict):
        return [Finding("a11y.tokens", "error", "tokens.colors missing or not an object")]
    findings: list[Finding] = []
    for fg_k, bg_k, min_ratio, label in (pairs or _DEFAULT_PAIRS):
        if level.upper() == "AAA" and min_ratio == WCAG_AA_NORMAL:
            min_ratio = WCAG_AAA_NORMAL
        fg = normalize_hex(colors.get(fg_k))
        bg = normalize_hex(colors.get(bg_k))
        if not fg or not bg:
            findings.append(Finding(
                "a11y.contrast.missing",
                "warning",
                f"cannot check {label}: missing {fg_k if not fg else bg_k}",
                path=f"colors.{fg_k}/{bg_k}",
            ))
            continue
        ratio = contrast_ratio(fg, bg)
        if ratio + 1e-9 < min_ratio:
            findings.append(Finding(
                "a11y.contrast.fail",
                "error",
                f"{label}: {fg} on {bg} ratio {ratio:.2f} < {min_ratio:.1f} (WCAG {level})",
                path=f"colors.{fg_k}/{bg_k}",
                ratio=round(ratio, 3),
                fix=f"set colors.{fg_k} to a readable color on {bg} "
                    f"(e.g. {contrast_text_on(bg)})",
            ))
    return findings


def auto_correct_contrast(tokens: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return a copy of *tokens* with failing FG colors snapped to readable ones.

    Only mutates the foreground side of known pairs (never the brand accent fill).
    """
    out = deepcopy(tokens)
    colors = out.setdefault("colors", {})
    notes: list[str] = []
    for fg_k, bg_k, min_ratio, label in _DEFAULT_PAIRS:
        fg = normalize_hex(colors.get(fg_k))
        bg = normalize_hex(colors.get(bg_k))
        if not bg:
            continue
        if not fg or contrast_ratio(fg, bg) + 1e-9 < min_ratio:
            # Do not pass preferred — contrast_text_on may keep a mid-gray
            # that still fails WCAG AA (brightness ≤45 is not a contrast floor).
            fixed = contrast_text_on(bg)
            if normalize_hex(colors.get(fg_k)) != fixed:
                notes.append(f"{fg_k}: {colors.get(fg_k)} → {fixed} ({label})")
                colors[fg_k] = fixed
    return out, notes


def reading_order_for_slide(
    slide: dict[str, Any],
    *,
    index: int = 0,
) -> list[dict[str, Any]]:
    """Deterministic reading order for a deck-spec slide.

    Order: title → primary narrative fields → structured lists (as listed) →
    media (src/alt) → notes last. Within homogeneous lists, original index is
    preserved (stable). Coordinates, when present on content items, sort
    top→bottom then left→right.
    """
    content = slide.get("content") if isinstance(slide.get("content"), dict) else {}
    recipe = slide.get("recipe") or "unknown"
    sid = slide.get("id") or f"slide-{index}"
    nodes: list[dict[str, Any]] = []

    def add(role: str, text: Any, *, y: float = 0.0, x: float = 0.0, extra: dict | None = None) -> None:
        if text is None or text == "":
            return
        entry = {
            "slide_id": sid,
            "recipe": recipe,
            "role": role,
            "text": str(text)[:200],
            "order_key": (y, x, len(nodes)),
        }
        if extra:
            entry.update(extra)
        nodes.append(entry)

    add("title", content.get("title") or content.get("value"), y=0.0, x=0.0)
    add("subtitle", content.get("subtitle") or content.get("blurb") or content.get("meta"), y=0.5, x=0.0)
    add("body", content.get("body") or content.get("quote") or content.get("insight_body"), y=1.0, x=0.0)

    for key in ("bullets", "items", "steps", "stages", "entries"):
        seq = content.get(key)
        if isinstance(seq, list):
            for i, item in enumerate(seq):
                if isinstance(item, dict):
                    y = float(item.get("y", item.get("top", 2.0 + i)))
                    x = float(item.get("x", item.get("left", 0.0)))
                    text = item.get("title") or item.get("label") or item.get("text") or item.get("name") or str(item)
                    add(f"{key}[{i}]", text, y=y, x=x)
                else:
                    add(f"{key}[{i}]", item, y=2.0 + i, x=0.0)

    if content.get("src"):
        add("image", content.get("alt") or "(missing alt)", y=5.0, x=0.0,
            extra={"alt": content.get("alt") or "", "src": content.get("src")})

    logos = content.get("logos") or content.get("panels") or content.get("figures")
    if isinstance(logos, list):
        for i, logo in enumerate(logos):
            if not isinstance(logo, dict):
                continue
            y = float(logo.get("y", 6.0 + i * 0.1))
            x = float(logo.get("x", i))
            add(f"media[{i}]", logo.get("alt") or logo.get("label") or logo.get("caption") or "(media)",
                y=y, x=x, extra={"alt": logo.get("alt") or "", "src": logo.get("src") or ""})

    add("notes", content.get("notes"), y=99.0, x=0.0)

    nodes.sort(key=lambda n: n["order_key"])
    ordered: list[dict[str, Any]] = []
    for i, n in enumerate(nodes):
        row = {k: v for k, v in n.items() if k != "order_key"}
        row["reading_index"] = i
        ordered.append(row)
    return ordered


def check_alt_and_notes(deck: dict[str, Any], *, require_notes: bool = False) -> list[Finding]:
    """Alt-text coverage + optional speaker-notes presence on deck-spec slides."""
    findings: list[Finding] = []
    slides = deck.get("slides") if isinstance(deck, dict) else None
    if not isinstance(slides, list):
        return [Finding("a11y.deck", "error", "deck-spec missing slides[]")]

    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        recipe = slide.get("recipe") or ""
        content = slide.get("content") if isinstance(slide.get("content"), dict) else {}
        path = f"slides[{i}].{slide.get('id', recipe)}"

        src = content.get("src")
        alt = (content.get("alt") or "").strip()
        if src and not alt:
            findings.append(Finding(
                "a11y.alt.missing",
                "error",
                f"{recipe}: src is set but alt is empty",
                path=path,
                fix="set content.alt to a short description of the image",
            ))

        if recipe in _IMAGE_RECIPES and not src and not alt:
            # no asset yet — warn so authors fill before ship
            findings.append(Finding(
                "a11y.alt.pending",
                "warning",
                f"{recipe}: no src/alt yet — add before final deliverable",
                path=path,
            ))

        for key in ("logos", "panels", "figures", "members"):
            seq = content.get(key)
            if not isinstance(seq, list):
                continue
            for j, item in enumerate(seq):
                if not isinstance(item, dict):
                    continue
                isrc = item.get("src")
                ialt = (item.get("alt") or item.get("label") or "").strip()
                if isrc and not ialt:
                    findings.append(Finding(
                        "a11y.alt.missing",
                        "error",
                        f"{recipe}.{key}[{j}]: src set without alt/label",
                        path=f"{path}.content.{key}[{j}]",
                        fix="set alt (or label) describing the image",
                    ))

        notes = (content.get("notes") or "").strip()
        if recipe in _NOTES_RECIPES and not notes:
            sev = "error" if require_notes else "warning"
            findings.append(Finding(
                "a11y.notes.missing",
                sev,
                f"{recipe}: speaker notes empty (recommended for narrative slides)",
                path=path,
                fix="set content.notes to a 1–2 sentence speaker cue",
            ))
    return findings


def ensure_notes_and_alt(
    deck: dict[str, Any],
    *,
    generate_alt: bool = True,
    generate_notes: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    """Fill missing alt/notes with deterministic placeholders (opt-in repair)."""
    out = deepcopy(deck)
    changes: list[str] = []
    slides = out.get("slides")
    if not isinstance(slides, list):
        return out, changes
    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        content = slide.setdefault("content", {})
        if not isinstance(content, dict):
            continue
        recipe = slide.get("recipe") or "slide"
        sid = slide.get("id") or f"slide-{i}"
        title = str(content.get("title") or recipe)

        if generate_alt and content.get("src") and not (content.get("alt") or "").strip():
            content["alt"] = f"Illustration for {title}"
            changes.append(f"{sid}: generated alt")

        for key in ("logos", "panels", "figures"):
            seq = content.get(key)
            if not isinstance(seq, list):
                continue
            for j, item in enumerate(seq):
                if not isinstance(item, dict):
                    continue
                if item.get("src") and not (item.get("alt") or item.get("label") or "").strip():
                    item["alt"] = item.get("caption") or f"{key.rstrip('s')} {j + 1} on {title}"
                    changes.append(f"{sid}.{key}[{j}]: generated alt")

        if generate_notes and recipe in _NOTES_RECIPES and not (content.get("notes") or "").strip():
            content["notes"] = f"Speak to: {title}."
            changes.append(f"{sid}: generated notes")
    return out, changes


def audit(
    *,
    tokens: dict[str, Any] | None = None,
    deck: dict[str, Any] | None = None,
    level: str = "AA",
    require_notes: bool = False,
    auto_correct: bool = False,
    generate_missing: bool = False,
) -> A11yReport:
    """Full a11y audit. ``ok`` is True only when there are zero error-severity findings
    **after** optional auto-correct / generation (so callers can gate output).
    """
    findings: list[Finding] = []
    reading: list[dict[str, Any]] = []
    corrected: dict[str, Any] | None = None
    work_tokens = deepcopy(tokens) if tokens else None
    work_deck = deepcopy(deck) if deck else None

    if work_tokens is not None:
        if auto_correct:
            work_tokens, notes = auto_correct_contrast(work_tokens)
            for n in notes:
                findings.append(Finding(
                    "a11y.contrast.corrected", "warning", f"auto-corrected {n}",
                ))
        findings.extend(check_token_contrast(work_tokens, level=level))

    if work_deck is not None:
        if generate_missing:
            work_deck, changes = ensure_notes_and_alt(work_deck)
            for c in changes:
                findings.append(Finding(
                    "a11y.generated", "warning", f"filled missing field: {c}",
                ))
        findings.extend(check_alt_and_notes(work_deck, require_notes=require_notes))
        for i, slide in enumerate(work_deck.get("slides") or []):
            if isinstance(slide, dict):
                reading.extend(reading_order_for_slide(slide, index=i))

    if auto_correct or generate_missing:
        corrected = {}
        if work_tokens is not None:
            corrected["tokens"] = work_tokens
        if work_deck is not None:
            corrected["deck"] = work_deck

    # Re-check errors after corrections already applied above
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    return A11yReport(
        ok=errors == 0,
        errors=errors,
        warnings=warnings,
        findings=findings,
        reading_order=reading,
        corrected=corrected,
    )


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_report(report: A11yReport, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
                 encoding="utf-8")
    return p
