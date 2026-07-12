/**
 * Trip Planning Flow Diagnostic Tests
 *
 * Purpose: Test trip planning functionality and identify issues including:
 * - Trip creation flow (chat-based vs direct)
 * - Flight search integration within trip planning
 * - Calendar integration and date selection
 * - Trip management (view, edit, delete)
 * - API endpoint connectivity for trip operations
 * - Trip data persistence and retrieval
 */

import { test, expect } from '@playwright/test';
import { URLS, SELECTORS, TIMEOUTS, generateTestUser, buildApiUrl, buildFrontendUrl } from '../utils/constants.js';
import { createApiClient } from '../utils/api-client.js';
import { navigateToVoya, navigateToApp } from '../helpers/navigation-helpers.js';
import { logTestStep, logSuccess, logError } from '../helpers/debug-helpers.js';




test.describe('Trip Planning Flow Diagnostics', () => {
  let authToken;

  test.beforeAll(async ({ request }) => {
    // Login to get auth token for API calls
    const loginResponse = await request.post(`${API_BASE}/auth/login`, {
      data: {
        email: "roel@myvoya.ai",
        password: "VoyaTest123!"
      }
    });

    if (loginResponse.ok()) {
      const loginData = await loginResponse.json();
      authToken = loginData.access_token;
      console.log('✅ Authentication successful for trip tests');
    } else {
      console.log('❌ Login failed, trip tests may not work properly');
    }
  });

  test('Trip API Endpoints - Backend Connectivity Test', async ({ request }) => {
    if (!authToken) {
      test.skip(true, 'No auth token available for API testing');
      return;
    }

    console.log('=== TRIP API ENDPOINTS TESTS ===');

    // Test trip endpoints availability
    const endpoints = [
      { method: 'GET', path: '/trips', description: 'Get user trips' },
      { method: 'POST', path: '/trips/create', description: 'Create new trip' },
      { method: 'GET', path: '/trips/123', description: 'Get specific trip' },
      { method: 'PUT', path: '/trips/123', description: 'Update trip' },
      { method: 'DELETE', path: '/trips/123', description: 'Delete trip' }
    ];

    for (const endpoint of endpoints) {
      console.log(`Testing ${endpoint.method} ${endpoint.path} - ${endpoint.description}`);

      try {
        const response = await request[endpoint.method.toLowerCase()](`${API_BASE}${endpoint.path}`, {
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          },
          data: endpoint.method === 'POST' ? {
            title: "Test Trip",
            destination: "Paris",
            start_date: "2024-12-01",
            end_date: "2024-12-05"
          } : undefined
        });

        console.log(`${endpoint.method} ${endpoint.path} - Status: ${response.status()}`);

        if (response.status() === 404) {
          console.log(`❌ Endpoint ${endpoint.path} not found - may not be implemented`);
        } else if (response.status() >= 200 && response.status() < 300) {
          console.log(`✅ Endpoint ${endpoint.path} accessible`);

          if (response.status() !== 204) { // Skip parsing empty responses
            try {
              const responseData = await response.json();
              console.log(`Response structure: ${Object.keys(responseData || {}).join(', ')}`);
            } catch (e) {
              console.log('Response not JSON or empty');
            }
          }
        } else {
          console.log(`⚠️ Endpoint ${endpoint.path} returned ${response.status()}`);
        }

      } catch (error) {
        console.log(`❌ Error testing ${endpoint.path}: ${error.message}`);
      }
    }
  });

  test('Trip Creation Flow - Frontend UI Test', async ({ page }) => {
    await page.goto(`${URLS.FRONTEND}/voya`);

    console.log('=== TRIP CREATION FLOW TESTS ===');

    // Take screenshot of main page
    await page.screenshot({ path: 'test-results/trip-main-page.png', fullPage: true });

    // Look for trip creation entry points
    const createTripButtons = [
      'button:has-text("Plan New Trip")',
      'button:has-text("Create Trip")',
      'a:has-text("New Trip")',
      '[data-testid="create-trip"]',
      '.create-trip-btn'
    ];

    let foundCreateButton = false;

    for (const selector of createTripButtons) {
      const button = page.locator(selector);
      if (await button.count() > 0) {
        console.log(`✅ Found trip creation button: ${selector}`);
        foundCreateButton = true;

        try {
          // Take screenshot before clicking
          await button.screenshot({ path: 'test-results/create-trip-button.png' });

          await button.click();
          await page.waitForTimeout(3000);

          // Check what happened after click
          const currentUrl = page.url();
          const hasTripForm = await page.locator('.trip-form, [data-testid="trip-form"], .create-trip-form').count() > 0;
          const hasChatMessage = await page.locator('.chat-message, [data-testid="chat-message"]').count() > 0;
          const hasModal = await page.locator('.modal, .MuiDialog-root, [role="dialog"]').count() > 0;

          console.log(`After clicking ${selector}:`);
          console.log(`URL: ${currentUrl}`);
          console.log(`Has Trip Form: ${hasTripForm}`);
          console.log(`Has Chat Message: ${hasChatMessage}`);
          console.log(`Has Modal: ${hasModal}`);

          // Take screenshot after clicking
          await page.screenshot({ path: 'test-results/after-create-trip-click.png', fullPage: true });

          if (hasTripForm) {
            console.log('✅ Trip creation opened form interface');
            await this.testTripForm(page);
          } else if (hasChatMessage) {
            console.log('✅ Trip creation triggered chat interaction');
          } else if (hasModal) {
            console.log('✅ Trip creation opened modal dialog');
          } else {
            console.log('❌ Trip creation button had no visible effect');
          }

          break; // Stop after testing first working button

        } catch (error) {
          console.log(`❌ Error testing ${selector}: ${error.message}`);
        }
      }
    }

    if (!foundCreateButton) {
      console.log('❌ No trip creation button found on main page');
    }
  });

  test('Trip Form Testing', async ({ page }) => {
    await testTripForm(page);
  });

  async function testTripForm(page) {
    console.log('=== TRIP FORM TESTING ===');

    const formFields = [
      { selector: 'input[name="title"], input[placeholder*="title"], [data-testid="trip-title"]', name: 'Trip Title' },
      { selector: 'input[name="destination"], input[placeholder*="destination"], [data-testid="destination"]', name: 'Destination' },
      { selector: 'input[type="date"], [data-testid="start-date"]', name: 'Start Date' },
      { selector: 'input[type="date"], [data-testid="end-date"]', name: 'End Date' },
      { selector: 'textarea[name="description"], [data-testid="description"]', name: 'Description' }
    ];

    for (const field of formFields) {
      const element = page.locator(field.selector);
      const fieldExists = await element.count() > 0;
      console.log(`${field.name} field exists: ${fieldExists}`);

      if (fieldExists) {
        try {
          await element.fill(field.name === 'Trip Title' ? 'Test Paris Trip' :
                           field.name === 'Destination' ? 'Paris, France' :
                           field.name === 'Description' ? 'A wonderful trip to Paris' :
                           '2024-12-01');
          console.log(`✅ ${field.name} field accepts input`);
        } catch (error) {
          console.log(`❌ ${field.name} field error: ${error.message}`);
        }
      }
    }

    // Look for submit button
    const submitButton = page.locator('button:has-text("Create"), button:has-text("Save"), button[type="submit"]');
    if (await submitButton.count() > 0) {
      console.log('Submit button found');
      try {
        await submitButton.click();
        await page.waitForTimeout(3000);

        // Check for success/error feedback
        const hasSuccess = await page.locator('.success, .MuiAlert-standard, .success-message').count() > 0;
        const hasError = await page.locator('.error, .MuiAlert-error, .error-message').count() > 0;

        console.log(`Form submission - Success: ${hasSuccess}, Error: ${hasError}`);

        await page.screenshot({ path: 'test-results/trip-form-submission.png', fullPage: true });

      } catch (error) {
        console.log(`❌ Form submission error: ${error.message}`);
      }
    } else {
      console.log('❌ No submit button found in trip form');
    }
  }

  test('Trip List and Management - View Existing Trips', async ({ page }) => {
    await page.goto(`${URLS.FRONTEND}/voya`);

    console.log('=== TRIP LIST AND MANAGEMENT TESTS ===');

    // Look for trips section or trip list
    const tripsSection = page.locator('text=My Trips').locator('..');
    const tripsList = page.locator('.trips-list, [data-testid="trips-list"], .trip-card');
    const tripsNavigation = page.locator('a:has-text("Trips"), button:has-text("Trips"), [data-testid="trips-nav"]');

    if (await tripsNavigation.count() > 0) {
      console.log('Trips navigation found');
      try {
        await tripsNavigation.click();
        await page.waitForTimeout(2000);

        await page.screenshot({ path: 'test-results/trips-page.png', fullPage: true });

        const currentUrl = page.url();
        console.log(`Trips navigation URL: ${currentUrl}`);

      } catch (error) {
        console.log(`❌ Trips navigation error: ${error.message}`);
      }
    }

    if (await tripsSection.count() > 0) {
      console.log('Trips section found on main page');
      await tripsSection.screenshot({ path: 'test-results/trips-section.png' });
    }

    // Count visible trips
    const tripCount = await tripsList.count();
    console.log(`Number of visible trips: ${tripCount}`);

    if (tripCount > 0) {
      console.log('✅ Trip list contains items');

      // Test first trip interaction
      const firstTrip = tripsList.first();

      try {
        // Look for trip details
        const tripTitle = await firstTrip.locator('h3, h4, h5, .trip-title').textContent();
        const tripDestination = await firstTrip.locator('.destination, [data-testid="destination"]').textContent();

        console.log(`First trip - Title: "${tripTitle}", Destination: "${tripDestination}"`);

        // Test trip click
        await firstTrip.click();
        await page.waitForTimeout(2000);

        const afterClickUrl = page.url();
        const hasTripDetails = await page.locator('.trip-details, [data-testid="trip-details"]').count() > 0;

        console.log(`Trip click - URL: ${afterClickUrl}, Details: ${hasTripDetails}`);

        await page.screenshot({ path: 'test-results/trip-details.png', fullPage: true });

      } catch (error) {
        console.log(`❌ Trip interaction error: ${error.message}`);
      }
    } else {
      console.log('❌ No trips visible in list - may be empty or not loading');
    }
  });

  test('Flight Search Integration within Trip Planning', async ({ page }) => {
    await page.goto(`${URLS.FRONTEND}/voya`);

    console.log('=== FLIGHT SEARCH INTEGRATION TESTS ===');

    // Navigate to trip planning or create a trip context
    const createTripBtn = page.locator('button:has-text("Plan New Trip"), [data-testid="create-trip"]');

    if (await createTripBtn.count() > 0) {
      await createTripBtn.click();
      await page.waitForTimeout(3000);
    }

    // Look for flight search within trip context
    const flightSearchElements = [
      '.flight-search, [data-testid="flight-search"]',
      'button:has-text("Search Flights")',
      'text=Flights',
      '.flight-tab, [data-testid="flights-tab"]'
    ];

    let foundFlightSearch = false;

    for (const selector of flightSearchElements) {
      const element = page.locator(selector);
      if (await element.count() > 0) {
        console.log(`✅ Found flight search element: ${selector}`);
        foundFlightSearch = true;

        try {
          if (selector.includes('button') || selector.includes('tab')) {
            await element.click();
            await page.waitForTimeout(2000);

            // Check if flight search form appears
            const hasFlightForm = await page.locator('.flight-form, [data-testid="flight-form"]').count() > 0;
            const hasFlightInputs = await page.locator('input[placeholder*="departure"], input[placeholder*="arrival"]').count() > 0;

            console.log(`Flight form visible: ${hasFlightForm}`);
            console.log(`Flight inputs visible: ${hasFlightInputs}`);

            if (hasFlightForm || hasFlightInputs) {
              await this.testFlightSearchForm(page);
            }
          }

          await page.screenshot({ path: 'test-results/trip-flight-search.png', fullPage: true });

        } catch (error) {
          console.log(`❌ Flight search test error: ${error.message}`);
        }

        break;
      }
    }

    if (!foundFlightSearch) {
      console.log('❌ No flight search integration found in trip planning');
    }
  });

  test('Flight Search Form Testing', async ({ page }) => {
    await testFlightSearchForm(page);
  });

  async function testFlightSearchForm(page) {
    console.log('=== FLIGHT SEARCH FORM TESTING ===');

    const flightFormFields = [
      { selector: 'input[placeholder*="departure"], input[name="from"]', value: 'Amsterdam', name: 'Departure' },
      { selector: 'input[placeholder*="arrival"], input[name="to"]', value: 'Paris', name: 'Arrival' },
      { selector: 'input[type="date"], input[placeholder*="departure date"]', value: '2024-12-01', name: 'Departure Date' },
      { selector: 'input[placeholder*="return"], input[name="return_date"]', value: '2024-12-05', name: 'Return Date' },
      { selector: 'select[name="passengers"], input[placeholder*="passenger"]', value: '1', name: 'Passengers' }
    ];

    for (const field of flightFormFields) {
      const element = page.locator(field.selector);
      const fieldExists = await element.count() > 0;
      console.log(`${field.name} field exists: ${fieldExists}`);

      if (fieldExists) {
        try {
          await element.fill(field.value);
          console.log(`✅ ${field.name} field filled with "${field.value}"`);
        } catch (error) {
          console.log(`❌ ${field.name} field error: ${error.message}`);
        }
      }
    }

    // Test flight search button
    const searchFlightsBtn = page.locator('button:has-text("Search Flights"), button:has-text("Search"), [data-testid="search-flights"]');

    if (await searchFlightsBtn.count() > 0) {
      console.log('Flight search button found');

      try {
        await searchFlightsBtn.click();
        await page.waitForTimeout(5000); // Wait for API call

        // Check for loading state and results
        const hasLoading = await page.locator('.loading, .spinner, [data-testid="loading"]').count() > 0;
        const hasResults = await page.locator('.flight-results, .flight-card, [data-testid="flight-results"]').count() > 0;
        const hasError = await page.locator('.error, .error-message').count() > 0;

        console.log(`Flight search - Loading: ${hasLoading}, Results: ${hasResults}, Error: ${hasError}`);

        if (hasResults) {
          console.log('✅ Flight search returned results');
          const resultCount = await page.locator('.flight-card, .flight-result').count();
          console.log(`Number of flight results: ${resultCount}`);
        } else if (hasError) {
          const errorText = await page.locator('.error, .error-message').textContent();
          console.log(`❌ Flight search error: ${errorText}`);
        } else {
          console.log('❌ Flight search had no visible results');
        }

        await page.screenshot({ path: 'test-results/flight-search-results.png', fullPage: true });

      } catch (error) {
        console.log(`❌ Flight search button error: ${error.message}`);
      }
    } else {
      console.log('❌ Flight search button not found');
    }
  }

  test('Calendar Integration - Date Selection and Trip Planning', async ({ page }) => {
    await page.goto(`${URLS.FRONTEND}/voya`);

    console.log('=== CALENDAR INTEGRATION TESTS ===');

    // Look for calendar components
    const calendarElements = [
      '.calendar, [data-testid="calendar"]',
      '.fc-calendar, .react-calendar', // Common calendar library classes
      '.date-picker, [data-testid="date-picker"]',
      '.MuiDatePicker-root, .MuiCalendarPicker-root'
    ];

    let foundCalendar = false;

    for (const selector of calendarElements) {
      const calendar = page.locator(selector);
      if (await calendar.count() > 0) {
        console.log(`✅ Found calendar component: ${selector}`);
        foundCalendar = true;

        try {
          await calendar.screenshot({ path: 'test-results/calendar-component.png' });

          // Test calendar interaction
          const dateCell = calendar.locator('.fc-daygrid-day, .react-calendar__tile, .MuiPickersDay-root').first();

          if (await dateCell.count() > 0) {
            await dateCell.click();
            await page.waitForTimeout(1000);

            // Check if date selection triggered any action
            const hasDateSelected = await page.locator('.fc-daygrid-day-selected, .react-calendar__tile--active, .Mui-selected').count() > 0;
            console.log(`Date selection working: ${hasDateSelected}`);

            if (hasDateSelected) {
              console.log('✅ Calendar date selection functional');
            }
          }

        } catch (error) {
          console.log(`❌ Calendar interaction error: ${error.message}`);
        }

        break;
      }
    }

    if (!foundCalendar) {
      console.log('❌ No calendar components found');

      // Look for alternative date inputs
      const dateInputs = await page.locator('input[type="date"]').count();
      console.log(`Found ${dateInputs} date input fields as alternative`);

      if (dateInputs > 0) {
        console.log('✅ Date inputs available for trip planning');
      }
    }

    // Test date range selection for trips
    const startDateInput = page.locator('input[name="start_date"], input[placeholder*="start"], [data-testid="start-date"]');
    const endDateInput = page.locator('input[name="end_date"], input[placeholder*="end"], [data-testid="end-date"]');

    if (await startDateInput.count() > 0 && await endDateInput.count() > 0) {
      console.log('Date range inputs found for trip planning');

      try {
        await startDateInput.fill('2024-12-01');
        await endDateInput.fill('2024-12-05');

        console.log('✅ Date range selection completed');

        // Check if date selection triggers trip planning features
        await page.waitForTimeout(2000);

        const hasFlightSuggestions = await page.locator('.flight-suggestions, [data-testid="flight-suggestions"]').count() > 0;
        const hasHotelSuggestions = await page.locator('.hotel-suggestions, [data-testid="hotel-suggestions"]').count() > 0;

        console.log(`Date selection triggered - Flights: ${hasFlightSuggestions}, Hotels: ${hasHotelSuggestions}`);

      } catch (error) {
        console.log(`❌ Date range selection error: ${error.message}`);
      }
    }

    await page.screenshot({ path: 'test-results/calendar-integration.png', fullPage: true });
  });

  test('Trip Data Persistence - Save and Load Test', async ({ page, request }) => {
    if (!authToken) {
      test.skip(true, 'No auth token available for persistence testing');
      return;
    }

    console.log('=== TRIP DATA PERSISTENCE TESTS ===');

    // First, try to create a trip via API
    try {
      const createResponse = await request.post(`${API_BASE}/trips/create`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        data: {
          title: "Playwright Test Trip",
          destination: "Amsterdam",
          start_date: "2024-12-01",
          end_date: "2024-12-05",
          description: "Test trip for persistence testing"
        }
      });

      console.log(`Trip creation API status: ${createResponse.status()}`);

      if (createResponse.ok()) {
        const tripData = await createResponse.json();
        console.log('✅ Trip created via API');
        console.log(`Trip ID: ${tripData.id || 'N/A'}`);

        // Now test if trip appears in frontend
        await page.goto(`${URLS.FRONTEND}/voya`);
        await page.waitForTimeout(3000);

        // Look for the created trip
        const tripExists = await page.locator(`text=${tripData.title || "Playwright Test Trip"}`).count() > 0;
        console.log(`Trip visible in frontend: ${tripExists}`);

        if (tripExists) {
          console.log('✅ Trip persistence working - API to Frontend');
        } else {
          console.log('❌ Trip not visible in frontend after API creation');
        }

        await page.screenshot({ path: 'test-results/trip-persistence.png', fullPage: true });

      } else {
        console.log('❌ Trip creation via API failed');
        const errorText = await createResponse.text();
        console.log(`Error: ${errorText}`);
      }

    } catch (error) {
      console.log(`❌ Trip persistence test error: ${error.message}`);
    }

    // Test frontend trip creation persistence
    await page.goto(`${URLS.FRONTEND}/voya`);

    const createTripBtn = page.locator('button:has-text("Plan New Trip"), [data-testid="create-trip"]');

    if (await createTripBtn.count() > 0) {
      console.log('Testing frontend trip creation persistence...');

      try {
        await createTripBtn.click();
        await page.waitForTimeout(2000);

        // If form appears, fill it
        const titleInput = page.locator('input[name="title"], [data-testid="trip-title"]');

        if (await titleInput.count() > 0) {
          await titleInput.fill('Frontend Test Trip');

          const submitBtn = page.locator('button:has-text("Create"), button[type="submit"]');
          if (await submitBtn.count() > 0) {
            await submitBtn.click();
            await page.waitForTimeout(3000);

            // Check if trip appears in list
            const newTripExists = await page.locator('text=Frontend Test Trip').count() > 0;
            console.log(`Frontend created trip persisted: ${newTripExists}`);

            if (newTripExists) {
              console.log('✅ Frontend trip creation persistence working');
            }
          }
        }

      } catch (error) {
        console.log(`❌ Frontend trip creation test error: ${error.message}`);
      }
    }
  });
});
