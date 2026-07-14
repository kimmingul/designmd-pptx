"""VS Code extension MVP packaging checks (#45) — no vscode runtime required."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "editor" / "vscode"


class VscodeExtension45(unittest.TestCase):
    def test_package_json_mvp_surface(self) -> None:
        pkg = json.loads((EXT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["name"], "designmd-pptx")
        self.assertIn("engines", pkg)
        cmds = {c["command"] for c in pkg["contributes"]["commands"]}
        for required in (
            "designmdPptx.doctor",
            "designmdPptx.compose",
            "designmdPptx.scaffold",
            "designmdPptx.a11y",
            "designmdPptx.refine",
            "designmdPptx.openContactSheet",
            "designmdPptx.openGate3Report",
        ):
            self.assertIn(required, cmds, required)
        views = pkg["contributes"]["views"]["designmdPptx"]
        self.assertTrue(any(v["id"] == "designmdPptx.explorer" for v in views))
        self.assertTrue((EXT / "extension.js").is_file())
        self.assertTrue((EXT / "cli.js").is_file())
        self.assertTrue((EXT / "README.md").is_file())
        self.assertTrue((EXT / "media" / "icon.svg").is_file())

    def test_cli_helper_resolves_python_module(self) -> None:
        # Node unit test for pure helper — argv, never shell-joined user input
        script = r"""
const path = require('path');
const { resolveCli, diagnosticsFromReport, hasShellMeta } = require('./cli.js');
const root = path.resolve('../..');
const r = resolveCli({
  workspaceRoot: root,
  pythonPath: 'python3',
  args: ['doctor', '--install', '--dry-run'],
});
if (!Array.isArray(r.argv)) throw new Error('argv missing');
if (!r.argv.includes('designmd_pptx')) throw new Error('argv: ' + JSON.stringify(r.argv));
if (!r.env.PYTHONPATH || !r.env.PYTHONPATH.includes('python')) {
  throw new Error('PYTHONPATH: ' + r.env.PYTHONPATH);
}
// Injection-sensitive feedback stays a single argv element (no shell eval)
const evil = resolveCli({
  workspaceRoot: root,
  pythonPath: 'python3',
  args: ['refine', 'deck.json', '--feedback', '$(id); rm -rf /'],
});
const fb = evil.argv[evil.argv.indexOf('--feedback') + 1];
if (fb !== '$(id); rm -rf /') throw new Error('feedback argv corrupted: ' + fb);
if (!hasShellMeta(fb)) throw new Error('meta detect');
const d = diagnosticsFromReport({
  pass: false,
  findings: [{ code: 'density', severity: 'error', message: 'crowded', slide: 2 }],
});
if (d.length < 2) throw new Error('diags ' + JSON.stringify(d));
if (d[0].line !== 1) throw new Error('line ' + d[0].line);
console.log('ok', r.argv.join(' '));
"""
        proc = subprocess.run(
            ["node", "-e", script],
            cwd=str(EXT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("ok", proc.stdout)

    def test_extension_uses_spawn_not_sendtext_for_cli(self) -> None:
        ext = (EXT / "extension.js").read_text(encoding="utf-8")
        self.assertIn("spawn", ext)
        self.assertIn("shell: false", ext)
        # Must not send user feedback through a shell string
        self.assertNotIn("terminal.sendText(shellCmd", ext)

    def test_decision_doc_points_at_extension(self) -> None:
        doc = (ROOT / "docs" / "editor-integration-decision.md").read_text(encoding="utf-8")
        self.assertIn("VS Code", doc)
        self.assertIn("#45", doc)
        readme = (EXT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Install", readme)
        self.assertIn("vsce", readme.lower() + readme)


if __name__ == "__main__":
    unittest.main()
