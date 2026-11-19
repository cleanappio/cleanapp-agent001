import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';

process.env.CLEANAPP_QA_CAPTURE = '1';
process.env.CLEANAPP_QA_ORIGIN = 'http://127.0.0.1:42731';

export default defineConfig({
  testDir: './fixture',
  retries: 1,
  workers: 1,
  reporter: [['line'], [fileURLToPath(import.meta.resolve('@cleanapp/playwright'))]],
  use: { channel: process.env.CLEANAPP_DEMO_BROWSER_CHANNEL, serviceWorkers: 'block' },
});
