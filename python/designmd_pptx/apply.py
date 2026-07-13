"""Apply recipe JSON via officecli batch with staging-safe overwrite (v1.1)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


def find_officecli() -> str | None:
    return shutil.which("officecli")


def _run(exe: str, args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [exe, *args],
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )


def _issues_are_clean(stdout: str) -> bool:
    text = stdout or ""
    if re.search(r"Found\s+0\s+issue", text, re.I):
        return True
    if re.search(r"\[[OCSF]\d+\]", text):
        return False
    # JSON path if present
    if '"Count"' in text or '"count"' in text:
        m = re.search(r'"Count"\s*:\s*(\d+)', text) or re.search(r'"count"\s*:\s*(\d+)', text)
        if m:
            return int(m.group(1)) == 0
    if "issue" in text.lower() and re.search(r"\b0\b", text):
        return True
    # empty / no issues phrasing
    if not text.strip():
        return True
    if "no issue" in text.lower():
        return True
    return "Found" not in text


def apply_sequence(
    pptx: str | Path,
    sequence_json: str | Path,
    *,
    create: bool = True,
    force: bool = False,
    require_clean_issues: bool = True,
    screenshot: bool = False,
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

    exe = find_officecli()
    if not exe:
        raise RuntimeError(
            "officecli not found on PATH. Install: "
            "https://github.com/iOfficeAI/OfficeCLI/releases"
        )

    dest_exists = pptx.exists()
    if dest_exists and not force:
        raise FileExistsError(
            f"{pptx} already exists. Pass force=True / --force to overwrite."
        )

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
            r = _run(exe, ["create", str(staging)])
            if r.returncode != 0:
                raise RuntimeError(f"officecli create failed: {r.stderr or r.stdout}")

        r = _run(exe, ["open", str(staging)])
        if r.returncode != 0:
            raise RuntimeError(f"officecli open failed: {r.stderr or r.stdout}")

        # Prefer file input over stdin (UTF-8 safe on Windows PowerShell)
        r = _run(exe, ["batch", str(staging), str(batch_file)])
        if r.returncode != 0:
            # fallback: stdin
            r2 = _run(exe, ["batch", str(staging)], input_text=json.dumps(ops))
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

        r = _run(exe, ["save", str(staging)])
        if r.returncode != 0:
            raise RuntimeError(f"officecli save failed: {r.stderr or r.stdout}")

        r = _run(exe, ["validate", str(staging)])
        print(r.stdout or "")
        if r.returncode != 0:
            sys.stderr.write(r.stderr or "")
            raise RuntimeError("officecli validate failed")

        r = _run(exe, ["view", str(staging), "issues"])
        issues_out = (r.stdout or "") + (r.stderr or "")
        print(issues_out)
        if require_clean_issues and not _issues_are_clean(issues_out):
            raise RuntimeError(
                "officecli view issues reported problems — fix recipes before delivery"
            )

        # close staging if possible (ignore errors)
        _run(exe, ["close", str(staging)])

        if staged:
            if dest_exists and not force:
                # should have been caught earlier
                raise FileExistsError(str(pptx))
            # atomic replace onto destination
            os.replace(str(staging), str(pptx))
            staged = False  # ownership transferred

        print(f"Applied → {pptx}")

        if screenshot:
            # Gate 3: whole-deck contact sheet for visual QA (overflow,
            # overlap, alignment). Non-fatal — the deck is already delivered.
            shot = pptx.with_suffix(".contact.png")
            r = _run(exe, ["view", str(pptx), "screenshot", "--grid", "-o", str(shot)])
            if r.returncode == 0 and shot.exists():
                print(f"Gate 3 contact sheet → {shot}")
            else:
                print(
                    "warning: Gate 3 screenshot failed: "
                    f"{((r.stderr or r.stdout) or '').strip()[:200]}"
                )
    finally:
        try:
            if batch_file.exists():
                batch_file.unlink()
        except OSError:
            pass
        if staged and staging.exists() and staging != pptx:
            try:
                _run(exe, ["close", str(staging)])
            except Exception:
                pass
            try:
                staging.unlink()
            except OSError:
                pass
