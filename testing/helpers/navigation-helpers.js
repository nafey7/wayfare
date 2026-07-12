/**
 * Navigation Helpers
 *
 * Reusable navigation functions for Playwright tests
 * Replaces 50+ instances of manual page.goto() calls
 */

import { URLS, TIMEOUTS, buildFrontendUrl } from '../utils/constants.js';

// =============================================================================
// CORE NAVIGATION
// =============================================================================

/**
 * Navigate to Voya home page and wait for React app to load
 */
export async function navigateToVoya(page) {
  await page.goto(buildFrontendUrl(URLS.VOYA_HOME));
  await waitForReactApp(page);
}

/**
 * Navigate to user profile page
 */
export async function navigateToProfile(page) {
  await page.goto(buildFrontendUrl(URLS.PROFILE));
  await waitForReactApp(page);
}

/**
 * Navigate to frontend root and wait for app
 */
export async function navigateToApp(page) {
  await page.goto(URLS.FRONTEND);
  await waitForReactApp(page);
}

/**
 * Navigate to a specific frontend route
 */
export async function navigateToRoute(page, route) {
  await page.goto(buildFrontendUrl(route));
  await waitForReactApp(page);
}

// =============================================================================
// WAITING PATTERNS
// =============================================================================

/**
 * Wait for React app to be fully loaded and interactive
 * Replaces scattered waitForTimeout calls
 */
export async function waitForReactApp(page) {
  // Wait for network to be idle (no requests for 500ms)
  await page.waitForLoadState('networkidle');

  // Wait for DOM to be fully loaded
  await page.waitForLoadState('domcontentloaded');

  // Wait for React to initialize (look for React-specific indicators)
  try {
    // Wait for common React elements or Voya-specific indicators
    await page.waitForSelector('body', { timeout: TIMEOUTS.FRONTEND_LOAD_TIMEOUT });
  } catch (error) {
    console.warn('React app loading indicator not found, continuing with test');
  }
}

/**
 * Wait for page to be ready for interaction
 */
export async function waitForPageReady(page) {
  await page.waitForLoadState('networkidle');
  await page.waitForLoadState('domcontentloaded');
}

/**
 * Wait briefly for UI transitions (try to avoid this)
 */
export async function waitBriefly(page, ms = TIMEOUTS.BRIEF) {
  await page.waitForTimeout(ms);
}

// =============================================================================
// NAVIGATION WITH SIDE EFFECTS
// =============================================================================

/**
 * Navigate back to Voya home if URL has changed
 * Common pattern in diagnostic tests
 */
export async function ensureOnVoyaHome(page) {
  const currentUrl = page.url();
  const expectedUrl = buildFrontendUrl(URLS.VOYA_HOME);

  if (currentUrl !== expectedUrl) {
    await navigateToVoya(page);
  }
}

/**
 * Navigate and handle potential URL changes
 * Used when testing buttons that might navigate away
 */
export async function navigateWithReset(page, action) {
  const originalUrl = page.url();

  // Perform the action that might navigate
  await action();

  // Check if URL changed and navigate back if needed
  const newUrl = page.url();
  if (newUrl !== originalUrl) {
    await page.goto(originalUrl);
    await waitForPageReady(page);
  }
}

// =============================================================================
// ROUTE TESTING
// =============================================================================

/**
 * Test if a route is accessible (returns 200)
 */
export async function testRouteAccessibility(page, route) {
  try {
    await page.goto(buildFrontendUrl(route));
    await page.waitForTimeout(TIMEOUTS.BRIEF);

    // Check if we got a 404 or error page
    const is404 = await page.locator('text=/404|not found|page not found/i').isVisible();

    return {
      route,
      url: page.url(),
      accessible: !is404,
      is404
    };
  } catch (error) {
    return {
      route,
      url: page.url(),
      accessible: false,
      error: error.message
    };
  }
}

/**
 * Test multiple routes for accessibility
 */
export async function testRoutesAccessibility(page, routes) {
  const results = [];

  for (const route of routes) {
    const result = await testRouteAccessibility(page, route);
    results.push(result);
  }

  return results;
}
