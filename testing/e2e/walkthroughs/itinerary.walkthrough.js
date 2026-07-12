// Phase 4 — authenticated chat → itinerary.
//
// User journey (verified manually against staging 2026-05-05):
//   1. Sign in via the auth modal (loginAsStagingTestUser)
//   2. Navigate to /chat
//   3. Type a fully-specified itinerary prompt
//   4. Click "Send message"
//   5. Chat bot generates a multi-day itinerary (slow — ~100-150s typical
//      on staging because the AI generates Day 1/2/3 cards with locations
//      and activities, all auto-saved to MongoDB during the response)
//   6. Page auto-redirects to /itinerary/<saved_itinerary_id>
//      (`chat_rich_result_auto_navigate` fires; the saved_itinerary_id
//      comes from the auto-save in ChatService and is returned in the
//      bot's response payload)
//   7. Itinerary page mounts (`itinerary_results_shown` with source 'chat'
//      fires from the chat-side bubble; the page itself doesn't fire a
//      separate event, see drift notes #954)
//
// This is the equivalent of the flight/hotel chat walkthroughs but for
// the itinerary surface. Itinerary auto-navigates like flights (vs hotels
// which require an explicit "View hotels" click).
//
// NOTE on prompt choice: itinerary is non-deterministic in two ways:
//   a) Under-specified prompts trigger clarification (e.g. "Plan a Paris
//      itinerary" → bot asks for dates / passenger count)
//   b) Itineraries can take 2+ minutes to generate. Use a generous
//      CHAT_ITINERARY_RESPONSE timeout.
// The default prompt below specifies city + dates + party size to bypass
// clarification on staging.
//
// Verification handles:
//   - `user_login` after sign-in
//   - `chat_message_sent` after the user prompt
//   - `chat_bot_response_received` after the AI reply (slow)
//   - `chat_rich_result_auto_navigate` when the SPA navigates
//   - `itinerary_results_shown` (source: 'chat') after the chat-side
//     bubble mounts. Note: this fires from the chat panel, NOT from the
//     /itinerary/<id> page itself — the page-level analogue is missing
//     and tracked in #954

import { expect } from '@playwright/test';
import { TIMEOUTS } from '../../utils/constants.js';
import { loginAsStagingTestUser } from './auth.helper.js';
import { noop, runSettledStep, runStep, waitForDataLayerEvent } from './walkthrough.utils.js';

const STAGING_BASE_URL = 'https://staging.myvoya.ai';

// Default prompt: Paris 3-day plan on a fixed future window. Manual
// verification 2026-05-05 generated a complete Day 1/2/3 plan in ~120s
// and auto-saved + auto-navigated to /itinerary/<id>. Override
// `options.prompt` to test specific scenarios.
const DEFAULT_PROMPT =
  'Plan a 3-day itinerary for Paris from 15 November 2026 to 17 November 2026 for 1 adult';

/**
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {(event: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>} [options.onStep]
 * @param {string} [options.prompt]
 * @returns {Promise<{ events: string[], finalUrl: string, durationMs: number }>}
 */
export async function walkItinerary(page, options = {}) {
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

  // 5: wait for the AI reply. Itinerary generation is the slowest of the
  // chat workflows (Day 1/2/3 cards + activities + auto-save). Use the
  // CHAT_ITINERARY_RESPONSE ceiling.
  await waitForDataLayerEvent(page, 'chat_bot_response_received', {
    timeout: TIMEOUTS.CHAT_ITINERARY_RESPONSE,
  });
  await runStep(events, onStep, 'chat_bot_response_received', { page });

  // 6: page auto-redirects to /itinerary/<saved_itinerary_id>. This works
  // when ChatService's auto-save returns a saved_itinerary_id in the
  // response payload (the default for authenticated users — guests fall
  // back to /itinerary with state via PublicChatPostAuthConversionTracker
  // post-auth).
  await page.waitForURL(/\/itinerary\/[a-f0-9]{24}/, { timeout: TIMEOUTS.PAGE_LOAD });
  await runStep(events, onStep, 'chat_rich_result_auto_navigate', { page });

  // 7: itinerary_results_shown fires from the chat-side bubble mount.
  // The /itinerary/<id> page itself doesn't currently fire an event (see
  // drift notes in #954) — the chat-bubble fire is the most reliable
  // signal we have.
  await waitForDataLayerEvent(page, 'itinerary_results_shown', {
    timeout: TIMEOUTS.CHAT_RESULT_SETTLE,
  });
  // Belt-and-braces: assert at least one Day card heading is visible on
  // the itinerary page itself. Mirrors the cheapest-tab assertion in
  // authChatFlightSearch and the / night assertion in hotelChatSearch.
  // Day labels render in both ": " and " · " formats on the page (heading-
  // style and label-style); .first() picks whichever appears first.
  await expect(page.getByText(/Day 1[: ·]/i).first()).toBeVisible({
    timeout: TIMEOUTS.ELEMENT_VISIBLE,
  });
  await runStep(events, onStep, 'itinerary_results_shown', { page });
  await runSettledStep(events, onStep, 'itinerary_results_shown', { page });

  return {
    events,
    finalUrl: page.url(),
    durationMs: Date.now() - t0,
  };
}
