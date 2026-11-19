import { deepEqual, equal, match } from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const outputRoot = resolve(process.env.CLEANAPP_QA_DIR || '.cleanapp-qa');
mkdirSync(outputRoot, { recursive: true, mode: 0o700 });
const outputDirectory = mkdtempSync(join(outputRoot, 'demo-'));
const cli = fileURLToPath(import.meta.resolve('@playwright/test/cli'));
const config = fileURLToPath(new URL('./demo.config.mjs', import.meta.url));

console.log('The fixture checkout assertion fails intentionally on both attempts.');
const result = spawnSync(process.execPath, [cli, 'test', '--config', config, '--output', join(outputDirectory, 'test-results')], {
  env: { ...process.env, CLEANAPP_QA_DIR: outputDirectory },
  stdio: 'inherit',
});
if (result.error) throw result.error;
equal(result.status, 1, 'Expected Playwright to preserve the failing checkout exit code');

const candidates = readdirSync(outputDirectory).filter(name => name.endsWith('.candidate.json'));
equal(candidates.length, 1, 'Expected exactly one candidate from the repeated fixture failure');
const candidatePath = join(outputDirectory, candidates[0]);
const candidate = JSON.parse(readFileSync(candidatePath, 'utf8'));
equal(candidate.kind, 'cleanapp-playwright-candidate');
equal(candidate.fixture, true);
equal(candidate.report.title, 'Fixture checkout cannot continue');
equal(candidate.report.url, 'http://127.0.0.1:42731/checkout');
match(candidate.report.description, /Observed: Checkout displays Checkout is unavailable\.$/u);
match(candidate.report.source_id, /^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/u);
deepEqual(candidate.report.handling, { publication: 'private', notices: 'none' });

function quotePath(path) {
  if (process.platform === 'win32') return `'${path.replaceAll("'", "''")}'`;
  return `'${path.replaceAll("'", "'\\''")}'`;
}

const reviewer = fileURLToPath(new URL('./review.mjs', import.meta.url));
console.log(`Demo verified Playwright exit code 1 and one offline candidate.\nCandidate: ${candidatePath}`);
console.log(`Preview offline:\nnode ${quotePath(reviewer)} ${quotePath(candidatePath)}`);
