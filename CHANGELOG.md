# Changelog

All notable changes to designmd-pptx are documented here.

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

### Deferred to v2.1
- Windows MSI (#35), animation (#40), generative layout (#21), chart
  reconstruction (#22), iterative vision loop (#19), editor integration
  (#44/#45), 100+ public benchmark corpus (#42).

## [1.7.x] — prior

Dual OfficeCLI backends, `render`, capability-first doctor, compose, layout
engine, extract/restyle/master, Gate 3. See git history and
[docs/migration-v1-v2.md](docs/migration-v1-v2.md).
