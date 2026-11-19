import { expect, test } from '@playwright/test';
import { recordCleanAppFailure } from '@cleanapp/playwright';

const url = 'http://127.0.0.1:42731/checkout?fixture_marker=drop-me#also-drop';
const checkout = `<!doctype html><html lang="en"><meta charset="utf-8"><title>Fixture checkout</title>
<form><button>Continue</button><p role="status" hidden>Checkout is unavailable.</p></form>
<script>document.querySelector('form').onsubmit = event => {
  event.preventDefault(); document.querySelector('[role=status]').hidden = false;
};</script></html>`;

test('fixture checkout shows confirmation after Continue', async ({ page }, testInfo) => {
  await page.route('**/*', route => route.request().url() === url.split('#')[0]
    ? route.fulfill({ contentType: 'text/html', body: checkout })
    : route.abort());
  await page.goto(url);
  await page.getByRole('button', { name: 'Continue' }).click();
  try {
    await expect(page.getByText('Order confirmed', { exact: true })).toBeVisible({ timeout: 700 });
  } catch (error) {
    if (await page.getByText('Checkout is unavailable.', { exact: true }).isVisible().catch(() => false)) {
      recordCleanAppFailure(testInfo, page.url(), {
        path: '/checkout',
        title: 'Fixture checkout cannot continue',
        steps: 'Open the fixture checkout and select Continue.',
        expected: 'Checkout displays Order confirmed.',
        observed: 'Checkout displays Checkout is unavailable.',
      });
    }
    throw error;
  }
});
