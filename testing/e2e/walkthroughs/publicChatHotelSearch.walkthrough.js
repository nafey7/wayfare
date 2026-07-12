// Phase 5A — public chat → hotel search (un-auth).
//
// User journey (verified manually against staging 2026-05-05):
//   1. Open https://staging.myvoya.ai/public/chat (no login required)
//   2. Type a hotel-search prompt
//   3. Click "Send message"
//   4. Bot replies with summary + "View hotels" CTA
//   5. The page auto-redirects to /public/chat/hotels/recommendations
//      (`chat_rich_result_auto_navigate` fires; this differs from the auth
//      `/chat` → hotels path which requires a manual "View hotels" click —
//      see hotelChatSearch.walkthrough.js for the auth sibling)
//   6. Hotel recommendations panel mounts. `hotel_search_results_shown`
//      fires three times on this guest path: source 'chat-inline', 'chat',
//      and 'recommendations'. We wait for the recommendations source.
//
// Verification handles:
//   - `chat_message_sent` after the user prompt
//   - `chat_bot_response_received` after the AI reply
//   - `chat_rich_result_auto_navigate` when the auto-redirect kicks in
//   - `hotel_search_results_shown` (source: 'recommendations') when the
//     panel mounts
//
// See:
//   - testing/e2e/walkthroughs/hotelChatSearch.walkthrough.js (auth sibling)
//   - testing/e2e/walkthroughs/publicChatFlightSearch.walkthrough.js (guest
//     flight equivalent, same auto-navigate pattern)
//   - docs/GTM_TRACKING_PLAN.md (event taxonomy)

import { expect } from '@playwright/test';
import { TIMEOUTS } from '../../utils/constants.js';
import {
  noop,
  runSettledStep,
  runStep,
  waitForDataLayerEvent,
  waitForDataLayerEventMatching,
} from './walkthrough.utils.js';

const STAGING_BASE_URL = 'https://staging.myvoya.ai';

// Default prompt: Paris is a reliably-served destination on staging
// (Google Geocoding resolves cleanly, FlightLogic Hotel API returns dense
// inventory). Manual verification 2026-05-05 yielded "1155 hotels in
// Paris for 2 nights, prices start from $81." Override `options.prompt`
// to test specific scenarios.
const DEFAULT_PROMPT =
  'Find a hotel in Paris from 15 November 2026 to 17 November 2026 for 1 adult';

/**
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {(event: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>} [options.onStep]
 * @param {string} [options.prompt]
 * @returns {Promise<{ events: string[], finalUrl: string, durationMs: number }>}
 */
export async function walkPublicChatHotelSearch(page, options = {}) {
  const { onStep = noop, prompt = DEFAULT_PROMPT } = options;
  const t0 = Date.now();
  const events = [];

  // 1: land on /public/chat
  await page.goto(`${STAGING_BASE_URL}/public/chat`);
  await page.waitForLoadState('networkidle');
  await runStep(events, onStep, '__on_public_chat', { page });

  await page.waitForFunction(() => Array.isArray(window.dataLayer), {
    timeout: TIMEOUTS.PAGE_LOAD,
  });

  // 2-3: type prompt + send
  const messageBox = page.getByRole('textbox', { name: 'Type your message...' });
  await messageBox.fill(prompt);
  const sendButton = page.getByRole('button', { name: 'Send message' });
  await expect(sendButton).toBeEnabled({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  await sendButton.click();
  await runStep(events, onStep, 'chat_message_sent', { page });

  // 4: wait for bot response. Hotel chat is slow on staging — Google
  // Geocoding + FlightLogic Hotel inventory walk before the reply.
  await waitForDataLayerEvent(page, 'chat_bot_response_received', {
    timeout: TIMEOUTS.CHAT_HOTEL_RESPONSE,
  });
  await runStep(events, onStep, 'chat_bot_response_received', { page });

  // 5: page auto-redirects to /public/chat/hotels/recommendations.
  // No manual click on "View hotels" required — the SPA navigates itself
  // for fully-specified prompts on the guest path.
  await page.waitForURL(/\/public\/chat\/hotels\/recommendations/, {
    timeout: TIMEOUTS.PAGE_LOAD,
  });
  await runStep(events, onStep, 'chat_rich_result_auto_navigate', { page });

  // 6: hotel_search_results_shown fires for the panel mount. Three sources
  // fire on this guest path (chat-inline, chat, recommendations); wait for
  // the recommendations one.
  await waitForDataLayerEventMatching(
    page,
    'hotel_search_results_shown',
    "e => e.source === 'recommendations'",
    { timeout: TIMEOUTS.CHAT_RESULT_SETTLE },
  );
  // Belt-and-braces: assert at least one visible hotel card. Card
  // accessible names include `/ night` (per-night price suffix).
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
