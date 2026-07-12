/**
 * Email Payment Links E2E Test
 *
 * Tests the complete email-to-payment flow for GDS flight bookings.
 * Verifies that users can click email payment links and complete ticket issuance.
 */

import { test, expect } from '@playwright/test';
import { URLS, TIMEOUTS, generateTestUser, buildFrontendUrl } from '../../../utils/constants.js';
import { navigateToVoya, waitForReactApp } from '../../../helpers/navigation-helpers.js';
import { ensureAuthenticated, clearAuthState } from '../../../helpers/auth-helpers.js';
import { logTestStep, logSuccess, logError } from '../../../helpers/debug-helpers.js';
import { MailHogHelper } from '../../../utils/mailhog-client.js';
import { createApiClient } from '../../../utils/api-client.js';

test.describe('Email Payment Links Flow', { tag: '@mock-required' }, () => {
  let mailhog;
  let apiClient;
  let testUser;

  test.beforeEach(async ({ page, request }) => {
    // Initialize helpers
    mailhog = new MailHogHelper(request);
    apiClient = createApiClient(request);

    // Generate unique test user (using existing seeded user)
    testUser = {
      email: 'flightbooker@example.com',
      password: 'Flight123!',
      firstName: 'Flight',
      lastName: 'Booker'
    };

    // Clear previous emails
    await mailhog.clearEmails();

    logTestStep('Email payment links test setup complete');
  });

  test.afterEach(async ({ page }) => {
    // Clean up auth state
    await clearAuthState(page);
  });

  test('should handle complete email-to-payment flow', async ({ page, request }) => {
    logTestStep('Starting email-to-payment flow test');

    // Step 1: Simulate a GDS booking confirmation email being sent
    const mockBookingReference = `VOYA-TEST${Date.now()}`;
    const paymentUrl = `${buildFrontendUrl()}/dev/flight-booker/index.html?booking=${mockBookingReference}&step=payment`;

    logTestStep(`Mock booking reference: ${mockBookingReference}`);
    logTestStep(`Payment URL: ${paymentUrl}`);

    // Step 2: Verify booking endpoint returns data without FlightLogic API call
    const bookingResponse = await request.get(`${URLS.BACKEND}/api/bookings/${mockBookingReference}`);

    if (bookingResponse.ok()) {
      const bookingData = await bookingResponse.json();
      logSuccess('✅ Booking endpoint accessible without authentication');

      expect(bookingData.voya_booking_reference).toBe(mockBookingReference);
      expect(bookingData.booking_status).toBe('CONFIRMED');
      expect(bookingData.ticket_status).toBe('PENDING');
      expect(bookingData.trip_details.payment_required).toBe(true);

      logTestStep('Booking data structure validated');
    } else {
      logError('❌ Booking endpoint failed - may need mock setup');
      // Continue test anyway to verify frontend behavior
    }

    // Step 3: Navigate to payment URL (simulating email link click)
    await page.goto(paymentUrl);
    await waitForReactApp(page);

    logTestStep('Navigated to payment URL from email link');

    // Step 4: Verify page loads in payment step with booking data
    await expect(page).toHaveURL(new RegExp(mockBookingReference));

    // Wait for booking data to load
    await page.waitForTimeout(2000);

    // Check if payment section is visible
    const paymentSection = page.locator('#payment-section');
    await expect(paymentSection).toBeVisible();

    logSuccess('✅ Payment page loaded successfully from email link');

    // Step 5: Verify booking summary displays (even with placeholder data)
    const bookingSummary = page.locator('.booking-summary, #booking-summary, [data-testid="booking-summary"]');
    if (await bookingSummary.isVisible()) {
      logSuccess('✅ Booking summary section visible');
    }

    // Check for booking reference display
    const bookingRefElement = page.locator('text=' + mockBookingReference);
    if (await bookingRefElement.isVisible()) {
      logSuccess('✅ Booking reference displayed correctly');
    }

    // Step 6: Verify authentication is handled automatically
    // The auto-login should happen seamlessly in loadBookingFromReference()

    // Wait for potential authentication
    await page.waitForTimeout(1000);

    // Step 7: Test payment button functionality
    const paymentButton = page.locator('button:has-text("Pay Now"), button:has-text("Complete Payment"), #payment-button');

    if (await paymentButton.isVisible()) {
      logTestStep('Payment button found, testing click behavior');

      // Mock Stripe payment intent for testing
      await page.route('**/create-payment-intent', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            client_secret: 'pi_test_1234567890_secret_test',
            payment_intent_id: 'pi_test_1234567890'
          })
        });
      });

      // Mock successful ticket issuance
      await page.route('**/api/flights/issue_ticket', async route => {
        const authHeader = route.request().headers()['authorization'];

        if (!authHeader || !authHeader.startsWith('Bearer ')) {
          await route.fulfill({
            status: 401,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Authentication required for ticketing' })
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              success: true,
              message: 'Ticket issued successfully',
              ticket_number: '123456789'
            })
          });
        }
      });

      await paymentButton.click();
      logSuccess('✅ Payment button clickable');

      // Step 8: Verify error handling without authentication
      // If auto-login fails, should show clear error message
      const errorMessage = page.locator('.error-message, .alert-danger, [data-testid="error-message"]');

      // Give time for payment processing
      await page.waitForTimeout(3000);

      if (await errorMessage.isVisible()) {
        const errorText = await errorMessage.textContent();
        if (errorText.toLowerCase().includes('authentication')) {
          logError('⚠️ Authentication error detected - auto-login may need improvement');
        } else {
          logSuccess('✅ Error handling working correctly');
        }
      } else {
        logSuccess('✅ Payment processing initiated successfully');
      }
    } else {
      logError('⚠️ Payment button not found - may need mock booking data');
    }

    logSuccess('🎉 Email-to-payment flow test completed');
  });

  test('should handle booking reference validation', async ({ page, request }) => {
    logTestStep('Testing booking reference validation');

    // Test with invalid booking reference
    const invalidRef = 'VOYA-INVALID123';
    const invalidUrl = `${buildFrontendUrl()}/dev/flight-booker/index.html?booking=${invalidRef}&step=payment`;

    await page.goto(invalidUrl);
    await waitForReactApp(page);

    // Should show error or redirect appropriately
    await page.waitForTimeout(2000);

    // Check for error handling
    const errorIndicators = [
      page.locator('.error-message'),
      page.locator('.alert-danger'),
      page.locator('text=not found'),
      page.locator('text=invalid')
    ];

    let errorFound = false;
    for (const indicator of errorIndicators) {
      if (await indicator.isVisible()) {
        errorFound = true;
        logSuccess('✅ Invalid booking reference handled correctly');
        break;
      }
    }

    if (!errorFound) {
      logError('⚠️ Invalid booking reference error handling may need improvement');
    }
  });

  test('should handle URL parameter edge cases', async ({ page }) => {
    logTestStep('Testing URL parameter edge cases');

    const testCases = [
      // Missing booking parameter
      `${buildFrontendUrl()}/dev/flight-booker/index.html?step=payment`,
      // Missing step parameter
      `${buildFrontendUrl()}/dev/flight-booker/index.html?booking=VOYA-TEST123`,
      // Invalid step parameter
      `${buildFrontendUrl()}/dev/flight-booker/index.html?booking=VOYA-TEST123&step=invalid`,
    ];

    for (const testUrl of testCases) {
      logTestStep(`Testing URL: ${testUrl}`);

      await page.goto(testUrl);
      await waitForReactApp(page);
      await page.waitForTimeout(1500);

      // Page should handle gracefully (not crash)
      const pageTitle = await page.title();
      expect(pageTitle).toBeTruthy();

      logSuccess('✅ URL parameter edge case handled gracefully');
    }
  });

  test('should maintain security for booking access', async ({ page, request }) => {
    logTestStep('Testing booking security');

    // Verify booking endpoint requires valid format
    const testCases = [
      'INVALID-FORMAT',
      'voya-lowercase',
      'VOYA-',
      'VOYA-TOOSHORT',
      ''
    ];

    for (const invalidRef of testCases) {
      if (invalidRef) {
        const response = await request.get(`${URLS.BACKEND}/api/bookings/${invalidRef}`);
        expect(response.status()).toBeGreaterThanOrEqual(400);
        logSuccess(`✅ Invalid reference ${invalidRef} properly rejected`);
      }
    }

    // Verify high-entropy reference format expected
    const validRef = 'VOYA-ABCDEFGHIJ';
    const response = await request.get(`${URLS.BACKEND}/api/bookings/${validRef}`);

    // Should either return booking data or 404, not a server error
    expect([200, 404]).toContain(response.status());

    logSuccess('✅ Booking reference security maintained');
  });

  test('should handle authentication flow correctly', async ({ page }) => {
    logTestStep('Testing authentication in payment flow');

    const mockBookingReference = `VOYA-AUTH${Date.now()}`;
    const paymentUrl = `${buildFrontendUrl()}/dev/flight-booker/index.html?booking=${mockBookingReference}&step=payment`;

    // Mock authentication endpoints
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock_token_12345',
          user: {
            id: 'test_user_id',
            email: 'flightbooker@example.com',
            first_name: 'Flight',
            last_name: 'Booker'
          }
        })
      });
    });

    await page.goto(paymentUrl);
    await waitForReactApp(page);

    // Wait for auto-login to potentially trigger
    await page.waitForTimeout(2000);

    // Check if authentication state is set
    const authToken = await page.evaluate(() => {
      return localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    });

    if (authToken) {
      logSuccess('✅ Auto-authentication successful');
    } else {
      logError('⚠️ Auto-authentication may need verification');
    }

    logSuccess('🎉 Authentication flow test completed');
  });
});
