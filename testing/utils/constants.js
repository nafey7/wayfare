/**
 * Testing Constants
 *
 * Centralized constants for all Playwright tests
 * Following Playwright best practices for maintainable test architecture
 */

// =============================================================================
// SERVICE URLS
// =============================================================================

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
 * NOTE: This resolution logic is duplicated in playwright.config.js. Keep them in sync.
 */
const TEST_ENV =
  process.env.TEST_ENV ||
  (process.env.NODE_ENV === 'testing' || process.env.ENVIRONMENT === 'testing'
    ? 'local'
    : 'dev');

const URL_CONFIG = {
  local: {
    FRONTEND: 'http://localhost:8001',
    BACKEND: 'http://localhost:8001',
    API_BASE: 'http://localhost:8001/api',
    MAILHOG: 'http://localhost:8026',
  },
  staging: {
    FRONTEND: 'https://staging.myvoya.ai',
    BACKEND: 'https://staging.myvoya.ai',
    API_BASE: 'https://staging.myvoya.ai/api',
    MAILHOG: null, // staging uses real email service, no MailHog
  },
  dev: {
    FRONTEND: 'http://localhost:3002',
    BACKEND: 'http://localhost:8000',
    API_BASE: 'http://localhost:8000/api',
    MAILHOG: 'http://localhost:8025',
  },
};

const envUrls = URL_CONFIG[TEST_ENV] || URL_CONFIG.local;

export const TEST_ENVIRONMENT = TEST_ENV;
export const IS_STAGING = TEST_ENV === 'staging';
export const IS_LOCAL = TEST_ENV === 'local';

export const URLS = {
  // Core Services (resolved per environment)
  FRONTEND: envUrls.FRONTEND,
  BACKEND: envUrls.BACKEND,
  API_BASE: envUrls.API_BASE,
  MAILHOG: envUrls.MAILHOG,

  // Frontend Routes
  VOYA_HOME: '/voya',
  PROFILE: '/voya/profile',
  RESET_PASSWORD: '/reset-password',

  // API Endpoints
  AUTH: {
    CHECK_EMAIL: '/api/auth/check-email',
    REGISTER: '/api/auth/register',
    LOGIN: '/api/auth/login',
    LOGOUT: '/api/auth/logout',
    FORGOT_PASSWORD: '/api/auth/forgot-password',
    RESET_PASSWORD: '/api/auth/reset-password',
    GOOGLE_AUTH: '/api/auth/google/authenticate',
    CONFIG_GOOGLE: '/api/auth/config/google',
    COMPLETE_REGISTRATION: '/api/auth/complete-registration',
    VALIDATE_RESET_TOKEN: '/api/auth/validate-reset-token',
    REFRESH: '/api/auth/refresh'
  },

  CHAT: {
    MESSAGE: '/api/chat/message'
  },

  HEALTH: '/health'
};

// =============================================================================
// TIMEOUTS & WAITS
// =============================================================================

export const TIMEOUTS = {
  // Page loading
  PAGE_LOAD: 15000,
  FRONTEND_LOAD_TIMEOUT: 10000,

  // UI interactions
  ELEMENT_VISIBLE: 10000,
  FORM_SUBMIT: 5000,
  MODAL_APPEAR: 10000,

  // API responses
  API_RESPONSE: 30000,
  AI_RESPONSE: 5000,  // AI typically responds in 1-3s, 5s provides adequate buffer
  EMAIL_DELIVERY: 30000,

  // Chat-driven AI workflows on staging — these include the full backend
  // pipeline (intent recognition → tool calls → AI summary). Observed
  // against staging.myvoya.ai 2026-05-04/05; values are ceilings well
  // above the typical-case latency.
  CHAT_FLIGHT_RESPONSE: 30000,     // typical 10-15s
  CHAT_HOTEL_RESPONSE: 90000,      // typical 50-80s (Geocoding + 1000+ inventory)
  CHAT_ITINERARY_RESPONSE: 180000, // typical 100-150s (multi-day plan generation)
  // Time for the final dataLayer event to settle after the SPA navigates
  // post-bot-response (e.g. flight_search_results_shown / hotel_search_results_shown
  // / itinerary_results_shown). Walkthroughs use this between the URL match
  // and the panel-mount event.
  CHAT_RESULT_SETTLE: 15000,

  // Brief waits (try to avoid these)
  BRIEF: 1000,
  SHORT: 2000,
  SHORT_WAIT: 2000,  // Alias for SHORT
  MEDIUM: 3000
};

// =============================================================================
// TEST DATA
// =============================================================================

export const TEST_DATA = {
  // Test users
  USERS: {
    NEW_USER: {
      email: 'new-user@example.com',
      firstName: 'Test',
      lastName: 'User',
      password: 'TestPassword123!'
    },

    EXISTING_USER: {
      email: 'existing@example.com',
      firstName: 'Existing',
      lastName: 'User',
      password: 'ExistingPassword123!'
    },

    INVALID_CREDENTIALS: {
      email: 'nonexistent@example.com',
      password: 'wrongpassword'
    }
  },

  // Test inputs
  INVALID_EMAIL: 'invalid-email',
  WEAK_PASSWORD: '123',

  // Mock tokens
  MOCK_JWT_TOKEN: 'mock-jwt-token'
};

// =============================================================================
// SELECTORS
// =============================================================================

export const SELECTORS = {
  // Navigation
  // Header CTA renamed from "Sign In" → "Log in" with the UnifiedHeader migration.
  // In-modal submit button (AuthModalPage) is still "Sign In" — those are different buttons.
  SIGN_IN_BUTTON: 'text=Log in',

  // Navigation elements (based on actual frontend)
  NAVIGATION: {
    PROFILE: 'text=Profile',
    HAMBURGER_MENU: 'button:has([data-testid="MenuIcon"]), button:has(svg), iconbutton:has(menuicon)',
    USER_MENU: '[data-testid="user-menu"]',
    // Profile-specific selectors
    PROFILE_BANNER: '[class*="ProfileBanner"], .profile-banner',
    PROFILE_AVATAR: 'img[alt="User Profile Pic"], avatar',
    PROFILE_NAME: 'h4:has-text(" ")', // Profile name display
    ACCOUNT_INFO_BUTTON: 'menuitem:has-text("Account & Billing Info")',
    MORE_VERT_BUTTON: 'iconbutton:has([data-testid="MoreVertIcon"])'
  },

  // Forms
  EMAIL_INPUT: 'input[placeholder*="Email Address"], input[name="email"], input[type="email"]',
  PASSWORD_INPUT: 'input[type="password"], input[name="password"]',
  CONTINUE_BUTTON: 'button:has-text("CONTINUE"), button:has-text("Continue")',

  // Authentication modals (based on event-driven auth)
  VERIFICATION_MODAL: 'text=Verification Required',
  AUTH_MODAL: '[role="dialog"], .MuiDialog-root',

  // Registration elements (note: registration may be part of auth modal)
  REGISTRATION: {
    FIRST_NAME: 'input[name="firstName"], input[name="first_name"]',
    LAST_NAME: 'input[name="lastName"], input[name="last_name"]',
    EMAIL: 'input[name="email"], input[type="email"]',
    PASSWORD: 'input[name="password"], input[type="password"]',
    CONFIRM_PASSWORD: 'input[name="confirmPassword"], input[name="confirm_password"]',
    PHONE: 'input[name="phoneNumber"], input[name="phone_number"], input[type="tel"]',
    SUBMIT: 'button[type="submit"], button:has-text("Register"), button:has-text("Create Account")'
  },

  // Chat elements (based on actual ChatBot implementation)
  CHAT: {
    INPUT: 'input[placeholder="Type your message..."], [class*="MuiInputBase"], textarea[placeholder*="message"]',
    SEND_BUTTON: 'button:has([data-testid="SendHorizonal"]), button:has-text("Send"), iconbutton:has(svg)',
    CONTAINER: '#chat-container, .chat-container',
    MESSAGES: '.chat-message-item, [data-id*="user-"], [data-id*="bot-"]',
    CHAT_BUTTON: 'button:has(img[src*="voya"]), iconbutton:has(avatar)',  // Minimized chat button
    CHAT_OPEN: '#chat-container paper'  // Full chat interface
  },

  // Auth indicators
  LOGOUT_BUTTON: '[data-testid="logout-button"], button:has-text("Logout"), button:has-text("Sign Out")',

  // Error indicators
  ERROR_MESSAGE: '.error, [data-testid*="error"], text="required", text="Please enter"',
  INVALID_EMAIL_ERROR: 'text=Invalid email'
};

// =============================================================================
// ROUTES FOR TESTING
// =============================================================================

export const TEST_ROUTES = [
  '/',
  '/voya',
  '/voya/profile',
  '/voya/trips',
  '/voya/settings',
  '/voya/inspirations',
  '/login',
  '/register',
  '/forgot-password'
];

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Build full URL for frontend routes
 */
export function buildFrontendUrl(path = '') {
  return `${URLS.FRONTEND}${path}`;
}

/**
 * Build full URL for API endpoints
 */
export function buildApiUrl(endpoint = '') {
  return `${URLS.BACKEND}${endpoint}`;
}

/**
 * Generate unique test email
 */
export function generateTestEmail(prefix = 'test') {
  const timestamp = Date.now();
  return `${prefix}-${timestamp}@example.com`;
}

/**
 * Generate test user data
 */
export function generateTestUser(overrides = {}) {
  return {
    email: generateTestEmail(),
    firstName: 'Test',
    lastName: 'User',
    password: 'TestPassword123!',
    phoneNumber: '+1234567890',
    ...overrides
  };
}
