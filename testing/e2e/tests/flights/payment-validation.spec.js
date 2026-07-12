const { test, expect } = require('@playwright/test');
const ChatPage = require('../../pages/ChatPage');
const { logTestStep, logSuccess, logError } = require('../../../helpers/debug-helpers');

test.describe('Flight Booker - Payment Validation', { tag: '@mock-required' }, () => {
  let chatPage;

  test.beforeEach(async ({ page }) => {
    chatPage = new ChatPage(page);
    await chatPage.page.goto('http://localhost:8001/dev/flight-booker');

    // Mock successful flight search and booking session
    await mockFlightSearchAndBookingSession(page);
  });

  test.describe('processPayment() Prevention Before Payment', () => {
    test('should prevent processPayment() calls when no payment intent exists', async ({ page }) => {
      logTestStep('Testing processPayment() prevention without payment intent');

      // Navigate through booking flow to payment step
      await navigateToPaymentStep(page);

      // Mock no payment intent (simulate no payment started)
      let processPaymentCalled = false;
      await page.route('**/api/flights/book-from-session/**', async route => {
        processPaymentCalled = true;
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Payment required before booking' })
        });
      });

      // Try to trigger processPayment() directly via JavaScript
      const result = await page.evaluate(() => {
        // Simulate missing paymentIntentId (no Stripe payment completed)
        window.paymentIntentId = null;
        window.paymentSucceeded = false;

        try {
          // Try to call processPayment() directly
          window.processPayment();
          return { success: true };
        } catch (error) {
          return { success: false, error: error.message };
        }
      });

      // Verify that processPayment() is blocked
      expect(result.success).toBe(true); // Function should run but be blocked internally
      expect(processPaymentCalled).toBe(false); // API should not be called

      // Verify error status is shown
      const statusElement = await page.locator('#status-message');
      await expect(statusElement).toContainText('Please complete payment first');

      logSuccess('processPayment() correctly blocked when no payment intent exists');
    });

    test('should prevent processPayment() calls when payment intent exists but not confirmed', async ({ page }) => {
      logTestStep('Testing processPayment() prevention with unconfirmed payment');

      await navigateToPaymentStep(page);

      // Mock payment intent creation but not confirmation
      await page.route('**/api/payments/create-payment-intent', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            client_secret: 'pi_test_pending_secret',  // pragma: allowlist secret
            payment_intent_id: 'pi_test_pending'
          })
        });
      });

      // Mock payment verification as failed/pending
      await page.route('**/api/payments/transaction/pi_test_pending', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'requires_payment_method', // Not succeeded
            amount: 27436,
            currency: 'USD'
          })
        });
      });

      let bookingApiCalled = false;
      await page.route('**/api/flights/book-from-session/**', async route => {
        bookingApiCalled = true;
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Should not reach this point' })
        });
      });

      // Initialize Stripe payment (but don't confirm)
      await page.evaluate(() => {
        window.paymentIntentId = 'pi_test_pending';
        window.paymentSucceeded = false;
      });

      // Try to call processPayment()
      await page.evaluate(() => {
        window.processPayment();
      });

      // Wait for payment verification to complete
      await page.waitForTimeout(2000);

      // Verify booking API was not called due to payment verification failure
      expect(bookingApiCalled).toBe(false);

      // Verify error message is displayed
      const statusElement = await page.locator('#status-message');
      await expect(statusElement).toContainText('Payment verification timeout');

      logSuccess('processPayment() correctly blocked for unconfirmed payment');
    });

    test('should allow processPayment() only after successful Stripe payment confirmation', async ({ page }) => {
      logTestStep('Testing processPayment() allowed after successful payment');

      await navigateToPaymentStep(page);

      // Mock successful payment intent creation
      await page.route('**/api/payments/create-payment-intent', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            client_secret: 'pi_test_success_secret',  // pragma: allowlist secret
            payment_intent_id: 'pi_test_success'
          })
        });
      });

      // Mock successful payment verification
      await page.route('**/api/payments/transaction/pi_test_success', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'succeeded', // Payment confirmed
            amount: 27436,
            currency: 'USD'
          })
        });
      });

      // Mock successful booking creation (LCC flow)
      let bookingApiCalled = false;
      await page.route('**/api/flights/book-from-session/**', async route => {
        bookingApiCalled = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            voya_booking_reference: 'VOYA-TEST-SUCCESS',
            external_booking_reference: 'TR999999',
            booking_status: 'CONFIRMED',
            is_successful: true
          })
        });
      });

      // Simulate successful Stripe payment
      await page.evaluate(() => {
        window.paymentIntentId = 'pi_test_success';
        window.paymentSucceeded = true;
        window.isLCC = true; // LCC flow for immediate booking
      });

      // Call processPayment() after successful payment
      await page.evaluate(() => {
        window.processPayment();
      });

      // Wait for payment verification and booking creation
      await page.waitForTimeout(3000);

      // Verify booking API was called after payment confirmation
      expect(bookingApiCalled).toBe(true);

      // Verify success status is displayed
      await expect(page.locator('#status-message')).toContainText('complete', { timeout: 5000 });

      logSuccess('processPayment() correctly allowed after successful payment confirmation');
    });

    test('should validate authentication before allowing processPayment()', async ({ page }) => {
      logTestStep('Testing authentication validation for processPayment()');

      await navigateToPaymentStep(page);

      // Mock successful payment but no authentication
      await page.evaluate(() => {
        window.paymentIntentId = 'pi_test_auth';
        window.paymentSucceeded = true;
        window.accessToken = null; // No authentication
      });

      let authenticationErrorCaught = false;
      await page.route('**/api/payments/transaction/**', async route => {
        // Should fail due to missing auth
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Authentication required' })
        });
        authenticationErrorCaught = true;
      });

      // Try to call processPayment() without authentication
      await page.evaluate(() => {
        window.processPayment();
      });

      await page.waitForTimeout(2000);

      // Verify authentication error was encountered
      expect(authenticationErrorCaught).toBe(true);

      // Verify error message is displayed
      await expect(page.locator('#status-message')).toContainText('Authentication', { timeout: 5000 });

      logSuccess('processPayment() correctly validates authentication');
    });
  });

  test.describe('Payment Button State Management', () => {
    test('should disable payment UI elements until Stripe payment completes', async ({ page }) => {
      logTestStep('Testing payment button state management');

      await navigateToPaymentStep(page);

      // Verify payment elements are in correct initial state
      const paymentButton = await page.locator('button:has-text("Pay")');

      // Initially, payment should be disabled until Stripe loads
      await expect(paymentButton).toBeDisabled();

      // Mock Stripe payment form loading
      await page.evaluate(() => {
        // Simulate Stripe Elements loading
        window.stripe = {
          elements: () => ({
            create: () => ({
              mount: () => {},
              on: () => {}
            })
          }),
          confirmPayment: () => Promise.resolve({
            paymentIntent: {
              id: 'pi_test_confirmed',
              status: 'succeeded'
            }
          })
        };
      });

      // Initialize Stripe payment
      await page.evaluate(() => {
        if (window.initializeStripePayment) {
          window.initializeStripePayment();
        }
      });

      await page.waitForTimeout(1000);

      // After Stripe loads, payment button should be enabled
      await expect(paymentButton).toBeEnabled({ timeout: 5000 });

      logSuccess('Payment button states managed correctly');
    });

    test('should show loading state during payment processing', async ({ page }) => {
      logTestStep('Testing payment processing loading states');

      await navigateToPaymentStep(page);

      // Mock slow payment verification (3 second delay)
      await page.route('**/api/payments/transaction/**', async route => {
        await new Promise(resolve => setTimeout(resolve, 1000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'succeeded' })
        });
      });

      // Set up payment state
      await page.evaluate(() => {
        window.paymentIntentId = 'pi_test_loading';
        window.paymentSucceeded = false;
      });

      // Start payment processing
      const processPromise = page.evaluate(() => {
        window.processPayment();
      });

      // Check loading state is shown
      await expect(page.locator('#status-message')).toContainText('Confirming payment', { timeout: 2000 });

      // Wait for payment to complete
      await processPromise;
      await page.waitForTimeout(2000);

      logSuccess('Loading states displayed correctly during payment processing');
    });
  });

  // Helper function to navigate to payment step
  async function navigateToPaymentStep(page) {
    // Mock being on the payment step with required data
    await page.evaluate(() => {
      // Set up minimal required state for payment step
      window.selectedFlightData = {
        session_id: 'test-session-123',
        selected_flight: {
          outbound: {
            pricing: {
              fare_totals: { total_fare: { amount: '274.36', currency: 'USD' } }
            }
          }
        }
      };

      // Navigate to payment step
      if (window.showStep) {
        window.showStep('payment');
      }
    });
  }

  // Helper function to mock flight search and booking session
  async function mockFlightSearchAndBookingSession(page) {
    // Mock booking session data
    await page.route('**/api/booking-sessions/**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: 'test-session-123',
          selected_flight: {
            outbound: {
              journey_type: 'OneWay',
              pricing: {
                fare_totals: {
                  total_fare: { amount: '274.36', currency: 'USD' }
                }
              }
            }
          }
        })
      });
    });

    // Mock authentication
    await page.route('**/api/auth/me', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-user-123',
          email: 'test@example.com',
          first_name: 'Test',
          last_name: 'User'
        })
      });
    });
  }
});
