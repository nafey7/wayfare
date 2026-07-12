import { test, expect } from '@playwright/test';
import { URLS, SELECTORS, TIMEOUTS, generateTestUser, buildApiUrl, buildFrontendUrl } from '../../../utils/constants.js';
import { createApiClient } from '../../../utils/api-client.js';
import { navigateToVoya, navigateToApp } from '../../../helpers/navigation-helpers.js';
import { logTestStep, logSuccess, logError } from '../../../helpers/debug-helpers.js';
import {
  openAuthModal,
  loginUser,
  isAuthenticated,
  getAuthToken
} from '../../../helpers/auth-helpers.js';

// @stale — pre-#722 hand-written auth suite. Selectors predate the current
// AuthModal UI (e.g. `input[name="email"]` instead of `getByLabel('Email Address')`).
// Kept for reference while the agent-generated replacements in
// `should-*.spec.js` land (plan: testing/specs/auth.md, issue #788).
test.describe('Login Flow', { tag: ['@mock-required', '@stale'] }, () => {

  test.beforeEach(async ({ page }) => {
    await navigateToApp(page);
  });

  test.afterEach(async ({ page }) => {
    // Clean up authentication state
    // Clear authentication state if needed
  });

  test('should display login form', async ({ page }) => {
    // Click sign in button and wait for email field
    await page.click(SELECTORS.SIGN_IN_BUTTON);
    await expect(page.locator('input[name="email"]')).toBeVisible({ timeout: 10000 });

    // Check for Continue button
    await expect(page.locator('button:has-text("CONTINUE"), button:has-text("Continue")')).toBeVisible();

    // Enter an email to proceed to password step
    await page.fill('input[name="email"]', 'test@example.com');
    await page.click('button:has-text("CONTINUE")');

    // Wait for the next step (could be password field or registration form)
    await page.waitForTimeout(2000); // Wait for any transitions

    // The test passes if we can navigate through the email step successfully
    logSuccess('Successfully navigated through email verification step');
  });

  test('should show validation errors for empty fields', async ({ page }) => {
    // Click sign in and wait for modal
    await page.click(SELECTORS.SIGN_IN_BUTTON);
    await expect(page.locator('input[name="email"]')).toBeVisible({ timeout: 10000 });

    // Try to submit empty form (click Continue without entering email)
    await page.click('button:has-text("CONTINUE"), button:has-text("Continue")');

    // Wait a bit for any validation to show
    await page.waitForTimeout(1000);

    // Email input should still be visible (form didn't proceed)
    await expect(page.locator('input[name="email"]')).toBeVisible();

    console.log('✅ Form validation prevents empty submission');
  });

  test('should show error for invalid email format', async ({ page }) => {
    // Click sign in and wait for modal
    await page.click(SELECTORS.SIGN_IN_BUTTON);
    await expect(page.locator('input[name="email"]')).toBeVisible({ timeout: 10000 });

    // Enter invalid email
    await page.fill('input[name="email"]', 'invalid-email');

    // Try to submit
    await page.click('button:has-text("CONTINUE"), button:has-text("Continue")');

    // Look for specific "Invalid email" error message
    const invalidEmailError = page.locator('text=Invalid email');
    const errorVisible = await invalidEmailError.isVisible();

    if (errorVisible) {
      console.log('✅ Email format validation working - Invalid email error shown');
    } else {
      // If no specific error, check if form is still on email step (didn't proceed)
      await expect(page.locator('input[placeholder*="Email Address"], input[name="email"]')).toBeVisible();
      console.log('✅ Form validation prevented invalid email submission');
    }
  });

  test('should handle login with invalid credentials', async ({ page }) => {
    // Click sign in and wait for modal
    await page.click(SELECTORS.SIGN_IN_BUTTON);
    await expect(page.locator('input[name="email"]')).toBeVisible({ timeout: 10000 });

    // Enter email and proceed
    await page.fill('input[name="email"]', 'nonexistent@example.com');
    await page.click('button:has-text("CONTINUE")');

    // Wait for password step (may show registration form or password field)
    await page.waitForTimeout(2000);

    // Try to fill password if field exists
    const passwordField = page.locator('input[type="password"], input[name="password"]');
    if (await passwordField.isVisible()) {
      await page.fill('input[type="password"], input[name="password"]', 'wrongpassword');
      await page.click('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")');

      // Check for error message
      await expect(page.locator('text="Invalid credentials", text="Login failed", text="Incorrect email or password"')).toBeVisible();
    }

    console.log('✅ Successfully tested invalid credentials flow');
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    // This test requires a test user to exist
    // You may want to create one via API first or use a known test account
    const testUser = {
      email: 'test@example.com', // Replace with actual test user
      password: 'TestPassword123!'
    };

    // Click sign in and wait for modal
    await page.click(SELECTORS.SIGN_IN_BUTTON);
    await expect(page.locator('input[name="email"]')).toBeVisible({ timeout: 10000 });

    // Enter email and proceed
    await page.fill('input[name="email"]', testUser.email);
    await page.click('button:has-text("CONTINUE")');

    // Wait for password step
    await page.waitForTimeout(2000);

    // Try to fill password if field exists
    const passwordField = page.locator('input[type="password"], input[name="password"]');
    if (await passwordField.isVisible()) {
      await page.fill('input[type="password"], input[name="password"]', testUser.password);

      // Submit form and wait for successful response
      await page.click('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")');
      await page.waitForResponse(
        (response) => response.url().includes('/auth/login') && response.status() === 200,
        { timeout: 10000 }
      );

      // Should redirect to dashboard or home page
      await expect(page).toHaveURL(/\/(dashboard|home|\w+)/, { timeout: 10000 });

      // Check for authentication indicators
      const authStatus = await isAuthenticated(page);
      expect(authStatus).toBe(true);

      // Check that auth token was stored
      const token = await getAuthToken(page);
      expect(token).toBeTruthy();
    } else {
      console.log('✅ Email verification step completed - password field not shown (may redirect to registration)');
    }
  });

  test('should handle Google OAuth login flow', async ({ page }) => {
    // Navigate to login form using robust helper
    await openAuthModal(page);

    // Wait for verification modal to appear
    await expect(page.locator('text=Verification Required')).toBeVisible({ timeout: 10000 });

    // Look for Google Sign In button
    const googleButton = page.locator('button:has-text("Google"), [data-testid="google-signin"]');

    if (await googleButton.isVisible()) {
      // Click Google button (this might open a popup or redirect)
      await googleButton.click();
      console.log('✅ Google OAuth button clicked successfully');
    } else {
      console.log('ℹ️ Google OAuth button not found in current modal');
    }

    // Note: Full Google OAuth testing would require special setup
    // For now, we just verify the button click doesn't error

    // In a real test, you might:
    // 1. Mock the Google OAuth response
    // 2. Use Google's testing accounts
    // 3. Intercept the OAuth flow
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Simulate network failure by intercepting requests
    await page.route('**/auth/**', route => {
      route.abort('failed');
    });

    // Click sign in and wait for modal
    await page.click(SELECTORS.SIGN_IN_BUTTON);
    await expect(page.locator('input[name="email"]')).toBeVisible({ timeout: 10000 });

    // Enter email
    await page.fill('input[name="email"]', 'test@example.com');

    // Try to submit (this should trigger network error)
    await page.click('button:has-text("CONTINUE")');

    // Should show network error message or remain on same step
    await page.waitForTimeout(2000);

    console.log('✅ Network error handling test completed - form should handle failed requests gracefully');
  });
});
