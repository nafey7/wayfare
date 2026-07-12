// spec: testing/specs/auth.md — Section 5, Scenarios 5.1–5.4
// seed: testing/seed.spec.js
//
// Per plan Appendix B: ProtectedRoute redirects to `/` (not `/login`) when
// unauthenticated. PublicRoute can land authenticated users on `/chat`
// instead of `/home` under certain localStorage flags, but that's not in
// scope here — we start with a cleared auth state.

import { test, expect } from '../../../fixtures/auth-fixtures.js';
import { URLS, TIMEOUTS } from '../../../utils/constants.js';

// Each test runs in a fresh Playwright browser context (fullyParallel: true in
// playwright.config.js), so localStorage/cookies are already empty. No explicit
// clearAuthState() call is needed.
const PROTECTED_ROUTES = [
  { path: '/home', scenario: '5.1' },
  { path: '/profile', scenario: '5.2' },
  { path: '/chat', scenario: '5.3' },
  { path: '/itineraries', scenario: '5.4' },
];

test.describe('Auth — Protected Routes', () => {
  for (const { path, scenario } of PROTECTED_ROUTES) {
    test(`should redirect unauthenticated user from ${path} to landing (§${scenario})`, async ({
      page,
    }) => {
      await page.goto(`${URLS.FRONTEND}${path}`);

      // ProtectedRoute sends the user back to the landing page at `/`.
      // `toHaveURL` auto-retries until the React Router redirect settles;
      // no explicit `waitForLoadState` needed.
      await expect(page).toHaveURL(`${URLS.FRONTEND}/`, {
        timeout: TIMEOUTS.PAGE_LOAD,
      });

      await expect(
        page.getByRole('heading', { level: 1, name: /Your next trip/ })
      ).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
    });
  }
});
