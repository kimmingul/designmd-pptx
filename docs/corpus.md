# Validation corpus (issue #36)

Real decks expose failures that synthetic fixtures never will — unusual namespace
prefixes, `sysClr` theme slots, BOM-prefixed parts, `Default`-declared content
types, deep SmartArt, dense tables. The corpus is a set of **anonymized real
`.pptx` decks** the toolchain is tested against, with provenance and a stable
held-out split so patterns are never tuned to the evaluation set.

This repo ships the **pipeline and format**, not the decks — populating the
corpus with ≥10 (Phase 0) → ≥50 (Phase 4) real decks is a manual, rights-aware
step.

## 1. Anonymize a deck

```bash
designmd-pptx anonymize path/to/real-deck.pptx -o corpus/<id>.pptx
# highly sensitive? also length-preserve-blank visible text (layout kept):
designmd-pptx anonymize path/to/real-deck.pptx -o corpus/<id>.pptx --redact-text
```

`anonymize` (namespace-aware, staging-safe) strips:

- **`docProps/core.xml`** — `creator` / `lastModifiedBy` → `anonymized`; `title`,
  `subject`, `description`, `keywords`, `category`, `contentStatus` → blank;
  `created` / `modified` → epoch.
- **`docProps/app.xml`** — `Company`, `Manager`, `HyperlinkBase` → blank.
- **`docProps/custom.xml`** — every custom property dropped (name **and** value).
- **comment authors** (`commentAuthors.xml` / `authors.xml`) — names/initials →
  `authorN`, userId/providerId → blank.
- **`--redact-text`** — every `a:t` run blanked char-for-char (spaces kept), so
  layout/geometry survive while wording does not.

Slide **content is preserved by default** so the corpus reflects real structure;
the printed report lists exactly what was scrubbed.

> Anonymization removes authorship metadata and (optionally) text — it does **not**
> guarantee removal of confidential content embedded in images, charts, or
> speaker notes. Review before redistributing, and treat `license: private`
> decks as non-committable (they are gitignored under `corpus/`).

## 2. Record it in the manifest

Add an entry to [`corpus/corpus.manifest.json`](../corpus/corpus.manifest.json)
(schema: [`corpus.manifest.schema.json`](../python/designmd_pptx/schema/corpus.manifest.schema.json)):

```json
{
  "id": "acme-fy26-board",
  "file": "corpus/acme-fy26-board.pptx",
  "source": "internal (Acme board deck, 2026)",
  "license": "private",
  "provenance": "exported from PowerPoint; anonymized with designmd-pptx anonymize v1.7.1",
  "sha256": "…", "admitted_at": "2026-07-14"
}
```

Required fields: `id`, `file`, `source`, `license`, `provenance`.

## 3. Verify + inspect the split

```bash
designmd-pptx corpus corpus/corpus.manifest.json
# corpus: 12 decks — 10 train / 2 held-out
```

**Held-out policy.** ~1/5 of decks are held out for evaluation by a **stable
hash** of each deck's `sha256` (falling back to `id`) — the split does not drift
between runs and cannot be gamed by reordering. Pin a deck explicitly with
`"held_out": true|false`. Never tune patterns or thresholds against held-out
decks; they exist to measure, not to fit.

## Maturity targets

| Milestone | Corpus size | Purpose |
|---|---|---|
| Phase 0 | ≥ 10 decks admitted | pipeline + format proven on real structure |
| Phase 4 (v2.0) | ≥ 50 decks, held-out benchmark | before/after regression gate (#37) |
| v2.1 | 100+ published benchmark | **shipped** as synthetic public suite — see [public-benchmark.md](public-benchmark.md) (#42) |

The **public** 100+ suite does not require admitting private decks into this
repo. Run `python -m designmd_pptx benchmark --public --publish-docs` to
regenerate methodology + summarized results.
