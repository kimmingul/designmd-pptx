#!/usr/bin/env node
/**
 * Sync canonical skills/ and commands/ into platform adapter layouts (.grok/).
 * Canonical source of truth: skills/, commands/ at repo root (Claude Code layout).
 * Usage: node scripts/sync-adapters.mjs [--check]
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const check = process.argv.includes('--check');

const PAIRS = [
  ['skills', path.join('.grok', 'skills')],
  ['commands', path.join('.grok', 'commands')],
];

function* walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else yield p;
  }
}

let drift = 0;
for (const [srcRel, dstRel] of PAIRS) {
  const src = path.join(root, srcRel);
  const dst = path.join(root, dstRel);
  if (!fs.existsSync(src)) {
    console.error(`missing canonical dir: ${srcRel}`);
    process.exit(1);
  }
  for (const file of walk(src)) {
    const rel = path.relative(src, file);
    const out = path.join(dst, rel);
    const want = fs.readFileSync(file, 'utf8');
    const have = fs.existsSync(out) ? fs.readFileSync(out, 'utf8') : null;
    if (have === want) continue;
    if (check) {
      console.error(`DRIFT ${path.join(dstRel, rel)} != ${path.join(srcRel, rel)}`);
      drift += 1;
    } else {
      fs.mkdirSync(path.dirname(out), { recursive: true });
      fs.writeFileSync(out, want);
      console.log(`synced ${path.join(dstRel, rel)}`);
    }
  }
}

if (check && drift) {
  console.error(`\n${drift} adapter file(s) out of sync — run: npm run sync`);
  process.exit(1);
}
console.log(check ? 'adapters in sync' : 'sync complete');
