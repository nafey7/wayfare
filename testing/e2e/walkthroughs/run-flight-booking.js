// Runner for the flight-booking walkthrough (Phase 2B of the staging-screenshot plan).
//
// Usage:
//   source .local/test-credentials/staging-test-user.env
//   cd testing
//   node e2e/walkthroughs/run-flight-booking.js [--entry=chat|searchbar] [--label=before|after]
//
// Output: PNG screenshots written to
//   .local/journal/<date>/screenshots/walkthroughs/<branch>/[<label>/]<flow>/<NN>-<step>.png
//
// Exit codes:
//   0 — walkthrough completed (review-booking page rendered)
//   1 — env var missing or walkthrough threw
//
// Defaults: --entry=chat (most-popular real-user path).
//
// IMPORTANT: walkthrough always targets staging. Staging shows the dev-only
// "Auto-fill all passengers" button (gated on VITE_ENV !== 'production'); the
// walkthrough depends on it. Production deploys do not show the button — so
// running this against production would fail at step 5 of
// flightBooking.walkthrough.js.
//
// Same TEST_ENV=staging requirement as run-flight-search.js (constants module
// resolves URLS.FRONTEND at import time from the env).

import { chromium } from '@playwright/test';
import { walkFlightBooking } from './flightBooking.walkthrough.js';
import { makeStepScreenshotter } from './screenshot.helper.js';
import { ensureStagingEnv, parseArgs } from './runner-utils.js';

const VALID_ENTRIES = ['chat', 'searchbar'];
const args = parseArgs(process.argv.slice(2));

if (args.entry && !VALID_ENTRIES.includes(args.entry)) {
  console.error(`Unknown --entry=${JSON.stringify(args.entry)}. Valid: ${VALID_ENTRIES.join(', ')}.`);
  process.exit(1);
}

const entry = args.entry || 'chat';
const label = args.label;

ensureStagingEnv('e2e/walkthroughs/run-flight-booking.js');

(async () => {
  // Headless by default for CI / scripted runs.
  // Pass `{ headless: false }` locally to watch the browser drive the flow.
  const browser = await chromium.launch();
  try {
    console.log(`\n=== flight-booking (entry=${entry}) ===`);
    const context = await browser.newContext();
    const page = await context.newPage();
    const flowName = `flight-booking-${entry}`;
    const onStep = makeStepScreenshotter({ flow: flowName, label });

    const wrappedOnStep = async (eventName, ctx) => {
      const { filepath } = await onStep(eventName, ctx);
      console.log(`  step: ${eventName.padEnd(40)} → ${filepath}`);
    };

    try {
      const result = await walkFlightBooking(page, { entryPoint: entry, onStep: wrappedOnStep });
      console.log(`  finalUrl: ${result.finalUrl}`);
      console.log(`  duration: ${result.durationMs}ms`);
      console.log(`  entryEvents:    ${result.entryEvents.join(' → ')}`);
      console.log(`  bookingEvents:  ${result.bookingEvents.join(' → ')}`);
    } catch (err) {
      console.error(`  FAILED: ${err.message}`);
      const failureShot = `failure-flight-booking-${entry}.png`;
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
  } finally {
    await browser.close();
  }
})();
