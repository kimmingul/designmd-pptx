# Editor integration — discovery & decision (#44)

**Status:** Decision complete. **Primary surface: VS Code / Cursor extension**  
(agent-workspace native). PowerPoint Add-in is **explicitly not** the v2.1 primary.

**Blocks:** #45 (implementation).  
**Non-goal for this spike:** shipping either product — decision + feasibility only.

---

## 1. Usage-signal review

Where designmd-pptx users actually work today:

| Signal | Evidence | Weight |
|---|---|---|
| **Agent terminals (Claude Code, Codex, Grok Build)** | Skills/commands, `AGENTS.md`, plugin manifests, `doctor` skill routing | **Primary** |
| **Git repos + DESIGN.md / briefs** | Canonical flow: compose → scaffold → apply; DESIGN.md lives next to product code | **Primary** |
| **Local CLI / PYTHONPATH checkout** | README, docs/install, package console entry | High |
| **PowerPoint desktop** | Destination of materialize (`apply` / legacy OfficeCLI), Gate 3 contact sheets | Consumer of **output**, not authoring home |
| **Office on the web / Teams** | No product telemetry; OfficeCLI agent-bridge already covers draft `render` | Low for v2.1 |

**Implication:** Authors and agents co-edit **markdown + deck-spec JSON in a workspace**.  
They do not primarily open PowerPoint to *compose* structure; they open it to *review* slides after `apply`/`render`.

---

## 2. Options compared

| Criterion | **A. PowerPoint Add-in** | **B. VS Code / Cursor extension** (chosen) |
|---|---|---|
| Matches current authoring surface | Weak — leaves git/DESIGN.md | Strong — same folder as code + agents |
| Agent interoperability | Hard (add-in sandbox, separate process) | Natural (shared files, terminals, tasks) |
| Uses existing CLI | Would re-wrap or reimplement | Thin UI over `designmd-pptx` / `python -m designmd_pptx` |
| OfficeCLI dependency | High (in-app host) | Unchanged (shell / tasks still call CLI) |
| Distribution | AppSource review, Microsoft identity | VS Marketplace / Open VSX / VSIX sideload |
| Auth complexity | Microsoft account + optional Graph | Optional GH auth only if marketplace private |
| Effort to MVP | Large (Office.js, manifests, host matrix) | Medium (webview + task provider + tree views) |
| Risk of dual product | High if we also keep CLI | Low — extension is a **shell** around CLI |

### Decision

**Pick B — VS Code / Cursor extension** as the single v2.1 editor surface.

**Rationale (summary):**

1. designmd-pptx is already an **agent + git workspace** tool; the highest-leverage UI is “run compose/scaffold/refine/a11y from the folder where DESIGN.md lives.”
2. PowerPoint remains the **renderer/viewer** via OfficeCLI — not the authoring IDE. Building an Add-in would duplicate backend work without improving agent loops.
3. One surface only (spike AC): we deliberately **do not** build a PPT Add-in in parallel.

**Rejected for v2.1 primary:** PowerPoint Task Pane Add-in, Google Slides, standalone Electron app.

**Revisit later if:** corporate users demand in-PPTX edit with zero git; then a thin Add-in that *only* imports/exports deck-spec JSON could be considered under a new milestone — still not dual-build with VS Code.

---

## 3. Feasibility notes

### 3.1 Packaging

| Item | Plan |
|---|---|
| Extension host | VS Code 1.85+ / Cursor-compatible |
| Bundle | TypeScript extension; spawn `designmd-pptx` or `python -m designmd_pptx` with `PYTHONPATH` / venv detection |
| Python | Prefer installed `designmd-pptx` console script; fallback to workspace `python/` |
| OfficeCLI | Not bundled; surface `doctor --install` from a command palette action |
| Assets | No Infograpify / licensed pptx in the VSIX |

### 3.2 Auth

| Path | Auth |
|---|---|
| Local CLI commands | None |
| Optional cloud vision (`DESIGNMD_VISION_CMD`) | User-configured env; extension does not store keys in repo |
| Marketplace publish | Publisher identity only |
| Private org gallery | Org admin; no Microsoft Graph required |

### 3.3 Distribution

1. **MVP:** `.vsix` attached to GitHub Releases (`designmd-pptx-editor-x.y.z.vsix`)
2. **Public:** Visual Studio Marketplace under same publisher as docs
3. **Cursor:** Install from VSIX or Open VSX if listed
4. **Docs:** `docs/install.md` section “VS Code / Cursor extension”

### 3.4 MVP feature cut (for #45 — not this spike)

1. Tree: DESIGN.md, briefs, content.deck.json in workspace  
2. Commands: compose, scaffold, a11y, refine, doctor  
3. Preview: open contact sheet / `.gate3.json` if present  
4. Problems: surface fit/a11y/refine report diagnostics  
5. **Out of MVP:** live PPTX WYSIWYG, Office.js co-authoring, animation timeline

### 3.5 Risks

| Risk | Mitigation |
|---|---|
| Users expect “edit inside PowerPoint” | Docs: PPTX is Gate 3 / apply destination; authoring is deck-spec |
| Python not on PATH | Extension setting `designmdPptx.pythonPath` + doctor command |
| Cursor API drift | Stick to standard VS Code extension API |

---

## 4. Acceptance checklist (#44)

- [x] Usage-signal review (section 1)
- [x] Decision: **VS Code / Cursor extension** over PowerPoint Add-in (section 2)
- [x] Feasibility: auth, packaging, distribution (section 3)

## 5. Next (#45)

Implement the VS Code extension MVP as listed in §3.4; track under #45. Do not open a PPT Add-in workstream in the same release train.

### Implementation status

- [x] MVP shipped under [`editor/vscode/`](../editor/vscode/) (commands, explorer, diagnostics, VSIX packaging docs)
- [ ] Marketplace listing (optional; VSIX sideload is the MVP distribution path)
