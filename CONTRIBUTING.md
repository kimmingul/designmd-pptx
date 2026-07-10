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

## Sync from monorepo workspace (optional)

If you also maintain `../designmd-pptx` as a workspace copy, re-copy into `python/` before release and bump `plugin.json` / `package.json` versions together.
