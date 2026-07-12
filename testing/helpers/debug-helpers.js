/**
 * Debug Helpers
 *
 * Centralized debugging, logging, and development utilities
 * Replaces 100+ scattered console.log calls and wait patterns
 */

import { TIMEOUTS } from '../utils/constants.js';

// =============================================================================
// LOGGING UTILITIES
// =============================================================================

/**
 * Log test step with consistent formatting
 * Replaces scattered console.log calls throughout tests
 */
export function logTestStep(message, type = 'info') {
  const timestamp = new Date().toISOString().substr(11, 12);
  const emoji = getLogEmoji(type);
  const formatted = `[${timestamp}] ${emoji} ${message}`;

  console.log(formatted);
}

/**
 * Log test section header
 */
export function logTestSection(sectionName) {
  const separator = '='.repeat(Math.max(50, sectionName.length + 10));
  console.log(`\n${separator}`);
  console.log(`=== ${sectionName.toUpperCase()} ===`);
  console.log(`${separator}\n`);
}

/**
 * Log success message
 */
export function logSuccess(message) {
  logTestStep(message, 'success');
}

/**
 * Log error message
 */
export function logError(message, error = null) {
  logTestStep(message, 'error');
  if (error) {
    console.error('Error details:', error);
  }
}

/**
 * Log warning message
 */
export function logWarning(message) {
  logTestStep(message, 'warning');
}

/**
 * Log info message
 */
export function logInfo(message) {
  logTestStep(message, 'info');
}

/**
 * Get emoji for log type
 */
function getLogEmoji(type) {
  const emojis = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️',
    debug: '🔍',
    test: '🧪',
    navigation: '🧭',
    auth: '🔑',
    api: '🔌',
    ui: '🎭'
  };

  return emojis[type] || 'ℹ️';
}

// =============================================================================
// WAIT UTILITIES
// =============================================================================

/**
 * Wait briefly with context logging
 * Prefer explicit waits over this when possible
 */
export async function waitBriefly(page, ms = TIMEOUTS.BRIEF, reason = 'UI transition') {
  logTestStep(`Waiting ${ms}ms for ${reason}`, 'debug');
  await page.waitForTimeout(ms);
}

/**
 * Wait for network to be idle
 */
export async function waitForNetworkIdle(page, timeout = TIMEOUTS.PAGE_LOAD) {
  logTestStep('Waiting for network to be idle', 'debug');
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Wait for DOM to be ready
 */
export async function waitForDomReady(page, timeout = TIMEOUTS.PAGE_LOAD) {
  logTestStep('Waiting for DOM to be ready', 'debug');
  await page.waitForLoadState('domcontentloaded', { timeout });
}

// =============================================================================
// SCREENSHOT UTILITIES
// =============================================================================

/**
 * Take screenshot with automatic naming
 */
export async function takeScreenshot(page, name, options = {}) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `${name}-${timestamp}.png`;

  logTestStep(`Taking screenshot: ${filename}`, 'debug');

  await page.screenshot({
    path: `test-results/${filename}`,
    fullPage: true,
    ...options
  });

  return filename;
}

/**
 * Take screenshot on test failure
 */
export async function screenshotOnFailure(page, testName, error) {
  logError(`Test failed: ${testName}`, error);

  try {
    const filename = await takeScreenshot(page, `failure-${testName}`);
    logInfo(`Failure screenshot saved: ${filename}`);
  } catch (screenshotError) {
    logError('Failed to take failure screenshot', screenshotError);
  }
}

// =============================================================================
// ELEMENT DEBUGGING
// =============================================================================

/**
 * Debug element visibility and properties
 */
export async function debugElement(page, selector, name = 'element') {
  logTestStep(`Debugging ${name}: ${selector}`, 'debug');

  try {
    const element = page.locator(selector);
    const count = await element.count();

    if (count === 0) {
      logWarning(`${name} not found: ${selector}`);
      return { found: false, count: 0 };
    }

    const isVisible = await element.first().isVisible();
    const isEnabled = await element.first().isEnabled();

    logInfo(`${name} found: count=${count}, visible=${isVisible}, enabled=${isEnabled}`);

    return {
      found: true,
      count,
      isVisible,
      isEnabled,
      element
    };

  } catch (error) {
    logError(`Error debugging ${name}`, error);
    return { found: false, error: error.message };
  }
}

/**
 * Debug form fields and their values
 */
export async function debugFormField(page, selector, name = 'field') {
  const debug = await debugElement(page, selector, name);

  if (debug.found && debug.isVisible) {
    try {
      const value = await debug.element.first().inputValue();
      const placeholder = await debug.element.first().getAttribute('placeholder');

      logInfo(`${name} value: "${value}", placeholder: "${placeholder}"`);

      return { ...debug, value, placeholder };
    } catch (error) {
      logWarning(`Could not get ${name} value: ${error.message}`);
      return debug;
    }
  }

  return debug;
}

// =============================================================================
// ERROR DETECTION
// =============================================================================

/**
 * Check for common error indicators on page
 */
export async function checkForErrors(page) {
  const errorSelectors = [
    '.error',
    '[data-testid*="error"]',
    '.alert-error',
    '.text-danger',
    '.error-message',
    'text=/error|Error|ERROR/',
    'text=/failed|Failed|FAILED/'
  ];

  const errors = [];

  for (const selector of errorSelectors) {
    try {
      const elements = await page.locator(selector).all();
      for (const element of elements) {
        if (await element.isVisible()) {
          const text = await element.textContent();
          errors.push({
            selector,
            text: text?.trim(),
            element
          });
        }
      }
    } catch {
      // Ignore errors in error detection
    }
  }

  if (errors.length > 0) {
    logWarning(`Found ${errors.length} error indicator(s) on page`);
    errors.forEach((error, index) => {
      logError(`Error ${index + 1}: "${error.text}" (${error.selector})`);
    });
  }

  return errors;
}

// =============================================================================
// PERFORMANCE DEBUGGING
// =============================================================================

/**
 * Measure and log performance of an action
 */
export async function measurePerformance(actionName, actionFunction) {
  const startTime = Date.now();
  logTestStep(`Starting: ${actionName}`, 'debug');

  try {
    const result = await actionFunction();
    const duration = Date.now() - startTime;
    logSuccess(`Completed: ${actionName} (${duration}ms)`);
    return { success: true, duration, result };

  } catch (error) {
    const duration = Date.now() - startTime;
    logError(`Failed: ${actionName} (${duration}ms)`, error);
    return { success: false, duration, error };
  }
}

// =============================================================================
// CONSOLE UTILITIES
// =============================================================================

/**
 * Listen to browser console for errors
 */
export function setupConsoleLogging(page) {
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();

    if (type === 'error') {
      logError(`Browser console error: ${text}`);
    } else if (type === 'warning') {
      logWarning(`Browser console warning: ${text}`);
    }
  });

  page.on('pageerror', error => {
    logError('Browser page error', error);
  });
}

/**
 * Clear console and start fresh logging
 */
export function clearConsole() {
  console.clear();
  logTestStep('Console cleared, starting fresh test logging', 'debug');
}