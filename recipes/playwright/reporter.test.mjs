import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import CleanAppReporter, { recordCleanAppFailure } from './cleanapp-reporter.mjs';

const origin = 'https://shop.example.test';
const details = {
  path: '/checkout', title: 'Checkout stops at Continue', steps: 'Select Continue.',
  expected: 'Confirmation appears.', observed: 'Checkout is unavailable.',
};

function record(url, observation = details) {
  const info = { annotations: [] };
  recordCleanAppFailure(info, url, observation);
  return info.annotations;
}

function run(results, outcome = 'unexpected') {
  const reporter = new CleanAppReporter();
  reporter.onBegin({}, { allTests: () => [{ expectedStatus: 'passed', outcome: () => outcome, results }] });
  reporter.onEnd();
}

test('keeps one private candidate only for the same observed failure on all retries', t => {
  const directory = mkdtempSync(join(tmpdir(), 'cleanapp-qa-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  t.mock.method(console, 'log', () => {});
  const previous = { ...process.env };
  t.after(() => {
    for (const name of ['CLEANAPP_QA_CAPTURE', 'CLEANAPP_QA_ORIGIN', 'CLEANAPP_QA_DIR']) {
      if (previous[name] === undefined) delete process.env[name];
      else process.env[name] = previous[name];
    }
  });

  const url = `${origin}/checkout?token=not-for-cleanapp#customer`;
  delete process.env.CLEANAPP_QA_CAPTURE;
  assert.deepEqual(record(url), []);
  Object.assign(process.env, { CLEANAPP_QA_CAPTURE: '1', CLEANAPP_QA_ORIGIN: origin, CLEANAPP_QA_DIR: directory });
  assert.deepEqual(record('https://other.example.test/checkout'), []);
  assert.deepEqual(record(`${origin}/accounts/customer-id`), []);

  const failure = (observation = details) => ({ status: 'failed', annotations: record(url, observation) });
  const first = failure();
  assert.match(first.annotations[0].description, /^[a-f\d-]{36}$/);
  assert.equal(statSync(join(directory, '.attempts', first.annotations[0].description)).mode & 0o777, 0o600);
  run([first]);
  run([failure(), { status: 'passed', annotations: [] }], 'flaky');
  run([failure(), { ...failure(), status: 'timedOut' }]);
  run([failure(), { status: 'failed', annotations: [] }]);
  run([failure(), failure({ ...details, observed: 'Different issue.' })]);
  assert.deepEqual(readdirSync(directory), ['.attempts']);
  assert.deepEqual(readdirSync(join(directory, '.attempts')), []);

  run([failure(), failure()]);
  const names = () => readdirSync(directory).filter(name => name.endsWith('.candidate.json'));
  const [name] = names();
  const path = join(directory, name);
  const original = readFileSync(path, 'utf8');
  assert.match(name, /^[a-f\d]{64}\.candidate\.json$/);
  assert.equal(statSync(path).mode & 0o777, 0o600);
  assert.equal(original.includes('not-for-cleanapp'), false);
  assert.equal(original.includes('#customer'), false);
  const { fixture, report } = JSON.parse(original);
  assert.equal(fixture, false);
  assert.equal(report.url, `${origin}/checkout`);
  assert.match(report.source_id, /^[a-f\d]{8}-[a-f\d]{4}-4[a-f\d]{3}-[89ab][a-f\d]{3}-[a-f\d]{12}$/);
  assert.deepEqual(report.handling, { publication: 'private', notices: 'none' });

  run([failure(), failure()]);
  assert.deepEqual(names(), [name]);
  assert.deepEqual(readdirSync(join(directory, '.attempts')), []);
  assert.equal(readFileSync(path, 'utf8'), original);
});
