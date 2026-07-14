# Changelog

All notable changes to designmd-pptx are documented here.

## [2.1.1] — 2026-07-15

Adversarial review follow-up (Codex gpt-5.6-sol@high **BLOCK** findings).

### Security
- **VS Code extension (#45):** run CLI via `child_process.spawn` + `shell:false`
  argv array; never `terminal.sendText` of shell-joined user feedback.

### Fixed
- **Animation (#40):** CT_Slide child order (`transition`/`timing` before
  `extLst`); numeric slide sort; in-place/`-o` overwrite requires `--force`;
  appear uses `animEffect` (no broken `p:set`); `pulse` emphasis removed as
  unimplemented.
- **Refine (#19):** deferred continuation inserts so multi-slide density
  patches no longer shift indices mid-pass.
- **Generative (#21):** overflow lists/prose preserved under `content.overflow`;
  external placements validated on-canvas; `DESIGNMD_LAYOUT_CMD` wired into
  freeform path.
- **Extract (#22):** `c:barChart` + `barDir=col` → `column` (not bar).
- **Windows installer (#35):** pin `designmd-pptx==2.1.1`; InstallRoot must
  stay under LocalAppData product dir; uninstall requires product manifest;
  OfficeCLI extract limited to `officecli.exe` + optional SHA-256.
- **Public benchmark (#42):** recipe-builder smoke per fixture; honest docs
  (synthetic deck-spec suite, not rendered PPTX corpus); gate not hard-coded
  pass without smoke.

### Changed
- Version **2.1.1**; `npm run check` requires exact version equality across
  plugin / package / `__version__`.

## [2.1.0] — 2026-07-15

Phase 5 / **intelligence** release. Production core from v2.0.0 plus generative
layout, animation, public benchmark, Windows installer, refine loop, chart/table
reconstruction, and VS Code/Cursor editor MVP.

### Added

#### Intelligence & layout
- **`refine`** CLI (#19) — iterative visual refinement: natural-language feedback
  and Gate 3 findings → deterministic deck-spec patches (split / shorten /
  recipe swap) over 1–N rounds.
- **`generate`** CLI (#21) — hybrid generative layout: NL style directives
  (Apple Keynote, Swiss, consulting, minimal, editorial) → pattern recipe maps
  and/or **`freeform`** Box trees validated by the constraint layout engine
  (title/body floors preserved). Vision density findings force re-layout.
  Results remain editable native PPTX shapes.
- Recipe registry **61** builders (`freeform` + `GENERATIVE_SEQUENCE`).

#### Charts / extract
- **`reconstruct`** CLI + modern extract classify (#22) — chart/table recovery
  maps to modern recipes (`waterfall_insight`, `chart_callout_panel`,
  `appendix_table`, …).

#### Animation
- **`animate`** CLI + DESIGN.md `animation:` frontmatter (#40) — entrance
  presets (`fade` / `appear` / `wipe` / `fly_in`), slide transitions, default
  targets on key patterns; **namespace-safe OOXML** via `opc` (lxml).

#### Editor
- **Editor decision** (#44) — primary surface is VS Code / Cursor (not PowerPoint
  Add-in); see `docs/editor-integration-decision.md`.
- **VS Code / Cursor extension MVP** (#45) — `editor/vscode/` (doctor, compose,
  scaffold, a11y, refine, benchmark, explorer, Problems from reports).

#### Ecosystem / packaging
- **Public ≥100-deck benchmark** (#42) — `benchmark --public` runs synthetic
  CC0 fixtures across the recipe catalog; methodology + results in
  [docs/public-benchmark.md](docs/public-benchmark.md).
- **Windows standalone installer** (#35) — one-file
  `packaging/windows/Install-DesignmdPptx.ps1` (venv + pip + pinned
  officecli-dist + user PATH + uninstall); optional Inno Setup Setup.exe;
  `windows-install` CLI for plan/manifest checks.
  Docs: [docs/windows-installer.md](docs/windows-installer.md).

#### Recipe coverage (post-v2.0 waves, landed before 2.1 cut)
- Wave 1 full-family patterns (12) + Wave 2 long-tail (12) + Wave 3 vertical
  example decks (business / marketing / health / education / finance).

### Changed
- Package / skill / plugin / compiler version **2.1.0** (was 2.0.0).
- Maturity roadmap: Phase 5 marked **shipped** as v2.1.0.
- Skill description and agent docs cover `generate`, `animate`, `refine`,
  `reconstruct`, `benchmark --public`, `windows-install`.

### Verified
- Full unit suite green (347 tests, 1 skip).
- Multi-OS CI unit + package + benchmark fixture + e2e pin contract.
- `benchmark --public` → 100 pass / 0 fail (CC0 synthetic).
- `npm run check` green (version alignment across manifests).

### Install
```bash
pip install .   # or: PYTHONPATH=python from a checkout
python -m designmd_pptx doctor --install
python -m designmd_pptx scaffold default -o out/demo \
  --content python/examples/content.deck.json
python -m designmd_pptx generate content.deck.json -o gen --directive "Keynote style"
python -m designmd_pptx benchmark --public -o public-benchmark-out
# Windows (one-file):
#   powershell -ExecutionPolicy Bypass -File packaging\windows\Install-DesignmdPptx.ps1
```

### Next (v3.0)
- Hosted gallery of rendered examples with DESIGN.md provenance
- Multi-format export evaluation
- Community pattern registry + signed releases / SBOM

## [2.0.0] — 2026-07-15

Production release: Phase 0–4 complete.

### Added
- **`doctor --install`** — version-locked official OfficeCLI install from
  **officecli-dist** (GitHub release tarball for host OS/arch). Pins
  `compatibility.json` (`0.2.117`). Falls back guidance for legacy binary.
  npm registry is **not** the primary path (often lags the pin).
- **`a11y`** CLI — WCAG contrast (AA/AAA), deterministic reading order,
  alt-text / speaker-notes checks; opt-in `--fix-contrast` /
  `--generate-missing`; fails before output is treated as clean.
- **`benchmark`** CLI — before/after regression metrics (corruption,
  extraction_loss, layout_failure, visual_gate_failure, a11y_error) with
  thresholds in `benchmark_thresholds.json`; CI fixture job; corpus held-out
  skips when assets absent. Before-side a11y is scored for real deltas.
- Docs: [docs/index.md](docs/index.md), install, concepts, commands, gallery,
  v1→v2 migration, maturity roadmap, production checklist, governance.
- Issue templates (bug + feedback), expanded CONTRIBUTING + PR checks.

### Changed
- Package / skill / plugin version **2.0.0** (was 1.7.1).
- README marks Phase 0–4 shipped; Phase 5 is the next train.
- Official install remedy and compatibility `install` field point at
  `doctor --install` / officecli-dist rather than a non-existent npm pin.

### Verified (real machine, release cut)
- `doctor --install` → official `officecli version 0.2.117` + agent-bridge
  `capabilities/get` OK.
- Gallery path: `scaffold default` + `a11y` PASS + `benchmark` PASS
  (`a11y_error` delta −4) + `render` → 7-slide draft.pptx.
- Full unit suite green; plugin `npm run check` green.

### Deferred at 2.0.0 cut (shipped in 2.1.0)
- Windows installer (#35), animation (#40), generative layout (#21), chart
  reconstruction (#22), iterative vision loop (#19), editor integration
  (#44/#45), 100+ public benchmark corpus (#42).

## [1.7.x] — prior

Dual OfficeCLI backends, `render`, capability-first doctor, compose, layout
engine, extract/restyle/master, Gate 3. See git history and
[docs/migration-v1-v2.md](docs/migration-v1-v2.md).
