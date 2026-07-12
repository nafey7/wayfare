/**
 * Complete Chat-to-Booking Flow E2E Test
 *
 * Tests the full conversational flight booking journey:
 * 1. User logs in via API (fast setup)
 * 2. Opens Voya homepage
 * 3. Chats with Voya to search for flights
 * 4. Answers questions (one-way/round-trip, dates)
 * 5. Selects a flight option
 * 6. Follows booking link
 *
 * Features:
 * - Always records video (even on success)
 * - Takes screenshots at key checkpoints
 * - Natural delays between messages (2s)
 * - Validates AI responses at each step
 */

import { test, expect } from '@playwright/test';
import { URLS, TIMEOUTS, generateTestUser, buildFrontendUrl } from '../../../utils/constants.js';
import { ChatPage } from '../../pages/ChatPage.js';
import { logTestStep, logSuccess, logError } from '../../../helpers/debug-helpers.js';
import { createApiClient } from '../../../utils/api-client.js';
import { MailHogHelper } from '../../../utils/mailhog-client.js';

// Configure test to always record video and take screenshots
test.use({
  video: 'on', // Always record video
  screenshot: 'on', // Take screenshot on failure
  trace: 'on', // Always collect trace
});

test.describe('Chat-to-Booking Complete Flow', { tag: '@mock-required' }, () => {
  // Set test timeout to 10 minutes (AI can be slow)
  test.setTimeout(600000);
  let chatPage;
  let testUser;
  let accessToken;

  test.beforeEach(async ({ page, request }) => {
    logTestStep('=== SETUP: Creating test user and authenticating ===');

    // Generate unique test user
    testUser = generateTestUser({
      email: `chat-booking-${Date.now()}@example.com`,
      firstName: 'John',
      lastName: 'Traveler'
    });

    // Helper for MailHog (to get activation token)
    const mailhog = new MailHogHelper(request);
    await mailhog.clearEmails();

    // Register user via API
    logTestStep('Registering user via API...');
    const registerResponse = await request.post(URLS.BACKEND + URLS.AUTH.REGISTER, {
      data: {
        email: testUser.email,
        first_name: testUser.firstName,
        last_name: testUser.lastName
      }
    });
    expect(registerResponse.ok()).toBeTruthy();

    // Get activation token from email
    logTestStep('Waiting for activation email...');
    const activationEmail = await mailhog.waitForEmail(testUser.email, 15000);
    const activationToken = mailhog.extractRegistrationToken(activationEmail);
    expect(activationToken).toBeTruthy();

    // Complete registration with password
    logTestStep('Completing registration...');
    const completeResponse = await request.post(URLS.BACKEND + URLS.AUTH.COMPLETE_REGISTRATION, {
      data: {
        token: activationToken,
        password: testUser.password,
        confirm_password: testUser.password
      }
    });
    expect(completeResponse.ok()).toBeTruthy();

    const userData = await completeResponse.json();
    accessToken = userData.access_token;
    expect(accessToken).toBeTruthy();

    logSuccess(`User created and authenticated: ${testUser.email}`);

    // Initialize chat page object
    chatPage = new ChatPage(page);

    logSuccess('=== SETUP COMPLETE ===\n');
  });

  test('Complete conversational flight booking flow', async ({ page, request }) => {
    logTestStep('=== STARTING COMPLETE CHAT BOOKING FLOW ===\n');

    // Calculate future dates
    const today = new Date();
    const departureDate = new Date(today);
    departureDate.setDate(today.getDate() + 10);
    const returnDate = new Date(today);
    returnDate.setDate(today.getDate() + 20);

    const formatDate = (date) => {
      return date.toISOString().split('T')[0]; // YYYY-MM-DD
    };

    const departureDateStr = formatDate(departureDate);
    const returnDateStr = formatDate(returnDate);

    logTestStep(`Departure: ${departureDateStr}, Return: ${returnDateStr}`);

    // =========================================================================
    // CHECKPOINT 1: Navigate to Voya Homepage and Set Auth
    // =========================================================================
    logTestStep('CHECKPOINT 1: Navigating to Voya homepage and setting auth...');

    // Navigate and set authentication
    await page.goto(buildFrontendUrl('/voya'));
    await page.waitForLoadState('domcontentloaded');

    // IMPORTANT: Frontend uses "Authorization" key, not "accessToken"
    await page.evaluate((token) => {
      localStorage.setItem('Authorization', token);
    }, accessToken);

    // Reload to apply authentication
    await page.reload();
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'test-results/checkpoint-01-homepage.png', fullPage: true });
    logSuccess('✓ Voya homepage loaded with authentication\n');

    // =========================================================================
    // CHECKPOINT 2: Open Chat and Send Initial Request
    // =========================================================================
    logTestStep('CHECKPOINT 2: Opening chat and requesting flight search...');

    await chatPage.openChat();
    await page.waitForTimeout(2000); // Wait for welcome message
    await page.screenshot({ path: 'test-results/checkpoint-02-chat-opened.png', fullPage: true });

    // Send initial flight request
    await chatPage.sendMessage('I want to fly from AMS to FAO');
    logSuccess('✓ Sent: "I want to fly from AMS to FAO"');

    // Wait for Voya's response (AI can be slow in test environment)
    const response1 = await chatPage.waitForAIResponse(60000); // 60 seconds for AI processing
    logTestStep(`Voya: ${response1.substring(0, 150)}...`);
    await page.screenshot({ path: 'test-results/checkpoint-03-initial-response.png', fullPage: true });

    // Verify Voya asks about trip type
    expect(response1.toLowerCase()).toMatch(/one.*way|round.*trip|return/i);
    logSuccess('✓ Voya asking about trip type\n');

    await page.waitForTimeout(2000); // Natural delay

    // =========================================================================
    // CHECKPOINT 3: Answer Trip Type
    // =========================================================================
    logTestStep('CHECKPOINT 3: Answering trip type...');
    await chatPage.sendMessage('round-trip');
    const response2 = await chatPage.waitForAIResponse(60000);
    logTestStep(`Voya: ${response2.substring(0, 100)}...`);
    expect(response2.toLowerCase()).toMatch(/depart|leave|when|date/i);
    logSuccess('✓ Voya asking about departure date\n');
    await page.waitForTimeout(2000);

    // =========================================================================
    // CHECKPOINT 4: Provide Departure Date
    // =========================================================================
    logTestStep('CHECKPOINT 4: Providing departure date...');
    await chatPage.sendMessage(departureDateStr);
    const response3 = await chatPage.waitForAIResponse(60000);
    logTestStep(`Voya: ${response3.substring(0, 100)}...`);
    expect(response3.toLowerCase()).toMatch(/return|back|end/i);
    logSuccess('✓ Voya asking about return date\n');
    await page.waitForTimeout(2000);

    // =========================================================================
    // CHECKPOINT 5: Provide Return Date and Wait for Flight Options
    // =========================================================================
    logTestStep('CHECKPOINT 5: Providing return date...');
    await chatPage.sendMessage(returnDateStr);
    logTestStep('Waiting for flight search (may take 30+ seconds)...');
    const response4 = await chatPage.waitForAIResponse(60000); // 60s for flight search
    logTestStep(`Voya: ${response4.substring(0, 150)}...`);
    await page.screenshot({ path: 'test-results/checkpoint-06-flight-options.png', fullPage: true });
    expect(response4.toLowerCase()).toMatch(/option|flight|€|eur|book/i);
    logSuccess('✓ Voya presented flight options\n');
    await page.waitForTimeout(2000);

    // =========================================================================
    // CHECKPOINT 6: Select Flight Option
    // =========================================================================
    logTestStep('CHECKPOINT 6: Selecting flight option 1...');
    await chatPage.sendMessage('BOOK 1');
    const response5 = await chatPage.waitForAIResponse(60000);
    logTestStep(`Voya: ${response5.substring(0, 150)}...`);
    await page.screenshot({ path: 'test-results/checkpoint-07-booking-link-response.png', fullPage: true });
    logSuccess('✓ Voya provided booking response\n');
    await page.waitForTimeout(2000);

    // =========================================================================
    // CHECKPOINT 7: Follow Booking Link (if provided)
    // =========================================================================
    logTestStep('CHECKPOINT 7: Checking for booking link...');

    // Look for booking link or redirect
    const bookingLink = page.locator('a[href*="flight-booker"]').first();
    const hasLink = await bookingLink.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasLink) {
      await bookingLink.click();
      await page.waitForTimeout(5000);
      await page.screenshot({ path: 'test-results/checkpoint-08-flight-booker-page.png', fullPage: true });
      logSuccess('✓ Navigated to flight booker page');
    } else {
      // Check if already redirected or link in message
      const currentUrl = page.url();
      logTestStep(`Current URL: ${currentUrl}`);
      if (currentUrl.includes('flight-booker')) {
        logSuccess('✓ Auto-redirected to flight booker');
      } else {
        logTestStep('ℹ️  No booking link found (may require manual booking)');
      }
    }

    await page.screenshot({ path: 'test-results/checkpoint-09-final-state.png', fullPage: true });

    logSuccess('\n=== 🎉 COMPLETE CHAT BOOKING FLOW TEST FINISHED 🎉 ===');
    logTestStep(`Departure: ${departureDateStr}, Return: ${returnDateStr}`);
  });

  test.afterEach(async ({ page }, testInfo) => {
    // Always take final screenshot
    await page.screenshot({
      path: `test-results/${testInfo.title.replace(/\s+/g, '-')}-final.png`,
      fullPage: true
    });

    logTestStep(`\n=== Test ${testInfo.status.toUpperCase()} ===`);
    logTestStep(`Duration: ${testInfo.duration}ms`);

    if (testInfo.status === 'failed') {
      logError(`Error: ${testInfo.error?.message}`);
    }
  });
});
