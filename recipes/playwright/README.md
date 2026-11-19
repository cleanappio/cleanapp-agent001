# CleanApp Playwright adapter

`@cleanapp/playwright` 0.1.0 captures a local report candidate when an approved Playwright check observes the same user-visible failure on its first attempt and every retry. A QA engineer can then review the exact report and approve a private submission with notices off. Playwright’s normal result still drives CI.

## Run the demo

From this directory with Node.js 22 or later, run:

```sh
npm ci
npx playwright install chromium
npm run demo
```

The demo uses a local checkout fixture. Its Playwright check intentionally fails twice. The demo succeeds after verifying that Playwright returned exit code 1 and wrote exactly one private fixture candidate. It prints the candidate path and a command to preview it offline.

If Chrome is already installed, use `CLEANAPP_DEMO_BROWSER_CHANNEL=chrome npm run demo`. To review a candidate, use Python 3.9 or later. The demo fixture is offline only.

## Install the local build

Build the versioned tarball from a checkout of this repository:

```sh
cd recipes/playwright
npm run pack:adapter
```

The package is available for local installation from `dist/cleanapp-playwright-0.1.0.tgz`. Copy it to `vendor/cleanapp-playwright-0.1.0.tgz` in your existing Playwright project and run:

```sh
npm install --save-dev --save-exact ./vendor/cleanapp-playwright-0.1.0.tgz
```

Keep the tarball alongside your dependency manifest and lockfile so CI can reproduce the install with `npm ci`. The adapter works with Playwright Test 1.52 through 1.x. It also exposes a TypeScript interface for recording failures.

## Add an approved check

Append CleanApp to your Playwright reporters and configure at least one retry for the selected test or project:

```js
reporter: [['line'], ['@cleanapp/playwright']],
retries: 1,
```

Import the helper in the selected test:

```js
import { recordCleanAppFailure } from '@cleanapp/playwright';
```

Call `recordCleanAppFailure(testInfo, page.url(), details)` only after confirming the specific symptom, then rethrow the test’s original assertion error. Provide a reviewed literal `path`, `title`, `steps`, `expected`, and `observed`. The [fixture test](fixture/checkout.spec.mjs) has a complete example.

Enable capture on one authorized HTTPS origin at a time:

```sh
CLEANAPP_QA_CAPTURE=1 CLEANAPP_QA_ORIGIN=https://shop.example.org npx playwright test
```

The runtime page URL must match the approved origin and literal path. The adapter drops query strings and fragments and leaves test errors, screenshots, credentials, network responses, console output, and traces out of the candidate. Keep customer identifiers and confidential details out of the supplied text and path. Add `.cleanapp-qa/` to your `.gitignore` when using the default local candidate directory. If the same observation appears again in the same candidate directory, the adapter retains the first observation ID.

## Copy the GitHub Actions setup

From your Playwright project, after installing the adapter:

```sh
mkdir -p .github/workflows
cp node_modules/@cleanapp/playwright/examples/github-actions.yml .github/workflows/cleanapp-qa.yml
```

The [workflow](examples/github-actions.yml) runs manually on the default branch on a trusted Linux runner labeled `cleanapp-qa`. Set the repository variables `CLEANAPP_QA_ORIGIN` to your approved HTTPS origin and `CLEANAPP_QA_DIR` to an existing private directory on persistent runner storage. Keep this directory outside the checkout. It needs to be available to the QA reviewer. The test step retains Playwright’s exit code and the workflow keeps candidates on the runner.

For two sites, run each approved project with its own exact origin and separate candidate directory. Keep candidate files, receipts, and ordinary Playwright HTML/JSON reports and traces out of public logs and artifacts. Completed Playwright runs remove temporary attempt files. If a run is interrupted, remove its abandoned `.attempts/` files after the run stops.

## Review and track a real observation

When you have CleanApp connected in an MCP client, you can first look up related public reports with `cleanapp_search_reports`. Use a few non-sensitive words about the product and symptom and `domain: digital`. [CleanApp agent guide](https://www.cleanapp.io/agents#connect)

From the project where you installed the adapter, replace the path below with the candidate you intend to review:

```sh
npx --no-install cleanapp-playwright-review /path/to/observation.candidate.json
npx --no-install cleanapp-playwright-review /path/to/observation.candidate.json --send
npx --no-install cleanapp-playwright-review /path/to/observation.candidate.json --status
```

The first command previews offline. The second displays the same payload and sends only after you enter `SEND PRIVATE` in a private interactive terminal. The command stores the receipt beside the candidate. Use `--status` to follow intake, the decision, and recorded action. If delivery was uncertain and you have a receipt, check status first. Otherwise use `--send --retry` and approve the unchanged payload. Exact retries keep the same observation ID.

The CI workflow stops at local capture. Submitted reports and receipts are private and approved reports have notices off. Keep the receipt private. [CleanApp privacy policy](https://live.cleanapp.io/openai/privacy)
