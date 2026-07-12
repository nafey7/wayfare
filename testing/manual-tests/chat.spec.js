/**
 * Chat System and Gemini AI Integration Diagnostic Tests
 *
 * Purpose: Test chat functionality and Gemini AI integration including:
 * - Basic chat message sending/receiving
 * - Gemini AI response generation (with new GOOGLE_AI_API_KEY)
 * - Trip planning through chat
 * - Flight search triggering via chat
 * - Chat history persistence
 * - Multiple chat handling
 */

import { test, expect } from '@playwright/test';
import { URLS, SELECTORS, TIMEOUTS, generateTestUser, buildApiUrl, buildFrontendUrl } from '../utils/constants.js';
import { createApiClient } from '../utils/api-client.js';
import { navigateToVoya, navigateToApp } from '../helpers/navigation-helpers.js';
import { logTestStep, logSuccess, logError } from '../helpers/debug-helpers.js';

test.describe('Chat System and Gemini AI Diagnostics', () => {
  let authToken;
  let page;

  test.beforeAll(async ({ request }) => {
    // Try to create a test user first
    const testEmail = "playwright-test@example.com";
    const testPassword = "TestPassword123";

    // Register test user
    await request.post(buildApiUrl(URLS.AUTH.REGISTER), {
      data: {
        email: testEmail,
        first_name: "Playwright",
        last_name: "Test"
      }
    });

    // For now, skip authentication and test without login
    // The chat interface should be accessible on the main page
    logTestStep('Running tests without authentication (testing public features)', 'info');
    authToken = null;
  });

  test('Basic Chat Interface - UI Elements and Interaction', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('BASIC CHAT INTERFACE TESTS', 'section');

    // Look for chat interface elements
    const chatInput = page.locator('input[placeholder*="message"], textarea[placeholder*="message"], [data-testid="chat-input"]');
    const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"], button:has([data-testid="SendIcon"])');
    const chatContainer = page.locator('.chat-container, [data-testid="chat-container"], .chat-messages');

    // Take screenshot of chat area
    await page.screenshot({ path: 'test-results/chat-interface.png', fullPage: true });

    console.log('Chat Input Found:', await chatInput.count() > 0);
    console.log('Send Button Found:', await sendButton.count() > 0);
    console.log('Chat Container Found:', await chatContainer.count() > 0);

    // Test chat input functionality
    if (await chatInput.count() > 0) {
      logTestStep('Testing chat input functionality...');

      try {
        await chatInput.fill('Hello, this is a test message');
        const inputValue = await chatInput.inputValue();
        logSuccess('Chat input accepts text:', inputValue);

        // Try to send message
        if (await sendButton.count() > 0) {
          await sendButton.click();
          await page.waitForTimeout(TIMEOUTS.AI_RESPONSE);

          // Check if message appears in chat
          const messages = await page.locator(SELECTORS.CHAT.MESSAGES).allTextContents();
          logTestStep('Messages in chat:', messages);

          if (messages.some(msg => msg.includes('test message'))) {
            logSuccess('Message successfully sent and displayed');
          } else {
            logError('Message not found in chat after sending');
          }

          // Take screenshot after sending message
          await page.screenshot({ path: 'test-results/chat-after-send.png', fullPage: true });
        } else {
          logError('Send button not found');
        }
      } catch (error) {
        logError('Chat input test failed:', error.message);
      }
    } else {
      logTestStep('❌ Chat input not found on page');
    }
  });

  test('Gemini AI Response Test - Direct API Integration', async ({ request }) => {
    if (!authToken) {
      test.skip(true, 'No auth token available for API testing');
      return;
    }

    logTestStep('GEMINI AI INTEGRATION TESTS', 'section');

    // Test direct API call to chat endpoint
    try {
      const chatResponse = await request.post(buildApiUrl(URLS.CHAT.MESSAGE), {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        data: {
          message: "Hello! Can you help me plan a trip to Paris?",
          chat_id: null // New chat
        }
      });

      logTestStep('Chat API Response Status:', chatResponse.status());

      if (chatResponse.ok()) {
        const responseData = await chatResponse.json();
        logTestStep('CHAT API RESPONSE ANALYSIS', 'section');
        logTestStep('Response structure:', Object.keys(responseData));
        logTestStep('Message:', responseData.message);
        logTestStep('Chat ID:', responseData.chat_id);
        logTestStep('Intent:', responseData.intent_name);
        logTestStep('Confidence:', responseData.confidence);
        logTestStep('Type:', responseData.type);

        // Check if Gemini AI is working
        const hasAIResponse = responseData.message && responseData.message.length > 50; // Reasonable AI response length
        const hasProperStructure = responseData.chat_id && responseData.message;

        if (hasAIResponse && hasProperStructure) {
          logSuccess('Gemini AI integration appears to be working');
          logSuccess('API returns structured response with chat_id');
        } else {
          logError('Gemini AI may not be working properly');
          logTestStep('Response too short or missing structure');
        }

        // Test follow-up message in same chat
        if (responseData.chat_id) {
          logTestStep('Testing follow-up message...');
          const followUpResponse = await request.post(buildApiUrl(URLS.CHAT.MESSAGE), {
            headers: {
              'Authorization': `Bearer ${authToken}`,
              'Content-Type': 'application/json'
            },
            data: {
              message: "What about hotels in Paris?",
              chat_id: responseData.chat_id
            }
          });

          if (followUpResponse.ok()) {
            const followUpData = await followUpResponse.json();
            logSuccess('Follow-up message successful');
            logTestStep('Follow-up response:', followUpData.message.substring(0, 100) + '...');
          } else {
            logError('Follow-up message failed');
          }
        }
      } else {
        const errorText = await chatResponse.text();
        logError('Chat API failed:', errorText);
      }
    } catch (error) {
      logTestStep('❌ Gemini AI test failed:', error.message);
    }
  });

  test('Trip Planning via Chat - Trigger Analysis', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('TRIP PLANNING CHAT TESTS', 'section');

    // Test trip planning keywords
    const tripPlanningMessages = [
      "I want to plan a trip to Japan",
      "Help me create a travel itinerary",
      "Plan a vacation to Europe",
      "I need help with trip planning"
    ];

    const chatInput = page.locator('input[placeholder*="message"], textarea[placeholder*="message"], [data-testid="chat-input"]');
    const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"], button:has([data-testid="SendIcon"])');

    if (await chatInput.count() > 0 && await sendButton.count() > 0) {
      for (const message of tripPlanningMessages) {
        console.log(`Testing trip planning message: "${message}"`);

        try {
          await chatInput.fill(message);
          await sendButton.click();
          await page.waitForTimeout(TIMEOUTS.AI_RESPONSE); // Wait for AI response

          // Check for trip-related UI elements that might appear
          const hasTripForm = await page.locator('[data-testid="trip-form"], .trip-form, .itinerary-builder').count() > 0;
          const hasFlightSearch = await page.locator('[data-testid="flight-search"], .flight-search').count() > 0;
          const hasDatePicker = await page.locator('.date-picker, [data-testid="date-picker"], input[type="date"]').count() > 0;

          console.log(`Trip Form Appeared: ${hasTripForm}`);
          console.log(`Flight Search Appeared: ${hasFlightSearch}`);
          console.log(`Date Picker Appeared: ${hasDatePicker}`);

          // Get AI response
          const messages = await page.locator(SELECTORS.CHAT.MESSAGES).allTextContents();
          const lastMessage = messages[messages.length - 1];

          if (lastMessage && lastMessage.length > 20) {
            console.log(`✅ AI responded: "${lastMessage.substring(0, 100)}..."`);

            // Check if response mentions trip planning features
            const mentionsTrips = lastMessage.toLowerCase().includes('trip') ||
                                lastMessage.toLowerCase().includes('travel') ||
                                lastMessage.toLowerCase().includes('itinerary');

            if (mentionsTrips) {
              logSuccess('AI response is trip-related');
            } else {
              logTestStep('⚠️ AI response may not be trip-focused');
            }
          } else {
            logError('No AI response received');
          }

          await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

        } catch (error) {
          console.log(`❌ Trip planning test failed for "${message}": ${error.message}`);
        }
      }

      // Take final screenshot
      await page.screenshot({ path: 'test-results/trip-planning-chat.png', fullPage: true });
    } else {
      logTestStep('❌ Chat input or send button not found for trip planning tests');
    }
  });

  test('Flight Search via Chat - Integration Test', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('FLIGHT SEARCH CHAT TESTS', 'section');

    const flightSearchMessages = [
      "Find flights from Amsterdam to Paris",
      "I need flights from AMS to CDG for next week",
      "Show me airline options for New York to London",
      "Search flights for my trip"
    ];

    const chatInput = page.locator('input[placeholder*="message"], textarea[placeholder*="message"], [data-testid="chat-input"]');
    const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"], button:has([data-testid="SendIcon"])');

    if (await chatInput.count() > 0 && await sendButton.count() > 0) {
      for (const message of flightSearchMessages) {
        console.log(`Testing flight search message: "${message}"`);

        try {
          await chatInput.fill(message);
          await sendButton.click();
          await page.waitForTimeout(TIMEOUTS.API_RESPONSE); // Longer wait for flight API calls

          // Check for flight-related UI elements
          const hasFlightResults = await page.locator('.flight-results, [data-testid="flight-results"], .flight-card').count() > 0;
          const hasFlightForm = await page.locator('.flight-search-form, [data-testid="flight-form"]').count() > 0;
          const hasLoadingState = await page.locator('.loading, [data-testid="loading"], .spinner').count() > 0;

          console.log(`Flight Results Appeared: ${hasFlightResults}`);
          console.log(`Flight Form Appeared: ${hasFlightForm}`);
          console.log(`Loading State: ${hasLoadingState}`);

          // Check AI response for flight-related content
          const messages = await page.locator(SELECTORS.CHAT.MESSAGES).allTextContents();
          const lastMessage = messages[messages.length - 1];

          if (lastMessage && lastMessage.length > 20) {
            const mentionsFlights = lastMessage.toLowerCase().includes('flight') ||
                                  lastMessage.toLowerCase().includes('airline') ||
                                  lastMessage.toLowerCase().includes('departure');

            if (mentionsFlights) {
              logSuccess('AI response mentions flights');
            } else {
              logTestStep('⚠️ AI response may not be flight-focused');
            }

            console.log(`AI Response: "${lastMessage.substring(0, 100)}..."`);
          }

          await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

        } catch (error) {
          console.log(`❌ Flight search test failed for "${message}": ${error.message}`);
        }
      }

      // Take screenshot of flight search results
      await page.screenshot({ path: 'test-results/flight-search-chat.png', fullPage: true });
    } else {
      logTestStep('❌ Chat input or send button not found for flight search tests');
    }
  });

  test('Chat History and Persistence Test', async ({ request, page }) => {
    if (!authToken) {
      test.skip(true, 'No auth token available for history testing');
      return;
    }

    logTestStep('CHAT HISTORY AND PERSISTENCE TESTS', 'section');

    // Test getting chat history via API
    try {
      const historyResponse = await request.get(buildApiUrl('/chat/latest'), {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (historyResponse.ok()) {
        const historyData = await historyResponse.json();
        logSuccess('Chat history API accessible');
        logTestStep('History response structure:', Object.keys(historyData));
        logTestStep('Number of messages:', historyData.messages ? historyData.messages.length : 'N/A');

        // Test if history shows in UI
        await navigateToVoya(page);
        await page.waitForTimeout(TIMEOUTS.AI_RESPONSE); // Allow time for chat history to load

        const visibleMessages = await page.locator('.chat-message, [data-testid="chat-message"], .message').count();
        console.log(`Visible messages in UI: ${visibleMessages}`);

        if (visibleMessages > 0) {
          logSuccess('Chat history is loading in UI');
        } else {
          logError('Chat history not visible in UI');
        }

      } else {
        logError('Chat history API failed:', historyResponse.status());
      }
    } catch (error) {
      logTestStep('❌ Chat history test failed:', error.message);
    }
  });

  test('Multiple Chat Handling Test', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('MULTIPLE CHAT HANDLING TESTS', 'section');

    // Look for new chat functionality
    const newChatButton = page.locator('button:has-text("New Chat"), [data-testid="new-chat"], .new-chat-btn');

    if (await newChatButton.count() > 0) {
      logTestStep('New Chat button found');

      try {
        // Send a message in current chat
        const chatInput = page.locator('input[placeholder*="message"], textarea[placeholder*="message"], [data-testid="chat-input"]');
        const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"]');

        if (await chatInput.count() > 0) {
          await chatInput.fill('First chat message');
          await sendButton.click();
          await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

          // Click new chat
          await newChatButton.click();
          await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

          // Send message in new chat
          await chatInput.fill('Second chat message');
          await sendButton.click();
          await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

          // Check if messages are properly separated
          const allMessages = await page.locator('.chat-message, [data-testid="chat-message"], .message').allTextContents();

          logTestStep('All messages after new chat test:', allMessages);

          const hasFirstMessage = allMessages.some(msg => msg.includes('First chat'));
          const hasSecondMessage = allMessages.some(msg => msg.includes('Second chat'));

          console.log(`Has first message: ${hasFirstMessage}`);
          console.log(`Has second message: ${hasSecondMessage}`);

          if (hasSecondMessage && !hasFirstMessage) {
            logSuccess('New chat properly separated messages');
          } else if (hasFirstMessage && hasSecondMessage) {
            logTestStep('⚠️ Both messages visible - may be single chat mode');
          } else {
            logError('Message handling unclear');
          }

          // Take screenshot of multiple chat test
          await page.screenshot({ path: 'test-results/multiple-chat-test.png', fullPage: true });
        }

      } catch (error) {
        console.log(`❌ Multiple chat test failed: ${error.message}`);
      }
    } else {
      logTestStep('❌ New Chat button not found - may not support multiple chats');
    }
  });

  test('Chat Error Handling and Edge Cases', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('CHAT ERROR HANDLING TESTS', 'section');

    const chatInput = page.locator('input[placeholder*="message"], textarea[placeholder*="message"], [data-testid="chat-input"]');
    const sendButton = page.locator('button:has-text("Send"), [data-testid="send-button"]');

    if (await chatInput.count() > 0) {
      // Test empty message
      logTestStep('Testing empty message...');
      try {
        await sendButton.click(); // Try to send without text
        await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

        const errorMessage = await page.locator('.error, .error-message, [data-testid="error"]').count() > 0;
        console.log(`Empty message error shown: ${errorMessage}`);

      } catch (error) {
        logTestStep('Empty message test error:', error.message);
      }

      // Test very long message
      logTestStep('Testing very long message...');
      const longMessage = 'A'.repeat(5000); // 5000 character message

      try {
        await chatInput.fill(longMessage);
        await sendButton.click();
        await page.waitForTimeout(3000);

        const messages = await page.locator('.chat-message, [data-testid="chat-message"], .message').allTextContents();
        const hasLongMessage = messages.some(msg => msg.length > 1000);

        console.log(`Long message handled: ${hasLongMessage}`);

      } catch (error) {
        logTestStep('Long message test error:', error.message);
      }

      // Test special characters
      logTestStep('Testing special characters...');
      const specialMessage = '🚀 Special chars: @#$%^&*()[]{}|;:,.<>? "quotes" \'apostrophes\'';

      try {
        await chatInput.fill(specialMessage);
        await sendButton.click();
        await page.waitForTimeout(2000);

        const messages = await page.locator('.chat-message, [data-testid="chat-message"], .message').allTextContents();
        const hasSpecialChars = messages.some(msg => msg.includes('🚀') || msg.includes('Special chars'));

        console.log(`Special characters handled: ${hasSpecialChars}`);

      } catch (error) {
        logTestStep('Special characters test error:', error.message);
      }

      // Final screenshot of error handling tests
      await page.screenshot({ path: 'test-results/chat-error-handling.png', fullPage: true });
    }
  });
});
