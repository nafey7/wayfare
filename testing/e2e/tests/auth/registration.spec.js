import { test, expect } from '@playwright/test';
import { URLS, SELECTORS, TIMEOUTS, generateTestUser, buildApiUrl, buildFrontendUrl } from '../../../utils/constants.js';
import { createApiClient } from '../../../utils/api-client.js';
import { navigateToVoya, navigateToApp } from '../../../helpers/navigation-helpers.js';
import { logTestStep, logSuccess, logError } from '../../../helpers/debug-helpers.js';
import { openAuthModal, clearAuthState } from '../../../helpers/auth-helpers.js';

// @stale — pre-#722 hand-written auth suite. Selectors predate the current
// AuthModal UI. Kept for reference while the agent-generated replacements in
// `should-*.spec.js` land (plan: testing/specs/auth.md, issue #788).
test.describe('Registration Flow', { tag: ['@mock-required', '@stale'] }, () => {
  let testUser;

  test.beforeEach(async ({ page }) => {
    testUser = generateTestUser();

    await navigateToApp(page);
  });

  test.afterEach(async ({ page }) => {
    // Clean up test data and authentication state
    await clearAuthState(page);
  });

  test('should display registration form', async ({ page }) => {
    // Open auth modal with enhanced detection
    await openAuthModal(page, { debug: true });

    // Enter a new email to trigger registration flow
    await page.fill(SELECTORS.EMAIL_INPUT, testUser.email);
    await page.click(SELECTORS.CONTINUE_BUTTON);

    // Wait for registration form to appear
    await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

    // Check that registration form fields are visible
    await expect(page.locator(SELECTORS.REGISTRATION.FIRST_NAME)).toBeVisible();
    await expect(page.locator(SELECTORS.REGISTRATION.LAST_NAME)).toBeVisible();
    await expect(page.locator(SELECTORS.REGISTRATION.EMAIL)).toBeVisible();

    // Check for submit button (may be "Continue" or "Register")
    await expect(page.locator(SELECTORS.REGISTRATION.SUBMIT)).toBeVisible();
  });

  test('should transition from email to registration or login based on email status', async ({ page }) => {
    // Start with auth modal
    await openAuthModal(page, { debug: true });

    // Enter new email - should go to registration
    await page.fill(SELECTORS.EMAIL_INPUT, testUser.email);
    await page.click(SELECTORS.CONTINUE_BUTTON);
    await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

    // Should see registration form
    await expect(page.locator(SELECTORS.REGISTRATION.FIRST_NAME)).toBeVisible();
    await expect(page.locator(SELECTORS.REGISTRATION.LAST_NAME)).toBeVisible();

    // Note: There's no direct navigation between forms - it's based on email check API response
  });

  test('should preserve form data on validation errors', async ({ page }) => {
    // Navigate to registration form through auth flow
    await openAuthModal(page, { debug: true });
    await page.fill(SELECTORS.EMAIL_INPUT, testUser.email);
    await page.click(SELECTORS.CONTINUE_BUTTON);
    await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

    // Fill form partially to trigger validation
    await page.fill(SELECTORS.REGISTRATION.FIRST_NAME, testUser.firstName);
    // Leave last name empty to trigger validation

    // Submit form (will fail validation)
    await page.click('button:has-text("Complete Registration")');

    // Check that form data is preserved
    await expect(page.locator(SELECTORS.REGISTRATION.FIRST_NAME)).toHaveValue(testUser.firstName);
    await expect(page.locator(SELECTORS.REGISTRATION.EMAIL)).toHaveValue(testUser.email); // Email should be disabled/preserved
  });
});
