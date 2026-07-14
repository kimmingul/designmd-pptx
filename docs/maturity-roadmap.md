# Maturity roadmap

Where designmd-pptx is going after the dual-backend (v1.7) foundation.

## v2.0 — production core (**shipped** as v2.0.0)

**Goal:** A contributor can install the package, diagnose the machine, generate
a brand-faithful deck, and gate it on structure + a11y + offline visual QA
without private tribal knowledge.

| Capability | Status | Evidence |
|---|---|---|
| OfficeCLI version contract (`compatibility.json`) | Shipped | #8, `compat`, CI pin |
| Self-contained `pip install designmd-pptx` | Shipped | #33 |
| `doctor --install` (pinned official OfficeCLI) | Shipped | #34 |
| DESIGN.md schema v2 + layout engine | Shipped | Phase 1 |
| Extract fidelity + premium/domain patterns | Shipped | Phase 2 |
| Compose LLM adapter + vision Gate 3 | Shipped | Phase 3 |
| WCAG contrast / reading order / alt+notes | Shipped | #39, `a11y` CLI |
| Before/after benchmark harness + thresholds | Shipped | #37, `benchmark` CLI |
| Maturity + production checklist | Shipped | #38 (this doc) |
| Docs / gallery / CONTRIBUTING / governance | Shipped | #41, #43 |

**Out of v2.0:** Windows MSI installer (#35), animation (#40), generative layout
(#21), chart reconstruction (#22), public 100+ deck corpus (#42).

### 50-deck corpus gap

The benchmark harness scores **held-out corpus entries when assets exist**, and
always exercises a **fixture suite** (default DESIGN.md + example deck-spec) in
CI. A private/licensed 50-deck held-out set may still be incomplete; that is
documented rather than blocking the release. Methodology and thresholds live in
`python/designmd_pptx/benchmark_thresholds.json`.

## v2.1 — intelligence (Phase 5)

- ✅ Iterative visual refinement loop (#19) — `refine` CLI
- ✅ Chart/table reconstruction from extract (#22) — modern classify + `reconstruct`
- ✅ Editor integration **decision** (#44) — VS Code/Cursor extension (not PPT Add-in)
- ✅ Editor integration **implementation** (#45) — `editor/vscode` MVP
- ✅ Hybrid generative layout (#21) — `generate` CLI + `freeform` recipe
- ✅ Animation / transitions (#40) — DESIGN.md `animation:` + `animate` CLI
- ✅ Public 100+ deck benchmark (#42) — `benchmark --public` + [public-benchmark.md](public-benchmark.md)
- ✅ Standalone Windows installer (#35) — `packaging/windows/Install-DesignmdPptx.ps1` + `windows-install` CLI

## v3.0 — platform

- Hosted gallery of rendered examples with DESIGN.md provenance
- Multi-format export (beyond PPTX) evaluated
- Community pattern registry with review SLA
- Signed releases + SBOM for the Python wheel and skill packs

## How we know we moved a maturity level

1. All production-readiness checklist items green (see
   [production-readiness.md](production-readiness.md)).
2. `python -m designmd_pptx benchmark` fixture suite PASS in CI.
3. Open Phase milestone issues closed or explicitly deferred with labels.
