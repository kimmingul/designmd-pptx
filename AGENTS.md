# designmd-pptx — agent guide

Compile [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) / Stitch `DESIGN.md` into [officecli](https://github.com/iOfficeAI/OfficeCLI) PPTX tokens, ordered decks, and staging-safe apply.

## Layout

- `python/designmd_pptx/` — core compiler (single source of truth)
- `skills/`, `commands/` — **canonical** agent skill + slash command
- `.grok/skills/`, `.grok/commands/` — generated Grok adapters; never hand-edit
- `.claude-plugin/` — Claude Code plugin + self-marketplace manifests
- `plugin.json` — Grok Build plugin manifest
- `scripts/sync-adapters.mjs` — canonical → adapter sync (`--check` for drift)
- `scripts/install-codex.ps1` — install into `~/.codex/skills/`

## Commands

```bash
npm run sync    # skills/ + commands/ → .grok/ adapters
npm run check   # plugin layout checks + adapter drift check
npm test        # python -m unittest discover -s python/tests -v
```

## Rules

- Edit skills only under `skills/` and `commands/`, then run `npm run sync`. The `.grok/` copies are generated.
- Keep versions aligned across `plugin.json`, `.claude-plugin/plugin.json`, `package.json`, and `python/designmd_pptx/__init__.py`.
- Python changes require `npm test` to pass; skill/manifest changes require `npm run check`.
- Overwrite of generated .pptx is staging-safe and requires `--force` / `DESIGNMD_FORCE=1`.

## Using the toolkit

```powershell
$env:PYTHONPATH = "$PWD\python"
python -m designmd_pptx scaffold python\fixtures\linear.DESIGN.md -o out\demo --content python\examples\content.deck.json
python -m designmd_pptx extract old.pptx -o extracted    # existing deck → deck-spec draft
python -m designmd_pptx restyle old.pptx DESIGN.md -o new.pptx   # rebrand in place
python -m designmd_pptx master deck.pptx DESIGN.md --potx brand.potx  # brand master + template
```

See `skills/officecli-pptx-designmd/SKILL.md` for full CLI reference and hard rules.
