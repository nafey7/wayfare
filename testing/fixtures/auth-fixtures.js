/**
 * Authentication Fixtures for Playwright Tests
 *
 * Reusable fixtures for common auth scenarios.
 * Reduces boilerplate in tests and ensures consistency.
 *
 * Usage:
 * ```js
 * import { test } from '../fixtures/auth-fixtures.js';
 *
 * test('should do something with authenticated user', async ({ authenticatedUser, request }) => {
 *   // User is already created and activated
 *   const { email, password, accessToken, user } = authenticatedUser;
 *   // Make requests with the accessToken
 * });
 * ```
 */

import { test as base } from '@playwright/test';
import { MailHogHelper } from '../utils/mailhog-client.js';
import { URLS, IS_STAGING } from '../utils/constants.js';

/**
 * Generate unique test email
 */
function generateUniqueEmail(prefix = 'fixture') {
  const timestamp = Date.now();
  const randomSuffix = Math.random().toString(36).substr(2, 9);
  return `${prefix}-${timestamp}-${randomSuffix}@example.com`;
}

/**
 * Extended test with authentication fixtures
 */
export const test = base.extend({
  /**
   * Registered but unverified user fixture
   *
   * Provides a user that has been registered but hasn't completed activation.
   * Useful for testing registration flows and unverified user scenarios.
   */
  registeredUser: async ({ request }, use) => {
    if (IS_STAGING) {
      throw new Error(
        'registeredUser fixture requires MailHog (not available on staging). ' +
        'Tag this test @mock-required to skip it on staging.'
      );
    }

    const email = generateUniqueEmail('registered');
    const firstName = 'Registered';
    const lastName = 'User';

    // Register user
    const response = await request.post(URLS.BACKEND + URLS.AUTH.REGISTER, {
      data: {
        email,
        first_name: firstName,
        last_name: lastName
      }
    });

    if (!response.ok()) {
      throw new Error(`Failed to register user: ${response.status()}`);
    }

    // Get registration token from MailHog
    const mailhog = new MailHogHelper(request);
    const registrationEmail = await mailhog.waitForEmail(email, 10000);
    const registrationToken = mailhog.extractRegistrationToken(registrationEmail);

    const userData = {
      email,
      firstName,
      lastName,
      registrationToken,
      isVerified: false
    };

    await use(userData);

    // Cleanup is handled by global teardown
  },

  /**
   * Fully authenticated user fixture
   *
   * Provides a user that has:
   * 1. Been registered
   * 2. Completed email verification
   * 3. Set a password
   * 4. Been logged in
   *
   * Returns access token and user details for making authenticated requests.
   */
  authenticatedUser: async ({ request }, use) => {
    // Staging path: log in with the dedicated test account from env vars.
    // No registration, no MailHog (staging uses real email).
    if (IS_STAGING) {
      const email = process.env.STAGING_TEST_USER_EMAIL;
      const password = process.env.STAGING_TEST_USER_PASSWORD;

      if (!email || !password) {
        throw new Error(
          'Staging tests require STAGING_TEST_USER_EMAIL and STAGING_TEST_USER_PASSWORD env vars'
        );
      }

      const loginResponse = await request.post(URLS.BACKEND + URLS.AUTH.LOGIN, {
        data: { email, password },
      });

      if (!loginResponse.ok()) {
        throw new Error(`Failed to login staging test user: ${loginResponse.status()}`);
      }

      const loginData = await loginResponse.json();

      await use({
        email,
        password,
        accessToken: loginData.access_token,
        refreshToken: loginData.refresh_token,
        user: loginData.user,
        isVerified: true,
      });
      return;
    }

    // Local/dev path: register a fresh user via API + MailHog.
    const email = generateUniqueEmail('authenticated');
    const firstName = 'Authenticated';
    const lastName = 'User';
    const password = 'TestPassword123!';

    // Step 1: Register user
    const registerResponse = await request.post(URLS.BACKEND + URLS.AUTH.REGISTER, {
      data: {
        email,
        first_name: firstName,
        last_name: lastName
      }
    });

    if (!registerResponse.ok()) {
      throw new Error(`Failed to register user: ${registerResponse.status()}`);
    }

    // Step 2: Get activation token from email
    const mailhog = new MailHogHelper(request);
    const activationEmail = await mailhog.waitForEmail(email, 10000);
    const activationToken = mailhog.extractRegistrationToken(activationEmail);

    // Step 3: Complete registration (set password)
    const completeResponse = await request.post(URLS.BACKEND + URLS.AUTH.COMPLETE_REGISTRATION, {
      data: {
        token: activationToken,
        password,
        confirm_password: password
      }
    });

    if (!completeResponse.ok()) {
      throw new Error(`Failed to complete registration: ${completeResponse.status()}`);
    }

    const completeData = await completeResponse.json();

    const userData = {
      email,
      firstName,
      lastName,
      password,
      accessToken: completeData.access_token,
      refreshToken: completeData.refresh_token,
      user: completeData.user,
      isVerified: true
    };

    await use(userData);

    // Cleanup is handled by global teardown
  },

  /**
   * User with reset password token fixture
   *
   * Provides a user that has:
   * 1. Been registered and activated
   * 2. Requested a password reset
   *
   * Returns reset token for testing password reset flows.
   */
  userWithResetToken: async ({ request }, use) => {
    if (IS_STAGING) {
      throw new Error(
        'userWithResetToken fixture requires MailHog (not available on staging). ' +
        'Tag this test @mock-required to skip it on staging.'
      );
    }

    const email = generateUniqueEmail('reset');
    const firstName = 'Reset';
    const lastName = 'User';
    const originalPassword = 'OriginalPassword123!';

    // Step 1: Register and activate user
    await request.post(URLS.BACKEND + URLS.AUTH.REGISTER, {
      data: {
        email,
        first_name: firstName,
        last_name: lastName
      }
    });

    const mailhog = new MailHogHelper(request);
    const activationEmail = await mailhog.waitForEmail(email, 10000);
    const activationToken = mailhog.extractRegistrationToken(activationEmail);

    await request.post(URLS.BACKEND + URLS.AUTH.COMPLETE_REGISTRATION, {
      data: {
        token: activationToken,
        password: originalPassword,
        confirm_password: originalPassword
      }
    });

    // Clear activation email
    await mailhog.clearEmails();

    // Step 2: Request password reset
    const resetRequest = await request.post(URLS.BACKEND + URLS.AUTH.FORGOT_PASSWORD, {
      data: { email }
    });

    if (!resetRequest.ok()) {
      throw new Error(`Failed to request password reset: ${resetRequest.status()}`);
    }

    // Step 3: Get reset token from email
    const resetEmail = await mailhog.waitForEmail(email, 10000);
    const resetToken = mailhog.extractPasswordResetToken(resetEmail);

    const userData = {
      email,
      firstName,
      lastName,
      originalPassword,
      resetToken,
      isVerified: true
    };

    await use(userData);

    // Cleanup is handled by global teardown
  }
});

// Re-export expect for convenience
export { expect } from '@playwright/test';
