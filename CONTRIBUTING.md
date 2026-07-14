# Contributing

## Layout

| Path | Purpose |
|---|---|
| `plugin.json` | Grok plugin manifest |
| `.grok/skills/` | Agent skills |
| `.grok/commands/` | Slash commands |
| `python/designmd_pptx/` | Compiler package |
| `python/tests/` | Unit tests |
| `scripts/check-plugin.mjs` | Static plugin layout checks |

## Dev loop

```bash
# from plugin root
export PYTHONPATH=python   # Windows: $env:PYTHONPATH = "python"
pip install -r python/requirements.txt
python -m unittest discover -s python/tests -v
node scripts/check-plugin.mjs
```

## Licensed premium templates (Phase 2)

Use **personally licensed** premium decks (e.g. Infograpify) as **visual
reference only**:

- Store originals in `infograpify_ppt_templates/` (gitignored) or outside the repo.
- **Never commit** original `.pptx` / vendor media / force-add ignored paths.
- Analyze with `python -m designmd_pptx reference …` (text redacted by default).
- Commit only original DESIGN.md tokens, recipes, layout code, and synthetic fixtures.
- See [docs/infograpify-reference.md](docs/infograpify-reference.md).

```bash
python -m designmd_pptx reference infograpify_ppt_templates --catalog -o .ref-analysis
```

## Sync from monorepo workspace (optional)

If you also maintain `../designmd-pptx` as a workspace copy, re-copy into `python/` before release and bump `plugin.json` / `package.json` versions together.
