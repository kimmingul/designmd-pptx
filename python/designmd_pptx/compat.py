"""OfficeCLI compatibility contract (issue #8).

The single machine-readable source of supported OfficeCLI versions lives in
``compatibility.json`` next to this module. Everything that needs to reason
about "is this OfficeCLI supported?" — the ``doctor`` command, CI, packaging,
and the docs — reads it through here, so a version bump is a one-line edit to
the manifest instead of a grep across the codebase.

Version strings are compared structurally (``0.2.117`` → ``(0, 2, 117)``) so a
``max_tested`` of ``0.2.117`` correctly flags ``0.3.0`` as newer-than-tested
rather than string-comparing ``"0.3.0" < "0.2.117"``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

MANIFEST_PATH = Path(__file__).with_name("compatibility.json")

# Support levels returned by classify_support().
OK = "supported"                 # within [min, max_tested]
TOO_OLD = "unsupported-too-old"  # below min — the hard failure
UNTESTED_NEWER = "untested-newer"  # above max_tested — probably fine, unverified
UNKNOWN = "unknown"              # could not parse a version out of the probe

_VERSION_RE = re.compile(r"(\d+(?:\.\d+)*)")
_MANIFEST_CACHE: dict | None = None


def parse_version(text: str | None) -> tuple[int, ...] | None:
    """First dotted-numeric run in *text* → tuple of ints, else None.

    Tolerant of the real probe outputs: ``"officecli version 0.2.117 (abc)"``
    and ``"9.9.9"`` both yield the leading version tuple."""
    if not text:
        return None
    m = _VERSION_RE.search(text)
    if not m:
        return None
    return tuple(int(p) for p in m.group(1).split("."))


def cmp_version(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    """-1 / 0 / 1, zero-padding the shorter tuple (1.2 == 1.2.0)."""
    n = max(len(a), len(b))
    a = a + (0,) * (n - len(a))
    b = b + (0,) * (n - len(b))
    return (a > b) - (a < b)


def load_manifest(path: str | Path | None = None) -> dict:
    """Parse and cache the compatibility manifest.

    An explicit *path* (used by tests) bypasses the cache."""
    global _MANIFEST_CACHE
    if path is None and _MANIFEST_CACHE is not None:
        return _MANIFEST_CACHE
    p = Path(path) if path is not None else MANIFEST_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    if path is None:
        _MANIFEST_CACHE = data
    return data


def spec_for(kind: str, manifest: dict | None = None) -> dict:
    """Backend spec block, ``kind`` in {'official', 'legacy'}."""
    return (manifest or load_manifest())["officecli"][kind]


def official_min_version() -> str:
    """Manifest 'min' for the official backend, with a literal fallback so an
    absent/corrupt manifest never breaks ``import backend``."""
    try:
        return spec_for("official")["min"]
    except Exception:
        return "0.2.117"


def classify_support(kind: str, version_text: str | None,
                     manifest: dict | None = None) -> tuple[str, str]:
    """(level, human reason) for a probed *version_text* against the manifest.

    A backend whose range is open (``min``/``max_tested`` null, e.g. legacy)
    is OK for any parseable version."""
    spec = spec_for(kind, manifest)
    v = parse_version(version_text)
    if v is None:
        return UNKNOWN, "could not parse a version from the probe output"
    mn = parse_version(spec.get("min"))
    mx = parse_version(spec.get("max_tested"))
    if mn is not None and cmp_version(v, mn) < 0:
        return TOO_OLD, f"below the minimum supported {spec['min']}"
    if mx is not None and cmp_version(v, mx) > 0:
        return UNTESTED_NEWER, f"newer than the max tested {spec['max_tested']}"
    return OK, "within the supported range"


def selfcheck(manifest: dict | None = None) -> None:
    """Assert the manifest is well-formed and internally ordered.

    Called by CI so a hand-edit that puts min > max_tested fails loudly
    instead of silently mis-gating ``doctor``."""
    m = manifest or load_manifest()
    assert m.get("schema") == 1, "unexpected manifest schema"
    officecli = m.get("officecli")
    assert isinstance(officecli, dict), "manifest missing 'officecli'"
    for kind in ("official", "legacy"):
        assert kind in officecli, f"manifest missing officecli.{kind}"
        spec = officecli[kind]
        vers = {k: parse_version(spec.get(k))
                for k in ("min", "recommended", "max_tested")}
        # Every present version string must parse.
        for k in ("min", "recommended", "max_tested"):
            if spec.get(k) is not None:
                assert vers[k] is not None, f"{kind}.{k} = {spec[k]!r} is unparseable"
        # Ordering: min <= recommended <= max_tested where all present.
        if vers["min"] and vers["recommended"]:
            assert cmp_version(vers["min"], vers["recommended"]) <= 0, \
                f"{kind}: min > recommended"
        if vers["recommended"] and vers["max_tested"]:
            assert cmp_version(vers["recommended"], vers["max_tested"]) <= 0, \
                f"{kind}: recommended > max_tested"


if __name__ == "__main__":  # pragma: no cover
    selfcheck()
    off = spec_for("official")
    print(f"officecli official: min {off['min']} / pinned {off['recommended']} "
          f"/ max tested {off['max_tested']} - manifest OK")
