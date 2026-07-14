"""Apply recipe JSON with staging-safe overwrite (v1.7: backend-abstracted).

All OfficeCLI subprocess/stdout handling lives in backend.LegacyBatchBackend
(issue #27); this module owns only the staging-safe orchestration: build into
a sibling temp file, validate + issues gate + Gate 3 screenshot, then atomic
replace. The destination is never deleted before success.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

from .backend import BackendUnavailable, LegacyBatchBackend, _issues_are_clean
from .backend import find_binaries


def find_officecli() -> str | None:
    """Back-compat helper: path of the legacy (shape-level) binary."""
    return find_binaries().get("legacy")


def apply_sequence(
    pptx: str | Path,
    sequence_json: str | Path,
    *,
    create: bool = True,
    force: bool = False,
    require_clean_issues: bool = True,
    screenshot: bool = False,
    gate3: bool = False,
    vision: bool = False,
    vision_fail: bool = False,
    vision_plan: str | Path | None = None,
    vision_cmd: str | None = None,
    backend: LegacyBatchBackend | None = None,
) -> None:
    """
    Materialize deck.sequence.json into pptx.

    Staging-safe: when destination exists and force=True, build into a sibling
    temp file, validate/issues, then os.replace onto destination. Destination
    is never deleted before success.
    """
    pptx = Path(pptx).resolve()
    sequence_json = Path(sequence_json).resolve()
    ops = json.loads(sequence_json.read_text(encoding="utf-8"))
    if not isinstance(ops, list):
        raise ValueError("sequence JSON must be a list of batch operations")

    dest_exists = pptx.exists()
    if dest_exists and not force:
        raise FileExistsError(
            f"{pptx} already exists. Pass force=True / --force to overwrite."
        )

    be = backend or LegacyBatchBackend()
    if not be.available():
        raise BackendUnavailable(
            "legacy OfficeCLI not found on PATH. Install: "
            "https://github.com/iOfficeAI/OfficeCLI/releases "
            "(the official officecli npm package is outline-only and cannot "
            "run the shape-level pipeline — see docs/officecli-backends.md)"
        )
    be.require("create", "open", "batch", "save", "validate", "view", "close")

    # Always build into staging when creating or overwriting
    staging = pptx
    staged = False
    if create:
        staging = pptx.with_name(f".{pptx.stem}.staging-{uuid.uuid4().hex[:8]}{pptx.suffix}")
        staged = True
        if staging.exists():
            staging.unlink()

    batch_file = sequence_json.parent / f"_batch_{uuid.uuid4().hex[:8]}.json"
    batch_file.write_text(json.dumps(ops, ensure_ascii=False), encoding="utf-8")

    try:
        if create:
            r = be.create(staging)
            if r.returncode != 0:
                raise RuntimeError(f"officecli create failed: {r.stderr or r.stdout}")

        r = be.open(staging)
        if r.returncode != 0:
            raise RuntimeError(f"officecli open failed: {r.stderr or r.stdout}")

        # Prefer file input over stdin (UTF-8 safe on Windows PowerShell)
        r = be.batch(staging, batch_file)
        if r.returncode != 0:
            r2 = be.batch_stdin(staging, ops)
            if r2.returncode != 0:
                sys.stderr.write(r.stdout or "")
                sys.stderr.write(r.stderr or "")
                sys.stderr.write(r2.stdout or "")
                sys.stderr.write(r2.stderr or "")
                raise RuntimeError("officecli batch failed")
            out_batch = (r2.stdout or "") + (r2.stderr or "")
        else:
            out_batch = (r.stdout or "") + (r.stderr or "")
        print(out_batch)
        if re.search(r"\d+\s+failed", out_batch, re.I):
            m = re.search(r"(\d+)\s+failed", out_batch, re.I)
            if m and int(m.group(1)) > 0:
                raise RuntimeError("officecli batch reported failed ops")

        r = be.save(staging)
        if r.returncode != 0:
            raise RuntimeError(f"officecli save failed: {r.stderr or r.stdout}")

        r = be.validate(staging)
        print(r.stdout or "")
        if r.returncode != 0:
            sys.stderr.write(r.stderr or "")
            raise RuntimeError("officecli validate failed")

        issues_out = be.issues_output(staging)
        print(issues_out)
        if require_clean_issues and not be.issues_clean(issues_out):
            raise RuntimeError(
                "officecli view issues reported problems — fix recipes before delivery"
            )

        # close staging if possible (ignore errors)
        be.close(staging)

        # Gate 3 runs on the STAGING copy, before the destination is replaced —
        # a deck whose contact sheet cannot even render never ships (--gate3).
        # Optional vision QA (#14) evaluates the sheet and may hard-fail.
        shot: Path | None = None
        want_shot = screenshot or gate3 or vision or vision_fail
        if want_shot:
            shot = pptx.with_suffix(".contact.png")
            r = be.screenshot(staging, shot)
            if r.returncode != 0 or not shot.exists():
                msg = (
                    "Gate 3 screenshot failed: "
                    f"{((r.stderr or r.stdout) or '').strip()[:200]}"
                )
                if gate3 or vision_fail:
                    raise RuntimeError(f"{msg} — destination left untouched")
                print(f"warning: {msg}")
                shot = None
            # the screenshot view starts its own resident on staging —
            # release it before the atomic replace (Windows locks the file)
            be.close(staging)

            if shot is not None and (vision or vision_fail or vision_plan):
                from .vision_gate import evaluate_contact_sheet, write_report

                eval_path = pptx.with_suffix(".gate3.json")
                result = evaluate_contact_sheet(
                    shot,
                    vision_plan=vision_plan,
                    use_subprocess=(
                        True if vision_cmd or os.environ.get("DESIGNMD_VISION_CMD")
                        else None
                    ),
                    vision_cmd=vision_cmd,
                    context={"pptx": pptx.name, "sequence": sequence_json.name},
                )
                write_report(result, eval_path)
                print(
                    f"Gate 3 vision → {eval_path} "
                    f"(pass={result.get('pass')} score={result.get('score')} "
                    f"provider={result.get('provider')})"
                )
                for f in result.get("findings") or []:
                    sev = f.get("severity") or "info"
                    print(f"  [{sev}] {f.get('code')}: {f.get('message')}")
                if vision_fail and not result.get("pass", False):
                    raise RuntimeError(
                        "Gate 3 vision QA failed — destination left untouched "
                        f"(see {eval_path.name})"
                    )

        if staged:
            if dest_exists and not force:
                # should have been caught earlier
                raise FileExistsError(str(pptx))
            # atomic replace onto destination; brief retry for lingering
            # resident file locks on Windows
            for attempt in range(10):
                try:
                    os.replace(str(staging), str(pptx))
                    break
                except PermissionError:
                    if attempt == 9:
                        raise
                    time.sleep(0.5)
            staged = False  # ownership transferred

        print(f"Applied → {pptx}")
        if shot:
            print(
                f"Gate 3 contact sheet → {shot} "
                "(inspect for overflow/overlap/alignment before delivery)"
            )
    finally:
        try:
            if batch_file.exists():
                batch_file.unlink()
        except OSError:
            pass
        if staged and staging.exists() and staging != pptx:
            try:
                be.close(staging)
            except Exception:
                pass
            try:
                staging.unlink()
            except OSError:
                pass


__all__ = ["apply_sequence", "find_officecli", "_issues_are_clean"]
