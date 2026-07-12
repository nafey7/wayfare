// Runner for the hotel-booking walkthrough (Phase 3B).
//
// Usage:
//   source .local/test-credentials/staging-test-user.env
//   cd testing
//   node e2e/walkthroughs/run-hotel-booking.js [--label=before|after]
//
// Output: PNG screenshots written to
//   .local/journal/<date>/screenshots/walkthroughs/<branch>/[<label>/]<flow>/<NN>-<step>.png
//
// Exit codes:
//   0 — walkthrough completed (review-booking page rendered)
//   1 — env var missing or walkthrough threw

import { chromium } from '@playwright/test';
import { walkHotelBooking } from './hotelBooking.walkthrough.js';
import { makeStepScreenshotter } from './screenshot.helper.js';
import { ensureStagingEnv, parseArgs } from './runner-utils.js';

const args = parseArgs(process.argv.slice(2));
const label = args.label;

ensureStagingEnv('e2e/walkthroughs/run-hotel-booking.js');

(async () => {
  // Headless by default for CI / scripted runs.
  // Pass `{ headless: false }` locally to watch the browser drive the flow.
  const browser = await chromium.launch();
  try {
    console.log(`\n=== hotel-booking ===`);
    const context = await browser.newContext();
    const page = await context.newPage();
    const flowName = 'hotel-booking-auth-chat';
    const onStep = makeStepScreenshotter({ flow: flowName, label });

    const wrappedOnStep = async (eventName, ctx) => {
      const { filepath } = await onStep(eventName, ctx);
      console.log(`  step: ${eventName.padEnd(40)} → ${filepath}`);
    };

    try {
      const result = await walkHotelBooking(page, { onStep: wrappedOnStep });
      console.log(`  finalUrl: ${result.finalUrl}`);
      console.log(`  duration: ${result.durationMs}ms`);
      console.log(`  entryEvents:    ${result.entryEvents.join(' → ')}`);
      console.log(`  bookingEvents:  ${result.bookingEvents.join(' → ')}`);
    } catch (err) {
      console.error(`  FAILED: ${err.message}`);
      const failureShot = `failure-hotel-booking.png`;
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
