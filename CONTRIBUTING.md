# Contributing

Thanks for helping improve designmd-pptx. This guide covers local setup, tests,
pattern authoring, PR checks, and governance.

## Layout

| Path | Purpose |
|---|---|
| `python/designmd_pptx/` | Compiler package (single source of truth) |
| `python/tests/` | Unit tests (`unittest`) |
| `python/fixtures/`, `python/examples/` | DESIGN.md + deck-spec samples |
| `skills/`, `commands/` | **Canonical** agent skill + slash command |
| `.grok/skills/`, `.grok/commands/` | Generated adapters — never hand-edit |
| `.claude-plugin/` | Claude Code plugin + marketplace manifests |
| `plugin.json`, `package.json` | Grok / npm manifests (keep versions aligned) |
| `docs/` | Install, concepts, gallery, maturity, migration |
| `scripts/sync-adapters.mjs` | Canonical → `.grok/` sync |
| `scripts/check-plugin.mjs` | Plugin layout + adapter drift |

## Dev setup

```bash
git clone https://github.com/kimmingul/designmd-pptx.git
cd designmd-pptx
python3 -m venv .venv && source .venv/bin/activate  # optional
pip install -r python/requirements.txt
export PYTHONPATH=python   # Windows: $env:PYTHONPATH = "python"
python -m designmd_pptx doctor
```

Optional: `pip install -e ".[schema]"` for full jsonschema validation.

## Test conventions

```bash
# Full suite (what CI unit jobs run)
npm test
# or:
PYTHONPATH=python python -m unittest discover -s python/tests -v

# Plugin / adapter drift
npm run sync    # after editing skills/ or commands/
npm run check

# New Phase 4 gates
PYTHONPATH=python python -m designmd_pptx a11y --design default \
  --content python/examples/content.deck.json
PYTHONPATH=python python -m designmd_pptx benchmark -o /tmp/bm-out
```

**Rules for tests**

- Prefer driving real package entry points (`main([...])`, public module APIs).
- Do not hard-code expected hex/layout magic that re-implements production code.
- OfficeCLI-dependent E2E classes **self-skip** when no binary is present.
- New modules ship unit tests in `python/tests/test_*.py`.

## Pattern / recipe authoring

1. Prefer extending `recipes.py` + `deck.py` content keys + `validate.CONTENT_KEYS`.
2. **One geometry system per recipe**: layout-engine tree **or** fixed cm — never both.
3. Engine-solved patterns (bullets, feature_cards, comparison_2col, image_text_2col, …)
   must stay 100% layout-engine; do not reintroduce hand coordinates.
4. Text: floors title ≥36pt, body ≥18pt; over-budget → shorten/split, never font-shrink.
5. Images: `alt` required when `src` set; a11y suite will fail otherwise.
6. Add catalog coverage in tests (`test_domain_patterns`, `test_v21_premium`, etc.).
7. Document new recipes in `skills/officecli-pptx-designmd/SKILL.md` Patterns section,
   then `npm run sync`.

## Licensed reference material

Use **personally licensed** premium decks (e.g. Infograpify) as **visual reference only**:

- Store originals in `infograpify_ppt_templates/` (gitignored) or outside the repo.
- **Never commit** original `.pptx` / vendor media / force-add ignored paths.
- Analyze with `python -m designmd_pptx reference …` (text redacted by default).
- Commit only original DESIGN.md tokens, recipes, layout code, and synthetic fixtures.
- See [docs/infograpify-reference.md](docs/infograpify-reference.md).

## PR checks (required locally before push)

| Check | Command | Expect |
|---|---|---|
| Unit tests | `npm test` | OK |
| Plugin layout | `npm run check` | all checks passed |
| Adapters | edit only `skills/` + `commands/`, then `npm run sync` | no drift |
| a11y (if tokens/content changed) | `python -m designmd_pptx a11y …` | 0 errors |
| Benchmark smoke | `python -m designmd_pptx benchmark -o out/bm` | PASS |
| Versions | bump together: `plugin.json`, `.claude-plugin/plugin.json`, `package.json`, `python/designmd_pptx/__init__.py` | aligned |

CI runs unit × (ubuntu/macOS/windows × py3.10–3.12), package wheel install, e2e pin probe,
and the fixture **benchmark** job.

## Governance & triage

See [docs/governance.md](docs/governance.md) for maintainers, labels, and release
ownership. Issue templates: bug report + feedback under `.github/ISSUE_TEMPLATE/`.

## Version alignment

Keep these in sync on release commits:

- `python/designmd_pptx/__init__.py` → `__version__`
- `package.json` / `plugin.json` / `.claude-plugin/plugin.json`

## License

By contributing you agree contributions are MIT-licensed unless noted otherwise.
Brand DESIGN.md tokens remain under their upstream collection terms.
