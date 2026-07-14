"""Validation corpus manifest + deterministic held-out split (issue #36).

The corpus is a set of anonymized real .pptx decks used to test the toolchain
against real-world structure instead of synthetic fixtures. Each deck is
recorded in a JSON manifest with provenance/licensing so admission is auditable,
and a fraction is held out by a STABLE hash rule — so patterns are never tuned
against the evaluation set and the split doesn't drift between runs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA = 1
_REQUIRED = ("id", "file", "source", "license", "provenance")
_HOLDOUT_BUCKETS = 5  # ~20% held out by the hash rule


def load_corpus(manifest_path: str | Path) -> list[dict[str, Any]]:
    """Parse a corpus manifest → list of entries (raises on schema mismatch)."""
    data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if data.get("schema") != MANIFEST_SCHEMA:
        raise ValueError(
            f"unsupported corpus manifest schema: {data.get('schema')!r} "
            f"(expected {MANIFEST_SCHEMA})")
    return list(data.get("entries", []))


def validate_entries(entries: list[dict[str, Any]]) -> list[str]:
    """Return human-readable problems (missing required fields, duplicate ids)."""
    errors: list[str] = []
    seen: set[str] = set()
    for i, e in enumerate(entries):
        for k in _REQUIRED:
            if not e.get(k):
                errors.append(f"entry[{i}] ({e.get('id', '?')}): missing '{k}'")
        eid = e.get("id")
        if eid:
            if eid in seen:
                errors.append(f"duplicate id: {eid}")
            seen.add(eid)
    return errors


def _holdout_bucket(entry: dict[str, Any]) -> int:
    # Hash the content digest (falling back to the id) so the bucket is stable
    # for a given deck regardless of manifest order or run.
    key = entry.get("sha256") or entry.get("id") or ""
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % _HOLDOUT_BUCKETS


def is_held_out(entry: dict[str, Any]) -> bool:
    """held_out=true/false pins the entry explicitly; otherwise the stable hash
    rule assigns ~1/5 of decks to the held-out evaluation set."""
    flag = entry.get("held_out")
    if isinstance(flag, bool):
        return flag
    return _holdout_bucket(entry) == 0


def split(entries: list[dict[str, Any]]) -> tuple[list, list]:
    """(train, held_out) partition."""
    train, held = [], []
    for e in entries:
        (held if is_held_out(e) else train).append(e)
    return train, held


def stats(entries: list[dict[str, Any]]) -> dict[str, Any]:
    train, held = split(entries)
    return {
        "total": len(entries),
        "train": len(train),
        "held_out": len(held),
        "licenses": sorted({e.get("license", "?") for e in entries}),
        "sources": sorted({e.get("source", "?") for e in entries}),
    }
