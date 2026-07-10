# Install designmd-pptx (Grok plugin)

## Layout

```text
designmd-pptx/
  plugin.json             # Grok manifest
  package.json
  skills/, commands/      # canonical sources (synced to .grok/ via npm run sync)
  .grok/skills/officecli-pptx-designmd/SKILL.md
  .grok/commands/designmd-pptx.md
  python/                 # vendored designmd_pptx package + fixtures/examples
  scripts/check-plugin.mjs
```

## Local install (this machine)

```powershell
$src = "C:\Users\kimmi\Downloads\ppt\designmd-pptx"
$dst = "$env:USERPROFILE\.grok\installed-plugins\designmd-pptx-local"
robocopy $src $dst /E /XD __pycache__ .git out
pip install -r "$dst\python\requirements.txt"
$env:PYTHONPATH = "$dst\python"
python -m designmd_pptx --help
node "$dst\scripts\check-plugin.mjs"
```

Register entry (optional, for registry.json):

```json
"designmd-pptx-local": {
  "kind": { "type": "Path", "path": "C:\\Users\\...\\.grok\\installed-plugins\\designmd-pptx-local" },
  "plugins": { "designmd-pptx": { "version": "1.1.0" } }
}
```

## Usage

```powershell
$env:PYTHONPATH = "$env:USERPROFILE\.grok\installed-plugins\designmd-pptx-local\python"
python -m designmd_pptx scaffold DESIGN.md -o out/demo --content examples/content.deck.json
```

In Grok chat: mention DESIGN.md → PPTX or run `/designmd-pptx` so the skill auto-loads.
