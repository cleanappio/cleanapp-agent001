import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const source = fileURLToPath(new URL('.', import.meta.url));
const manifest = JSON.parse(readFileSync(join(source, 'package.json'), 'utf8'));
const output = resolve(process.argv[2] ?? 'dist');
const staging = mkdtempSync(join(tmpdir(), 'cleanapp-playwright-pack-'));

try {
  for (const path of ['package.json', ...manifest.files]) {
    const input = path === 'support/report.py'
      ? resolve(source, '../../openclaw-skill/report.py')
      : join(source, path);
    const target = join(staging, path);
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(input, target);
  }
  mkdirSync(output, { recursive: true });
  execFileSync(process.execPath, [
    process.env.npm_execpath, 'pack', staging, '--ignore-scripts', '--pack-destination', output,
  ], { stdio: 'inherit' });
} finally {
  rmSync(staging, { recursive: true, force: true });
}
