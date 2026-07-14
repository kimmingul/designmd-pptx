---
name: Bug report
about: Report incorrect output, crashes, or false green gates
title: "[bug] "
labels: ["bug"]
---

## Environment

- OS:
- Python:
- designmd-pptx version (`python -c "import designmd_pptx; print(designmd_pptx.__version__)"`):
- OfficeCLI (legacy / official / versions from `doctor`):

## What happened

<!-- Clear description + expected vs actual -->

## Repro

```bash
# minimal commands
```

Attach (if possible): DESIGN.md excerpt, `content.deck.json` slide, `a11y.report.json`,
`benchmark.report.json`, contact sheet, or extract `loss_ledger` — **no licensed
vendor pptx**.

## Gates already run?

- [ ] `doctor`
- [ ] `a11y`
- [ ] `benchmark` (fixture)
- [ ] `--screenshot` / Gate 3
