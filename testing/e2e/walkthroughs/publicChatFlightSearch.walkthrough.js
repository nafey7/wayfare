// Flow C — public chat → flight search (un-auth).
//
// User journey (verified manually against staging 2026-05-02):
//   1. Open https://staging.myvoya.ai/public/chat (no login required)
//   2. Type a flight-search prompt
//   3. Click "Send message"
//   4. Chat bot replies with a "View flights" CTA
//   5. The page auto-redirects to /public/chat/flights/recommendations
//      (`chat_rich_result_auto_navigate` fires)
//   6. Flight recommendations panel mounts with Cheapest / Best / Fastest tabs
//      (`flight_search_results_shown` with source: 'recommendations' fires)
//
// NOTE on prompt choice: the AI is non-deterministic. Some prompts ("AMS → Inverness
// for 3 adults Oct 7–11") may return "No flights found" depending on FlightLogic
// availability, in which case there's no results panel to navigate to. The default
// prompt below uses AMS → BCN (one of the busiest staging routes) and a relative
// future date, which has consistently returned results during manual verification.
// Override `options.prompt` to test specific scenarios.
//
// Verification handles:
//   - `chat_message_sent` after the user prompt is sent
//   - `chat_bot_response_received` after the AI reply renders
//   - `chat_rich_result_auto_navigate` when the auto-redirect kicks in
//   - `flight_search_results_shown` (source: "recommendations") when the cards mount
//
// This flow is the better verification path than auth-first → /flights/search
// because it actually fires the documented `flight_search_results_shown` event;
// the auth-first path doesn't emit it (per drift notes / issue #954).
//
// Notes from manual run (2026-05-02):
//   - End-to-end took ~14s on staging (chat send → results visible)
//   - Result counts varied: a 3-adult Inverness search showed $5,119 cheapest
//   - The right-rail filter chips (May 3 / 1 Adult / One way / Economy) didn't
//     match the chat-derived params on first render — UX bug, doesn't affect
//     screenshot capture
//
// See:
//   - docs/GTM_TRACKING_PLAN.md (event taxonomy)
//   - issue #954 (drift reconciliation)

import { expect } from '@playwright/test';
import { TIMEOUTS } from '../../utils/constants.js';
import { noop, runSettledStep, runStep, waitForDataLayerEvent } from './walkthrough.utils.js';

const STAGING_BASE_URL = 'https://staging.myvoya.ai';

// Default prompt: AMS → BCN is one of the most reliably-served routes on staging
// FlightLogic. The prompt MUST be specific enough to skip the AI's clarification
// step (otherwise the bot replies asking for trip-type / dates / passengers and
// no auto-navigation happens). Manual verification 2026-05-02:
//   - "Find flights from Amsterdam to Barcelona next month for 1 adult"
//     → bot asks for trip type + return date (ambiguous "next month")
//   - "One-way flight from Amsterdam to Barcelona on 15 November 2026 for 1 adult"
//     → search runs, results panel mounts, flight_search_results_shown fires
// Override `options.prompt` to exercise specific scenarios.
//
// The dates use 2026 explicitly so they don't drift out of the FlightLogic search
// window as time passes. Update the year once 2026 exits the FlightLogic search
// window (~12 months from current date).
const DEFAULT_PROMPT =
  'One-way flight from Amsterdam to Barcelona on 15 November 2026 for 1 adult';

/**
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {(event: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>} [options.onStep]
 * @param {string} [options.prompt] — chat prompt; default exercises the AMS → BCN
 *   one-way path on a fixed future date which has consistently returned non-empty
 *   FlightLogic results during manual verification (see `DEFAULT_PROMPT` below).
 * @returns {Promise<{ events: string[], finalUrl: string, durationMs: number }>}
 */
export async function walkPublicChatFlightSearch(page, options = {}) {
  const { onStep = noop, prompt = DEFAULT_PROMPT } = options;
  const t0 = Date.now();
  const events = [];

  // 1: land on /public/chat
  await page.goto(`${STAGING_BASE_URL}/public/chat`);
  await page.waitForLoadState('networkidle');
  await runStep(events, onStep, '__on_public_chat', { page });

  // Wait for the GTM container to attach so we don't miss the early chat_opened
  // event when reading dataLayer later.
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

  // 4: wait for bot response — `chat_bot_response_received` is the cleanest signal
  await waitForDataLayerEvent(page, 'chat_bot_response_received', {
    timeout: TIMEOUTS.CHAT_FLIGHT_RESPONSE,
  });
  await runStep(events, onStep, 'chat_bot_response_received', { page });

  // 5: page auto-redirects to /public/chat/flights/recommendations (no manual click
  // on "View flights" required — the SPA navigates itself)
  await page.waitForURL(/\/public\/chat\/flights\/recommendations/, {
    timeout: TIMEOUTS.PAGE_LOAD,
  });
  await runStep(events, onStep, 'chat_rich_result_auto_navigate', { page });

  // 6: flight_search_results_shown fires when the recommendations panel mounts
  // with data
  await waitForDataLayerEvent(page, 'flight_search_results_shown', {
    timeout: TIMEOUTS.CHAT_RESULT_SETTLE,
  });
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
