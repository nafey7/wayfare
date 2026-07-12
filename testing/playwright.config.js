import { defineConfig, devices } from '@playwright/test';
import { config } from 'dotenv';

/**
 * Test environment selection.
 *
 * TEST_ENV controls which target environment to run tests against:
 * - 'local'   (default): isolated Docker test stack at localhost:8001 (compose.test.yaml)
 * - 'staging': deployed staging environment at staging.myvoya.ai
 * - 'dev':    Vite dev server at localhost:3002
 *
 * For backwards compatibility, NODE_ENV=testing also implies TEST_ENV=local.
 *
 * NOTE: This resolution logic is duplicated in utils/constants.js. Keep them in sync.
 */
const TEST_ENV =
  process.env.TEST_ENV ||
  (process.env.NODE_ENV === 'testing' || process.env.ENVIRONMENT === 'testing' ? 'local' : 'dev');

const isLocal = TEST_ENV === 'local';
const isStaging = TEST_ENV === 'staging';

// Load environment-specific .env files
if (isLocal) {
  config({ path: '../.env.testing' });
}

// Configure base URL based on environment.
// Note: API and MailHog URLs are resolved in utils/constants.js where tests import them.
function resolveBaseUrl() {
  if (isStaging) return 'https://staging.myvoya.ai';
  if (isLocal) return process.env.FRONTEND_URL || 'http://localhost:8001';
  return 'http://localhost:3002'; // dev (Vite dev server)
}

const baseUrl = resolveBaseUrl();

// Test tagging:
// - @mock-required: tests that need the compose.test.yaml mock services
//   (skip on staging since they have no mocks; also skip on dev because
//   the dev Docker stack uses different ports than compose.test.yaml)
// - @staging: tests that only run against staging (skip on local and dev)
// - @stale: pre-agent-generated tests kept for reference but skipped everywhere
//   until they're retired or ported to the generated suite
const grepInvert =
  isStaging
    ? /@mock-required|@stale/
    : isLocal
      ? /@staging|@stale/
      : /@staging|@mock-required|@stale/;

export default defineConfig({
  testDir: '.',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 1 : 3,
  timeout: 60000,

  // Skip tests tagged for other environments
  grepInvert,

  // Global setup/teardown only runs against local (which has a test database to manage)
  globalSetup: isLocal ? './setup/global-setup.js' : undefined,
  globalTeardown: isLocal ? './setup/global-teardown.js' : undefined,

  reporter: [
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/results.xml' }],
    ['line'],
  ],

  outputDir: 'test-results/',

  use: {
    baseURL: baseUrl,
    headless: !process.env.HEADED,
    trace: 'on-first-retry',
    screenshot: 'on',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 20000,
    waitForLoadState: 'networkidle',

    extraHTTPHeaders: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      // Cloudflare bypass header for CI on staging. The matching CF custom rule
      // (`Allow CI E2E with bypass header (staging only)`) skips bot management,
      // managed WAF rules, and rate limiting when the secret matches. Required
      // because GitHub Actions runners get classified as automated by SBFM.
      // Locally / on dev the env var is unset and the header is empty (no effect).
      ...(isStaging && process.env.CF_TEST_BYPASS_TOKEN
        ? { 'X-Voya-CI-Bypass': process.env.CF_TEST_BYPASS_TOKEN }
        : {}),
    },
  },

  projects: [
    // Setup project for database initialization (local only)
    ...(isLocal
      ? [
          {
            name: 'setup',
            testMatch: /.*\.setup\.js/,
            use: { ...devices['Desktop Chrome'] },
          },
        ]
      : []),

    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
      },
      dependencies: isLocal ? ['setup'] : [],
    },
  ],

  expect: {
    timeout: 10000,
  },

  testIgnore: [
    '**/node_modules/**',
    '**/dist/**',
    '**/build/**',
    '**/manual-tests/**',
  ],
});
