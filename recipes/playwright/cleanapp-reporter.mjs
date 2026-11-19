import { createHash, randomUUID } from 'node:crypto';
import { linkSync, mkdirSync, readFileSync, rmSync, unlinkSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const annotationType = 'cleanapp-observed-failure';
const loopback = new Set(['localhost', '127.0.0.1', '[::1]']);
const candidateDirectory = () => process.env.CLEANAPP_QA_DIR || '.cleanapp-qa';
const uuidPattern = /^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/u;

function approvedSite() {
  if (process.env.CLEANAPP_QA_CAPTURE !== '1') return null;
  try {
    const site = new URL(process.env.CLEANAPP_QA_ORIGIN);
    const fixture = loopback.has(site.hostname);
    if (site.href !== `${site.origin}/` || (site.protocol !== 'https:' && !(fixture && site.protocol === 'http:'))) return null;
    return { origin: site.origin, fixture };
  } catch {
    return null;
  }
}

function safeText(value, limit) {
  return typeof value === 'string' && value.trim() === value && value.length > 0
    && Buffer.byteLength(value) <= limit && !/[\u0000-\u001f\u007f]/u.test(value);
}

// Call this only after confirming the authored, user-visible symptom in this attempt.
export function recordCleanAppFailure(testInfo, pageUrl, details) {
  const site = approvedSite();
  if (!site) return;
  try {
    const page = new URL(pageUrl);
    const { path, title, steps, expected, observed } = details;
    if (page.origin !== site.origin || page.username || page.password || page.pathname !== path
      || !/^\/(?:[a-z0-9_-]+\/)*[a-z0-9_-]*$/iu.test(path) || path.length > 200
      || !safeText(title, 180) || ![steps, expected, observed].every(value => safeText(value, 280))) return;
    const report = {
      title,
      description: `A Playwright browser check reproduced this failure. Steps: ${steps} Expected: ${expected} Observed: ${observed}`,
      url: `${site.origin}${path}`,
    };
    const directory = join(candidateDirectory(), '.attempts');
    const marker = randomUUID();
    mkdirSync(directory, { recursive: true, mode: 0o700 });
    writeFileSync(join(directory, marker), JSON.stringify(report), { mode: 0o600, flag: 'wx' });
    // Other Playwright reporters only see this opaque local marker.
    testInfo.annotations.push({ type: annotationType, description: marker });
  } catch {
    // Candidate capture cannot replace or suppress the original test failure.
  }
}

function repeatedReport(test, directory) {
  const { results } = test;
  const observed = results.map(result => {
    const markers = result.annotations.filter(item => item.type === annotationType && uuidPattern.test(item.description));
    const reports = markers.map(item => {
      const path = join(directory, '.attempts', item.description);
      try {
        return readFileSync(path, 'utf8');
      } catch {
        return null;
      } finally {
        rmSync(path, { force: true });
      }
    });
    return result.status === 'failed' && reports.length === 1 ? reports[0] : null;
  });
  if (test.expectedStatus !== 'passed' || test.outcome() !== 'unexpected' || observed.length < 2
    || !observed[0] || !observed.every(value => value === observed[0])) return null;
  return JSON.parse(observed[0]);
}

function saveCandidate(directory, fixture, report) {
  const fingerprint = createHash('sha256').update(JSON.stringify([fixture, report])).digest('hex');
  const candidate = {
    kind: 'cleanapp-playwright-candidate',
    fixture,
    report: {
      ...report,
      source_id: randomUUID(),
      handling: { publication: 'private', notices: 'none' },
    },
  };
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const temporary = join(directory, `.${randomUUID()}.tmp`);
  writeFileSync(temporary, JSON.stringify(candidate, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
  try {
    // Publish a complete file once. Concurrent and repeated runs keep the first source ID.
    linkSync(temporary, join(directory, `${fingerprint}.candidate.json`));
    return true;
  } catch (error) {
    if (error.code !== 'EEXIST') throw error;
    return false;
  } finally {
    unlinkSync(temporary);
  }
}

export default class CleanAppReporter {
  onBegin(_config, suite) {
    this.suite = suite;
  }

  onEnd() {
    const site = approvedSite();
    if (!site) {
      if (process.env.CLEANAPP_QA_CAPTURE === '1') console.error('CleanApp QA: configure an exact HTTPS origin to capture candidates.');
      return;
    }
    const directory = candidateDirectory();
    let count = 0;
    for (const test of this.suite.allTests()) {
      try {
        const report = repeatedReport(test, directory);
        if (!report) continue;
        const { title, description, url } = report;
        const page = new URL(url);
        if (page.origin !== site.origin || page.href !== `${site.origin}${page.pathname}`
          || !safeText(title, 180) || !safeText(description, 1024)) continue;
        if (saveCandidate(directory, site.fixture, { title, description, url })) count++;
      } catch {
        console.error('CleanApp QA: could not save a local candidate. The Playwright result is unchanged.');
      }
    }
    if (count) console.log(`CleanApp QA: saved ${count} new local candidate(s) for human review.`);
  }

  printsToStdio() {
    return false;
  }
}
