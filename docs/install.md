# Install

## Requirements

- Python 3.10+
- PyYAML, lxml, defusedxml (`python/requirements.txt`)
- Optional: Node/npm for official `officecli` (agent-bridge / `render`)
- Optional: legacy shape-level OfficeCLI binary for scaffold/apply precision

## From a checkout

```bash
git clone https://github.com/kimmingul/designmd-pptx.git
cd designmd-pptx
pip install -r python/requirements.txt
export PYTHONPATH=python   # Windows: $env:PYTHONPATH = "python"
python -m designmd_pptx doctor
```

## pip package

```bash
pip install .                  # from checkout
# pip install designmd-pptx    # when published to PyPI
designmd-pptx doctor
```

The wheel is self-contained: schemas, `compatibility.json`,
`benchmark_thresholds.json`, and the default house style ship inside
`designmd_pptx/`.

## doctor --install (version-locked)

```bash
python -m designmd_pptx doctor --install --dry-run   # print plan
python -m designmd_pptx doctor --install             # apply
```

Installs the official `officecli` **pin** from
`python/designmd_pptx/compatibility.json` by downloading the matching
**officecli-dist** release asset for your OS/arch (npm often lags — e.g. npm
max 0.2.106 while the pin is 0.2.117). Binary lands in
`~/.local/share/designmd-pptx/officecli-official/` with a symlink to
`~/.local/bin/officecli` when writable. PyYAML is installed via pip when
missing. The legacy shape-level binary remains **manual** (release URL printed).

## Agent plugins

| Platform | Install |
|---|---|
| Claude Code | `/plugin marketplace add kimmingul/designmd-pptx` then `/plugin install designmd-pptx@designmd-pptx` |
| Codex | `pwsh scripts/install-codex.ps1` |
| Grok | copy/link into `~/.grok/installed-plugins/designmd-pptx-local` (see AGENTS.md) |

## VS Code / Cursor extension (#45)

Primary **editor surface** (decision: [editor-integration-decision.md](editor-integration-decision.md)).

```bash
cd editor/vscode
npx @vscode/vsce package --no-dependencies   # → designmd-pptx-0.1.0.vsix
code --install-extension designmd-pptx-0.1.0.vsix
# Cursor: Extensions → Install from VSIX…
```

Or **Developer: Install Extension from Location…** → select `editor/vscode`.

Commands (palette `designmd-pptx:`): Doctor, Compose, Scaffold, A11y, Refine,  
Benchmark, open contact sheet / Gate 3 JSON. Activity bar lists DESIGN.md and  
`*.deck.json`. See [editor/vscode/README.md](../editor/vscode/README.md).

## Version pin

Do not hardcode OfficeCLI versions in scripts. Read
`compatibility.json` (or `python -m designmd_pptx.compat`).
