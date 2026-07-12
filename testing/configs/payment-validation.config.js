/**
 * Playwright configuration for payment validation tests
 *
 * Prerequisites - Start isolated test environment BEFORE running tests:
 *   1. cd /path/to/voya-review
 *   2. docker compose -f compose.test.yaml up -d
 *   3. Wait for services to be healthy (~30 seconds)
 *
 * Run tests:
 *   cd testing
 *   npx playwright test --config=configs/payment-validation.config.js
 *
 * Cleanup:
 *   docker compose -f compose.test.yaml down -v
 *
 * Test Environment URLs:
 *   - Backend serves SPA: http://localhost:8001
 *   - Backend API: http://localhost:8001/api
 *   - Database: voya_test on port 27018
 *   - MailHog: http://localhost:8026
 */
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '../e2e/tests/flights',
  testMatch: '**/payment-validation.spec.js',

  // Test execution settings
  timeout: 60000, // 60 seconds per test
  expect: {
    timeout: 10000 // 10 seconds for assertions
  },

  // Retry failed tests once (payment tests can be flaky)
  retries: process.env.CI ? 2 : 1,

  // Run tests in parallel
  workers: process.env.CI ? 1 : 2,

  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'payment-validation-report' }],
    ['junit', { outputFile: 'payment-validation-results.xml' }],
    ['list']
  ],

  use: {
    // Base URL for testing environment
    baseURL: 'http://localhost:8001',

    // Browser settings
    headless: process.env.CI ? true : false,
    viewport: { width: 1280, height: 720 },

    // Screenshots and videos for debugging
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',

    // Extra HTTP headers
    extraHTTPHeaders: {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    }
  },

  // Test projects for different scenarios
  projects: [
    {
      name: 'payment-security-chrome',
      use: { ...require('@playwright/test').devices['Desktop Chrome'] },
      testMatch: '**/payment-validation.spec.js'
    },
    {
      name: 'payment-security-api',
      testDir: '../api',
      testMatch: '**/payment-security.spec.js',
      use: {
        // API tests don't need browser context
        headless: true
      }
    }
  ],

  // Global setup and teardown
  globalSetup: require.resolve('../setup/global-setup.js'),
  globalTeardown: require.resolve('../setup/global-teardown.js'),

  // NOTE: Tests assume services are already running via Docker Compose
  // Run: docker compose -f compose.test.yaml up -d
  // See documentation at top of file for complete setup instructions
});
