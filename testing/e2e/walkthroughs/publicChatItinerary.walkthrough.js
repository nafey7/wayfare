// Phase 5B — public chat → itinerary (un-auth).
//
// User journey (verified manually against staging 2026-05-05):
//   1. Open https://staging.myvoya.ai/public/chat (no login required)
//   2. Type a fully-specified itinerary prompt
//   3. Click "Send message"
//   4. Bot generates a multi-day itinerary (~100-150s typical)
//   5. The page auto-redirects to /public/chat/itinerary?destination=<city>
//      (`chat_rich_result_auto_navigate` fires; no /<id> route since guests
//      can't save itineraries — the destination passes via query string and
//      the page reads from chat slice state)
//   6. Itinerary page mounts (`itinerary_results_shown` source 'chat' fires
//      from the chat-side bubble. Unlike hotels which fire 3 sources, this
//      surface only fires once — the page itself doesn't fire its own.)
//
// This is the guest sibling of `itinerary.walkthrough.js`. Differences:
//   - No auth (skip login)
//   - Final URL is /public/chat/itinerary?destination=<city> (not
//     /itinerary/<saved_id>) because guests don't have saved_itinerary_id
//
// Verification handles:
//   - `chat_message_sent` after the user prompt
//   - `chat_bot_response_received` after the AI reply (slow)
//   - `chat_rich_result_auto_navigate` when the auto-redirect kicks in
//   - `itinerary_results_shown` (source: 'chat') when the bubble mounts
//
// See:
//   - testing/e2e/walkthroughs/itinerary.walkthrough.js (auth sibling)
//   - docs/GTM_TRACKING_PLAN.md (event taxonomy)

import { expect } from '@playwright/test';
import { TIMEOUTS } from '../../utils/constants.js';
import { noop, runSettledStep, runStep, waitForDataLayerEvent } from './walkthrough.utils.js';

const STAGING_BASE_URL = 'https://staging.myvoya.ai';

// Default prompt: Paris 3-day plan on a fixed future window. Manual
// verification 2026-05-05 generated the itinerary in ~100-130s and
// auto-navigated to /public/chat/itinerary?destination=Paris. Override
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
export async function walkPublicChatItinerary(page, options = {}) {
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

  // 4: wait for bot response. Itinerary is the slowest chat workflow
  // (multi-day plan generation).
  await waitForDataLayerEvent(page, 'chat_bot_response_received', {
    timeout: TIMEOUTS.CHAT_ITINERARY_RESPONSE,
  });
  await runStep(events, onStep, 'chat_bot_response_received', { page });

  // 5: page auto-redirects to /public/chat/itinerary?destination=<city>.
  // Note: guest itinerary uses query-string state, NOT a path-based id —
  // because guests don't have a saved_itinerary_id. The route reads
  // destination + structured payload from the chat slice on mount.
  await page.waitForURL(/\/public\/chat\/itinerary(\?|$)/, {
    timeout: TIMEOUTS.PAGE_LOAD,
  });
  await runStep(events, onStep, 'chat_rich_result_auto_navigate', { page });

  // 6: itinerary_results_shown fires from the chat-side bubble. Only one
  // source ('chat') fires on this guest surface, unlike hotels' 3-source
  // pattern.
  await waitForDataLayerEvent(page, 'itinerary_results_shown', {
    timeout: TIMEOUTS.CHAT_RESULT_SETTLE,
  });
  // Belt-and-braces: assert at least one Day card heading is visible.
  // `.first()` because Day labels render in both ": " heading-style and
  // " · " label-style on the same page.
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
