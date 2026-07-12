// Phase 2B — full flight booking walkthrough.
//
// Composes a flight-search entry walkthrough (auth chat by default, search
// bar optional) and continues all the way to /flights/review-booking. STOPS
// before clicking "Continue to payment" — that button creates a Revolut
// sandbox order (and for GDS suppliers, a real PNR/booking record on the
// supplier side). Walkthroughs are read-only against the booking system.
//
// User journey (verified manually against staging 2026-05-04 + 2026-05-05):
//   [entry walkthrough]
//   1. Sign in via auth modal (auth-chat) or skip (public-chat)
//   2. Drive chat / search-bar to /flights/recommendations
//   [this walkthrough continues here]
//   3. Click the first flight card (the whole card is a button)
//      → /flights/details/<encrypted-id>
//   4. Click "Complete Passenger Details"
//      → /flights/passenger-info
//   5. Click "Auto-fill all passengers" (the dev-only Quick Fill button,
//      visible because VITE_ENV !== 'production' on staging)
//      → all passenger fields populated with Test1 Passenger / etc.
//      → contact email / phone / phone-country populated
//   6. Click "Review booking"
//      → /flights/review-booking
//   7. Assert "Continue to payment" button is visible (DO NOT CLICK)
//      → walkthrough returns
//
// Why stop at step 7 and not step 8 (Continue to payment):
//   - LCC suppliers: clicking creates a Revolut sandbox order — sandbox-side
//     residue accumulates per run, polluting Revolut admin.
//   - GDS suppliers: clicking creates a Revolut order AND a real booking
//     record (PNR-style hold) on the supplier side that we'd have to
//     manually cancel. That's a hard no for repeated walkthrough runs.
//   The review-booking page mount with all data hydrated is the most
//   stable, reproducible "fully-booked-but-not-paid" state we can capture.
//
// Note on the dev-only Quick Fill button:
//   `frontend-v2/src/features/flights/pages/PassengerInfoPage.tsx` gates
//   the "Auto-fill all passengers" button behind `VITE_ENV !== 'production'`.
//   Staging satisfies this. Production deploys do NOT show the button — so
//   this walkthrough is staging-only by design (see env check in
//   run-flight-booking.js).
//
// Verification handles (from the entry walkthrough plus this one):
//   - All entry-walkthrough handles (chat_message_sent, ...,
//     flight_search_results_shown)
//   - Synthetic `__on_flight_details` after navigation
//   - Synthetic `__on_passenger_info` after navigation
//   - Synthetic `__quick_fill_clicked` after the auto-fill button click
//   - Synthetic `__on_review_booking` after navigation; this is the final
//     state where screenshots should be taken
//
// Known pre-existing bugs surfaced during manual exploration (not fixed by
// this walkthrough — tracked separately):
//   - Right-rail filter chips drift (#984)
//   - Map pin shows first-card origin instead of searched origin (#985)
//   - Chat history doesn't persist on /flights/review-booking (#986)
//   - CountrySelect cosmetic: phone country shows "CA +1" for stored
//     dial code "1" because Canada is the first array match (#979)

import { expect } from '@playwright/test';
import { TIMEOUTS } from '../../utils/constants.js';
import { walkAuthChatFlightSearch } from './authChatFlightSearch.walkthrough.js';
import { walkFlightSearchAuthFirst } from './flightSearch.walkthrough.js';
import { noop, runStep } from './walkthrough.utils.js';

/**
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {(event: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>} [options.onStep]
 * @param {'chat' | 'searchbar'} [options.entryPoint]
 *   How to reach `/flights/recommendations`. Defaults to `chat` — the most
 *   popular real-user path. Pass `searchbar` to use the auth-first search-bar
 *   walkthrough, useful for migration PRs touching that surface.
 * @param {string} [options.prompt]
 *   Forwarded to the entry walkthrough when entryPoint='chat'.
 * @returns {Promise<{ events: string[], finalUrl: string, durationMs: number, entryEvents: string[], bookingEvents: string[] }>}
 */
export async function walkFlightBooking(page, options = {}) {
  const { onStep = noop, entryPoint = 'chat', prompt } = options;
  const t0 = Date.now();
  const events = [];
  // bookingEvents tracks only the booking-leg steps (post-recommendations).
  // events also includes them via runStep, but the runner prints these
  // separately from the entry walkthrough events for readability.
  const bookingEvents = [];

  // 1-2: drive entry walkthrough → lands on /flights/recommendations (or
  // /flights/search?q=... for the searchbar entry)
  const entryResult =
    entryPoint === 'searchbar'
      ? await walkFlightSearchAuthFirst(page, { onStep })
      : await walkAuthChatFlightSearch(page, { onStep, prompt });
  events.push(...entryResult.events);

  // 3: click the first flight card on /flights/recommendations.
  // The whole card is a button (post-#970 SearchParamsBar redesign — there
  // are no separate "Book Now" buttons inside the cards in chat-driven
  // recommendations; the card itself navigates).
  // For the searchbar entry, the cards on /flights/search?q= still use the
  // "Book Ticket" button — handle both shapes.
  if (entryPoint === 'searchbar') {
    const bookTicket = page.getByRole('button', { name: 'Book Ticket' }).first();
    await bookTicket.click({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  } else {
    // The chat-driven recommendations panel renders each flight card as one
    // big button. Inside the card is a smaller "Flight details" button. Both
    // match `getByRole('button', ...)`. Pick the OUTER card buttons by their
    // accessible name signature: only the card name contains the route arrow
    // pattern `(IATA) → (IATA)` (e.g. "Amsterdam (AMS) → Barcelona (BCN)").
    const firstCard = page
      .getByRole('button', { name: /\([A-Z]{3}\) → \w/ })
      .first();
    await firstCard.click({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  }
  await page.waitForURL(/\/flights\/details\//, { timeout: TIMEOUTS.PAGE_LOAD });
  await runStep(events, onStep, '__on_flight_details', { page });
  bookingEvents.push('__on_flight_details');

  // 4: click "Complete Passenger Details" → /flights/passenger-info
  const completeBtn = page.getByRole('button', { name: 'Complete Passenger Details' });
  await expect(completeBtn).toBeEnabled({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  await completeBtn.click();
  await page.waitForURL(/\/flights\/passenger-info/, { timeout: TIMEOUTS.PAGE_LOAD });
  // Also wait for the form heading to render — the route briefly shows a
  // loader skeleton while the revalidate response hydrates.
  await expect(page.getByRole('heading', { name: 'Passenger details' })).toBeVisible({
    timeout: TIMEOUTS.PAGE_LOAD,
  });
  await runStep(events, onStep, '__on_passenger_info', { page });
  bookingEvents.push('__on_passenger_info');

  // 5: click "Auto-fill all passengers" — populates everything via the
  // dev-only Quick Fill (VITE_ENV !== 'production'). Confirms the button
  // is present BEFORE clicking so we get a clean error if the gate flips.
  const quickFill = page.getByRole('button', { name: 'Auto-fill all passengers' });
  await expect(quickFill).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  await quickFill.click();
  // Anchor on a populated form field before proceeding — Quick Fill writes
  // to React state and re-renders, so there's a brief window where Review
  // booking can become enabled before fields actually carry values. Waiting
  // for First name to be non-empty avoids flaky empty-passenger-data
  // screenshots if the runner is repeated.
  await expect(page.getByRole('textbox', { name: 'First name' }).first()).not.toHaveValue('', {
    timeout: TIMEOUTS.ELEMENT_VISIBLE,
  });
  await runStep(events, onStep, '__quick_fill_clicked', { page });
  bookingEvents.push('__quick_fill_clicked');

  // 6: click "Review booking" → /flights/review-booking
  const reviewBtn = page.getByRole('button', { name: 'Review booking' });
  await expect(reviewBtn).toBeEnabled({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  await reviewBtn.click();
  await page.waitForURL(/\/flights\/review-booking/, { timeout: TIMEOUTS.PAGE_LOAD });
  // Wait for the page heading to confirm the route fully rendered.
  await expect(page.getByRole('heading', { name: 'Review your booking' })).toBeVisible({
    timeout: TIMEOUTS.PAGE_LOAD,
  });

  // 7: STOP — confirm "Continue to payment" exists, but DO NOT CLICK.
  // Clicking would create a Revolut sandbox order (and for GDS suppliers,
  // a real PNR-style booking record).
  await expect(page.getByRole('button', { name: 'Continue to payment' })).toBeVisible({
    timeout: TIMEOUTS.ELEMENT_VISIBLE,
  });
  await runStep(events, onStep, '__on_review_booking', { page });
  bookingEvents.push('__on_review_booking');

  return {
    events,
    entryEvents: entryResult.events,
    bookingEvents,
    finalUrl: page.url(),
    durationMs: Date.now() - t0,
  };
}
