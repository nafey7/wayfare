// Flow A — auth-first → flight search.
//
// User journey (verified manually against staging 2026-05-02):
//   1. Open https://staging.myvoya.ai/
//   2. Click "Sign in" header button → auth modal opens
//   3. Submit email STAGING_TEST_USER_EMAIL → "Welcome Back" step
//   4. Submit password → redirect to /home (PublicRoute decision)
//      `user_login` fires on the dataLayer
//   5. Navigate to /flights/search
//   6. Click the Origin/Destination card to expand the search bar
//   7. Fill From "Amsterdam" → pick "Amsterdam Airport Schiphol (AMS)"
//   8. Fill To "Barcelona" → pick "Barcelona International Airport (BCN)"
//   9. Click "Done" to close the route picker dialog
//  10. Click "Search flights" → URL becomes /flights/search?q=<base64(searchParams)>
//      Results render below the bar (44 flight cards in this manual run)
//
// Verification handles:
//   - `user_login` dataLayer event on step 4
//   - `flight_search_results_shown` does NOT fire on this auth-first → /flights/search
//     route (per drift notes, only the public-chat → /flights/recommendations path
//     fires it consistently). Falls back to the "Search flights" button being
//     enabled and the .flight-card list mounting.
//
// See:
//   - testing/e2e/pages/AuthModalPage.js (modal selectors)
//   - docs/GTM_TRACKING_PLAN.md (event taxonomy)
//   - issue #954 (drift reconciliation — covers why flight_search_results_shown is
//     missing here)

import { expect } from '@playwright/test';
import { TIMEOUTS } from '../../utils/constants.js';
import { loginAsStagingTestUser } from './auth.helper.js';

const STAGING_BASE_URL = 'https://staging.myvoya.ai';

/**
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {(event: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>} [options.onStep]
 * @param {string} [options.from] — default "Amsterdam"
 * @param {string} [options.to] — default "Barcelona"
 * @returns {Promise<{ events: string[], finalUrl: string, durationMs: number }>}
 */
export async function walkFlightSearchAuthFirst(page, options = {}) {
  const { onStep = noop, from = 'Amsterdam', to = 'Barcelona' } = options;
  const t0 = Date.now();
  const events = [];

  // 1-4: login (helper appends its own events)
  const loginResult = await loginAsStagingTestUser(page, { onStep });
  events.push(...loginResult.events);

  // 5: navigate to flight search
  await page.goto(`${STAGING_BASE_URL}/flights/search`);
  await page.waitForLoadState('networkidle');
  await runStep(events, onStep, '__on_flight_search_page', { page });

  // 6: expand the search bar by clicking the Origin/Destination header
  // (the bar is collapsed by default until interacted with)
  await page.getByRole('heading', { name: 'Origin', level: 5 }).click();

  // 7: fill From + pick airport
  const fromCombobox = page.getByRole('combobox', { name: 'City or airport' }).first();
  await fromCombobox.fill(from);
  // Wait for the airport listbox option matching the city + (IATA) suffix
  await page
    .getByRole('option', { name: new RegExp(`${from} Airport.*\\([A-Z]{3}\\)`, 'i') })
    .first()
    .click({ timeout: TIMEOUTS.ELEMENT_VISIBLE });

  // 8: fill To + pick airport
  const toCombobox = page.getByRole('combobox', { name: 'City or airport' }).nth(1);
  await toCombobox.fill(to);
  await page
    .getByRole('option', { name: new RegExp(`${to} International Airport.*\\([A-Z]{3}\\)`, 'i') })
    .first()
    .click({ timeout: TIMEOUTS.ELEMENT_VISIBLE });

  // 9: close route picker dialog
  await page.getByRole('button', { name: 'Done', exact: true }).click();
  await runStep(events, onStep, '__route_picked', { page });

  // 10: submit search
  // Search flights button has the same accessible name as the page header — pin to
  // the one inside <main> by waiting until it's enabled (the header copy isn't a
  // button until both From/To are filled).
  const searchButton = page.getByRole('button', { name: 'Search flights' }).last();
  await expect(searchButton).toBeEnabled({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
  await searchButton.click();

  // Wait for URL to update with the q= search-params payload (bar serialises
  // search to URL). This is more reliable than waiting on a card-render selector
  // because the cards render lazily as the FlightLogic API streams.
  await page.waitForURL(/\/flights\/search\?q=/, { timeout: TIMEOUTS.PAGE_LOAD });
  await runStep(events, onStep, '__search_submitted', { page });

  // Results panel mounts — wait for either a flight count header OR the first
  // card. "44 flights found" style header is the most stable signal.
  await expect(page.getByText(/\d+ flights? found/i)).toBeVisible({
    timeout: TIMEOUTS.PAGE_LOAD,
  });
  await runStep(events, onStep, '__results_visible', { page });

  return {
    events,
    finalUrl: page.url(),
    durationMs: Date.now() - t0,
  };
}

async function runStep(events, onStep, eventName, ctx) {
  events.push(eventName);
  await onStep(eventName, ctx);
}

function noop() {}
