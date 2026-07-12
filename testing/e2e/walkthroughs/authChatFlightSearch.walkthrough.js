// Flow B — authenticated chat → flight search.
//
// User journey (verified manually against staging 2026-05-04 + 2026-05-05):
//   1. Sign in via the auth modal (loginAsStagingTestUser → lands on /home or /chat)
//   2. Navigate to /chat
//   3. Type a fully-specified flight-search prompt
//   4. Click "Send message"
//   5. Chat bot replies with a "View flights" CTA
//   6. The page auto-redirects to /flights/recommendations
//      (`chat_rich_result_auto_navigate` fires)
//   7. Flight recommendations panel mounts with Cheapest / Best / Fastest tabs
//      (`flight_search_results_shown` fires twice — once with `source: 'chat-inline'`
//      from the chat bubble panel, once with `source: 'recommendations'` from the
//      page mount. Both are intentional and have the same `search_session_id`.)
//
// This is the **authenticated** sibling of `publicChatFlightSearch.walkthrough.js`
// and the most-popular real-user path (vs `flightSearch.walkthrough.js` which
// drives the `/flights/search` search-bar entry — a less-trafficked surface).
//
// NOTE on prompt choice: the AI is non-deterministic. Some prompts ("AMS to BCN
// for 1 adult") return a clarification request asking for date / trip type /
// passengers, in which case auto-navigation does NOT happen. The default prompt
// below is fully-specified (origin + destination + trip type + date + passengers)
// which has consistently returned non-empty FlightLogic results during manual
// verification on AMS → BCN. Override `options.prompt` to test specific scenarios.
//
// Also note: the chat-driven search may return mixed-origin results (cheapest
// from RTM even though the user asked AMS) — see issue #985 for the map-pin
// drift this causes. Doesn't affect this walkthrough (we don't assert origin).
//
// Verification handles:
//   - `user_login` after sign-in (from loginAsStagingTestUser)
//   - `chat_message_sent` after the user prompt is sent
//   - `chat_bot_response_received` after the AI reply renders
//   - `chat_rich_result_auto_navigate` when the auto-redirect kicks in
//   - `flight_search_results_shown` (source: "recommendations") when the panel mounts
//
// See:
//   - testing/e2e/walkthroughs/publicChatFlightSearch.walkthrough.js (guest sibling)
//   - docs/GTM_TRACKING_PLAN.md (event taxonomy)
//   - issue #954 (drift reconciliation — covers any GTM gaps)

import { expect } from '@playwright/test';
import { TIMEOUTS } from '../../utils/constants.js';
import { loginAsStagingTestUser } from './auth.helper.js';
import {
  noop,
  runSettledStep,
  runStep,
  waitForDataLayerEvent,
  waitForDataLayerEventMatching,
} from './walkthrough.utils.js';

const STAGING_BASE_URL = 'https://staging.myvoya.ai';

// Default prompt: AMS → BCN one-way is one of the most reliably-served routes
// on staging FlightLogic. The prompt MUST be specific enough to skip the AI's
// clarification step (otherwise the bot replies asking for trip-type / dates /
// passengers and no auto-navigation happens). Manual verification 2026-05-05:
//   - "find flights from amsterdam to inverness" → bot asks for date / trip
//     type / passengers (clarification, no navigate)
//   - "one-way flight from Amsterdam to Barcelona on 15 November 2026 for 1 adult"
//     → search runs, panel mounts, flight_search_results_shown × 2 fires
// Override `options.prompt` to exercise specific scenarios.
//
// The dates use 2026 explicitly so they don't drift out of the FlightLogic search
// window as time passes. Update the year once 2026 exits the search window
// (~12 months from current date).
const DEFAULT_PROMPT =
  'One-way flight from Amsterdam to Barcelona on 15 November 2026 for 1 adult';

/**
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {(event: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>} [options.onStep]
 * @param {string} [options.prompt] — chat prompt; default exercises AMS → BCN one-way
 *   on a fixed future date which has consistently returned non-empty FlightLogic
 *   results during manual verification (see `DEFAULT_PROMPT` above).
 * @returns {Promise<{ events: string[], finalUrl: string, durationMs: number }>}
 */
export async function walkAuthChatFlightSearch(page, options = {}) {
  const { onStep = noop, prompt = DEFAULT_PROMPT } = options;
  const t0 = Date.now();
  const events = [];

  // 1: login (helper appends its own events including user_login)
  const loginResult = await loginAsStagingTestUser(page, { onStep });
  events.push(...loginResult.events);

  // 2: navigate to /chat
  await page.goto(`${STAGING_BASE_URL}/chat`);
  await page.waitForLoadState('networkidle');
  await runStep(events, onStep, '__on_chat', { page });

  // Wait for the GTM container to attach so we don't miss events when reading
  // dataLayer later.
  await page.waitForFunction(() => Array.isArray(window.dataLayer), {
    timeout: TIMEOUTS.PAGE_LOAD,
  });

  // 3-4: type prompt + send
  const messageBox = page.getByRole('textbox', { name: 'Type your message...' });
  await messageBox.fill(prompt);
  const sendButton = page.getByRole('button', { name: 'Send message' });
  await expect(sendButton).toBeEnabled({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  await sendButton.click();
  await runStep(events, onStep, 'chat_message_sent', { page });

  // 5: wait for bot response — `chat_bot_response_received` is the cleanest signal
  await waitForDataLayerEvent(page, 'chat_bot_response_received', {
    timeout: TIMEOUTS.CHAT_FLIGHT_RESPONSE,
  });
  await runStep(events, onStep, 'chat_bot_response_received', { page });

  // 6: page auto-redirects to /flights/recommendations (no manual click on
  // "View flights" required — the SPA navigates itself for fully-specified
  // prompts that match a single search result set)
  await page.waitForURL(/\/flights\/recommendations/, {
    timeout: TIMEOUTS.PAGE_LOAD,
  });
  await runStep(events, onStep, 'chat_rich_result_auto_navigate', { page });

  // 7: flight_search_results_shown fires when the recommendations panel mounts
  // with data. Note: this event fires twice in practice — once with source
  // 'chat-inline' from the chat bubble panel that mounted earlier, once with
  // 'recommendations' here. We wait for the recommendations source specifically
  // because it's the post-navigation render we care about for screenshots.
  await waitForDataLayerEventMatching(
    page,
    'flight_search_results_shown',
    "e => e.source === 'recommendations'",
    { timeout: TIMEOUTS.CHAT_RESULT_SETTLE },
  );
  // Belt-and-braces: also wait for the visible tabs to assert the panel rendered
  await expect(page.getByRole('tab', { name: /cheapest/i })).toBeVisible({
    timeout: TIMEOUTS.ELEMENT_VISIBLE,
  });
  await runStep(events, onStep, 'flight_search_results_shown', { page });
  await runSettledStep(events, onStep, 'flight_search_results_shown', { page });

  return {
    events,
    finalUrl: page.url(),
    durationMs: Date.now() - t0,
  };
}
