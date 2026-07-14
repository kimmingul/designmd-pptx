# OfficeCLI backends — investigation & architecture (v1.7)

designmd-pptx talks to two generations of OfficeCLI through a backend
abstraction (`python/designmd_pptx/backend.py`). This document records the
investigation behind that split (issue #28) and the resulting contract.

## The two OfficeCLIs

| | Legacy `iOfficeAI/OfficeCLI` | Official `officecli/officecli` |
|---|---|---|
| Distribution | single binary (releases) | npm `officecli` + `officecli/officecli-dist` releases |
| Interface | CLI verbs + JSON batch ops, human-readable stdout | **agent-bridge**: JSON-RPC 2.0 over stdio, `Content-Length` framing |
| PPTX model | **shape-level**: absolute cm geometry, per-shape fonts/colors, glued connectors, notes, validate / view issues / screenshot | **outline-level**: `office.render` with `document_generation.pptx.payload_schema` |
| Probe | `officecli help all --json` (schema reference) | `initialize` → `capabilities/get` |

## Investigation result (2026-07-14, officecli 0.2.117)

`capabilities/get → document_generation.pptx`:

- `preferred_tool: office.render`, `prepare_required: false`, `agent_render_supported: true`
- `payload_schema` slide fields: `bgColor, bgColor2, chart, content, hasImage,
  imagePos, imagePrompt, isTitle, layout, metrics, narrativeRole, points,
  sectionIndex, sectionTitle, sections, source, subtitle, title, variant, visuals`
- `pptx_backends: [officegen]` (renderer fixed)
- `document_modification.pptx`: not offered (docx only, "minimal" in v1)

**Verdict: hybrid.** The official payload schema is an *outline* contract — it
has no absolute geometry, no connectors, no per-shape typography, no tables,
and no brand-token-level control. Everything that makes designmd-pptx
designmd-pptx (DESIGN.md tokens → engine-solved cm geometry, 20 exact
patterns, glued process connectors, slide-master/.potx surgery, Gate 3
screenshots) cannot be expressed in it today. An upstream issue asking for
shape-level payload support is filed with the officecli team.

## Backend contract

```text
OfficeCliBackend (ABC)
├── LegacyBatchBackend    — precision path (default for scaffold/apply)
│     wraps the legacy binary: create/open/batch/save/validate/issues/
│     screenshot/close; all subprocess + stdout parsing lives HERE only
└── AgentBridgeBackend    — outline path (render command)
      speaks JSON-RPC 2.0 (initialize, capabilities/get, session/open,
      task/invoke, task/respond, task/status, session/close) and maps a
      designmd deck-spec / compose brief onto the office.render payload
```

Selection is **capability-first** (issue #26): each backend probes before it
is used — the bridge via `capabilities/get`, the legacy binary via its
schema-reference help — and `doctor` reports which binaries resolve, their
versions, and which backend each designmd command will use. Nothing assumes
a verb exists.

### When is which backend used?

- `scaffold` / `apply` / `restyle` / `master` / `extract`: **LegacyBatchBackend**
  (shape-level fidelity is the product). Fails with a clear install remedy
  when the legacy binary is missing.
- `render` (v1.7): **AgentBridgeBackend** — quick outline→deck generation
  through the official `office.render`, honoring the official skill's
  guidance (structured JSON-RPC, no stdout parsing, capability fields
  cached from `capabilities/get`).

## Windows install notes (issue #29)

- npm `officecli@0.2.106` postinstall could fail downloading from
  `officecli-dist` (gzip EOF) and leave broken PATH shims that **shadow the
  legacy binary** (both are named `officecli`). The installer and `doctor`
  therefore identify binaries by probing `--version` + agent-bridge support,
  never by name alone.
- **Case-insensitivity trap**: the legacy default install dir is
  `%LOCALAPPDATA%\OfficeCLI` — on Windows that is the SAME directory as
  `%LOCALAPPDATA%\officecli`, so installing the official binary there
  silently overwrites the legacy one. We use `officecli-official\` for the
  direct-download location.
- Reliable fallback: download the platform asset from
  `github.com/officecli/officecli-dist` releases directly.
- Minimum supported official version: **0.2.117** (first version verified
  against this backend contract).
