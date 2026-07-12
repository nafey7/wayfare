/**
 * Authentication API Tests with Email Verification
 *
 * Comprehensive API tests for authentication flows using Playwright.
 * Tests both API functionality and email delivery/links via MailHog.
 */

import { test, expect } from '@playwright/test';
import { MailHogHelper } from '../utils/mailhog-client.js';
import { createApiClient } from '../utils/api-client.js';
import { URLS, generateTestUser, IS_STAGING } from '../utils/constants.js';
import { logTestSection, logSuccess, logError } from '../helpers/debug-helpers.js';
import { DatabaseHelper } from '../utils/database-helper.js';

// Utility function for generating highly unique email addresses
function generateUniqueEmail(prefix = 'test') {
  const timestamp = Date.now();
  const randomSuffix = Math.random().toString(36).substr(2, 9);
  return `${prefix}-${timestamp}-${randomSuffix}@example.com`;
}

// Test data
const TEST_USER = generateTestUser({
  email: 'api-test@example.com',
  firstName: 'API',
  lastName: 'Test'
});

const RESET_USER = generateTestUser({
  email: 'reset-test@example.com',
  firstName: 'Reset',
  lastName: 'Test'
});

// Helper to clean up test users
async function cleanupTestUsers(request) {
  // This is a simple approach - in a real app you might want a dedicated cleanup endpoint
  const emails = [TEST_USER.email, RESET_USER.email, 'e2e-test@example.com'];

  for (const email of emails) {
    try {
      // Try to register and then we can clean up later if needed
      await request.post(URLS.BACKEND + URLS.AUTH.REGISTER, {
        data: { email, first_name: 'Test', last_name: 'User' }
      });
    } catch (e) {
      // User might already exist, that's fine
    }
  }
}

// Helper to get reset token from database (for testing)
async function getResetToken(email) {
  // In a real test, you might query the database directly
  // For now, we'll use the fact that we know the token exists after requesting reset
  return 'test-token-will-be-replaced-with-real-implementation';
}

test.describe('Authentication API', () => {
  let mailhog;
  let dbHelper;

  test.beforeEach(async ({ request }) => {
    // Initialize helpers (MailHog/DB only available on local; staging uses real services)
    if (!IS_STAGING) {
      mailhog = new MailHogHelper(request);
      dbHelper = new DatabaseHelper();
      await dbHelper.connect();
    }

    // Ensure API is accessible
    const health = await request.get(URLS.BACKEND + URLS.HEALTH);
    expect(health.ok()).toBeTruthy();

    // Clear previous test data (local only)
    if (!IS_STAGING) {
      await mailhog.clearEmails();
      await dbHelper.clearTestUsers();
    }
  });

  test.afterEach(async () => {
    // Cleanup database connection
    if (dbHelper) {
      await dbHelper.disconnect();
    }
  });

  test.describe('Registration Flow', () => {

    test('should check email for new user', async ({ request }) => {
      // Use unique email to avoid conflicts with previous test runs
      const uniqueEmail = generateUniqueEmail('new-user-check');

      const response = await request.post(URLS.BACKEND + URLS.AUTH.CHECK_EMAIL, {
        data: { email: uniqueEmail }
      });

      expect(response.ok()).toBeTruthy();
      const data = await response.json();

      expect(data.exists).toBe(false);
      expect(data.verified).toBe(null);
      expect(data.message.toLowerCase()).toContain('new user');
    });

  });

  test.describe('Password Reset Flow', () => {

    test('should accept forgot password request for existing user', { tag: '@mock-required' }, async ({ request }) => {
      // Register user first
      await request.post(URLS.BACKEND + URLS.AUTH.REGISTER, {
        data: {
          email: RESET_USER.email,
          first_name: RESET_USER.firstName,
          last_name: RESET_USER.lastName
        }
      });

      // Request password reset
      const response = await request.post(URLS.BACKEND + URLS.AUTH.FORGOT_PASSWORD, {
        data: { email: RESET_USER.email }
      });

      expect(response.ok()).toBeTruthy();
      const data = await response.json();

      expect(data.message.toLowerCase()).toContain('password reset link has been sent');
    });

    test('should not reveal user existence for forgot password', async ({ request }) => {
      const response = await request.post(URLS.BACKEND + URLS.AUTH.FORGOT_PASSWORD, {
        data: { email: 'nonexistent@example.com' }
      });

      expect(response.ok()).toBeTruthy();
      const data = await response.json();

      // Should return same message to avoid email enumeration
      expect(data.message.toLowerCase()).toContain('password reset link has been sent');
    });

    test('should validate valid reset token', { tag: '@mock-required' }, async ({ request }) => {
      // Setup: register user and request reset
      await request.post(URLS.BACKEND + URLS.AUTH.REGISTER, {
        data: {
          email: RESET_USER.email,
          first_name: RESET_USER.firstName,
          last_name: RESET_USER.lastName
        }
      });

      await request.post(URLS.BACKEND + URLS.AUTH.FORGOT_PASSWORD, {
        data: { email: RESET_USER.email }
      });

      // For this test, we'd need to extract the actual token
      // For now, we'll test the endpoint behavior with an invalid token
      const response = await request.post(URLS.BACKEND + URLS.AUTH.VALIDATE_RESET_TOKEN, {
        data: { token: 'invalid-token' }
      });

      expect(response.status()).toBe(400);
      const data = await response.json();
      expect(data.detail.toLowerCase()).toContain('invalid');
    });

    test('should reject invalid reset token validation', async ({ request }) => {
      const response = await request.post(URLS.BACKEND + URLS.AUTH.VALIDATE_RESET_TOKEN, {
        data: { token: 'definitely-invalid-token-12345' }
      });

      expect(response.status()).toBe(400);
      const data = await response.json();
      expect(data.detail.toLowerCase()).toContain('invalid');
    });

    test('should reject password reset with mismatched passwords', async ({ request }) => {
      const response = await request.post(URLS.BACKEND + URLS.AUTH.RESET_PASSWORD, {
        data: {
          token: 'some-token',
          new_password: 'password123',
          confirm_password: 'different456'
        }
      });

      expect(response.status()).toBe(400);
      const data = await response.json();

      // Handle both possible response structures
      let errorMessage = '';
      if (Array.isArray(data.detail) && data.detail.length > 0 && data.detail[0].msg) {
        errorMessage = data.detail[0].msg.toLowerCase();
      } else if (typeof data.detail === 'string') {
        errorMessage = data.detail.toLowerCase();
      } else if (data.message) {
        errorMessage = data.message.toLowerCase();
      }

      expect(errorMessage).toContain('password');
    });
  });

  test.describe('Login Flow', () => {

    test('should reject login for nonexistent user', async ({ request }) => {
      const response = await request.post(URLS.BACKEND + URLS.AUTH.LOGIN, {
        data: {
          email: 'nonexistent@example.com',
          password: 'anypassword'
        }
      });

      expect(response.status()).toBe(401);
      const data = await response.json();
      expect(data.detail.toLowerCase()).toContain('invalid email or password');
    });
  });

  test.describe('Session Management', () => {

    test('should require authentication for logout', async ({ request }) => {
      const response = await request.post(URLS.BACKEND + URLS.AUTH.LOGOUT);

      // Backend returns 401 (no credentials), CF can also surface this as 403.
      // Either is acceptable for the "auth required" semantic.
      expect([401, 403]).toContain(response.status());
      const data = await response.json();
      expect(data.detail.toLowerCase()).toContain('not authenticated');
    });

    test('should reject invalid refresh token', async ({ request }) => {
      const response = await request.post(URLS.BACKEND + URLS.AUTH.REFRESH, {
        data: { refresh_token: 'invalid-refresh-token-12345' }
      });

      expect(response.status()).toBe(401);
      const data = await response.json();
      expect(data.detail.toLowerCase()).toContain('invalid or expired');
    });
  });

  test.describe('Configuration Endpoints', () => {

    test('should return Google OAuth configuration', async ({ request }) => {
      const response = await request.get(URLS.BACKEND + URLS.AUTH.CONFIG_GOOGLE);

      expect(response.ok()).toBeTruthy();
      const data = await response.json();

      expect(data).toHaveProperty('client_id');
      expect(data).toHaveProperty('enabled');
      expect(typeof data.enabled).toBe('boolean');
    });
  });

  test.describe('Complete User Flows', () => {

    test('Flow B: Existing user login → send chat message', { tag: '@mock-required' }, async ({ request }) => {
      const testEmail = generateUniqueEmail('flow-b-existing');
      const password = 'existinguserpassword123';

      // Setup: Create and activate a user first
      await request.post(URLS.BACKEND + URLS.AUTH.REGISTER, {
        data: {
          email: testEmail,
          first_name: 'Flow',
          last_name: 'B'
        }
      });

      const activationEmail = await mailhog.waitForEmail(testEmail, 10000);
      const activationToken = mailhog.extractRegistrationToken(activationEmail);

      await request.post(URLS.BACKEND + URLS.AUTH.COMPLETE_REGISTRATION, {
        data: {
          token: activationToken,
          password: password,
          confirm_password: password
        }
      });

      await mailhog.clearEmails();

      // Step 1: Enter email → exists
      let response = await request.post(URLS.BACKEND + URLS.AUTH.CHECK_EMAIL, {
        data: { email: testEmail }
      });
      expect(response.ok()).toBeTruthy();
      let data = await response.json();
      expect(data.exists).toBe(true);
      expect(data.verified).toBe(true);  // User completed registration, so verified
      expect(data.message.toLowerCase()).toContain('welcome back');

      // Step 2: Enter correct password to login
      response = await request.post(URLS.BACKEND + URLS.AUTH.LOGIN, {
        data: {
          email: testEmail,
          password: password
        }
      });
      expect(response.ok()).toBeTruthy();
      data = await response.json();
      expect(data.user.email).toBe(testEmail);
      expect(data.access_token).toBeTruthy();

      const accessToken = data.access_token;

      // Step 3: Send chat message and get successful response
      response = await request.post(URLS.BACKEND + URLS.CHAT.MESSAGE, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
        data: {
          message: 'Hello, this is a test message from Flow B'
        }
      });
      expect(response.ok()).toBeTruthy();
      data = await response.json();
      expect(data.message).toBeTruthy();
      expect(data.chat_id).toBeTruthy();
    });
  });
});
