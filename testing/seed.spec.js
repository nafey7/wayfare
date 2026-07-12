/**
 * Seed test for Playwright agent test generation.
 *
 * This file is the **template** that the Playwright Generator agent uses to
 * understand Voya's testing conventions. Tests it generates should match this
 * style:
 *
 * - Imports come from `./fixtures/auth-fixtures.js`, NOT `@playwright/test`,
 *   so the staging-aware `authenticatedUser` fixture is available.
 * - Constants (URLs, SELECTORS, TIMEOUTS) are imported from `./utils/constants.js`,
 *   never hardcoded.
 * - Helpers (`navigateToApp`, `openAuthModal`, etc.) are imported from `./helpers/`,
 *   not reimplemented inline.
 * - `IS_STAGING` guards wrap any code that touches MailHog or MongoDB directly.
 * - Tests that depend on MailHog or local mocks are tagged `@mock-required`.
 * - Assertions use Playwright's auto-retry `expect(locator).toBeVisible()` form,
 *   not `await locator.isVisible()` checks.
 *
 * This seed is referenced by `.claude/agents/playwright-test-generator.md`. The
 * Generator does not execute it — it reads it for style. We keep it as a real
 * passing test so that breaks in conventions are caught immediately.
 *
 * To run: `npx playwright test seed.spec.js`
 *
 * Tracked in: #686
 */

import { test, expect } from './fixtures/auth-fixtures.js';
import { URLS, SELECTORS, TIMEOUTS, IS_STAGING, generateTestUser } from './utils/constants.js';
import { navigateToApp } from './helpers/navigation-helpers.js';
import { openAuthModal, clearAuthState } from './helpers/auth-helpers.js';
import { MailHogHelper } from './utils/mailhog-client.js';
import { DatabaseHelper } from './utils/database-helper.js';

test.describe('Seed: convention reference', () => {
  let mailhog;
  let dbHelper;

  test.beforeEach(async ({ request, page }) => {
    // CONVENTION: MailHog/DB are local-only. Guard initialization with IS_STAGING.
    // Without this guard, dbHelper.connect() blocks for 5s and rethrows on staging,
    // breaking every test in the file before any assertion runs.
    if (!IS_STAGING) {
      mailhog = new MailHogHelper(request);
      dbHelper = new DatabaseHelper();
      await dbHelper.connect();
      await mailhog.clearEmails();
      await dbHelper.clearTestUsers();
    }

    // CONVENTION: API health check works in both environments.
    const health = await request.get(URLS.BACKEND + URLS.HEALTH);
    expect(health.ok()).toBeTruthy();

    // CONVENTION: Use navigateToApp() helper, not bare page.goto().
    await navigateToApp(page);
  });

  test.afterEach(async ({ page }) => {
    // CONVENTION: Always clear browser auth state between tests so they remain
    // independent (per-test isolation, see playwright.config.js fullyParallel: true).
    await clearAuthState(page);

    if (dbHelper) {
      await dbHelper.disconnect();
    }
  });

  /**
   * Smoke test that runs in BOTH local and staging.
   *
   * Demonstrates: navigation helper, SELECTORS constants, auto-retry assertion.
   */
  test('homepage renders the hero CTA', async ({ page }) => {
    // CONVENTION: prefer Playwright's accessibility-first locators
    // (getByRole / getByText) when the element has stable semantics.
    await expect(
      page.getByRole('heading', { level: 1, name: 'Your next trip, planned in minutes.' })
    ).toBeVisible();

    // Landing now renders multiple inputs sharing the "Chat with Voya AI"
    // aria-label (hero, closing section, chat panel). Target the hero by id.
    await expect(page.locator('#landing-hero-search-input')).toBeVisible();
  });

  /**
   * Auth modal flow that requires MailHog and would create real users on staging.
   *
   * Demonstrates: @mock-required tag, openAuthModal helper, SELECTORS constants,
   * generateTestUser fixture for unique synthetic emails, TIMEOUTS constant
   * instead of magic numbers.
   */
  test(
    'auth modal opens and accepts a new email',
    { tag: '@mock-required' },
    async ({ page }) => {
      const testUser = generateTestUser();

      // CONVENTION: Use the helper. It has fallback strategies for opening
      // the modal (main button, hamburger menu) and waits for the modal to be
      // fully interactive before returning.
      await openAuthModal(page);

      // CONVENTION: Use SELECTORS.* constants, not hardcoded selectors.
      await page.fill(SELECTORS.EMAIL_INPUT, testUser.email);
      await page.click(SELECTORS.CONTINUE_BUTTON);

      // CONVENTION: Use TIMEOUTS.* constants, not magic numbers.
      // For new emails, the form transitions to the registration step.
      await expect(
        page.locator(SELECTORS.REGISTRATION.FIRST_NAME)
      ).toBeVisible({ timeout: TIMEOUTS.MODAL_APPEAR });

      await expect(
        page.locator(SELECTORS.REGISTRATION.LAST_NAME)
      ).toBeVisible();
    }
  );

  /**
   * Authenticated API request using the staging-aware fixture.
   *
   * Demonstrates: authenticatedUser fixture (handles both staging and local
   * paths internally), API request via Playwright's request context, robust
   * assertion that tolerates both 200 and empty-array responses.
   *
   * This test runs on BOTH environments because authenticatedUser branches on
   * IS_STAGING and uses STAGING_TEST_USER_* env vars in CI.
   */
  test('authenticated user can fetch their bookings', async ({ authenticatedUser, request }) => {
    const { accessToken } = authenticatedUser;

    const response = await request.get(URLS.BACKEND + '/api/flights/my-bookings?limit=10', {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
  });
});
