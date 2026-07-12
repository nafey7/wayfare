// Runner for the flight-search walkthroughs (Phase 1 of the staging-screenshot plan).
//
// Usage:
//   source .local/test-credentials/staging-test-user.env
//   cd testing
//   node e2e/walkthroughs/run-flight-search.js [--flow=auth-first|public-chat|auth-chat] [--label=before|after]
//
// Output: PNG screenshots written to
//   .local/journal/<date>/screenshots/walkthroughs/<branch>/[<label>/]<flow>/<NN>-<step>.png
//
// Exit codes:
//   0 — both walkthrough(s) completed
//   1 — env var missing or walkthrough threw
//
// Defaults: runs both flows. Pass --flow to limit to one.
//
// IMPORTANT: walkthroughs always target staging (https://staging.myvoya.ai). The
// existing testing/helpers/navigation-helpers.js resolves URLS.FRONTEND via
// TEST_ENV at module-load time — so TEST_ENV=staging MUST be set in the shell
// before this script runs. Setting it in JS here doesn't work because ES module
// imports hoist before any runtime statements.
//
// If TEST_ENV is unset, the constants module silently defaults to 'dev' and
// AuthModalPage.navigate() lands on http://localhost:3002 instead of staging.
// We catch that early with the env-check below.

import { chromium } from '@playwright/test';
import { walkFlightSearchAuthFirst } from './flightSearch.walkthrough.js';
import { walkPublicChatFlightSearch } from './publicChatFlightSearch.walkthrough.js';
import { walkAuthChatFlightSearch } from './authChatFlightSearch.walkthrough.js';
import { makeStepScreenshotter } from './screenshot.helper.js';
import { ensureStagingEnv, parseArgs } from './runner-utils.js';

const VALID_FLOWS = ['auth-first', 'public-chat', 'auth-chat'];
const args = parseArgs(process.argv.slice(2));

if (args.flow && !VALID_FLOWS.includes(args.flow)) {
  console.error(`Unknown --flow=${JSON.stringify(args.flow)}. Valid: ${VALID_FLOWS.join(', ')}.`);
  process.exit(1);
}

const flowsToRun = args.flow ? [args.flow] : ['public-chat', 'auth-chat', 'auth-first'];

const label = args.label; // optional "before" / "after" segment

ensureStagingEnv('e2e/walkthroughs/run-flight-search.js');

(async () => {
  const browser = await chromium.launch();
  try {
    for (const flow of flowsToRun) {
      console.log(`\n=== ${flow} ===`);
      const context = await browser.newContext();
      const page = await context.newPage();
      const flowName = `flight-search-${flow}`;
      const onStep = makeStepScreenshotter({ flow: flowName, label });

      const wrappedOnStep = async (eventName, ctx) => {
        const { filepath } = await onStep(eventName, ctx);
        console.log(`  step: ${eventName.padEnd(40)} → ${filepath}`);
      };

      try {
        const walker =
          flow === 'auth-first'
            ? walkFlightSearchAuthFirst
            : flow === 'auth-chat'
              ? walkAuthChatFlightSearch
              : walkPublicChatFlightSearch;
        const result = await walker(page, { onStep: wrappedOnStep });
        console.log(`  finalUrl: ${result.finalUrl}`);
        console.log(`  duration: ${result.durationMs}ms`);
        console.log(`  events:   ${result.events.join(' → ')}`);
      } catch (err) {
        console.error(`  FAILED: ${err.message}`);
        // Dump current state so we can see what the page actually looked like
        const failureShot = `failure-${flow}.png`;
        await page.screenshot({ path: failureShot, fullPage: true }).catch(() => {});
        const url = page.url();
        const html = await page
          .evaluate(() => document.body.innerText.slice(0, 500))
          .catch(() => '<eval failed>');
        console.error(`  url at failure: ${url}`);
        console.error(`  body excerpt: ${html.replace(/\n/g, ' | ').slice(0, 400)}`);
        console.error(`  full screenshot: ${failureShot}`);
        process.exitCode = 1;
      } finally {
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }
})();
