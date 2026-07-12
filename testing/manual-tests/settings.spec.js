/**
 * Settings and Preferences Diagnostic Tests
 *
 * Purpose: Test all settings functionality and identify issues including:
 * - Flight preferences settings and persistence
 * - Timezone settings (reported "Not set" issue)
 * - User profile settings updates
 * - Notification preferences
 * - Travel preferences (clickable buttons)
 * - Settings persistence and API integration
 */

import { test, expect } from '@playwright/test';
import { URLS, SELECTORS, TIMEOUTS, generateTestUser, buildApiUrl, buildFrontendUrl } from '../utils/constants.js';
import { createApiClient } from '../utils/api-client.js';
import { navigateToVoya, navigateToApp } from '../helpers/navigation-helpers.js';
import { logTestStep, logSuccess, logError } from '../helpers/debug-helpers.js';

test.describe('Settings and Preferences Diagnostics', () => {
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
      console.log('✅ Authentication successful for settings tests');
    } else {
      console.log('❌ Login failed, settings tests may not work properly');
    }
  });

  test('Flight Preferences Settings - Maximum Stops and Time Ranges', async ({ page }) => {
    await page.goto(`${URLS.FRONTEND}/voya/profile`);

    console.log('=== FLIGHT PREFERENCES SETTINGS TESTS ===');

    // Take screenshot of profile page
    await page.screenshot({ path: 'test-results/profile-settings-page.png', fullPage: true });

    // Look for flight preferences section
    const flightPrefsSection = page.locator('text=Flight Preferences', 'text=Maximum Stops', 'text=Take Off Time').first().locator('..');

    if (await flightPrefsSection.count() > 0) {
      console.log('Flight Preferences section found');

      // Take screenshot of flight preferences
      await flightPrefsSection.screenshot({ path: 'test-results/flight-preferences-section.png' });

      // Test Maximum Stops setting
      console.log('Testing Maximum Stops setting...');
      const maxStopsSelect = page.locator('select').filter({ has: page.locator('option:has-text("Non-stop")') });

      if (await maxStopsSelect.count() > 0) {
        console.log('✅ Maximum Stops selector found');

        try {
          const currentValue = await maxStopsSelect.inputValue();
          console.log(`Current Max Stops value: ${currentValue}`);

          // Try different values
          const testValues = ['0', '1', '2', 'unlimited'];

          for (const value of testValues) {
            try {
              await maxStopsSelect.selectOption(value);
              await page.waitForTimeout(500);

              const newValue = await maxStopsSelect.inputValue();
              console.log(`Max Stops set to "${value}" - actual value: "${newValue}"`);

              if (newValue === value) {
                console.log(`✅ Max Stops value "${value}" accepted`);
              } else {
                console.log(`⚠️ Max Stops value "${value}" not applied correctly`);
              }
            } catch (error) {
              console.log(`❌ Max Stops value "${value}" failed: ${error.message}`);
            }
          }

        } catch (error) {
          console.log(`❌ Max Stops testing failed: ${error.message}`);
        }
      } else {
        console.log('❌ Maximum Stops selector not found');
      }

      // Test Time Range Sliders
      console.log('Testing time range sliders...');
      const timeSliders = page.locator('input[type="range"]');
      const sliderCount = await timeSliders.count();

      console.log(`Found ${sliderCount} time range sliders`);

      if (sliderCount > 0) {
        for (let i = 0; i < sliderCount; i++) {
          const slider = timeSliders.nth(i);

          try {
            const minValue = await slider.getAttribute('min') || '0';
            const maxValue = await slider.getAttribute('max') || '100';
            const currentValue = await slider.inputValue();

            console.log(`Slider ${i + 1} - Min: ${minValue}, Max: ${maxValue}, Current: ${currentValue}`);

            // Test moving slider
            const testValue = Math.floor((parseInt(minValue) + parseInt(maxValue)) / 2).toString();
            await slider.fill(testValue);
            await page.waitForTimeout(500);

            const newValue = await slider.inputValue();
            console.log(`Slider ${i + 1} set to ${testValue}, actual value: ${newValue}`);

            if (newValue === testValue) {
              console.log(`✅ Slider ${i + 1} responsive`);
            } else {
              console.log(`❌ Slider ${i + 1} not responsive`);
            }

          } catch (error) {
            console.log(`❌ Slider ${i + 1} test failed: ${error.message}`);
          }
        }
      } else {
        console.log('❌ No time range sliders found');
      }

      // Test Update button
      console.log('Testing flight preferences Update button...');
      const updateButton = page.locator('button:has-text("Update"), button:has-text("Save")').filter({
        has: page.locator('text=Flight Preferences').locator('..')
      }).or(
        page.locator('button:has-text("Update"), button:has-text("Save")').last()
      );

      if (await updateButton.count() > 0) {
        console.log('✅ Update button found');

        try {
          await updateButton.click();
          await page.waitForTimeout(3000);

          // Check for feedback messages
          const successMessage = await page.locator('.success, .MuiAlert-standardSuccess, .success-message').count() > 0;
          const errorMessage = await page.locator('.error, .MuiAlert-error, .error-message').count() > 0;
          const loadingIndicator = await page.locator('.loading, .spinner, [data-testid="loading"]').count() > 0;

          console.log(`Update result - Success: ${successMessage}, Error: ${errorMessage}, Loading: ${loadingIndicator}`);

          if (successMessage) {
            console.log('✅ Flight preferences update successful');
          } else if (errorMessage) {
            const errorText = await page.locator('.error, .MuiAlert-error, .error-message').textContent();
            console.log(`❌ Flight preferences update error: ${errorText}`);
          } else {
            console.log('❌ Flight preferences update had no visible feedback');
          }

          // Take screenshot after update
          await page.screenshot({ path: 'test-results/flight-prefs-after-update.png', fullPage: true });

        } catch (error) {
          console.log(`❌ Update button click failed: ${error.message}`);
        }
      } else {
        console.log('❌ Update button not found for flight preferences');
      }

    } else {
      console.log('❌ Flight Preferences section not found');
    }
  });

  test('Timezone Settings - "Not set" Issue Investigation', async ({ page }) => {
    await page.goto(`${URLS.FRONTEND}/voya/profile`);

    console.log('=== TIMEZONE SETTINGS TESTS ===');

    // Look for timezone section
    const timezoneSection = page.locator('text=Timezone', 'text=Time Zone', 'text=timezone').first().locator('..');

    if (await timezoneSection.count() > 0) {
      console.log('Timezone section found');

      // Take screenshot of timezone section
      await timezoneSection.screenshot({ path: 'test-results/timezone-section.png' });

      // Find timezone control (select or input)
      const timezoneSelect = page.locator('select').filter({ hasText: /GMT|UTC|timezone|America|Europe/i });
      const timezoneInput = page.locator('input').filter({ hasText: /timezone/i });
      const timezoneAutocomplete = page.locator('.MuiAutocomplete-input, [data-testid="timezone-autocomplete"]');

      console.log('Timezone controls found:');
      console.log(`- Select elements: ${await timezoneSelect.count()}`);
      console.log(`- Input elements: ${await timezoneInput.count()}`);
      console.log(`- Autocomplete elements: ${await timezoneAutocomplete.count()}`);

      // Test the primary timezone control
      let timezoneControl = null;
      let controlType = '';

      if (await timezoneSelect.count() > 0) {
        timezoneControl = timezoneSelect.first();
        controlType = 'select';
      } else if (await timezoneAutocomplete.count() > 0) {
        timezoneControl = timezoneAutocomplete.first();
        controlType = 'autocomplete';
      } else if (await timezoneInput.count() > 0) {
        timezoneControl = timezoneInput.first();
        controlType = 'input';
      }

      if (timezoneControl) {
        console.log(`✅ Timezone control found (${controlType})`);

        try {
          // Get current value
          let currentValue = '';
          if (controlType === 'select' || controlType === 'input') {
            currentValue = await timezoneControl.inputValue();
          } else if (controlType === 'autocomplete') {
            currentValue = await timezoneControl.textContent() || '';
          }

          console.log(`Current timezone value: "${currentValue}"`);

          // Check if it shows "Not set" issue
          const showsNotSet = currentValue.includes('Not set') || currentValue === '' || currentValue === 'undefined';
          console.log(`Shows "Not set" issue: ${showsNotSet}`);

          if (showsNotSet) {
            console.log('❌ CONFIRMED: Timezone showing "Not set" despite detected timezone');
          }

          // Test setting a timezone
          const testTimezone = 'America/New_York';
          console.log(`Testing timezone change to: ${testTimezone}`);

          if (controlType === 'select') {
            try {
              await timezoneControl.selectOption(testTimezone);
              console.log(`✅ Timezone select set to ${testTimezone}`);
            } catch (error) {
              console.log(`❌ Timezone select failed: ${error.message}`);
            }
          } else if (controlType === 'input' || controlType === 'autocomplete') {
            try {
              await timezoneControl.fill(testTimezone);
              console.log(`✅ Timezone input set to ${testTimezone}`);
            } catch (error) {
              console.log(`❌ Timezone input failed: ${error.message}`);
            }
          }

          await page.waitForTimeout(1000);

          // Check if value changed
          let newValue = '';
          if (controlType === 'select' || controlType === 'input') {
            newValue = await timezoneControl.inputValue();
          } else if (controlType === 'autocomplete') {
            newValue = await timezoneControl.textContent() || '';
          }

          console.log(`New timezone value: "${newValue}"`);

          // Look for save mechanism
          const saveButton = page.locator('button:has-text("Save"), button:has-text("Update")').filter({
            has: timezoneSection
          }).or(
            page.locator('button:has-text("Save"), button:has-text("Update")').last()
          );

          if (await saveButton.count() > 0) {
            console.log('✅ Timezone save button found');

            try {
              await saveButton.click();
              await page.waitForTimeout(3000);

              // Check persistence
              let finalValue = '';
              if (controlType === 'select' || controlType === 'input') {
                finalValue = await timezoneControl.inputValue();
              }

              console.log(`Final timezone value after save: "${finalValue}"`);

              if (finalValue === testTimezone) {
                console.log('✅ Timezone setting persisted successfully');
              } else if (finalValue === currentValue) {
                console.log('❌ Timezone setting not persisted - reverted to original');
              } else {
                console.log('⚠️ Timezone setting partially persisted - unexpected value');
              }

              // Take screenshot after save
              await page.screenshot({ path: 'test-results/timezone-after-save.png', fullPage: true });

            } catch (error) {
              console.log(`❌ Timezone save failed: ${error.message}`);
            }
          } else {
            console.log('❌ No save button found for timezone');
          }

        } catch (error) {
          console.log(`❌ Timezone control test failed: ${error.message}`);
        }
      } else {
        console.log('❌ No timezone control found');
      }

    } else {
      console.log('❌ Timezone section not found');
    }
  });

  test('Travel Preferences - Button Clickability and Functionality', async ({ page }) => {
    await page.goto(`${URLS.FRONTEND}/voya/profile`);

    console.log('=== TRAVEL PREFERENCES BUTTON TESTS ===');

    // Find travel preferences section
    const travelPrefsSection = page.locator('text=Travel Preferences').locator('..');

    if (await travelPrefsSection.count() > 0) {
      console.log('Travel Preferences section found');

      // Take screenshot of travel preferences
      await travelPrefsSection.screenshot({ path: 'test-results/travel-preferences-section.png' });

      // Find preference buttons/chips
      const preferenceButtons = page.locator('.MuiChip-root, button').filter({
        hasText: /Adventure|Relaxation|Culture|Nature|City|Beach|Mountain|Food/i
      });

      const buttonCount = await preferenceButtons.count();
      console.log(`Found ${buttonCount} travel preference buttons`);

      if (buttonCount > 0) {
        // Test each preference button
        for (let i = 0; i < buttonCount; i++) {
          const button = preferenceButtons.nth(i);

          try {
            const buttonText = await button.textContent();
            console.log(`Testing travel preference: "${buttonText}"`);

            // Check button properties
            const isEnabled = await button.isEnabled();
            const hasClickHandler = await button.getAttribute('onclick') !== null;
            const hasRole = await button.getAttribute('role');
            const isClickable = await button.getAttribute('aria-disabled') !== 'true';

            console.log(`${buttonText} - Enabled: ${isEnabled}, Clickable: ${isClickable}, HasHandler: ${hasClickHandler}, Role: ${hasRole}`);

            // Test clicking the button
            try {
              const beforeClass = await button.getAttribute('class');

              await button.click({ timeout: 2000 });
              await page.waitForTimeout(500);

              const afterClass = await button.getAttribute('class');
              const classChanged = beforeClass !== afterClass;

              console.log(`${buttonText} - Click successful, Class changed: ${classChanged}`);

              if (classChanged) {
                console.log(`✅ ${buttonText} button is interactive (class changed)`);
              } else {
                console.log(`❌ ${buttonText} button click had no visual effect`);
              }

              // Check for any API calls or state changes
              await page.waitForTimeout(1000);

            } catch (error) {
              console.log(`❌ ${buttonText} button click failed: ${error.message}`);
            }

          } catch (error) {
            console.log(`❌ Error testing preference button ${i + 1}: ${error.message}`);
          }
        }

        // Take screenshot after button tests
        await page.screenshot({ path: 'test-results/travel-prefs-after-clicks.png', fullPage: true });

      } else {
        console.log('❌ No travel preference buttons found');
      }

    } else {
      console.log('❌ Travel Preferences section not found');
    }
  });

  test('User Profile Settings - Personal Information Updates', async ({ page }) => {
    await page.goto(`${URLS.FRONTEND}/voya/profile`);

    console.log('=== USER PROFILE SETTINGS TESTS ===');

    // Look for profile editing functionality
    const editProfileButton = page.locator('button:has-text("Edit Profile"), button:has([data-testid="EditIcon"]), [data-testid="edit-profile"]');

    if (await editProfileButton.count() > 0) {
      console.log('Edit Profile button found');

      try {
        await editProfileButton.click();
        await page.waitForTimeout(2000);

        // Check if edit form appears
        const hasEditForm = await page.locator('.edit-form, [data-testid="profile-edit"], form').count() > 0;
        const hasModal = await page.locator('.modal, .MuiDialog-root').count() > 0;

        console.log(`Edit form visible: ${hasEditForm}, Modal opened: ${hasModal}`);

        if (hasEditForm || hasModal) {
          await this.testProfileEditForm(page);
        } else {
          console.log('❌ Edit Profile button did not open editing interface');
        }

      } catch (error) {
        console.log(`❌ Edit Profile button test failed: ${error.message}`);
      }
    } else {
      console.log('❌ Edit Profile button not found');
    }

    // Test inline profile editing (if available)
    const profileFields = [
      { selector: 'input[name="first_name"], input[name="firstName"]', name: 'First Name' },
      { selector: 'input[name="last_name"], input[name="lastName"]', name: 'Last Name' },
      { selector: 'input[name="email"]', name: 'Email' },
      { selector: 'input[name="mobile"], input[name="phone"]', name: 'Phone' }
    ];

    console.log('Testing direct profile field editing...');

    for (const field of profileFields) {
      const element = page.locator(field.selector);

      if (await element.count() > 0) {
        console.log(`✅ ${field.name} field found`);

        try {
          const isEditable = await element.isEnabled();
          const currentValue = await element.inputValue();

          console.log(`${field.name} - Editable: ${isEditable}, Value: "${currentValue}"`);

          if (isEditable) {
            // Test editing
            const testValue = field.name === 'First Name' ? 'TestFirst' :
                             field.name === 'Last Name' ? 'TestLast' :
                             field.name === 'Email' ? 'test@example.com' :
                             '+1234567890';

            await element.fill(testValue);
            await page.waitForTimeout(500);

            const newValue = await element.inputValue();
            console.log(`${field.name} set to: "${newValue}"`);

            if (newValue === testValue) {
              console.log(`✅ ${field.name} field accepts changes`);
            } else {
              console.log(`❌ ${field.name} field did not accept changes`);
            }

            // Revert to original value
            await element.fill(currentValue);
          }

        } catch (error) {
          console.log(`❌ ${field.name} field test failed: ${error.message}`);
        }
      } else {
        console.log(`❌ ${field.name} field not found`);
      }
    }

    await page.screenshot({ path: 'test-results/profile-settings-test.png', fullPage: true });
  });

  test('Profile Edit Form Testing', async ({ page }) => {
    await testProfileEditForm(page);
  });

  async function testProfileEditForm(page) {
    console.log('=== PROFILE EDIT FORM TESTING ===');

    const editFields = [
      { selector: 'input[name="first_name"], input[name="firstName"]', value: 'EditTest', name: 'First Name' },
      { selector: 'input[name="last_name"], input[name="lastName"]', value: 'User', name: 'Last Name' },
      { selector: 'textarea[name="bio"], textarea[name="description"]', value: 'Test bio', name: 'Bio' },
      { selector: 'input[name="mobile"], input[name="phone"]', value: '+1234567890', name: 'Phone' }
    ];

    for (const field of editFields) {
      const element = page.locator(field.selector);

      if (await element.count() > 0) {
        console.log(`Testing edit field: ${field.name}`);

        try {
          await element.fill(field.value);
          const inputValue = await element.inputValue();

          if (inputValue === field.value) {
            console.log(`✅ ${field.name} edit field working`);
          } else {
            console.log(`❌ ${field.name} edit field not working`);
          }
        } catch (error) {
          console.log(`❌ ${field.name} edit field error: ${error.message}`);
        }
      }
    }

    // Test save button
    const saveButton = page.locator('button:has-text("Save"), button:has-text("Update"), button[type="submit"]');

    if (await saveButton.count() > 0) {
      console.log('Save button found in edit form');

      try {
        await saveButton.click();
        await page.waitForTimeout(3000);

        // Check for success/error messages
        const hasSuccess = await page.locator('.success, .MuiAlert-standardSuccess').count() > 0;
        const hasError = await page.locator('.error, .MuiAlert-error').count() > 0;

        console.log(`Profile save result - Success: ${hasSuccess}, Error: ${hasError}`);

        if (hasSuccess) {
          console.log('✅ Profile update successful');
        } else if (hasError) {
          const errorText = await page.locator('.error, .MuiAlert-error').textContent();
          console.log(`❌ Profile update error: ${errorText}`);
        }

      } catch (error) {
        console.log(`❌ Save button test failed: ${error.message}`);
      }
    } else {
      console.log('❌ Save button not found in edit form');
    }
  }

  test('Settings API Integration - Backend Persistence Test', async ({ request }) => {
    if (!authToken) {
      test.skip(true, 'No auth token available for API testing');
      return;
    }

    console.log('=== SETTINGS API INTEGRATION TESTS ===');

    // Test user profile update API
    try {
      const updateResponse = await request.put(`${API_BASE}/user/me`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        data: {
          first_name: "API",
          last_name: "Test",
          timezone: "America/New_York",
          mobile: "+1234567890"
        }
      });

      console.log(`Profile update API status: ${updateResponse.status()}`);

      if (updateResponse.ok()) {
        const responseData = await updateResponse.json();
        console.log('✅ Profile update API working');
        console.log('Response keys:', Object.keys(responseData));

        // Verify the update
        const getResponse = await request.get(`${API_BASE}/user/me`, {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });

        if (getResponse.ok()) {
          const userData = await getResponse.json();
          console.log('Updated user data:');
          console.log(`- First Name: ${userData.first_name}`);
          console.log(`- Last Name: ${userData.last_name}`);
          console.log(`- Timezone: ${userData.timezone}`);
          console.log(`- Mobile: ${userData.mobile}`);

          const dataMatches = userData.first_name === 'API' &&
                             userData.last_name === 'Test' &&
                             userData.timezone === 'America/New_York';

          if (dataMatches) {
            console.log('✅ Settings persistence working via API');
          } else {
            console.log('❌ Settings not persisted correctly via API');
          }
        }

      } else {
        const errorText = await updateResponse.text();
        console.log(`❌ Profile update API failed: ${errorText}`);
      }

    } catch (error) {
      console.log(`❌ Settings API test failed: ${error.message}`);
    }
  });

  test('Notification Preferences - Settings Test', async ({ page }) => {
    await page.goto(`${URLS.FRONTEND}/voya/profile`);

    console.log('=== NOTIFICATION PREFERENCES TESTS ===');

    // Look for notification settings
    const notificationSection = page.locator('text=Notifications', 'text=Email Preferences', 'text=Alerts').first().locator('..');

    if (await notificationSection.count() > 0) {
      console.log('Notification settings section found');

      await notificationSection.screenshot({ path: 'test-results/notification-settings.png' });

      // Test notification toggles/checkboxes
      const notificationToggles = page.locator('input[type="checkbox"]').filter({
        hasText: /notification|email|alert|newsletter/i
      });

      const toggleCount = await notificationToggles.count();
      console.log(`Found ${toggleCount} notification toggles`);

      if (toggleCount > 0) {
        for (let i = 0; i < toggleCount; i++) {
          const toggle = notificationToggles.nth(i);

          try {
            const isChecked = await toggle.isChecked();
            const label = await toggle.locator('..').textContent();

            console.log(`Notification toggle "${label}": ${isChecked ? 'ON' : 'OFF'}`);

            // Test toggling
            await toggle.click();
            await page.waitForTimeout(500);

            const newState = await toggle.isChecked();
            console.log(`After click: ${newState ? 'ON' : 'OFF'}`);

            if (newState !== isChecked) {
              console.log(`✅ Notification toggle "${label}" is functional`);
            } else {
              console.log(`❌ Notification toggle "${label}" not responsive`);
            }

          } catch (error) {
            console.log(`❌ Notification toggle ${i + 1} test failed: ${error.message}`);
          }
        }

        // Look for save button
        const saveButton = page.locator('button:has-text("Save Preferences"), button:has-text("Update Notifications")');

        if (await saveButton.count() > 0) {
          console.log('✅ Notification preferences save button found');

          try {
            await saveButton.click();
            await page.waitForTimeout(2000);

            const hasSuccess = await page.locator('.success, .MuiAlert-standardSuccess').count() > 0;
            console.log(`Notification preferences save successful: ${hasSuccess}`);

          } catch (error) {
            console.log(`❌ Notification preferences save failed: ${error.message}`);
          }
        }

      } else {
        console.log('❌ No notification toggles found');
      }

    } else {
      console.log('❌ Notification settings section not found');
    }

    await page.screenshot({ path: 'test-results/notification-prefs-final.png', fullPage: true });
  });
});
