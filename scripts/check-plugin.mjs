#!/usr/bin/env node
/** Static checks for designmd-pptx multi-platform plugin layout (Claude Code / Codex / Grok). */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawnSync } from 'child_process';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
let failed = 0;
const ok = (c, m) => {
  if (c) console.log(`  ok  ${m}`);
  else {
    console.error(`  FAIL ${m}`);
    failed += 1;
  }
};

console.log('check-plugin designmd-pptx');
const pj = path.join(root, 'plugin.json');
ok(fs.existsSync(pj), 'plugin.json exists');
const plugin = JSON.parse(fs.readFileSync(pj, 'utf8'));
ok(plugin.name === 'designmd-pptx', 'name designmd-pptx');
ok(/^\d+\.\d+\.\d+/.test(plugin.version || ''), 'semver version');
ok(Array.isArray(plugin.skills) && plugin.skills.length >= 1, 'skills listed');

const skill = path.join(root, '.grok', 'skills', 'officecli-pptx-designmd', 'SKILL.md');
ok(fs.existsSync(skill), 'skill SKILL.md');
const skillBody = fs.readFileSync(skill, 'utf8');
ok(/^---\n[\s\S]*?name:\s*officecli-pptx-designmd/m.test(skillBody), 'skill frontmatter name');
ok(skillBody.includes('designmd_pptx'), 'skill mentions package');

const cmd = path.join(root, '.grok', 'commands', 'designmd-pptx.md');
ok(fs.existsSync(cmd), 'command designmd-pptx.md');

// Canonical (Claude Code) layout
const canonSkill = path.join(root, 'skills', 'officecli-pptx-designmd', 'SKILL.md');
ok(fs.existsSync(canonSkill), 'canonical skills/ SKILL.md');
const canonCmd = path.join(root, 'commands', 'designmd-pptx.md');
ok(fs.existsSync(canonCmd), 'canonical commands/designmd-pptx.md');

const cpj = path.join(root, '.claude-plugin', 'plugin.json');
ok(fs.existsSync(cpj), '.claude-plugin/plugin.json exists');
const cplugin = JSON.parse(fs.readFileSync(cpj, 'utf8'));
ok(cplugin.name === 'designmd-pptx', 'claude plugin name designmd-pptx');
ok(cplugin.version === plugin.version, 'claude plugin version matches grok plugin.json');

const mpj = path.join(root, '.claude-plugin', 'marketplace.json');
ok(fs.existsSync(mpj), '.claude-plugin/marketplace.json exists');
const market = JSON.parse(fs.readFileSync(mpj, 'utf8'));
ok(
  Array.isArray(market.plugins) && market.plugins[0]?.source === './',
  'marketplace self-hosts plugin at ./'
);

ok(fs.existsSync(path.join(root, 'AGENTS.md')), 'AGENTS.md (Codex) exists');
ok(fs.existsSync(path.join(root, 'scripts', 'install-codex.ps1')), 'install-codex.ps1 exists');

// Adapter drift: .grok copies must match canonical skills/ + commands/
const sync = spawnSync(
  process.execPath,
  [path.join(root, 'scripts', 'sync-adapters.mjs'), '--check'],
  { cwd: root, encoding: 'utf-8' }
);
ok(sync.status === 0, `adapters in sync: ${(sync.stdout || sync.stderr || '').trim().split('\n').pop()}`);

const pkg = path.join(root, 'python', 'designmd_pptx', '__init__.py');
ok(fs.existsSync(pkg), 'python package present');
const init = fs.readFileSync(pkg, 'utf8');
ok(init.includes('1.1'), 'package version 1.1.x');

const req = path.join(root, 'python', 'requirements.txt');
ok(fs.existsSync(req), 'requirements.txt');

const pyCode =
  "import sys; sys.path.insert(0, 'python'); from designmd_pptx import __version__; print(__version__)";
const py = spawnSync('python', ['-c', pyCode], {
  cwd: root,
  encoding: 'utf-8',
  shell: false,
});
ok(
  py.status === 0 && (py.stdout || '').includes('1.1'),
  `python import: ${(py.stdout || py.stderr || '').trim()}`
);

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall checks passed');
