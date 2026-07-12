// Runner for the itinerary walkthrough (Phase 4).
//
// Usage:
//   source .local/test-credentials/staging-test-user.env
//   cd testing
//   node e2e/walkthroughs/run-itinerary.js [--label=before|after]
//
// Output: PNG screenshots written to
//   .local/journal/<date>/screenshots/walkthroughs/<branch>/[<label>/]<flow>/<NN>-<step>.png
//
// Exit codes:
//   0 — walkthrough completed (/itinerary/<id> rendered)
//   1 — env var missing or walkthrough threw
//
// Note: itinerary generation is the slowest chat workflow (~100-150s
// typical). Total walkthrough duration is ~2-3 minutes.

import { chromium } from '@playwright/test';
import { walkItinerary } from './itinerary.walkthrough.js';
import { makeStepScreenshotter } from './screenshot.helper.js';
import { ensureStagingEnv, parseArgs } from './runner-utils.js';

const args = parseArgs(process.argv.slice(2));
const label = args.label;

ensureStagingEnv('e2e/walkthroughs/run-itinerary.js');

(async () => {
  // Headless by default for CI / scripted runs.
  // Pass `{ headless: false }` locally to watch the browser drive the flow.
  const browser = await chromium.launch();
  try {
    console.log(`\n=== itinerary ===`);
    const context = await browser.newContext();
    const page = await context.newPage();
    const flowName = 'itinerary-auth-chat';
    const onStep = makeStepScreenshotter({ flow: flowName, label });

    const wrappedOnStep = async (eventName, ctx) => {
      const { filepath } = await onStep(eventName, ctx);
      console.log(`  step: ${eventName.padEnd(40)} → ${filepath}`);
    };

    try {
      const result = await walkItinerary(page, { onStep: wrappedOnStep });
      console.log(`  finalUrl: ${result.finalUrl}`);
      console.log(`  duration: ${result.durationMs}ms`);
      console.log(`  events:   ${result.events.join(' → ')}`);
    } catch (err) {
      console.error(`  FAILED: ${err.message}`);
      const failureShot = `failure-itinerary.png`;
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
