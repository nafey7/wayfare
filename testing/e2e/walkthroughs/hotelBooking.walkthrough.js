// Phase 3B — full hotel booking walkthrough.
//
// Composes hotelChatSearch.walkthrough.js (default; auth chat → recommendations)
// and continues all the way to /hotels/review-booking. STOPS at the page mount
// — does NOT click "Continue to payment" (would create a Revolut sandbox order)
// and does NOT attempt to fill the guest form (HotelReviewBookingPage has no
// dev-only Quick Fill button, unlike PassengerInfoPage).
//
// User journey (verified manually against staging 2026-05-04 + 2026-05-05):
//   [hotelChatSearch entry walkthrough]
//   1. Sign in
//   2. Drive chat → /hotels/recommendations
//   [this walkthrough continues here]
//   3. Click the first hotel's "Book Now" button
//      → /hotels/rooms/<encrypted-id>
//   4. Click the first room's "Reserve" button
//      → /hotels/review-booking
//   5. Assert the page mounted and "Continue to payment" exists.
//      DO NOT click it.
//
// Why stop at step 5 and not actually submit the form:
//   - HotelReviewBookingPage has NO equivalent of the flight Quick Fill
//     button. To submit, the walkthrough would have to fill ~10 fields per
//     guest (name, DOB, nationality, passport, email, phone, country, etc.)
//     — that's a separate form-filler concern, out of scope for a screenshot
//     capture walkthrough.
//   - Even with the form filled, clicking "Continue to payment" creates a
//     Revolut sandbox order — same constraint as flightBooking.
//   The post-Reserve render of /hotels/review-booking is the most stable,
//   reproducible "selected room, ready to enter guest details" state.
//
// Verification handles (from the entry walkthrough plus this one):
//   - All hotelChatSearch entry-walkthrough handles
//   - Synthetic `__on_hotel_rooms` after navigation
//   - Synthetic `__on_hotel_review_booking` after navigation; this is the
//     final state where screenshots should be taken
//
// Pre-existing bugs surfaced during manual exploration (not fixed here):
//   - `/hotels/review-booking` was rendering blank pre-#977 (Mantine
//     CountrySelect crash). Now fixed; this walkthrough exists in part to
//     guard against that class of regression.

import { expect } from '@playwright/test';
import { TIMEOUTS } from '../../utils/constants.js';
import { walkHotelChatSearch } from './hotelChatSearch.walkthrough.js';
import { noop, runStep } from './walkthrough.utils.js';

/**
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {(event: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>} [options.onStep]
 * @param {string} [options.prompt]
 *   Forwarded to hotelChatSearch (e.g. to swap city or dates).
 * @returns {Promise<{ events: string[], finalUrl: string, durationMs: number, entryEvents: string[], bookingEvents: string[] }>}
 */
export async function walkHotelBooking(page, options = {}) {
  const { onStep = noop, prompt } = options;
  const t0 = Date.now();
  const events = [];
  // bookingEvents tracks only the booking-leg steps (post-recommendations).
  // events also includes them via runStep, but the runner prints these
  // separately from the entry walkthrough events for readability.
  const bookingEvents = [];

  // 1-2: drive entry walkthrough → lands on /hotels/recommendations
  const entryResult = await walkHotelChatSearch(page, { onStep, prompt });
  events.push(...entryResult.events);

  // 3: click the first hotel card on /hotels/recommendations.
  // Post-#970 (SearchParamsBar redesign) the whole hotel card is a button
  // — there are no separate "Book Now" buttons inside. Pick the first card
  // by its accessible name signature: only hotel cards include the
  // " / night" per-night price suffix in their name (e.g. "Square ... USD
  // 599.16 total USD 299.58 / night").
  const firstCard = page.getByRole('button', { name: /\/ night/ }).first();
  await expect(firstCard).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  await firstCard.click();
  await page.waitForURL(/\/hotels\/rooms\//, { timeout: TIMEOUTS.PAGE_LOAD });
  await runStep(events, onStep, '__on_hotel_rooms', { page });
  bookingEvents.push('__on_hotel_rooms');

  // 4: click the first room's "Reserve" button → /hotels/review-booking.
  // The rooms page lists multiple rates per room with their own Reserve
  // buttons. Pick the first by document order.
  const reserve = page.getByRole('button', { name: 'Reserve' }).first();
  await expect(reserve).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  await reserve.click();
  await page.waitForURL(/\/hotels\/review-booking/, { timeout: TIMEOUTS.PAGE_LOAD });

  // 5: STOP — verify the page mounted and "Continue to payment" exists, but
  // DO NOT CLICK. Note the button is rendered as `Box component="button"` so
  // it has button role with name starting with "Continue to payment · $XXX"
  // (price suffix varies). Match the prefix loosely.
  await expect(
    page.getByRole('button', { name: /Continue to payment/i }),
  ).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  await runStep(events, onStep, '__on_hotel_review_booking', { page });
  bookingEvents.push('__on_hotel_review_booking');

  return {
    events,
    entryEvents: entryResult.events,
    bookingEvents,
    finalUrl: page.url(),
    durationMs: Date.now() - t0,
  };
}
