# Governance & triage

## Maintainers

- **Primary:** repository owner ([@kimmingul](https://github.com/kimmingul))
- **Reviewers:** anyone with write access; agent-assisted PRs are welcome when
  tests + `npm run check` are green

## Decision rights

| Area | Owner | Notes |
|---|---|---|
| Recipe geometry / layout engine | maintainers | Engine vs fixed — one system per recipe |
| OfficeCLI pin (`compatibility.json`) | maintainers | Bump with CI pin in same PR |
| Public API / CLI surface | maintainers | Prefer additive flags |
| Docs / gallery | any contributor | Follow docs style; link from `docs/index.md` |
| Licensed template analysis | contributors with license | Never commit originals |

## Label taxonomy

| Label | Use |
|---|---|
| `bug` | Incorrect behavior / crash |
| `enhancement` | Feature or improvement |
| `documentation` | Docs-only |
| `cluster:infra` | CI, packaging, corpus, doctor |
| `cluster:a11y-anim` | Accessibility / animation |
| `effort:S` / `effort:M` / `effort:L` | Rough sizing |
| `v2.0` / `v2.1` | Target release train |

Milestones map to roadmap phases (Phase 4 = v2.0 release, Phase 5 = intelligence).

## Triage SLA (best-effort)

1. New issues: label + milestone within a few days when active.
2. Security / data exposure: treat as highest priority; do not paste secrets in issues.
3. Duplicate: close with pointer to canonical issue.
4. Out of scope (Phase 5 while shipping v2.0): label `v2.1` and leave open.

## PR merge bar

1. CI green (unit + package + benchmark fixture job).
2. No adapter drift (`npm run check`).
3. For behavior changes: tests that exercise the shipped entry point.
4. For CLI changes: skill/command docs updated under `skills/` / `commands/` + sync.
5. Squash or rebase merge preferred for linear history on `main`.

## Release ownership

- Roadmap status lives in README + [maturity-roadmap.md](maturity-roadmap.md).
- Production bar: [production-readiness.md](production-readiness.md).
- Closing a milestone requires checklist items for that train to be done or
  explicitly deferred with an issue.

## Community feedback

- Bug template: `.github/ISSUE_TEMPLATE/bug_report.md`
- Feedback template: `.github/ISSUE_TEMPLATE/feedback.md`
- Discussions may be enabled later; until then use issues.
