"""Corpus pipeline suite (issue #36): PII anonymization + held-out split."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from lxml import etree

from designmd_pptx import corpus
from designmd_pptx.anonymize import anonymize_pptx

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC = "http://purl.org/dc/elements/1.1/"

CORE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<cp:coreProperties xmlns:cp="{CP}" xmlns:dc="{DC}" '
    'xmlns:dcterms="http://purl.org/dc/terms/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    '<dc:creator>John Doe</dc:creator>'
    '<cp:lastModifiedBy>Jane Smith</cp:lastModifiedBy>'
    '<dc:title>Secret Acquisition Plan</dc:title>'
    '<dcterms:created xsi:type="dcterms:W3CDTF">2024-03-15T10:00:00Z</dcterms:created>'
    '</cp:coreProperties>'
)
# app.xml with a DEFAULT namespace (no prefix) — prefix-independence check.
APP = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
    '<Application>Microsoft Office PowerPoint</Application>'
    '<Company>Acme Corp</Company><Manager>Boss Person</Manager></Properties>'
)
CUSTOM = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
    '<property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="ClientName">'
    '<vt:lpwstr>BigCo Industries</vt:lpwstr></property></Properties>'
)
AUTHORS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<p:cmAuthorLst xmlns:p="{P}">'
    '<p:cmAuthor id="0" name="Reviewer Name" initials="RN"/></p:cmAuthorLst>'
)
SLIDE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<p:sld xmlns:a="{A}" xmlns:p="{P}"><p:cSld><p:spTree>'
    '<a:t>Confidential Q3 revenue: $4.2M</a:t>'
    '</p:spTree></p:cSld></p:sld>'
)


def _make_deck(path: Path) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("docProps/core.xml", CORE)
        z.writestr("docProps/app.xml", APP)
        z.writestr("docProps/custom.xml", CUSTOM)
        z.writestr("ppt/commentAuthors.xml", AUTHORS)
        z.writestr("ppt/slides/slide1.xml", SLIDE)
    return path


class AnonymizeV36(unittest.TestCase):
    def _anon(self, **kw):
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        src = _make_deck(root / "in.pptx")
        out = root / "out.pptx"
        report = anonymize_pptx(src, out=out, **kw)
        self.zf = zipfile.ZipFile(out)
        return report

    def _part(self, name):
        return etree.fromstring(self.zf.read(name))

    def test_metadata_scrubbed(self):
        report = self._anon()
        core = self._part("docProps/core.xml")
        self.assertEqual(core.find(f"{{{DC}}}creator").text, "anonymized")
        self.assertEqual(core.find(f"{{{CP}}}lastModifiedBy").text, "anonymized")
        self.assertIn(core.find(f"{{{DC}}}title").text or "", ("", None))
        app = self._part("docProps/app.xml")
        locals_ = {etree.QName(e).localname: (e.text or "") for e in app}
        self.assertEqual(locals_["Company"], "")
        self.assertEqual(locals_["Manager"], "")
        self.assertEqual(locals_["Application"], "Microsoft Office PowerPoint")  # kept
        custom = self._part("docProps/custom.xml")
        self.assertEqual(len(custom), 0)                     # every property dropped
        self.assertGreaterEqual(report["custom_props_dropped"], 1)

    def test_comment_author_anonymized(self):
        self._anon()
        authors = self._part("ppt/commentAuthors.xml")
        cm = authors[0]
        self.assertEqual(cm.get("name"), "author1")
        self.assertNotEqual(cm.get("name"), "Reviewer Name")

    def test_content_preserved_by_default(self):
        self._anon()
        slide = self._part("ppt/slides/slide1.xml")
        self.assertEqual(slide.find(f".//{{{A}}}t").text, "Confidential Q3 revenue: $4.2M")

    def test_redact_text_blanks_but_preserves_length(self):
        report = self._anon(redact_text=True)
        slide = self._part("ppt/slides/slide1.xml")
        txt = slide.find(f".//{{{A}}}t").text
        self.assertNotIn("Confidential", txt)
        self.assertNotIn("4.2M", txt)
        self.assertEqual(len(txt), len("Confidential Q3 revenue: $4.2M"))
        self.assertGreaterEqual(report["text_runs_redacted"], 1)


class CorpusSplitV36(unittest.TestCase):
    def _entry(self, i, **kw):
        e = {"id": f"deck{i}", "file": f"corpus/deck{i}.pptx",
             "source": "internal", "license": "private",
             "provenance": "anonymized", "sha256": f"{i:064x}"}
        e.update(kw)
        return e

    def test_validate_flags_missing_and_dupes(self):
        entries = [self._entry(1), {"id": "deck1"}]  # missing fields + dup id
        errors = corpus.validate_entries(entries)
        self.assertTrue(any("missing" in e for e in errors))
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_holdout_is_deterministic(self):
        e = self._entry(7)
        self.assertEqual(corpus.is_held_out(e), corpus.is_held_out(e))  # stable

    def test_explicit_flag_overrides_hash(self):
        self.assertTrue(corpus.is_held_out(self._entry(1, held_out=True)))
        self.assertFalse(corpus.is_held_out(self._entry(1, held_out=False)))

    def test_split_and_stats(self):
        entries = [self._entry(i) for i in range(20)]
        train, held = corpus.split(entries)
        self.assertEqual(len(train) + len(held), 20)
        self.assertGreater(len(held), 0)          # ~1/5 held out
        self.assertGreater(len(train), len(held))
        s = corpus.stats(entries)
        self.assertEqual(s["total"], 20)
        self.assertEqual(s["licenses"], ["private"])


if __name__ == "__main__":
    unittest.main()
