# designmd-pptx documentation

Compile [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) /
Stitch `DESIGN.md` into [OfficeCLI](https://github.com/officecli/officecli) PPTX
tokens, ordered decks, and staging-safe apply.

## Guides

| Doc | Topic |
|---|---|
| [Install](install.md) | pip, plugins, doctor --install |
| [Concepts](concepts.md) | DESIGN.md, tokens, deck-spec, backends, gates |
| [Command reference](commands.md) | Full CLI |
| [Gallery walkthrough](gallery.md) | DESIGN.md → deck end-to-end |
| [v1 → v2 migration](migration-v1-v2.md) | Breaking changes and new commands |
| [Maturity roadmap](maturity-roadmap.md) | v2.0 / v2.1 / v3.0 |
| [Production checklist](production-readiness.md) | Explicit ship thresholds |
| [OfficeCLI backends](officecli-backends.md) | Legacy vs agent-bridge |
| [DESIGN.md schema v2](design-md-v2.md) | Token schema |
| [Corpus](corpus.md) | Anonymize + validation corpus |
| [Infograpify reference](infograpify-reference.md) | License-safe premium analysis |
| [Recipe coverage roadmap](recipe-coverage-roadmap.md) | Full-family recipe plan vs 400-deck library |

## Quick start

```bash
pip install -r python/requirements.txt   # or: pip install .
export PYTHONPATH=python                 # checkout only
python -m designmd_pptx doctor --install --dry-run
python -m designmd_pptx scaffold default -o out/demo \
  --content python/examples/content.deck.json
python -m designmd_pptx a11y --design default \
  --content python/examples/content.deck.json --show-order
python -m designmd_pptx benchmark -o benchmark-out
```

Materializing real `.pptx` still needs an OfficeCLI backend (legacy for
scaffold/apply precision; official for `render`).
