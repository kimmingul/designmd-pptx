# designmd-pptx — VS Code / Cursor extension

MVP editor surface chosen in [#44](https://github.com/kimmingul/designmd-pptx/blob/main/docs/editor-integration-decision.md) / implemented for **#45**.

Thin **command palette + explorer + Problems** shell around the existing  
`python -m designmd_pptx` CLI. Does **not** bundle OfficeCLI or licensed templates.

## Install (distribution path)

### A. Development / sideload (MVP)

1. Open this folder as an extension in VS Code:
   - Command Palette → **Developer: Install Extension from Location…**  
     select `editor/vscode`, **or**
   - `code --install-extension` is for VSIX; for raw folder use F5 from a  
     dedicated extension host (see below).
2. Or package a VSIX (requires Node 18+):

```bash
cd editor/vscode
npm install -g @vscode/vsce   # once
npx @vscode/vsce package --no-dependencies
# → designmd-pptx-0.2.0.vsix
code --install-extension designmd-pptx-0.2.0.vsix
```

Cursor: **Extensions → … → Install from VSIX…**

### B. GitHub Releases

Attach `designmd-pptx-*.vsix` to the release notes (see root `docs/install.md`).

### C. Marketplace (later)

Publisher `kimmingul`, same repo URL. Not required for MVP acceptance.

## Prerequisites

- Workspace folder opened (repo checkout or project that vendors `python/`)
- Python 3.10+ with designmd-pptx importable:
  - `pip install -e .` from repo root, **or**
  - extension auto-sets `PYTHONPATH` to workspace `python/`
- Optional: OfficeCLI via `designmd-pptx: Doctor Install (dry-run)` then terminal install

## Commands (palette: `designmd-pptx:`)

| Command | CLI |
|---|---|
| Doctor | `doctor` |
| Doctor Install (dry-run) | `doctor --install --dry-run` |
| Compose brief → deck-spec | `compose <md> -o out/…` |
| Scaffold deck | `scaffold default -o out/… --content …` |
| Accessibility audit | `a11y --design default --content …` |
| Refine deck-spec | `refine … --feedback` |
| Fixture benchmark | `benchmark -o …` |
| Open contact sheet / Gate3 JSON | opens workspace files |

## Settings

| Setting | Meaning |
|---|---|
| `designmdPptx.pythonPath` | Python binary |
| `designmdPptx.cliPath` | Optional `designmd-pptx` script |
| `designmdPptx.pythonPathExtra` | Extra `PYTHONPATH` |
| `designmdPptx.defaultDesign` | `default` or path to DESIGN.md |
| `designmdPptx.outputDir` | Under workspace (default `out/designmd`) |

## Explorer & Problems

- Activity bar **designmd-pptx** lists DESIGN.md, `*.deck.json`, briefs, reports.
- Writing `a11y.report.json` / `refine.report.json` / `*.gate3.json` loads  
  findings into the **Problems** panel.

## End-to-end author → deck

1. Open repo workspace.  
2. Write `brief.md` → **Compose brief**.  
3. **Scaffold deck** with `composed/content.deck.json`.  
4. **Accessibility audit** / **Refine** as needed.  
5. In terminal (or later: apply command):  
   `python -m designmd_pptx apply --force --screenshot …` when legacy OfficeCLI is available.

## Out of scope (MVP)

Live PPTX WYSIWYG, Office.js Add-in, animation timeline, bundling OfficeCLI.
