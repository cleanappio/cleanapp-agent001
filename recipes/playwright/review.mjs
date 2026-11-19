#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const python = process.platform === 'win32' ? 'python' : 'python3';
const reviewer = fileURLToPath(new URL('./review.py', import.meta.url));
const result = spawnSync(python, [reviewer, ...process.argv.slice(2)], { stdio: 'inherit' });

if (result.error) {
  console.error(`CleanApp QA: could not run ${python}. Install Python 3.9 or later.`);
}
process.exitCode = result.status ?? 2;
