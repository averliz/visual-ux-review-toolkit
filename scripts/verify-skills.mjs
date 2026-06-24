#!/usr/bin/env node
// Repo-health check (does NOT ship inside any skill).
//   node scripts/verify-skills.mjs
// 1) the two browser-tools.md copies are byte-identical
// 2) `npx skills` discovers both skills from this repo
import { readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
const SKILLS = ['visual-ux-review', 'ux-flow-walkthrough'];
const A = 'skills/visual-ux-review/references/browser-tools.md';
const B = 'skills/ux-flow-walkthrough/references/browser-tools.md';

let failed = false;
const fail = (m) => { console.error('FAIL: ' + m); failed = true; };

if (readFileSync(A).equals(readFileSync(B))) console.log('ok: browser-tools.md copies identical');
else fail(`${A} and ${B} differ — keep them byte-identical`);

try {
  // execSync via shell is deliberate: on Windows npx is npx.cmd, which execFileSync('npx', …) can't resolve. Command is a fixed constant — no injection surface.
  const out = execSync('npx -y skills@latest add . --list', { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  for (const s of SKILLS) out.includes(s) ? console.log(`ok: npx skills lists ${s}`) : fail(`npx skills did not list ${s}`);
} catch (e) {
  fail('could not run `npx skills … --list`: ' + (e.stderr?.toString() || e.message));
}

process.exit(failed ? 1 : 0);
