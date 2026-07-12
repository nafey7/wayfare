// Runner for the public-chat walkthroughs (Phase 5).
//
// Usage (guest flows — no staging-test-user creds needed):
//   cd testing
//   TEST_ENV=staging node e2e/walkthroughs/run-public-chat.js --flow=hotel|itinerary [--label=before|after]
//
// Note: --flow is required. Public-chat flight is already covered by
// run-flight-search.js --flow=public-chat (existing runner since Phase 1).
// This runner only covers the Phase 5 additions.
//
// Exit codes:
//   0 — walkthrough completed
//   1 — env var missing or walkthrough threw

import { chromium } from '@playwright/test';
import { walkPublicChatHotelSearch } from './publicChatHotelSearch.walkthrough.js';
import { walkPublicChatItinerary } from './publicChatItinerary.walkthrough.js';
import { makeStepScreenshotter } from './screenshot.helper.js';
import { ensureStagingEnv, parseArgs } from './runner-utils.js';

const VALID_FLOWS = ['hotel', 'itinerary'];
const args = parseArgs(process.argv.slice(2));

if (!args.flow) {
  console.error(`--flow is required. Valid: ${VALID_FLOWS.join(', ')}.`);
  process.exit(1);
}
if (!VALID_FLOWS.includes(args.flow)) {
  console.error(`Unknown --flow=${JSON.stringify(args.flow)}. Valid: ${VALID_FLOWS.join(', ')}.`);
  process.exit(1);
}

const flow = args.flow;
const label = args.label;

// Public-chat walkthroughs don't login — no creds required.
ensureStagingEnv('e2e/walkthroughs/run-public-chat.js', { creds: false });

(async () => {
  // Headless by default for CI / scripted runs.
  // Pass `{ headless: false }` locally to watch the browser drive the flow.
  const browser = await chromium.launch();
  try {
    console.log(`\n=== public-chat ${flow} ===`);
    const context = await browser.newContext();
    const page = await context.newPage();
    const flowName = `public-chat-${flow}`;
    const onStep = makeStepScreenshotter({ flow: flowName, label });

    const wrappedOnStep = async (eventName, ctx) => {
      const { filepath } = await onStep(eventName, ctx);
      console.log(`  step: ${eventName.padEnd(40)} → ${filepath}`);
    };

    try {
      const walker = flow === 'hotel' ? walkPublicChatHotelSearch : walkPublicChatItinerary;
      const result = await walker(page, { onStep: wrappedOnStep });
      console.log(`  finalUrl: ${result.finalUrl}`);
      console.log(`  duration: ${result.durationMs}ms`);
      console.log(`  events:   ${result.events.join(' → ')}`);
    } catch (err) {
      console.error(`  FAILED: ${err.message}`);
      const failureShot = `failure-public-chat-${flow}.png`;
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
