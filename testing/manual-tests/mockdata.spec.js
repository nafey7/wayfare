/**
 * Mock Data and Broken Features Documentation Tests
 *
 * Purpose: Systematically identify and document mock/dummy data and broken features including:
 * - Dummy trip entries and destinations
 * - Mock "Premium Explorer" subscription data
 * - Fake payment methods and billing information
 * - Placeholder content vs real functionality
 * - Data source analysis (hardcoded vs API-driven)
 */

import { test, expect } from '@playwright/test';
import { URLS, SELECTORS, TIMEOUTS, generateTestUser, buildApiUrl, buildFrontendUrl } from '../utils/constants.js';
import { createApiClient } from '../utils/api-client.js';
import { navigateToVoya, navigateToApp } from '../helpers/navigation-helpers.js';
import { logTestStep, logSuccess, logError } from '../helpers/debug-helpers.js';




test.describe('Mock Data and Broken Features Documentation', () => {
  let authToken;

  test.beforeAll(async ({ request }) => {
    // Login to get auth token for API calls
    const loginResponse = await request.post(buildApiUrl(URLS.AUTH.LOGIN), {
      data: {
        email: "roel@myvoya.ai",
        password: "VoyaTest123!"
      }
    });

    if (authToken = loginResponse.ok() ? (await loginResponse.json()).access_token : null) {
      logSuccess('Authentication successful for mock data analysis');
    } else {
      logError('Login failed, will analyze without authentication');
    }
  });

  test('Main Page Mock Data Analysis - Dummy Entries Detection', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('MAIN PAGE MOCK DATA ANALYSIS', 'section');

    // Take full page screenshot for reference
    await page.screenshot({ path: 'test-results/main-page-mockdata.png', fullPage: true });

    // Extract all text content from the page
    const pageContent = await page.textContent('body');

    // Common indicators of mock/dummy data
    const mockDataIndicators = [
      { pattern: /dummy/gi, type: 'Dummy Data References' },
      { pattern: /placeholder/gi, type: 'Placeholder Content' },
      { pattern: /lorem ipsum/gi, type: 'Lorem Ipsum Text' },
      { pattern: /test.*trip|example.*destination/gi, type: 'Test/Example Content' },
      { pattern: /\$\d+\.\d{2}.*demo|\$\d+\.\d{2}.*mock/gi, type: 'Mock Pricing' },
      { pattern: /demo.*user|test.*user/gi, type: 'Demo/Test User References' }
    ];

    logTestStep('Mock data indicator analysis:');
    let foundMockData = false;

    for (const indicator of mockDataIndicators) {
      const matches = pageContent.match(indicator.pattern);
      if (matches) {
        logSuccess(`Found ${indicator.type}:`, matches.slice(0, 5)); // Show first 5 matches
        foundMockData = true;
      } else {
        logError(`No ${indicator.type} found`);
      }
    }

    // Analyze trip entries for dummy data patterns
    const tripElements = page.locator('.trip-card, .destination-card, [data-testid="trip"], [data-testid="destination"]');
    const tripCount = await tripElements.count();

    logTestStep(`Found ${tripCount} trip/destination elements`);

    if (tripCount > 0) {
      logTestStep('Analyzing individual trip/destination entries:');

      for (let i = 0; i < Math.min(tripCount, 5); i++) { // Analyze first 5 entries
        const tripElement = tripElements.nth(i);

        try {
          const tripText = await tripElement.textContent();
          const hasPrice = tripText.match(/\$\d+/);
          const hasDate = tripText.match(/\d{1,2}\/\d{1,2}\/\d{4}|\d{4}-\d{2}-\d{2}/);
          const hasLocation = tripText.match(/[A-Z][a-z]+,\s*[A-Z][a-z]+/);

          logTestStep(`Entry ${i + 1}:`);
          logTestStep(`  - Text: "${tripText.substring(0, 100)}..."`);
          logTestStep(`  - Has Price: ${!!hasPrice} ${hasPrice ? hasPrice[0] : ''}`);
          logTestStep(`  - Has Date: ${!!hasDate} ${hasDate ? hasDate[0] : ''}`);
          logTestStep(`  - Has Location: ${!!hasLocation} ${hasLocation ? hasLocation[0] : ''}`);

          // Check if entry appears clickable but doesn't work
          try {
            const isClickable = await tripElement.isEnabled();
            logTestStep(`  - Appears clickable: ${isClickable}`);

            if (isClickable) {
              // Test click to see if it's functional
              await tripElement.click({ timeout: 1000 });
              await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

              const urlChanged = page.url() !== buildFrontendUrl(URLS.VOYA_HOME);
              const modalOpened = await page.locator('.modal, .MuiDialog-root').count() > 0;
              const hasNewContent = await page.locator('.trip-details, .destination-details').count() > 0;

              logTestStep(`  - Click functional: ${urlChanged || modalOpened || hasNewContent}`);

              if (!urlChanged && !modalOpened && !hasNewContent) {
                logTestStep(`  ❌ Entry appears clickable but non-functional (likely dummy)`);
              }

              // Navigate back if URL changed
              if (urlChanged) {
                await navigateToVoya(page);
              }
            }

          } catch (error) {
            logTestStep(`  - Click test failed: ${error.message}`);
          }

        } catch (error) {
          logTestStep(`Error analyzing entry ${i + 1}: ${error.message}`);
        }
      }
    } else {
      logError('No trip/destination entries found');
    }

    return foundMockData;
  });

  test('Dream Destinations Analysis - Dummy vs Real Data', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('DREAM DESTINATIONS MOCK DATA ANALYSIS', 'section');

    // Find dream destinations section
    const destinationsSection = page.locator('text=Dream Destinations').locator('..');

    if (await destinationsSection.count() > 0) {
      logSuccess('Dream Destinations section found');

      // Take screenshot of destinations
      await destinationsSection.screenshot({ path: 'test-results/dream-destinations-analysis.png' });

      // Extract destination information
      const destinationCards = destinationsSection.locator('.destination-card, .card, img').or(
        page.locator('img[alt*="destination"], img[src*="destination"]')
      );

      const cardCount = await destinationCards.count();
      logTestStep(`Found ${cardCount} destination cards`);

      if (cardCount > 0) {
        logTestStep('Analyzing destination entries:');

        for (let i = 0; i < cardCount; i++) {
          const card = destinationCards.nth(i);

          try {
            // Get image source and alt text
            const imgSrc = await card.getAttribute('src');
            const imgAlt = await card.getAttribute('alt');
            const cardText = await card.locator('..').textContent();

            logTestStep(`Destination ${i + 1}:`);
            logTestStep(`  - Image source: ${imgSrc}`);
            logTestStep(`  - Alt text: ${imgAlt}`);
            logTestStep(`  - Card text: "${cardText?.substring(0, 100) || 'No text'}..."`);

            // Analyze if image is stock/placeholder
            const isStockPhoto = imgSrc?.includes('unsplash') ||
                               imgSrc?.includes('stock') ||
                               imgSrc?.includes('placeholder') ||
                               imgSrc?.includes('example');

            const isLocalAsset = imgSrc?.includes('/assets/') ||
                               imgSrc?.includes('/images/');

            logTestStep(`  - Likely stock photo: ${isStockPhoto}`);
            logTestStep(`  - Local asset: ${isLocalAsset}`);

            // Test "View Details" functionality
            const viewDetailsBtn = card.locator('..').locator('button:has-text("View Details"), a:has-text("View Details")');

            if (await viewDetailsBtn.count() > 0) {
              logTestStep(`  - Has "View Details" button`);

              try {
                const beforeUrl = page.url();
                await viewDetailsBtn.click({ timeout: 2000 });
                await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

                const afterUrl = page.url();
                const modalOpened = await page.locator('.modal, .MuiDialog-root').count() > 0;
                const hasDetails = await page.locator('.destination-details, .trip-details').count() > 0;

                const isFunctional = beforeUrl !== afterUrl || modalOpened || hasDetails;

                logTestStep(`  - "View Details" functional: ${isFunctional}`);

                if (!isFunctional) {
                  logTestStep(`  ❌ "View Details" button non-functional (likely dummy data)`);
                } else {
                  logTestStep(`  ✅ "View Details" button appears functional`);

                  // Take screenshot if modal opened
                  if (modalOpened) {
                    await page.screenshot({ path: `test-results/destination-${i + 1}-details.png` });
                  }
                }

                // Navigate back if needed
                if (beforeUrl !== afterUrl) {
                  await navigateToVoya(page);
                }

              } catch (error) {
                logTestStep(`  ❌ "View Details" test failed: ${error.message}`);
              }
            } else {
              logTestStep(`  - No "View Details" button found`);
            }

          } catch (error) {
            logTestStep(`  Error analyzing destination ${i + 1}: ${error.message}`);
          }
        }
      } else {
        logError('No destination cards found in section');
      }
    } else {
      logError('Dream Destinations section not found');
    }
  });

  test('Premium Plan and Billing Mock Data Analysis', async ({ page }) => {
    await navigateToApp(page);
    await page.goto(buildFrontendUrl('/profile'));

    logTestStep('PREMIUM PLAN & BILLING MOCK DATA ANALYSIS', 'section');

    // Try to access account & billing via menu
    const menuButton = page.locator('button:has([data-testid="MoreVertIcon"]), [data-testid="MoreVertIcon"]');

    if (await menuButton.count() > 0) {
      logSuccess('Profile menu found');

      await menuButton.click();
      await page.waitForTimeout(1000);

      const billingOption = page.locator('text=Account & Billing');

      if (await billingOption.count() > 0) {
        logSuccess('Account & Billing menu option found');

        await billingOption.click();
        await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

        // Take screenshot of billing section
        await page.screenshot({ path: 'test-results/billing-mockdata-analysis.png', fullPage: true });

        // Extract billing page content
        const billingContent = await page.textContent('body');

        logTestStep('Billing section analysis:');

        // Check for "Premium Explorer" plan
        const hasPremiumPlan = billingContent.includes('Premium Explorer');
        logTestStep(`- Has "Premium Explorer" plan: ${hasPremiumPlan}`);

        if (hasPremiumPlan) {
          logError('CONFIRMED: "Premium Explorer" appears to be dummy subscription data');
        }

        // Check for payment method information
        const paymentMethodPatterns = [
          /payment method/gi,
          /credit card/gi,
          /\*\*\*\*.*\d{4}/gi, // Masked credit card numbers
          /visa|mastercard|amex/gi,
          /expires?\s*\d{2}\/\d{2}/gi // Expiration dates
        ];

        logTestStep('Payment method analysis:');
        let foundPaymentInfo = false;

        for (const pattern of paymentMethodPatterns) {
          const matches = billingContent.match(pattern);
          if (matches) {
            logTestStep(`  - Found payment info: ${matches[0]}`);
            foundPaymentInfo = true;
          }
        }

        if (foundPaymentInfo) {
          logError('CONFIRMED: Payment method information appears to be mock data');
        } else {
          logSuccess('No payment method mock data detected');
        }

        // Check for subscription pricing
        const priceMatches = billingContent.match(/\$\d+(\.\d{2})?\s*(\/month|\/year|monthly|yearly)/gi);
        if (priceMatches) {
          logTestStep(`- Subscription pricing found: ${priceMatches.join(', ')}`);
          logError('CONFIRMED: Subscription pricing appears to be dummy data');
        }

        // Test plan management buttons
        const planButtons = page.locator('button:has-text("Upgrade"), button:has-text("Cancel"), button:has-text("Change Plan")');
        const buttonCount = await planButtons.count();

        if (buttonCount > 0) {
          logTestStep(`Found ${buttonCount} plan management buttons`);

          for (let i = 0; i < buttonCount; i++) {
            const button = planButtons.nth(i);
            const buttonText = await button.textContent();

            try {
              await button.click({ timeout: 2000 });
              await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

              // Check if button actually does something
              const hasNewModal = await page.locator('.modal, .MuiDialog-root').count() > 0;
              const urlChanged = !page.url().includes('/profile');

              logTestStep(`- "${buttonText}" button functional: ${hasNewModal || urlChanged}`);

              if (!hasNewModal && !urlChanged) {
                logTestStep(`  ❌ "${buttonText}" button non-functional (likely dummy)`);
              }

            } catch (error) {
              logTestStep(`  ❌ "${buttonText}" button test failed: ${error.message}`);
            }
          }
        } else {
          logTestStep('- No plan management buttons found');
        }

      } else {
        logError('Account & Billing option not found in menu');
      }
    } else {
      logError('Profile menu button not found');
    }
  });

  test('API Data vs Frontend Mock Data Cross-Reference', async ({ request, page }) => {
    if (!authToken) {
      test.skip(true, 'No auth token available for API comparison');
      return;
    }

    logTestStep('API vs FRONTEND MOCK DATA COMPARISON', 'section');

    try {
      // Get real user data from API
      const userResponse = await request.get(`${API_BASE}/user/me`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      if (userResponse.ok()) {
        const apiUserData = await userResponse.json();
        logTestStep('Real API user data structure:');
        logTestStep(Object.keys(apiUserData));

        // Navigate to profile to compare frontend display
        await navigateToApp(page);
    await page.goto(buildFrontendUrl('/profile'));
        await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

        // Extract displayed user information
        const profileContent = await page.textContent('body');

        logTestStep('\nAPI vs Frontend comparison:');

        // Check name display (known issue: "undefined undefined")
        const displayedName = await page.locator('h4, h5').filter({ hasText: /undefined|null|[A-Z][a-z]+\s+[A-Z][a-z]+/ }).textContent();

        logTestStep(`- API first_name: "${apiUserData.first_name}"`);
        logTestStep(`- API last_name: "${apiUserData.last_name}"`);
        logTestStep(`- Frontend displays: "${displayedName}"`);

        if (displayedName?.includes('undefined')) {
          logTestStep(`❌ CONFIRMED: Frontend shows "undefined undefined" despite API having name data`);
        }

        // Check subscription info
        const hasSubscriptionAPI = apiUserData.plan_id || apiUserData.subscription_id;
        const hasSubscriptionFrontend = profileContent.includes('Premium Explorer');

        logTestStep(`- API has subscription data: ${!!hasSubscriptionAPI}`);
        logTestStep(`- Frontend shows Premium plan: ${hasSubscriptionFrontend}`);

        if (!hasSubscriptionAPI && hasSubscriptionFrontend) {
          logTestStep(`❌ CONFIRMED: Frontend shows dummy subscription data not in API`);
        }

        // Check timezone issue
        logTestStep(`- API timezone: "${apiUserData.timezone}"`);
        const timezoneDisplay = await page.locator('text=Timezone').locator('..').textContent();
        logTestStep(`- Frontend timezone display: "${timezoneDisplay}"`);

        if (apiUserData.timezone && timezoneDisplay?.includes('Not set')) {
          logTestStep(`❌ CONFIRMED: Frontend shows "Not set" despite API having timezone`);
        }

      } else {
        logError('Failed to get user data from API');
      }

      // Test trips API vs frontend
      try {
        const tripsResponse = await request.get(`${API_BASE}/trips`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const apiHasTrips = tripsResponse.ok() && (await tripsResponse.json()).length > 0;

        await navigateToVoya(page);
        const frontendTrips = await page.locator('.trip-card, [data-testid="trip"]').count();

        logTestStep(`\nTrips comparison:`);
        logTestStep(`- API has trips: ${apiHasTrips}`);
        logTestStep(`- Frontend shows ${frontendTrips} trip(s)`);

        if (!apiHasTrips && frontendTrips > 0) {
          logTestStep(`❌ CONFIRMED: Frontend shows dummy trips not in API`);
        }

      } catch (error) {
        logError('Trips API comparison failed:', error.message);
      }

    } catch (error) {
      logError('API comparison test failed:', error.message);
    }
  });

  test('Static Assets and Content Analysis', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('STATIC ASSETS AND CONTENT ANALYSIS', 'section');

    // Analyze all images on the page
    const images = page.locator('img');
    const imageCount = await images.count();

    logTestStep(`Found ${imageCount} images on main page`);

    if (imageCount > 0) {
      logTestStep('Image source analysis:');

      for (let i = 0; i < Math.min(imageCount, 10); i++) { // Analyze first 10 images
        const img = images.nth(i);

        try {
          const src = await img.getAttribute('src');
          const alt = await img.getAttribute('alt');

          const isPlaceholder = src?.includes('placeholder') ||
                               alt?.includes('placeholder') ||
                               src?.includes('example') ||
                               src?.includes('dummy');

          const isStockPhoto = src?.includes('unsplash') ||
                             src?.includes('pexels') ||
                             src?.includes('shutterstock');

          const isLocalAsset = src?.includes('/assets/') ||
                             src?.startsWith('./') ||
                             src?.startsWith('/');

          logTestStep(`Image ${i + 1}:`);
          logTestStep(`  - Source: ${src}`);
          logTestStep(`  - Alt: ${alt}`);
          logTestStep(`  - Is placeholder: ${isPlaceholder}`);
          logTestStep(`  - Is stock photo: ${isStockPhoto}`);
          logTestStep(`  - Is local asset: ${isLocalAsset}`);

          if (isPlaceholder) {
            logTestStep(`  ❌ Confirmed placeholder image`);
          }

        } catch (error) {
          logTestStep(`  Error analyzing image ${i + 1}: ${error.message}`);
        }
      }
    }

    // Check for hardcoded text content
    const pageText = await page.textContent('body');
    const hardcodedPatterns = [
      { pattern: /lorem ipsum/gi, name: 'Lorem Ipsum' },
      { pattern: /coming soon/gi, name: 'Coming Soon' },
      { pattern: /under construction/gi, name: 'Under Construction' },
      { pattern: /work in progress/gi, name: 'Work in Progress' },
      { pattern: /demo only/gi, name: 'Demo Only' },
      { pattern: /not yet implemented/gi, name: 'Not Yet Implemented' }
    ];

    logTestStep('Hardcoded content analysis:');
    let foundHardcodedContent = false;

    for (const pattern of hardcodedPatterns) {
      const matches = pageText.match(pattern.pattern);
      if (matches) {
        logTestStep(`❌ Found ${pattern.name}: ${matches.length} instance(s)`);
        foundHardcodedContent = true;
      }
    }

    if (!foundHardcodedContent) {
      logSuccess('No obvious hardcoded placeholder content found');
    }

    // Final comprehensive screenshot
    await page.screenshot({ path: 'test-results/mockdata-comprehensive-analysis.png', fullPage: true });
  });

  test('Feature Completeness Assessment', async ({ page }) => {
    await navigateToVoya(page);

    logTestStep('FEATURE COMPLETENESS ASSESSMENT', 'section');

    // Define features and test their completeness
    const features = [
      {
        name: 'Trip Planning',
        elements: ['button:has-text("Plan New Trip")', '.trip-form', 'input[name="destination"]'],
        functional: false
      },
      {
        name: 'Flight Search',
        elements: ['button:has-text("Search Flights")', '.flight-results', 'input[placeholder*="departure"]'],
        functional: false
      },
      {
        name: 'User Profile',
        elements: ['a:has-text("Profile")', '.profile-banner', 'input[name="first_name"]'],
        functional: false
      },
      {
        name: 'Chat System',
        elements: ['input[placeholder*="message"]', '.chat-message', 'button:has-text("Send")'],
        functional: false
      },
      {
        name: 'Travel Preferences',
        elements: ['.MuiChip-root', 'button:has-text("Adventure")', 'text=Travel Preferences'],
        functional: false
      }
    ];

    for (const feature of features) {
      logTestStep(`Analyzing ${feature.name}:`);

      let elementsFound = 0;
      let functionalElements = 0;

      for (const selector of feature.elements) {
        const element = page.locator(selector);
        const exists = await element.count() > 0;

        if (exists) {
          elementsFound++;
          logTestStep(`  ✅ Found: ${selector}`);

          // Test functionality
          try {
            if (selector.includes('button') || selector.includes('a:has-text')) {
              await element.first().click({ timeout: 2000 });
              await page.waitForTimeout(TIMEOUTS.SHORT_WAIT);

              const hasEffect = page.url() !== buildFrontendUrl(URLS.VOYA_HOME) ||
                              await page.locator('.modal, .MuiDialog-root').count() > 0 ||
                              await page.locator('.success, .error').count() > 0;

              if (hasEffect) {
                functionalElements++;
                logTestStep(`    ✅ Element is functional`);
              } else {
                logTestStep(`    ❌ Element appears non-functional`);
              }

              // Navigate back if needed
              if (page.url() !== buildFrontendUrl(URLS.VOYA_HOME)) {
                await navigateToVoya(page);
              }
            } else {
              functionalElements++; // Assume non-interactive elements are functional if they exist
            }
          } catch (error) {
            logTestStep(`    ❌ Element test failed: ${error.message}`);
          }
        } else {
          logTestStep(`  ❌ Not found: ${selector}`);
        }
      }

      const completeness = Math.round((elementsFound / feature.elements.length) * 100);
      const functionality = Math.round((functionalElements / feature.elements.length) * 100);

      console.log(`  ${feature.name} Completeness: ${completeness}% (${elementsFound}/${feature.elements.length} elements)`);
      console.log(`  ${feature.name} Functionality: ${functionality}% (${functionalElements}/${feature.elements.length} working)`);

      if (completeness < 50) {
        logTestStep(`  ❌ ${feature.name} appears incomplete or broken`);
      } else if (functionality < 50) {
        logTestStep(`  ⚠️ ${feature.name} has UI elements but limited functionality`);
      } else {
        logTestStep(`  ✅ ${feature.name} appears reasonably complete and functional`);
      }
    }

    console.log('\n=== SUMMARY', 'section');
    console.log('Mock data and broken features have been systematically documented.');
    console.log('Screenshots and detailed analysis saved to test-results/ directory.');
  });
});
