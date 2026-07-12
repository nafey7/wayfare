/**
 * Authentication Helpers
 *
 * Reusable authentication functions for Playwright tests
 * Centralizes login/logout patterns and auth state management
 */

import { expect } from '@playwright/test';
import { URLS, SELECTORS, TIMEOUTS, TEST_DATA } from '../utils/constants.js';
import { navigateToApp, waitBriefly } from './navigation-helpers.js';

// =============================================================================
// LOGIN FLOWS
// =============================================================================

/**
 * Enhanced auth modal opening with multiple fallback strategies
 * @param {Page} page - Playwright page object
 * @param {Object} options - Configuration options
 */
export async function openAuthModal(page, options = {}) {
  const { debug = false, timeout = TIMEOUTS.MODAL_APPEAR } = options;

  try {
    if (debug) console.log('🔑 Opening auth modal...');

    // Ensure page is ready
    await page.waitForLoadState('networkidle');

    // Strategy 1: Try main Sign In button
    let signInClicked = false;
    try {
      await page.click(SELECTORS.SIGN_IN_BUTTON, { timeout: 5000 });
      signInClicked = true;
      if (debug) console.log('   ✅ Clicked main Sign In button');
    } catch (error) {
      if (debug) console.log('   ⚠️ Main Sign In button not found, trying alternatives...');
    }

    // Strategy 2: Try hamburger menu + Sign In (if main button failed)
    if (!signInClicked) {
      try {
        await page.click(SELECTORS.NAVIGATION.HAMBURGER_MENU, { timeout: 3000 });
        await page.waitForTimeout(1000); // Wait for menu animation
        await page.click(SELECTORS.SIGN_IN_BUTTON, { timeout: 3000 });
        signInClicked = true;
        if (debug) console.log('   ✅ Clicked Sign In from hamburger menu');
      } catch (menuError) {
        throw new Error(`Failed to find Sign In button using any strategy`);
      }
    }

    // Wait for auth modal with enhanced detection.
    // VERIFICATION_MODAL ("text=Verification Required") targets the post-signup
    // email-verification notice, not the auth dialog itself. Use AUTH_MODAL so
    // this helper works for sign-in / email-check entry.
    const modalLocator = page.locator(SELECTORS.AUTH_MODAL).first();
    await modalLocator.waitFor({
      state: 'visible',
      timeout: timeout
    });

    if (debug) console.log('   ✅ Auth modal opened and verified');
    return true;

  } catch (error) {
    if (debug) console.log(`   ❌ Failed to open auth modal: ${error.message}`);
    throw error;
  }
}

/**
 * Complete login flow with enhanced error handling and timing
 * Replaces duplicated login patterns across tests
 */
export async function loginUser(page, email, password, options = {}) {
  const { debug = false } = options;

  try {
    // Navigate to app
    await navigateToApp(page);

    // Open auth modal with enhanced detection
    await openAuthModal(page, { debug });

    // Enter email and continue
    if (debug) console.log('🔑 Entering email and continuing...');
    await page.fill(SELECTORS.EMAIL_INPUT, email);
    await page.click(SELECTORS.CONTINUE_BUTTON);

    // Wait for response and next step
    await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

    // Enhanced password field detection
    const passwordField = page.locator(SELECTORS.PASSWORD_INPUT);
    const isPasswordVisible = await passwordField.isVisible();

    if (isPasswordVisible) {
      if (debug) console.log('🔑 Password field found, attempting login...');

      await passwordField.fill(password);

      // Enhanced submit button detection
      const submitButton = page.locator('button:has-text("Sign In"), button[type="submit"]:visible');
      await submitButton.click();

      // Wait for login response with better error handling
      try {
        await page.waitForResponse(
          response => {
            return response.url().includes('/auth/login') &&
                   (response.status() === 200 || response.status() === 401);
          },
          { timeout: TIMEOUTS.API_RESPONSE }
        );

        // Check if we're still on login or redirected
        const currentUrl = page.url();
        if (currentUrl.includes('/voya') || currentUrl.includes('/dashboard')) {
          if (debug) console.log('   ✅ Login successful - redirected to app');
          return { success: true, step: 'login_completed' };
        } else {
          if (debug) console.log('   ⚠️ Login response received but no redirect');
          return { success: false, step: 'login_no_redirect' };
        }

      } catch (error) {
        if (debug) console.log(`   ❌ Login API call failed: ${error.message}`);
        return { success: false, step: 'login_api_failed', error: error.message };
      }

    } else {
      if (debug) console.log('🔑 No password field - user may need activation or registration');
      return { success: true, step: 'email_verified_no_password' };
    }

  } catch (error) {
    if (debug) console.log(`❌ Login flow failed: ${error.message}`);
    return { success: false, step: 'login_flow_failed', error: error.message };
  }
}

/**
 * Quick login for tests that need authenticated state
 */
export async function quickLogin(page, user = TEST_DATA.USERS.EXISTING_USER) {
  const result = await loginUser(page, user.email, user.password);

  if (!result.success) {
    console.warn(`Quick login failed: ${result.error || result.step}`);
  }

  return result;
}

/**
 * Attempt login with invalid credentials (for testing error handling)
 */
export async function loginWithInvalidCredentials(page) {
  return await loginUser(
    page,
    TEST_DATA.USERS.INVALID_CREDENTIALS.email,
    TEST_DATA.USERS.INVALID_CREDENTIALS.password
  );
}

// =============================================================================
// LOGOUT FLOWS
// =============================================================================

/**
 * Logout current user
 */
export async function logoutUser(page) {
  try {
    // Find and click logout button
    await page.click(SELECTORS.LOGOUT_BUTTON, { timeout: TIMEOUTS.ELEMENT_VISIBLE });

    // Wait for redirect to login or home page
    await page.waitForURL(/\/(login|home|\/)/, { timeout: TIMEOUTS.PAGE_LOAD });

    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// =============================================================================
// AUTH STATE MANAGEMENT
// =============================================================================

/**
 * Check if user is currently authenticated
 */
export async function isAuthenticated(page) {
  try {
    // Check for auth indicators like user menu, logout button, etc.
    await page.waitForSelector(SELECTORS.USER_MENU, { timeout: TIMEOUTS.ELEMENT_VISIBLE });
    return true;
  } catch {
    return false;
  }
}

/**
 * Get authentication token from localStorage
 */
export async function getAuthToken(page) {
  return await page.evaluate(() => {
    return localStorage.getItem('token') ||
           localStorage.getItem('authToken') ||
           localStorage.getItem('access_token');
  });
}

/**
 * Set mock authentication token for testing
 */
export async function setMockAuthToken(page, token = TEST_DATA.MOCK_JWT_TOKEN) {
  await page.evaluate((token) => {
    localStorage.setItem('token', token);
    localStorage.setItem('authToken', token);
  }, token);
}

/**
 * Clear all authentication state
 */
export async function clearAuthState(page) {
  await page.evaluate(() => {
    // Clear common auth storage keys
    localStorage.removeItem('token');
    localStorage.removeItem('authToken');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');

    // Clear all localStorage and sessionStorage
    localStorage.clear();
    sessionStorage.clear();
  });
}

// =============================================================================
// AUTH TESTING UTILITIES
// =============================================================================

/**
 * Test authentication by attempting to access protected content
 */
export async function testAuthenticationStatus(page) {
  const authIndicators = {
    hasUserMenu: false,
    hasLogoutButton: false,
    hasAuthToken: false,
    canAccessProtectedContent: false
  };

  try {
    // Check for user menu
    authIndicators.hasUserMenu = await page.locator(SELECTORS.USER_MENU).isVisible();
  } catch {}

  try {
    // Check for logout button
    authIndicators.hasLogoutButton = await page.locator(SELECTORS.LOGOUT_BUTTON).isVisible();
  } catch {}

  // Check for auth token
  const token = await getAuthToken(page);
  authIndicators.hasAuthToken = !!token;

  // Overall auth status
  const isAuth = authIndicators.hasUserMenu || authIndicators.hasLogoutButton || authIndicators.hasAuthToken;

  return {
    isAuthenticated: isAuth,
    indicators: authIndicators,
    token: token
  };
}

/**
 * Ensure user is authenticated for tests that require it
 */
export async function ensureAuthenticated(page, user = TEST_DATA.USERS.EXISTING_USER) {
  const authStatus = await testAuthenticationStatus(page);

  if (!authStatus.isAuthenticated) {
    console.log('🔑 User not authenticated, attempting login...');
    const loginResult = await quickLogin(page, user);

    if (!loginResult.success) {
      console.warn('❌ Authentication failed, continuing with unauthenticated test');
      return false;
    } else {
      console.log('✅ Authentication successful');
      return true;
    }
  } else {
    console.log('✅ User already authenticated');
    return true;
  }
}

/**
 * Ensure user is NOT authenticated (for testing login flows)
 */
export async function ensureNotAuthenticated(page) {
  const authStatus = await testAuthenticationStatus(page);

  if (authStatus.isAuthenticated) {
    await logoutUser(page);
    await clearAuthState(page);
  }
}
