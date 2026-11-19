import type { TestInfo } from '@playwright/test';
import type { FullConfig, Reporter, Suite } from '@playwright/test/reporter';

export interface CleanAppFailureDetails {
  path: string;
  title: string;
  steps: string;
  expected: string;
  observed: string;
}

export function recordCleanAppFailure(
  testInfo: TestInfo,
  pageUrl: string,
  details: CleanAppFailureDetails,
): void;

export default class CleanAppReporter implements Reporter {
  onBegin(config: FullConfig, suite: Suite): void;
  onEnd(): void;
  printsToStdio(): boolean;
}
