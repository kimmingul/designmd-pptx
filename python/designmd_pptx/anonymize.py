"""Anonymize a .pptx for validation-corpus admission (issue #36).

Strips author / organization / custom metadata and comment authorship so a real
deck can join the corpus without leaking PII. Slide **content is preserved by
default** — the corpus exists to test layout/extraction fidelity on real
structure — while `redact_text=True` also blanks visible text (length-preserving)
for highly sensitive decks. Namespace-aware throughout via the OPC layer (#16);
staging-safe via restyle.rewrite_package.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lxml import etree
from lxml.etree import XMLSyntaxError

from . import opc
from .restyle import rewrite_package

# docProps namespaces (core / dublin-core / extended / — matched by URI).
_NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
}


def _q(prefix: str, local: str) -> str:
    return f"{{{_NS[prefix]}}}{local}"


_PLACEHOLDER = "anonymized"
_EPOCH = "1970-01-01T00:00:00Z"

# core.xml identifying fields → replaced with a fixed placeholder / blanked.
_CORE_IDENTITY = [_q("dc", "creator"), _q("cp", "lastModifiedBy")]
_CORE_BLANK = [
    _q("dc", "title"), _q("dc", "subject"), _q("dc", "description"),
    _q("cp", "keywords"), _q("cp", "category"), _q("cp", "contentStatus"),
    _q("cp", "lastPrinted"),
]
_CORE_EPOCH = [_q("dcterms", "created"), _q("dcterms", "modified")]
# extended-properties (app.xml) identity fields — matched by local name so the
# extended-properties prefix (ap:/Ap:/none) is irrelevant.
_APP_IDENTITY_LOCALS = frozenset({"Company", "Manager", "HyperlinkBase"})
# comment-author identity attributes, on cmAuthor / author elements.
_AUTHOR_ATTRS = ("name", "initials", "userId", "providerId")


def _redact_runs(root: etree._Element) -> int:
    """Length-preserving blank of every DrawingML text run (`a:t`)."""
    n = 0
    for t in root.iter(opc.qn("a:t")):
        if t.text:
            t.text = "".join(" " if c.isspace() else "x" for c in t.text)
            n += 1
    return n


def anonymize_pptx(
    pptx: str | Path,
    out: str | Path | None = None,
    *,
    force: bool = False,
    redact_text: bool = False,
) -> dict[str, Any]:
    """Strip PII from *pptx*. out=None anonymizes in place (requires force).

    Returns a report of what was scrubbed. Unparseable parts are passed through
    untouched (never corrupt a deck we cannot read)."""
    report: dict[str, Any] = {
        "source": str(Path(pptx).resolve()), "dest": "",
        "core_fields": [], "app_fields": [], "custom_props_dropped": 0,
        "comment_authors": 0, "text_runs_redacted": 0, "redact_text": redact_text,
        "unparsed": [],
    }

    def _core(root: etree._Element) -> None:
        for tag in _CORE_IDENTITY:
            el = root.find(f".//{tag}")
            if el is not None and (el.text or "").strip():
                el.text = _PLACEHOLDER
                report["core_fields"].append(etree.QName(tag).localname)
        for tag in _CORE_BLANK:
            el = root.find(f".//{tag}")
            if el is not None and (el.text or "").strip():
                el.text = ""
                report["core_fields"].append(etree.QName(tag).localname)
        for tag in _CORE_EPOCH:
            el = root.find(f".//{tag}")
            if el is not None and (el.text or "").strip():
                el.text = _EPOCH

    def _app(root: etree._Element) -> None:
        for el in root.iter():
            if etree.QName(el).localname in _APP_IDENTITY_LOCALS and (el.text or "").strip():
                report["app_fields"].append(etree.QName(el).localname)
                el.text = ""

    def _custom(root: etree._Element) -> None:
        # Drop every custom property (name AND value can identify) but keep the
        # (now empty) Properties root so the part + its content-type stay valid.
        dropped = 0
        for prop in list(root):
            if etree.QName(prop).localname == "property":
                root.remove(prop)
                dropped += 1
        report["custom_props_dropped"] += dropped

    def _authors(root: etree._Element) -> None:
        for el in root.iter():
            if etree.QName(el).localname in ("cmAuthor", "author"):
                touched = False
                for i, attr in enumerate(_AUTHOR_ATTRS):
                    for key in [k for k in el.attrib if etree.QName(k).localname == attr]:
                        el.set(key, f"author{report['comment_authors'] + 1}"
                                if attr in ("name", "initials") else "")
                        touched = True
                if touched:
                    report["comment_authors"] += 1

    def transform(name: str, data: bytes) -> bytes:
        handler = None
        if name == "docProps/core.xml":
            handler = _core
        elif name == "docProps/app.xml":
            handler = _app
        elif name == "docProps/custom.xml":
            handler = _custom
        elif re.fullmatch(r"ppt/(comment|)[Aa]uthors\.xml", name) \
                or name in ("ppt/authors.xml", "ppt/commentAuthors.xml"):
            handler = _authors
        elif redact_text and re.fullmatch(
                r"ppt/(slides|notesSlides)/[^/]+\.xml", name):
            handler = "text"  # sentinel
        if handler is None:
            return data
        decl = opc.xml_declaration(data)
        try:
            root = opc.parse(data)
        except XMLSyntaxError:
            report["unparsed"].append(name)
            return data
        if handler == "text":
            report["text_runs_redacted"] += _redact_runs(root)
        else:
            handler(root)
        return opc.serialize(root, declaration=decl)

    dest = rewrite_package(pptx, out, transform, force=force)
    report["dest"] = str(dest)
    return report
