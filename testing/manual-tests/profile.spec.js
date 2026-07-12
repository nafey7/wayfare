/**
 * Profile Page Diagnostic Tests
 *
 * Purpose: Identify and document profile-related issues including:
 * - "undefined undefined" name display issue
 * - Non-functional buttons and settings
 * - Data mapping problems between backend and frontend
 */

import { test, expect } from '@playwright/test';
import { URLS, SELECTORS, TIMEOUTS, generateTestUser, buildApiUrl, buildFrontendUrl } from '../utils/constants.js';
import { createApiClient } from '../utils/api-client.js';
import { navigateToVoya, navigateToProfile } from '../helpers/navigation-helpers.js';
import { logTestStep, logSuccess, logError } from '../helpers/debug-helpers.js';

test.describe('Profile Page Diagnostics', () => {
  let authToken;

  test.beforeAll(async ({ request }) => {
    // Login to get auth token for API calls
    const loginResponse = await request.post(buildApiUrl(URLS.AUTH.LOGIN), {
      data: {
        email: "roel@myvoya.ai",
        password: "VoyaTest123!"
      }
    });

    if (loginResponse.ok()) {
      const loginData = await loginResponse.json();
      authToken = loginData.access_token;
    } else {
      logTestStep('Login failed, will test with unauthenticated user');
    }
  });

  test('Profile name display - Check for "undefined undefined" issue', async ({ page }) => {
    await navigateToVoya(page);

    // Navigate to profile page
    await page.click(SELECTORS.NAVIGATION.PROFILE, { timeout: TIMEOUTS.PAGE_LOAD });
    await page.waitForURL('**/profile', { timeout: TIMEOUTS.PAGE_LOAD });

    // Take screenshot of full profile page
    await page.screenshot({
      path: 'test-results/profile-overview.png',
      fullPage: true
    });

    // Look for the name display area
    const profileBanner = page.locator('[data-testid="profile-banner"], .profile-banner, .MuiTypography-h4, .MuiTypography-h5');

    // Take screenshot of name area specifically
    if (await profileBanner.count() > 0) {
      await profileBanner.first().screenshot({
        path: 'test-results/profile-name-area.png'
      });
    }

    // Extract text content to look for "undefined undefined"
    const pageContent = await page.textContent('body');

    const undefinedMatches = pageContent.match(/undefined\s+undefined/gi);

    logTestStep('PROFILE NAME DISPLAY ANALYSIS', 'section');
    console.log('Found "undefined undefined" instances:', undefinedMatches?.length || 0);

    if (undefinedMatches) {
      console.log('Undefined text found at locations:', undefinedMatches);
    }

    // Try to find name-related elements
    const nameElements = await page.locator('h1, h2, h3, h4, h5, h6').allTextContents();
    console.log('All heading elements:', nameElements);

    // Check what's actually displayed vs what should be displayed
    const possibleNameSelectors = [
      '.profile-name',
      '[data-testid="user-name"]',
      'h4',
      'h5',
      '.MuiTypography-h4',
      '.MuiTypography-h5'
    ];

    for (const selector of possibleNameSelectors) {
      const element = page.locator(selector).first();
      if (await element.count() > 0) {
        const text = await element.textContent();
        console.log(`${selector}: "${text}"`);
      }
    }
  });

  test('Profile API data vs Frontend display', async ({ request }) => {
    if (!authToken) {
      test.skip(true, 'No auth token available for API testing');
      return;
    }

    // Get user data from API
    const apiResponse = await request.get(buildApiUrl('/user/me'), {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    if (apiResponse.ok()) {
      const userData = await apiResponse.json();

      logTestStep('BACKEND USER DATA', 'section');
      console.log('Raw API Response:', JSON.stringify(userData, null, 2));

      // Check data structure
      logTestStep('DATA MAPPING ANALYSIS', 'section');
      console.log('Backend first_name:', userData.first_name);
      console.log('Backend last_name:', userData.last_name);
      console.log('Backend firstName:', userData.firstName);
      console.log('Backend lastName:', userData.lastName);

      // Document the mismatch
      const hasCamelCase = userData.firstName !== undefined || userData.lastName !== undefined;
      const hasSnakeCase = userData.first_name !== undefined || userData.last_name !== undefined;

      logTestStep('NAMING CONVENTION MISMATCH', 'section');
      console.log('Has camelCase (firstName/lastName):', hasCamelCase);
      console.log('Has snake_case (first_name/last_name):', hasSnakeCase);

      if (hasSnakeCase && !hasCamelCase) {
        console.log('❌ ISSUE: Backend uses snake_case, frontend expects camelCase');
        console.log('💡 FIX: Transform backend response or update frontend properties');
      }
    }
  });

  test('Travel Preferences - Button functionality test', async ({ page }) => {
    await page.goto(buildFrontendUrl(URLS.PROFILE));

    // Take screenshot of travel preferences section
    const travelPrefs = page.locator('text=Travel Preferences').locator('..');
    if (await travelPrefs.count() > 0) {
      await travelPrefs.screenshot({
        path: 'test-results/travel-preferences.png'
      });
    }

    // Test clickability of preference buttons
    const preferenceButtons = [
      'Adventure',
      'Relaxation',
      'Culture',
      'Nature',
      'City',
      'Beach'
    ];

    logTestStep('TRAVEL PREFERENCES BUTTON TEST', 'section');

    for (const buttonText of preferenceButtons) {
      const button = page.locator(`text=${buttonText}`).first();

      if (await button.count() > 0) {
        const isClickable = await button.isEnabled();
        const hasClickHandler = await button.getAttribute('onclick') !== null;

        console.log(`${buttonText}: Enabled=${isClickable}, HasOnClick=${hasClickHandler}`);

        // Try clicking and see what happens
        try {
          await button.click({ timeout: 2000 });
          console.log(`${buttonText}: Click succeeded`);
        } catch (error) {
          console.log(`${buttonText}: Click failed - ${error.message}`);
        }
      } else {
        console.log(`${buttonText}: Button not found`);
      }
    }
  });

  test('Flight Preferences Settings - Update functionality', async ({ page }) => {
    await page.goto(buildFrontendUrl(URLS.PROFILE));

    // Look for flight preferences section
    const flightPrefs = page.locator('text=Flight Preferences', 'text=Maximum Stops', 'text=Take Off Time');

    if (await flightPrefs.count() > 0) {
      await page.screenshot({
        path: 'test-results/flight-preferences.png'
      });
    }

    logTestStep('FLIGHT PREFERENCES TEST', 'section');

    // Test max stops setting
    const maxStopsSelect = page.locator('select', { has: page.locator('option:has-text("Non-stop")') });
    if (await maxStopsSelect.count() > 0) {
      console.log('Max stops selector found');
      await maxStopsSelect.selectOption('1');
    }

    // Test time range sliders if present
    const timeSliders = page.locator('input[type="range"]');
    const sliderCount = await timeSliders.count();
    console.log('Time range sliders found:', sliderCount);

    // Look for Update button
    const updateButton = page.locator('button:has-text("Update"), button:has-text("Save")');
    if (await updateButton.count() > 0) {
      console.log('Update button found');

      // Click update and check response
      await updateButton.click();

      // Wait for any feedback/response
      await page.waitForTimeout(2000);

      // Check for success/error messages
      const feedback = await page.locator('.success, .error, .MuiAlert-message').allTextContents();
      console.log('Update feedback:', feedback);
    } else {
      console.log('❌ No Update/Save button found');
    }
  });

  test('Timezone Setting - Update functionality', async ({ page }) => {
    await page.goto(buildFrontendUrl(URLS.PROFILE));

    logTestStep('TIMEZONE SETTING TEST', 'section');

    // Look for timezone section
    const timezoneSection = page.locator('text=Timezone', 'text=Time Zone');

    if (await timezoneSection.count() > 0) {
      await timezoneSection.locator('..').screenshot({
        path: 'test-results/timezone-setting.png'
      });
    }

    // Find timezone dropdown/select
    const timezoneSelect = page.locator('select').filter({ hasText: /GMT|UTC|timezone/i });
    const timezoneInput = page.locator('input').filter({ hasText: /timezone/i });

    const timezoneControl = await timezoneSelect.count() > 0 ? timezoneSelect : timezoneInput;

    if (await timezoneControl.count() > 0) {
      console.log('Timezone control found');

      // Get current value
      const currentValue = await timezoneControl.inputValue();
      console.log('Current timezone value:', currentValue);

      // Try to select a different timezone
      if (await timezoneSelect.count() > 0) {
        await timezoneSelect.selectOption('America/New_York');
        console.log('Selected America/New_York timezone');
      }

      // Look for save/update mechanism
      const saveButton = page.locator('button:has-text("Save"), button:has-text("Update")');
      if (await saveButton.count() > 0) {
        await saveButton.click();
        console.log('Clicked save button');

        await page.waitForTimeout(2000);

        // Check if value persisted
        const newValue = await timezoneControl.inputValue();
        console.log('New timezone value:', newValue);

        if (newValue === currentValue) {
          console.log('❌ Timezone value did not change - update may have failed');
        } else {
          console.log('✅ Timezone value updated successfully');
        }
      } else {
        console.log('❌ No save button found for timezone');
      }
    } else {
      console.log('❌ Timezone control not found');
    }
  });

  test('Account & Billing Section - Premium Plan Display', async ({ page }) => {
    await page.goto(buildFrontendUrl(URLS.PROFILE));

    logTestStep('ACCOUNT & BILLING TEST', 'section');

    // Look for three dots menu or account section
    const menuButton = page.locator(SELECTORS.NAVIGATION.MORE_VERT_BUTTON);

    if (await menuButton.count() > 0) {
      console.log('Menu button found');
      await menuButton.click();

      await page.waitForTimeout(1000);

      // Take screenshot of menu
      await page.screenshot({ path: 'test-results/profile-menu.png' });

      // Look for Account & Billing option
      const billingOption = page.locator('text=Account & Billing');
      if (await billingOption.count() > 0) {
        await billingOption.click();

        await page.waitForTimeout(2000);

        // Take screenshot of billing section
        await page.screenshot({ path: 'test-results/billing-section.png' });

        // Extract billing information
        const pageContent = await page.textContent('body');

        const hasPremiumPlan = pageContent.includes('Premium Explorer');
        const hasPaymentMethod = pageContent.includes('Payment Method');

        console.log('Has Premium Explorer plan:', hasPremiumPlan);
        console.log('Has Payment Method section:', hasPaymentMethod);

        if (hasPremiumPlan) {
          console.log('✅ Premium plan information displayed');
          console.log('🔍 Check if this is dummy data or real subscription');
        }
      }
    } else {
      console.log('❌ Menu button not found');
    }
  });
});
