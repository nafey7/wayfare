/**
 * Navigation and Header Diagnostic Tests
 *
 * Purpose: Test navigation functionality and identify non-functional elements including:
 * - "How to Use" button functionality
 * - "Likes" button functionality
 * - "New Chat" button functionality
 * - Navigation menu interactions
 * - Header button responses and redirects
 */

import { test, expect } from '@playwright/test';
import { URLS, SELECTORS, TIMEOUTS, generateTestUser, buildApiUrl, buildFrontendUrl } from '../utils/constants.js';
import { createApiClient } from '../utils/api-client.js';
import { navigateToVoya, navigateToApp } from '../helpers/navigation-helpers.js';
import { logTestStep, logSuccess, logError } from '../helpers/debug-helpers.js';

test.describe('Navigation and Header Diagnostics', () => {
  let authToken;

  test.beforeAll(async ({ request }) => {
    // Login to get auth token for authenticated tests
    const loginResponse = await request.post(buildApiUrl(URLS.AUTH.LOGIN), {
      data: {
        email: "roel@myvoya.ai",
        password: "VoyaTest123!"
      }
    });

    if (loginResponse.ok()) {
      const loginData = await loginResponse.json();
      authToken = loginData.access_token;
    } else {
      logTestStep('Login failed, will test with unauthenticated user');
    }
  });

  test('Main Navigation - Button Functionality Test', async ({ page }) => {
    await navigateToVoya(page);

    // Take screenshot of main page
    await page.screenshot({
      path: 'test-results/main-navigation.png',
      fullPage: true
    });

    logTestStep('MAIN NAVIGATION BUTTON TESTS', 'section');

    // Test "How to Use" button
    const howToUseButton = page.locator('button:has-text("How to Use"), a:has-text("How to Use"), [data-testid="how-to-use"]');
    if (await howToUseButton.count() > 0) {
      logTestStep('How to Use button found');

      // Check if clickable
      const isEnabled = await howToUseButton.isEnabled();
      const hasHref = await howToUseButton.getAttribute('href');
      const hasOnClick = await howToUseButton.getAttribute('onclick');

      console.log(`How to Use - Enabled: ${isEnabled}, HasHref: ${hasHref}, HasOnClick: ${hasOnClick !== null}`);

      // Try clicking
      try {
        await howToUseButton.click({ timeout: 3000 });
        await page.waitForTimeout(2000);

        // Check if URL changed or modal opened
        const currentUrl = page.url();
        const hasModal = await page.locator('.MuiModal-root, .modal, [role="dialog"]').count() > 0;

        logTestStep(`How to Use - After click: URL=${currentUrl}, ModalOpen=${hasModal}`);

        if (currentUrl === `${URLS.FRONTEND}/voya` && !hasModal) {
          logTestStep('❌ How to Use button click had no effect');
        } else {
          logTestStep('✅ How to Use button appears to work');
        }
      } catch (error) {
        logError(`How to Use button click failed: ${error.message}`);
      }
    } else {
      logTestStep('❌ How to Use button not found');
    }

    // Test "Likes" button
    const likesButton = page.locator('button:has-text("Likes"), a:has-text("Likes"), [data-testid="likes"]');
    if (await likesButton.count() > 0) {
      logTestStep('Likes button found');

      const isEnabled = await likesButton.isEnabled();
      const hasHref = await likesButton.getAttribute('href');

      console.log(`Likes - Enabled: ${isEnabled}, HasHref: ${hasHref}`);

      try {
        const beforeUrl = page.url();
        await likesButton.click({ timeout: 3000 });
        await page.waitForTimeout(2000);

        const afterUrl = page.url();
        const hasModal = await page.locator('.MuiModal-root, .modal, [role="dialog"]').count() > 0;

        logTestStep(`Likes - Before: ${beforeUrl}, After: ${afterUrl}, ModalOpen: ${hasModal}`);

        if (beforeUrl === afterUrl && !hasModal) {
          logTestStep('❌ Likes button click had no effect');
        } else {
          logTestStep('✅ Likes button appears to work');
        }
      } catch (error) {
        logError(`Likes button click failed: ${error.message}`);
      }
    } else {
      logTestStep('❌ Likes button not found');
    }

    // Test "New Chat" button
    const newChatButton = page.locator('button:has-text("New Chat"), a:has-text("New Chat"), [data-testid="new-chat"]');
    if (await newChatButton.count() > 0) {
      logTestStep('New Chat button found');

      const isEnabled = await newChatButton.isEnabled();

      console.log(`New Chat - Enabled: ${isEnabled}`);

      try {
        const beforeUrl = page.url();
        await newChatButton.click({ timeout: 3000 });
        await page.waitForTimeout(2000);

        const afterUrl = page.url();
        const hasChatInterface = await page.locator('.chat-interface, [data-testid="chat"], .MuiTextField-root').count() > 0;

        logTestStep(`New Chat - Before: ${beforeUrl}, After: ${afterUrl}, ChatVisible: ${hasChatInterface}`);

        if (beforeUrl === afterUrl && !hasChatInterface) {
          logTestStep('❌ New Chat button click had no effect');
        } else {
          logTestStep('✅ New Chat button appears to work');
        }
      } catch (error) {
        logError(`New Chat button click failed: ${error.message}`);
      }
    } else {
      logTestStep('❌ New Chat button not found');
    }
  });

  test('Sidebar Navigation - Profile and Menu Tests', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('SIDEBAR NAVIGATION TESTS', 'section');

    // Look for sidebar or navigation menu
    const sidebar = page.locator('.sidebar, [data-testid="sidebar"], nav');
    const hamburgerMenu = page.locator('button:has([data-testid="MenuIcon"]), .hamburger-menu, button:has-text("☰")');

    if (await sidebar.count() > 0) {
      logTestStep('Sidebar found');
      await sidebar.screenshot({ path: 'test-results/sidebar.png' });
    }

    if (await hamburgerMenu.count() > 0) {
      logTestStep('Hamburger menu found');
      try {
        await hamburgerMenu.click();
        await page.waitForTimeout(1000);

        // Take screenshot after opening menu
        await page.screenshot({ path: 'test-results/menu-opened.png' });

        logTestStep('✅ Hamburger menu opened successfully');
      } catch (error) {
        logError(`Hamburger menu click failed: ${error.message}`);
      }
    }

    // Test Profile navigation
    const profileLink = page.locator('a:has-text("Profile"), button:has-text("Profile"), [data-testid="profile-link"]');
    if (await profileLink.count() > 0) {
      logTestStep('Profile link found');

      try {
        await profileLink.click();
        await page.waitForURL('**/profile', { timeout: 5000 });

        const profileUrl = page.url();
        logSuccess(`Profile navigation successful: ${profileUrl}`);

        // Take screenshot of profile page
        await page.screenshot({ path: 'test-results/profile-page.png', fullPage: true });

      } catch (error) {
        logError(`Profile navigation failed: ${error.message}`);
      }
    } else {
      logTestStep('❌ Profile link not found');
    }
  });

  test('Header Actions - Sign In and User Menu', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('HEADER ACTIONS TESTS', 'section');

    // Test sign-in button for unauthenticated users
    const signInButton = page.locator('button:has-text("Sign In"), a:has-text("Sign In"), [data-testid="sign-in"]');
    if (await signInButton.count() > 0) {
      logTestStep('Sign In button found');

      try {
        await signInButton.click();
        await page.waitForTimeout(2000);

        // Look for login modal or redirect
        const hasAuthModal = await page.locator('.auth-modal, [data-testid="auth-dialog"], .MuiDialog-root').count() > 0;
        const currentUrl = page.url();

        logTestStep(`Sign In - URL: ${currentUrl}, AuthModal: ${hasAuthModal}`);

        if (hasAuthModal) {
          logTestStep('✅ Sign In button opened authentication modal');
          await page.screenshot({ path: 'test-results/auth-modal.png' });
        } else {
          logTestStep('❌ Sign In button click had no visible effect');
        }

      } catch (error) {
        logError(`Sign In button click failed: ${error.message}`);
      }
    }

    // Test user menu/avatar for authenticated users
    const userAvatar = page.locator('.user-avatar, [data-testid="user-avatar"], .MuiAvatar-root');
    const userMenuButton = page.locator('button:has(.MuiAvatar-root), [data-testid="user-menu"]');

    if (await userAvatar.count() > 0 || await userMenuButton.count() > 0) {
      logTestStep('User menu/avatar found');

      const menuTrigger = await userMenuButton.count() > 0 ? userMenuButton : userAvatar;

      try {
        await menuTrigger.click();
        await page.waitForTimeout(1000);

        // Look for dropdown menu
        const hasDropdown = await page.locator('.user-dropdown, [data-testid="user-menu-dropdown"], .MuiMenu-root').count() > 0;

        if (hasDropdown) {
          logTestStep('✅ User menu opened successfully');
          await page.screenshot({ path: 'test-results/user-menu.png' });

          // Test menu items
          const menuItems = await page.locator('.MuiMenuItem-root, .dropdown-item').allTextContents();
          logTestStep('Menu items found:', menuItems);

        } else {
          logTestStep('❌ User menu click had no visible effect');
        }

      } catch (error) {
        logError(`User menu click failed: ${error.message}`);
      }
    }
  });

  test('Trip Planning Navigation - "Plan New Trip" Button', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('TRIP PLANNING NAVIGATION TESTS', 'section');

    // Find "Plan New Trip" button
    const planTripButton = page.locator('button:has-text("Plan New Trip"), a:has-text("Plan New Trip"), [data-testid="plan-trip"]');

    if (await planTripButton.count() > 0) {
      logTestStep('Plan New Trip button found');

      // Take screenshot before clicking
      await page.screenshot({ path: 'test-results/before-plan-trip.png', fullPage: true });

      try {
        await planTripButton.click();
        await page.waitForTimeout(3000);

        // Check what happened after click
        const currentUrl = page.url();
        const hasChatMessage = await page.locator('.chat-message, [data-testid="chat-message"]').count() > 0;
        const hasNewPage = currentUrl !== `${URLS.FRONTEND}/voya`;

        logTestStep(`Plan Trip - URL: ${currentUrl}, NewPage: ${hasNewPage}, ChatMessage: ${hasChatMessage}`);

        // Take screenshot after clicking
        await page.screenshot({ path: 'test-results/after-plan-trip.png', fullPage: true });

        if (hasChatMessage) {
          // Extract chat messages to see what was sent
          const messages = await page.locator('.chat-message, [data-testid="chat-message"]').allTextContents();
          logTestStep('Chat messages after Plan Trip click:', messages);
          logTestStep('✅ Plan Trip button triggered chat interaction');
        } else if (hasNewPage) {
          logTestStep('✅ Plan Trip button navigated to new page');
        } else {
          logTestStep('❌ Plan Trip button click had no visible effect');
        }

      } catch (error) {
        logError(`Plan Trip button click failed: ${error.message}`);
      }
    } else {
      logTestStep('❌ Plan New Trip button not found');
    }
  });

  test('Dream Destinations - View Details Functionality', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('DREAM DESTINATIONS TESTS', 'section');

    // Look for dream destinations section
    const destinationsSection = page.locator('text=Dream Destinations').locator('..');

    if (await destinationsSection.count() > 0) {
      logTestStep('Dream Destinations section found');

      // Take screenshot of destinations
      await destinationsSection.screenshot({ path: 'test-results/dream-destinations.png' });

      // Find "View Details" buttons
      const viewDetailsButtons = page.locator('button:has-text("View Details"), a:has-text("View Details"), [data-testid="view-details"]');
      const buttonCount = await viewDetailsButtons.count();

      console.log(`Found ${buttonCount} View Details buttons`);

      if (buttonCount > 0) {
        // Test first View Details button
        try {
          const firstButton = viewDetailsButtons.first();
          const beforeUrl = page.url();

          await firstButton.click();
          await page.waitForTimeout(2000);

          const afterUrl = page.url();
          const hasModal = await page.locator('.destination-modal, [data-testid="destination-modal"], .MuiDialog-root').count() > 0;
          const hasNewPage = beforeUrl !== afterUrl;

          logTestStep(`View Details - Before: ${beforeUrl}, After: ${afterUrl}, Modal: ${hasModal}, NewPage: ${hasNewPage}`);

          if (hasModal) {
            logTestStep('✅ View Details opened modal');
            await page.screenshot({ path: 'test-results/destination-modal.png' });
          } else if (hasNewPage) {
            logTestStep('✅ View Details navigated to new page');
            await page.screenshot({ path: 'test-results/destination-page.png', fullPage: true });
          } else {
            logTestStep('❌ View Details button had no visible effect');
          }

        } catch (error) {
          logError(`View Details button click failed: ${error.message}`);
        }
      }
    } else {
      logTestStep('❌ Dream Destinations section not found');
    }
  });

  test('Travel Survey - "Start Travel Survey" Functionality', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('TRAVEL SURVEY TESTS', 'section');

    // Find "Start Travel Survey" button
    const surveyButton = page.locator('button:has-text("Start Travel Survey"), a:has-text("Start Travel Survey"), [data-testid="travel-survey"]');

    if (await surveyButton.count() > 0) {
      logTestStep('Start Travel Survey button found');

      try {
        await surveyButton.click();
        await page.waitForTimeout(3000);

        // Check if it triggered chat message
        const hasChatMessage = await page.locator('.chat-message, [data-testid="chat-message"]').count() > 0;
        const currentUrl = page.url();
        const hasNewChat = currentUrl.includes('/chat') || currentUrl.includes('/survey');

        logTestStep(`Travel Survey - URL: ${currentUrl}, NewChat: ${hasNewChat}, ChatMessage: ${hasChatMessage}`);

        if (hasChatMessage) {
          // Extract chat messages
          const messages = await page.locator('.chat-message, [data-testid="chat-message"]').allTextContents();
          logTestStep('Chat messages after Survey click:', messages);
          logTestStep('✅ Travel Survey triggered chat interaction');

          // Take screenshot of chat
          await page.screenshot({ path: 'test-results/survey-chat.png', fullPage: true });
        } else if (hasNewChat) {
          logTestStep('✅ Travel Survey opened new chat/survey interface');
        } else {
          logTestStep('❌ Travel Survey button had no visible effect');
        }

      } catch (error) {
        logError(`Travel Survey button click failed: ${error.message}`);
      }
    } else {
      logTestStep('❌ Start Travel Survey button not found');
    }
  });

  test('Route Integrity - 404 and Missing Pages Test', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('ROUTE INTEGRITY TESTS', 'section');

    // Test "Explore More" link (reported 404 issue)
    const exploreMoreButton = page.locator('button:has-text("Explore More"), a:has-text("Explore More"), [data-testid="explore-more"]');

    if (await exploreMoreButton.count() > 0) {
      logTestStep('Explore More button found');

      try {
        await exploreMoreButton.click();
        await page.waitForTimeout(2000);

        const currentUrl = page.url();
        logTestStep(`Explore More clicked - URL: ${currentUrl}`);

        // Check if we're on a 404 page
        const has404Content = await page.locator('text=404, text=Not Found, text=Page not found').count() > 0;
        const hasErrorContent = await page.locator('.error-page, [data-testid="404"], .not-found').count() > 0;

        logTestStep(`404 Content: ${has404Content}, Error Page: ${hasErrorContent}`);

        if (currentUrl.includes('/inspirations')) {
          logTestStep('❌ CONFIRMED: Explore More links to /inspirations route (404)');
        }

        if (has404Content || hasErrorContent) {
          logTestStep('❌ Explore More button leads to 404/error page');
        } else {
          logTestStep('✅ Explore More button works correctly');
        }

        // Take screenshot of the result
        await page.screenshot({ path: 'test-results/explore-more-result.png', fullPage: true });

      } catch (error) {
        logError(`Explore More button test failed: ${error.message}`);
      }
    } else {
      logTestStep('❌ Explore More button not found');
    }

    // Test other common routes that might be broken
    const routesToTest = [
      '/voya/inspirations',
      '/voya/trips',
      '/voya/settings',
      '/voya/help',
      '/voya/about'
    ];

    console.log('Testing common routes for 404s...');

    for (const route of routesToTest) {
      try {
        await page.goto(`${URLS.FRONTEND}${route}`);
        await page.waitForTimeout(1000);

        const has404 = await page.locator('text=404, text=Not Found, text=Page not found').count() > 0;
        const currentUrl = page.url();

        logTestStep(`Route ${route} - URL: ${currentUrl}, 404: ${has404}`);

        if (has404) {
          logError(`Route ${route} returns 404`);
        } else if (currentUrl.includes(route.replace('/voya', ''))) {
          logSuccess(`Route ${route} accessible`);
        } else {
          logTestStep(`⚠️ Route ${route} redirected to ${currentUrl}`);
        }

      } catch (error) {
        logError(`Error testing route ${route}: ${error.message}`);
      }
    }
  });
});
