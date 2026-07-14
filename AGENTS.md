# designmd-pptx — agent guide

Compile [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) / Stitch `DESIGN.md` into [OfficeCLI](https://github.com/officecli/officecli) PPTX tokens, ordered decks, and staging-safe apply. Two backends (docs/officecli-backends.md): the legacy shape-level binary drives the precision pipeline; the official agent-bridge (JSON-RPC, capability-first) drives `render`.

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
- Geometry: a recipe uses **one declared** system in `recipes.PATTERN_LAYOUT`
  (`engine` | `hybrid` | `structured` | `fixed`). Pure engine recipes
  (bullets/feature_cards/comparison_2col/image_text_2col/…) must not reintroduce
  hand coordinates; hybrid may combine fixed chrome + engine region + post-solve
  markers. Empty scaffolds default to `CORE_SEQUENCE` (not the full catalog).
- Overwrite of generated .pptx is staging-safe and requires `--force` / `DESIGNMD_FORCE=1`.
- Licensed Infograpify (or other premium) `.pptx` templates are **local reference only** —
  keep under `infograpify_ppt_templates/` (gitignored). Never commit originals.
  Analyze with `python -m designmd_pptx reference` (see `docs/infograpify-reference.md`).

## Using the toolkit

```powershell
$env:PYTHONPATH = "$PWD\python"
python -m designmd_pptx scaffold python\fixtures\linear.DESIGN.md -o out\demo --content python\examples\content.deck.json
python -m designmd_pptx extract old.pptx -o extracted    # existing deck → deck-spec draft
python -m designmd_pptx restyle old.pptx DESIGN.md -o new.pptx   # rebrand in place
python -m designmd_pptx master deck.pptx DESIGN.md --potx brand.potx  # brand master + template
python -m designmd_pptx doctor   # verify officecli + skill routing (Claude/Codex/Grok)
python -m designmd_pptx a11y --design default --content python/examples/content.deck.json
python -m designmd_pptx benchmark -o benchmark-out
python -m designmd_pptx benchmark --public -o public-benchmark-out   # #42 ≥100 decks
python -m designmd_pptx generate content.deck.json -o gen --directive "Keynote style"  # #21
python -m designmd_pptx animate deck.pptx --entrance fade --force   # #40
python -m designmd_pptx windows-install --plan --check-script       # #35
python -m designmd_pptx compose brief.md -o composed --design default   # outline → deck-spec
```

Windows non-dev install: `packaging/windows/Install-DesignmdPptx.ps1`
(see `docs/windows-installer.md`).

No brand DESIGN.md? Use the literal `default` as the design argument. Author content
via `compose` (markdown brief → deck-spec draft), not by hand-writing JSON. Always
finish an `--apply` run with `--screenshot` (add `--gate3` to abort on render failure)
and inspect the contact sheet (Gate 3). Text budgets are CJK-aware — over-budget
content must be shortened or split, never font-shrunk.

See `skills/officecli-pptx-designmd/SKILL.md` for full CLI reference and hard rules.
