"""True Visual Gate 3 — structured contact-sheet QA (Phase 3 / #14).

Existing ``--gate3`` only checks that a contact-sheet PNG **rendered**.
This module evaluates visual quality and returns structured JSON.

Providers (opt-in; default apply path unchanged)
------------------------------------------------
1. **offline heuristic** — no network: PNG signature, dimensions, file size,
   aspect plausibility. Catches missing/corrupt/tiny sheets.
2. **plan/result file** (``--vision-plan``) — inject a pre-authored evaluation
   JSON (tests + replay).
3. **subprocess vision** (``DESIGNMD_VISION_CMD`` / ``--vision-cmd``) — external
   vision model. Reads a JSON request on stdin (paths + context), writes
   evaluation JSON on stdout.

Evaluation schema (subset)
--------------------------
{
  "version": 1,
  "pass": true|false,
  "score": 0.0-1.0,
  "provider": "offline|subprocess|plan_file",
  "findings": [
    {"code": "overflow|overlap|density|contrast|alignment|corrupt|...",
     "severity": "error|warn|info",
     "message": "...",
     "slide": null|int}
  ],
  "metrics": {"width_px": N, "height_px": N, "bytes": N, ...}
}

Hard gate (``vision_fail=True`` / ``--gate3-vision``): any finding with
severity=error, or pass=false, aborts apply before the destination is replaced.
"""

from __future__ import annotations

import json
import os
import re
import struct
import subprocess
from pathlib import Path
from typing import Any


def _png_size(path: Path) -> tuple[int, int] | None:
    """Read IHDR width/height without third-party deps. None if not PNG."""
    try:
        data = path.read_bytes()[:32]
    except OSError:
        return None
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    # IHDR: 8 sig + 4 len + 4 type + 4 width + 4 height
    if data[12:16] != b"IHDR":
        return None
    w, h = struct.unpack(">II", data[16:24])
    return int(w), int(h)


def offline_evaluate(
    contact_png: str | Path,
    *,
    min_width: int = 400,
    min_height: int = 200,
    min_bytes: int = 2_000,
    max_bytes: int = 80_000_000,
) -> dict[str, Any]:
    """Zero-network visual gate based on contact-sheet file health."""
    path = Path(contact_png)
    findings: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}

    if not path.exists():
        findings.append({
            "code": "missing",
            "severity": "error",
            "message": f"contact sheet not found: {path.name}",
            "slide": None,
        })
        return {
            "version": 1,
            "pass": False,
            "score": 0.0,
            "provider": "offline",
            "findings": findings,
            "metrics": metrics,
        }

    size = path.stat().st_size
    metrics["bytes"] = size
    if size < min_bytes:
        findings.append({
            "code": "too_small",
            "severity": "error",
            "message": f"contact sheet only {size} bytes (min {min_bytes})",
            "slide": None,
        })
    if size > max_bytes:
        findings.append({
            "code": "too_large",
            "severity": "warn",
            "message": f"contact sheet {size} bytes exceeds soft max {max_bytes}",
            "slide": None,
        })

    dims = _png_size(path)
    if dims is None:
        findings.append({
            "code": "corrupt",
            "severity": "error",
            "message": "not a valid PNG (missing IHDR) — render may have failed silently",
            "slide": None,
        })
    else:
        w, h = dims
        metrics["width_px"] = w
        metrics["height_px"] = h
        metrics["aspect"] = round(w / h, 3) if h else None
        if w < min_width or h < min_height:
            findings.append({
                "code": "dimensions",
                "severity": "error",
                "message": f"contact sheet {w}×{h} below min {min_width}×{min_height}",
                "slide": None,
            })
        # Contact sheets are usually wider than tall; extreme ratios are suspicious.
        if h and w / h < 0.5:
            findings.append({
                "code": "aspect",
                "severity": "warn",
                "message": f"unusual portrait aspect {w}×{h} for a contact sheet",
                "slide": None,
            })
        if h and w / h > 20:
            findings.append({
                "code": "aspect",
                "severity": "warn",
                "message": f"extreme wide aspect {w}×{h} — check grid screenshot",
                "slide": None,
            })

    errors = [f for f in findings if f["severity"] == "error"]
    warns = [f for f in findings if f["severity"] == "warn"]
    score = 1.0
    if errors:
        score = 0.2
    elif warns:
        score = 0.75
    return {
        "version": 1,
        "pass": not errors,
        "score": score,
        "provider": "offline",
        "findings": findings,
        "metrics": metrics,
    }


def merge_evaluations(*parts: dict[str, Any]) -> dict[str, Any]:
    """Combine offline + vision findings; pass only if all parts pass."""
    findings: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    providers: list[str] = []
    scores: list[float] = []
    for p in parts:
        if not p:
            continue
        findings.extend(p.get("findings") or [])
        metrics.update(p.get("metrics") or {})
        if p.get("provider"):
            providers.append(str(p["provider"]))
        if isinstance(p.get("score"), (int, float)):
            scores.append(float(p["score"]))
    errors = [f for f in findings if f.get("severity") == "error"]
    return {
        "version": 1,
        "pass": not errors and all(bool(p.get("pass", True)) for p in parts if p),
        "score": round(min(scores) if scores else 0.0, 3),
        "provider": "+".join(providers) if providers else "none",
        "findings": findings,
        "metrics": metrics,
    }


def run_subprocess_vision(
    request: dict[str, Any],
    *,
    cmd: str | None = None,
    timeout_s: float = 180.0,
) -> dict[str, Any]:
    """External vision evaluator: stdin JSON request → stdout evaluation JSON."""
    cmd = cmd or os.environ.get("DESIGNMD_VISION_CMD") or ""
    if not cmd.strip():
        raise ValueError("DESIGNMD_VISION_CMD is not set")
    payload = json.dumps(request, ensure_ascii=False).encode("utf-8")
    proc = subprocess.run(
        cmd,
        input=payload,
        capture_output=True,
        shell=True,
        timeout=timeout_s,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or b"").decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"vision evaluator failed (rc={proc.returncode}): {err}")
    text = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    if not text:
        raise RuntimeError("vision evaluator returned empty stdout")
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise RuntimeError("vision evaluator must return a JSON object")
    data.setdefault("provider", "subprocess")
    data.setdefault("version", 1)
    # Normalize findings
    findings = data.get("findings") or []
    if not isinstance(findings, list):
        findings = []
    norm: list[dict[str, Any]] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        sev = str(f.get("severity") or "warn").lower()
        if sev not in ("error", "warn", "info"):
            sev = "warn"
        norm.append({
            "code": str(f.get("code") or "vision"),
            "severity": sev,
            "message": str(f.get("message") or ""),
            "slide": f.get("slide"),
        })
    data["findings"] = norm
    if "pass" not in data:
        data["pass"] = not any(f["severity"] == "error" for f in norm)
    if "score" not in data:
        data["score"] = 0.3 if not data["pass"] else 0.85
    return data


def evaluate_contact_sheet(
    contact_png: str | Path,
    *,
    vision_plan: str | Path | None = None,
    use_subprocess: bool | None = None,
    vision_cmd: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run offline (+ optional vision/plan) evaluation of a contact sheet."""
    offline = offline_evaluate(contact_png)
    parts: list[dict[str, Any]] = [offline]

    if vision_plan is not None:
        plan = json.loads(Path(vision_plan).read_text(encoding="utf-8"))
        if not isinstance(plan, dict):
            raise ValueError("vision plan must be a JSON object")
        plan.setdefault("provider", "plan_file")
        parts.append(plan)
    else:
        want = use_subprocess
        if want is None:
            want = bool(vision_cmd or os.environ.get("DESIGNMD_VISION_CMD"))
        if want:
            request = {
                "version": 1,
                "task": "gate3_vision",
                "contact_sheet": str(Path(contact_png).resolve()),
                "offline": offline,
                "context": context or {},
                "instructions": (
                    "Evaluate the contact-sheet image for overflow, overlap, "
                    "low contrast, density, alignment. Return JSON with pass, "
                    "score 0-1, findings:[{code,severity,message,slide?}]."
                ),
            }
            try:
                parts.append(run_subprocess_vision(request, cmd=vision_cmd))
            except Exception as e:  # noqa: BLE001
                parts.append({
                    "version": 1,
                    "pass": True,  # soft: vision outage does not fail offline pass
                    "score": offline.get("score", 0.5),
                    "provider": "subprocess_failed",
                    "findings": [{
                        "code": "vision_unavailable",
                        "severity": "warn",
                        "message": f"vision evaluator failed: {e}",
                        "slide": None,
                    }],
                    "metrics": {},
                })

    result = merge_evaluations(*parts)
    result["contact_sheet"] = Path(contact_png).name
    return result


def write_report(result: dict[str, Any], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
