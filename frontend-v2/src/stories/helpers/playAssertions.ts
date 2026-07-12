// Reusable assertion helpers for Storybook `play` functions.
//
// Story authors should declare what a successful render looks like
// rather than relying on cross-cutting heuristics. The helpers below
// cover the assertions that came up while reviewing the chat / flight
// recommendations track (PR #703, PR #852); extend per domain as needed.
//
// Usage:
//
//   import { expect, within } from 'storybook/test';
//   import { expectAirportPair, expectDurationPresent, expectNoPlaceholderText }
//     from '@/stories/helpers/playAssertions';
//
//   export const Default: Story = {
//     play: async ({ canvasElement }) => {
//       const canvas = within(canvasElement);
//       expectAirportPair(canvas, 'AMS', 'BCN');
//       expectDurationPresent(canvas);
//       expectNoPlaceholderText(canvas);
//     },
//   };

import { expect, type within } from 'storybook/test';

type Canvas = ReturnType<typeof within>;

/** A duration formatted like "2h 15m", "10h 0m", "0h 5m". */
const DURATION_PATTERN = /\d+\s*h\s+\d+\s*m/i;

/** Sentinels for "data is missing" — what `flightMapper`'s fallback prints. */
const PLACEHOLDER_PATTERNS: Array<{ pattern: RegExp; label: string; budgetKey: 'na' | 'duration' }> = [
  { pattern: /\bN\/A\b/, label: 'N/A', budgetKey: 'na' },
  { pattern: /\b0\s*h\s+0\s*m\b/i, label: '0h 0m', budgetKey: 'duration' },
];

/** Assert an IATA airport code (e.g. "AMS", "JFK") is visible at least once. */
export function expectAirportCode(canvas: Canvas, code: string): void {
  // IATA codes appear multiple times on round-trip / multi-leg cards (header,
  // outbound, inbound, summary). We just need at least one — use queryAllByText
  // and check non-empty rather than getByText (which throws on multiple matches).
  const matches = canvas.queryAllByText(new RegExp(`\\b${code}\\b`));
  expect(matches.length, `expected airport code "${code}" to be visible at least once`).toBeGreaterThan(0);
}

/** Assert both an origin and destination airport code are visible. */
export function expectAirportPair(canvas: Canvas, origin: string, destination: string): void {
  expectAirportCode(canvas, origin);
  expectAirportCode(canvas, destination);
}

/**
 * Assert at least one duration string in `<n>h <m>m` format is visible.
 * Useful for any flight / hotel card that should display a time figure.
 */
export function expectDurationPresent(canvas: Canvas): void {
  const matches = canvas.queryAllByText(DURATION_PATTERN);
  expect(
    matches.length,
    `expected at least one duration like "2h 15m" to be visible (got ${matches.length})`
  ).toBeGreaterThan(0);
}

/**
 * Assert a price string with currency symbol (€, $, £) is visible.
 * `currency` is optional — when omitted, any currency is accepted.
 */
export function expectPricePresent(canvas: Canvas, currency?: '€' | '$' | '£'): void {
  const symbols = currency ? [currency] : ['€', '$', '£'];
  const found = symbols.some((sym) => {
    return canvas.queryAllByText(new RegExp(`${sym.replace(/[$]/g, '\\$')}\\s*\\d`)).length > 0;
  });
  expect(found, `expected a price with currency symbol${currency ? ` ${currency}` : ''}`).toBe(true);
}

/**
 * Assert no placeholder text leaked through. This is the primary guard
 * against the PR #852 class — fixture is shape-compatible with the type
 * but doesn't supply what the render util reads, so cards display N/A
 * and 0h 0m instead of real data.
 *
 * Pass `allow` to permit a small budget of placeholder occurrences (some
 * stories legitimately render one or two N/A cells, e.g. a flight whose
 * inbound leg is intentionally absent).
 */
export function expectNoPlaceholderText(canvas: Canvas, allow: { naBudget?: number; durationBudget?: number } = {}): void {
  const budgets = {
    na: allow.naBudget ?? 0,
    duration: allow.durationBudget ?? 0,
  };
  for (const { pattern, label, budgetKey } of PLACEHOLDER_PATTERNS) {
    const matches = canvas.queryAllByText(pattern);
    const budget = budgets[budgetKey];
    expect(
      matches.length,
      `expected at most ${budget} occurrence(s) of "${label}" placeholder; got ${matches.length}. ` +
        `If the placeholder is intentional in this story, raise the budget; otherwise the fixture ` +
        `is missing fields the component reads (see /storybook-story skill, step 2).`
    ).toBeLessThanOrEqual(budget);
  }
}

/**
 * Composite check for a flight card. Asserts that origin, destination,
 * a duration, and a price are all visible — and that the placeholder
 * text isn't leaking through.
 *
 * For round-trip stories, both `outbound` and `inbound` must be supplied
 * so the inbound leg gets validated separately (PR #852's second-pass
 * regression rendered outbound correctly but inbound as N/A).
 */
export function expectFlightCardPopulated(
  canvas: Canvas,
  legs: { outbound: { origin: string; destination: string }; inbound?: { origin: string; destination: string } }
): void {
  expectAirportPair(canvas, legs.outbound.origin, legs.outbound.destination);
  if (legs.inbound) {
    expectAirportPair(canvas, legs.inbound.origin, legs.inbound.destination);
  }
  expectDurationPresent(canvas);
  expectPricePresent(canvas);
  expectNoPlaceholderText(canvas);
}

// ---------------------------------------------------------------------------
// Hotel-card helpers (PR #849: hotel search/results)
// ---------------------------------------------------------------------------

/**
 * Assert a hotel name is visible at least once.
 * Uses queryAllByText so multiple occurrences don't throw.
 */
export function expectHotelName(canvas: Canvas, name: string): void {
  const matches = canvas.queryAllByText(new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  expect(matches.length, `expected hotel name "${name}" to be visible at least once`).toBeGreaterThan(0);
}

/**
 * Assert a star-rating chip / label is visible for the given count.
 */
export function expectStarRating(canvas: Canvas, stars: number): void {
  // Matches both "5 stars" (old inline format) and "5-star" (new chip format).
  const matches = canvas.queryAllByText(new RegExp(`${stars}[- ]?stars?`, 'i'));
  expect(matches.length, `expected "${stars}-star" chip or "${stars} stars" label to be visible`).toBeGreaterThan(0);
}

/**
 * Assert a price formatted as "<currency> <amount>" is visible.
 */
export function expectPricePerNight(canvas: Canvas, currency: string): void {
  // \s* matches both "EUR 1,234" (code + space) and "€1,234" (symbol, no space).
  const matches = canvas.queryAllByText(new RegExp(`${currency.replace(/[$]/g, '\\$')}\\s*[\\d.,]+`));
  expect(
    matches.length,
    `expected a price formatted as "${currency}<amount>" to be visible`
  ).toBeGreaterThan(0);
}

/**
 * Composite check for a hotel card.
 */
export function expectHotelCardPopulated(
  canvas: Canvas,
  opts: { name: string; stars?: number; currency?: string }
): void {
  expectHotelName(canvas, opts.name);
  if (opts.stars !== undefined) {
    expectStarRating(canvas, opts.stars);
  }
  if (opts.currency) {
    expectPricePerNight(canvas, opts.currency);
  }
  expectNoPlaceholderText(canvas);
}

// ---------------------------------------------------------------------------
// Itinerary helpers (PR #851)
// ---------------------------------------------------------------------------

/**
 * Assert an itinerary day card is visible with the given day number chip and title.
 * The redesigned card renders the day chip ("Day N") and title in separate elements.
 */
export function expectItineraryDayCard(canvas: Canvas, dayNumber: number, title: string): void {
  const chipMatches = canvas.queryAllByText(new RegExp(`Day\\s+${dayNumber}\\b`, 'i'));
  expect(
    chipMatches.length,
    `expected day chip "Day ${dayNumber}" to be visible`
  ).toBeGreaterThan(0);

  const titlePattern = new RegExp(title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
  const titleMatches = canvas.queryAllByText(titlePattern);
  expect(
    titleMatches.length,
    `expected itinerary day card title "${title}" to be visible`
  ).toBeGreaterThan(0);
}

/**
 * Assert the linked-booking chips group is rendered.
 */
export function expectLinkedBookingChips(canvas: Canvas): void {
  const groups = canvas.queryAllByRole('group', {
    name: /bookings linked to this itinerary/i,
  });
  expect(groups.length, 'expected linked-booking chips group to be visible').toBeGreaterThan(0);
}

// ---------------------------------------------------------------------------
// Profile booking helpers (PR #851)
// ---------------------------------------------------------------------------

/**
 * Assert a profile booking card shows the expected route text.
 */
export function expectBookingCardPopulated(canvas: Canvas, routeText: string | RegExp): void {
  const pattern = typeof routeText === 'string' ? new RegExp(routeText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') : routeText;
  const matches = canvas.queryAllByText(pattern);
  expect(
    matches.length,
    `expected booking card with text matching ${String(routeText)} to be visible`
  ).toBeGreaterThan(0);
}

// ---------------------------------------------------------------------------
// Hotel-detail helpers (PR #850)
// ---------------------------------------------------------------------------

/**
 * Assert the cancellation policy card shows the expected text.
 */
export function expectCancellationCopy(
  canvas: Canvas,
  opts: { refundable?: boolean; hasDeadline?: boolean; containsText?: string }
): void {
  const headings = canvas.queryAllByText(/cancellation policy/i);
  expect(headings.length, 'expected "Cancellation policy" heading').toBeGreaterThan(0);

  if (opts.refundable === true) {
    const refundable = canvas.queryAllByText(/refundable/i);
    expect(refundable.length, 'expected "Refundable" to appear in cancellation copy').toBeGreaterThan(0);
  }
  if (opts.refundable === false) {
    const nonRefundable = canvas.queryAllByText(/non-refundable/i);
    expect(
      nonRefundable.length,
      'expected "Non-refundable" to appear in cancellation copy'
    ).toBeGreaterThan(0);
  }
  if (opts.hasDeadline) {
    const deadline = canvas.queryAllByText(/deadline/i);
    expect(deadline.length, 'expected "Deadline" text in cancellation copy').toBeGreaterThan(0);
  }
  if (opts.containsText) {
    const found = canvas.queryAllByText(new RegExp(opts.containsText, 'i'));
    expect(found.length, `expected "${opts.containsText}" in cancellation copy`).toBeGreaterThan(0);
  }
}

/**
 * Assert the price breakdown card shows a total amount with the expected currency.
 */
export function expectPriceBreakdownTotals(
  canvas: Canvas,
  opts: { currency: '€' | '$' | '£'; hasTotal: boolean; hasDiscount?: boolean }
): void {
  const heading = canvas.queryAllByText(/price summary/i);
  expect(heading.length, 'expected "Price summary" heading').toBeGreaterThan(0);

  if (opts.hasTotal) {
    expectPricePresent(canvas, opts.currency);
  }
  if (opts.hasDiscount) {
    const discount = canvas.queryAllByText(/promo discount/i);
    expect(discount.length, 'expected promo discount row in price breakdown').toBeGreaterThan(0);
  }
}

/**
 * Assert the hotel info banner shows the hotel name and night count.
 */
export function expectHotelBannerPopulated(
  canvas: Canvas,
  opts: { hotelName: string; nights: number }
): void {
  const nameMatches = canvas.queryAllByText(new RegExp(opts.hotelName, 'i'));
  expect(
    nameMatches.length,
    `expected hotel name "${opts.hotelName}" in banner`
  ).toBeGreaterThan(0);

  const nightsPattern = new RegExp(`${opts.nights}\\s*night`, 'i');
  const nightMatches = canvas.queryAllByText(nightsPattern);
  expect(
    nightMatches.length,
    `expected "${opts.nights} night(s)" in banner`
  ).toBeGreaterThan(0);
}

/**
 * Assert the room configurator shows the expected total adults and children summary.
 */
export function expectRoomConfigPopulated(
  canvas: Canvas,
  opts: { totalAdults: number; totalChildren: number }
): void {
  const adultsPattern = new RegExp(`${opts.totalAdults}\\s*adult`, 'i');
  const adults = canvas.queryAllByText(adultsPattern);
  expect(
    adults.length,
    `expected "${opts.totalAdults} adult(s)" summary in room configurator`
  ).toBeGreaterThan(0);

  const childrenPattern = new RegExp(`${opts.totalChildren}\\s*child`, 'i');
  const children = canvas.queryAllByText(childrenPattern);
  expect(
    children.length,
    `expected "${opts.totalChildren} child(ren)" summary in room configurator`
  ).toBeGreaterThan(0);
}

/**
 * Assert that an itinerary day title (e.g. "Arrival & Gothic Quarter") is
 * visible in the canvas. Used by ItineraryResultMessage mobile stories where
 * ItineraryDetailsComponent renders day-by-day preview cards.
 */
export function expectItineraryDayPresent(canvas: Canvas, dayTitle: string): void {
  const escaped = dayTitle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const matches = canvas.queryAllByText(new RegExp(escaped, 'i'));
  expect(
    matches.length,
    `expected itinerary day title "${dayTitle}" to be visible at least once`
  ).toBeGreaterThan(0);
}
