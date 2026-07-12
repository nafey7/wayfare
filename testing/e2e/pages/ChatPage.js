/**
 * Chat Page Object
 *
 * Encapsulates all chatbot interactions for E2E tests
 * Provides reusable methods for sending messages and waiting for AI responses
 */

import { expect } from '@playwright/test';
import { SELECTORS, TIMEOUTS } from '../../utils/constants.js';

export class ChatPage {
  constructor(page) {
    this.page = page;

    // Selectors for chat elements based on ChatBot.jsx
    // Chat button when minimized (has Avatar with bot emoji)
    this.chatButton = page.locator('button:has([alt]), button').filter({ has: page.locator('div[class*="MuiAvatar"]') });

    // Chat container - look for visible chat widget
    this.chatContainer = page.locator('[placeholder="Type your message..."]').locator('xpath=ancestor::div[5]');

    // Input field - textbox with placeholder
    this.chatInput = page.locator('[placeholder="Type your message..."]');

    // Send button - button near the input field (in parent container)
    this.sendButton = page.locator('[placeholder="Type your message..."]/..//button').last();

    // Chat messages - look for all paragraphs in the message area
    // They appear after the bot/user images
    this.messages = page.locator('img[alt="Bot"] ~ p, img[alt="User"] ~ p, p:has-text("")');
  }

  /**
   * Open the chat interface if not already open
   */
  async openChat() {
    // Check if chat is already open
    const isOpen = await this.chatContainer.isVisible().catch(() => false);

    if (!isOpen) {
      // Click chat button to open
      await this.chatButton.click();

      // Wait for chat container to be visible
      await this.chatContainer.waitFor({ state: 'visible', timeout: TIMEOUTS.MODAL_APPEAR });
    }

    // Wait for input to be ready
    await this.chatInput.waitFor({ state: 'visible', timeout: TIMEOUTS.ELEMENT_VISIBLE });
  }

  /**
   * Send a message via chat
   * @param {string} message - The message text to send
   */
  async sendMessage(message) {
    // Ensure chat is open
    await this.openChat();

    // Fill message input and press Enter (simpler than clicking button)
    await this.chatInput.fill(message);
    await this.chatInput.press('Enter');

    // Brief wait for message to be sent
    await this.page.waitForTimeout(1000);
  }

  /**
   * Wait for AI response after sending a message
   * @param {number} timeout - Max wait time in milliseconds
   * @returns {Promise<string>} The AI response text
   */
  async waitForAIResponse(timeout = TIMEOUTS.AI_RESPONSE) {
    // Count current bot messages
    const initialBotCount = await this.page.locator('img[alt="Bot"]').count();

    try {
      // Wait for a NEW bot message to appear (count increases)
      await this.page.waitForFunction(
        (initialCount) => {
          const currentCount = document.querySelectorAll('img[alt="Bot"]').length;
          return currentCount > initialCount;
        },
        initialBotCount,
        { timeout }
      );

      // Wait a bit for the message text to be fully rendered
      await this.page.waitForTimeout(500);
    } catch (error) {
      console.error(`[ChatPage] Timeout waiting for AI response (waited ${timeout}ms)`);
      throw error;
    }

    // Get all messages now
    const allMessages = await this.messages.allTextContents();

    // Return the last message (should be AI response)
    return allMessages[allMessages.length - 1] || '';
  }

  /**
   * Send message and wait for AI response
   * @param {string} message - The message to send
   * @param {number} timeout - Max wait time for response
   * @returns {Promise<string>} The AI response text
   */
  async sendAndWaitForResponse(message, timeout = TIMEOUTS.AI_RESPONSE) {
    await this.sendMessage(message);
    return await this.waitForAIResponse(timeout);
  }

  /**
   * Get all messages in the chat
   * @returns {Promise<string[]>} Array of message texts
   */
  async getAllMessages() {
    const messages = await this.messages.allTextContents();
    return messages;
  }

  /**
   * Get the last message in chat
   * @returns {Promise<string>} Last message text
   */
  async getLastMessage() {
    const messages = await this.getAllMessages();
    return messages[messages.length - 1] || '';
  }

  /**
   * Wait for a specific text to appear in chat messages
   * @param {string|RegExp} text - Text or pattern to wait for
   * @param {number} timeout - Max wait time
   */
  async waitForMessageContaining(text, timeout = TIMEOUTS.AI_RESPONSE) {
    const textPattern = typeof text === 'string' ? new RegExp(text, 'i') : text;

    await this.page.waitForFunction(
      ({ selector, pattern }) => {
        const messages = Array.from(document.querySelectorAll(selector));
        return messages.some(msg => pattern.test(msg.textContent));
      },
      { selector: SELECTORS.CHAT.MESSAGES, pattern: textPattern },
      { timeout }
    );
  }

  /**
   * Check if chat contains a specific message
   * @param {string|RegExp} text - Text or pattern to search for
   * @returns {Promise<boolean>}
   */
  async hasMessage(text) {
    const messages = await this.getAllMessages();
    const pattern = typeof text === 'string' ? new RegExp(text, 'i') : text;
    return messages.some(msg => pattern.test(msg));
  }

  /**
   * Extract flight options from AI response
   * Looks for numbered options or flight details in messages
   * @returns {Promise<string[]>} Array of flight option texts
   */
  async getFlightOptions() {
    const messages = await this.getAllMessages();

    // Look for messages containing flight information
    const flightMessages = messages.filter(msg =>
      msg.toLowerCase().includes('option') ||
      msg.toLowerCase().includes('flight') ||
      msg.toLowerCase().includes('€') ||
      msg.toLowerCase().includes('eur')
    );

    return flightMessages;
  }

  /**
   * Select a flight option by number (e.g., "book option 1")
   * @param {number} optionNumber - The option number to select (1-based)
   */
  async selectFlightOption(optionNumber) {
    await this.sendMessage(`book option ${optionNumber}`);

    // Wait for booking process to start (URL should change to flight-booker)
    await this.page.waitForTimeout(TIMEOUTS.SHORT_WAIT);
  }

  /**
   * Close the chat interface
   */
  async closeChat() {
    const closeButton = this.page.locator('button:has-text("Close"), [data-testid="close-chat"], iconbutton:has(closeicon)');

    if (await closeButton.isVisible().catch(() => false)) {
      await closeButton.click();
      await this.chatContainer.waitFor({ state: 'hidden', timeout: TIMEOUTS.ELEMENT_VISIBLE });
    }
  }

  /**
   * Clear chat history or start new chat
   */
  async startNewChat() {
    const newChatButton = this.page.locator('button:has-text("New Chat"), [data-testid="new-chat"]');

    if (await newChatButton.isVisible().catch(() => false)) {
      await newChatButton.click();
      await this.page.waitForTimeout(TIMEOUTS.BRIEF);
    }
  }
}
