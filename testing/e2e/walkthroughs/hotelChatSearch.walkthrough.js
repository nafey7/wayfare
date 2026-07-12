// Phase 3A — authenticated chat → hotel search.
//
// User journey (verified manually against staging 2026-05-04 + 2026-05-05):
//   1. Sign in via the auth modal (loginAsStagingTestUser)
//   2. Navigate to /chat
//   3. Type a fully-specified hotel-search prompt
//   4. Click "Send message"
//   5. Chat bot replies with a "View hotels" CTA — note that hotels do NOT
//      auto-navigate to /hotels/recommendations like flights do; the user
//      must click the CTA explicitly
//   6. Click the "View hotels" button → /hotels/recommendations
//   7. Hotel recommendations panel mounts with cards (`hotel_search_results_shown`
//      fires twice — once with `source: 'chat-inline'` from the chat bubble,
//      once with `source: 'recommendations'` from the panel mount, same as the
//      flight equivalent — both intentional, same `search_session_id`)
//
// This is the authenticated mirror of the (not-yet-built)
// `publicChatHotelSearch.walkthrough.js` and the most-popular hotel-search
// real-user path.
//
// NOTE on prompt choice: hotels are non-deterministic in two ways:
//   a) The AI may ask for clarification if the prompt is under-specified
//      (e.g. "find a hotel in Paris" → bot asks for dates / guest count)
//   b) The Google Geocoding step may need disambiguation for cities with
//      multiple metro areas (the bot will ask "Did you mean Paris, France
//      or Paris, Texas?")
// The default prompt below specifies city + dates + guest count to avoid
// both clarification paths.
//
// Verification handles:
//   - `user_login` after sign-in
//   - `chat_message_sent` after the user prompt
//   - `chat_bot_response_received` after the AI reply
//   - `hotel_search_results_shown` (source: "recommendations") after the
//     panel mounts post-navigation
//
// Known bugs surfaced during manual exploration (not blocking this walkthrough):
//   - Right-rail filter chips drift on /hotels/recommendations too — same
//     class of bug as #984 (which is flight-side); worth filing a hotels
//     equivalent if it persists on staging post-walkthrough run

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

// Default prompt: Paris is one of the most reliably-served destinations on
// staging (Google Geocoding resolves it cleanly to "Paris, France" without
// asking for disambiguation, and FlightLogic Hotel API has dense inventory).
// Manual verification 2026-05-04: this prompt yielded "1153 hotels in Paris
// for 2 nights, prices start from $81." Override `options.prompt` to test
// specific scenarios.
//
// The dates use 2026 explicitly so they don't drift out of the search window
// as time passes. Update once 2026 exits the window (~12 months from current).
const DEFAULT_PROMPT =
  'Find a hotel in Paris from 15 November 2026 to 17 November 2026 for 1 adult';

/**
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {(event: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>} [options.onStep]
 * @param {string} [options.prompt] — chat prompt; default exercises the Paris
 *   2-night 1-adult path which has consistently returned non-empty results.
 * @returns {Promise<{ events: string[], finalUrl: string, durationMs: number }>}
 */
export async function walkHotelChatSearch(page, options = {}) {
  const { onStep = noop, prompt = DEFAULT_PROMPT } = options;
  const t0 = Date.now();
  const events = [];

  // 1: login
  const loginResult = await loginAsStagingTestUser(page, { onStep });
  events.push(...loginResult.events);

  // 2: navigate to /chat
  await page.goto(`${STAGING_BASE_URL}/chat`);
  await page.waitForLoadState('networkidle');
  await runStep(events, onStep, '__on_chat', { page });

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

  // 5: wait for the AI reply with the "View hotels" CTA. Hotel search is
  // genuinely slow on staging — Google Geocoding lookup + FlightLogic Hotel
  // API search across 1000+ inventory before the bot replies. Manual runs
  // 2026-05-05 took 60-80s. CHAT_HOTEL_RESPONSE caps at 90s.
  await waitForDataLayerEvent(page, 'chat_bot_response_received', {
    timeout: TIMEOUTS.CHAT_HOTEL_RESPONSE,
  });
  await runStep(events, onStep, 'chat_bot_response_received', { page });

  // 6: click "View hotels" — hotels do NOT auto-navigate; the SPA waits for
  // the user to click the CTA. This differs from flights where
  // chat_rich_result_auto_navigate fires automatically after the bot reply.
  const viewHotelsBtn = page.getByRole('button', { name: 'View hotels' });
  await expect(viewHotelsBtn).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  await viewHotelsBtn.click();
  await page.waitForURL(/\/hotels\/recommendations/, { timeout: TIMEOUTS.PAGE_LOAD });
  await runStep(events, onStep, '__view_hotels_clicked', { page });

  // 7: hotel_search_results_shown fires when the recommendations panel mounts.
  // Like the flight equivalent, this fires twice — with source 'chat-inline'
  // from the chat bubble and 'recommendations' from the panel mount. We wait
  // for the recommendations source specifically.
  await waitForDataLayerEventMatching(
    page,
    'hotel_search_results_shown',
    "e => e.source === 'recommendations'",
    { timeout: TIMEOUTS.CHAT_RESULT_SETTLE },
  );
  // Belt-and-braces: also wait for at least one visible hotel card. The cards'
  // accessible name signature `/ night` is unique to recommendations cards
  // (matches the per-night price suffix). Mirrors the cheapest-tab assertion
  // in authChatFlightSearch.
  await expect(page.getByRole('button', { name: /\/ night/ }).first()).toBeVisible({
    timeout: TIMEOUTS.ELEMENT_VISIBLE,
  });
  await runStep(events, onStep, 'hotel_search_results_shown', { page });
  await runSettledStep(events, onStep, 'hotel_search_results_shown', { page });

  return {
    events,
    finalUrl: page.url(),
    durationMs: Date.now() - t0,
  };
}
