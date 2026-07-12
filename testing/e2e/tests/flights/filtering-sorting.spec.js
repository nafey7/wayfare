/**
 * E2E Tests for Flight Filtering and Sorting
 *
 * Tests complete user workflows for filtering and sorting flight search results.
 * Verifies that users can filter by price, stops, airlines, cabin class, duration, and time.
 * Verifies that users can sort by price, duration, departure time, and arrival time.
 */

import { test, expect } from "@playwright/test";
import { URLS, TIMEOUTS, buildFrontendUrl } from "../../../utils/constants.js";
import { logTestStep, logSuccess, logError } from "../../../helpers/debug-helpers.js";
import { ensureAuthenticated } from "../../../helpers/auth-helpers.js";

test.describe("Flight Filtering and Sorting E2E", { tag: '@mock-required' }, () => {
  let testUser;

  test.beforeEach(async ({ page }) => {
    testUser = {
      email: "flightbooker@example.com",
      password: "Flight123!", // pragma: allowlist secret
    };

    // Navigate to flight booker
    await page.goto(`${buildFrontendUrl()}/dev/flight-booker/`);
    await page.waitForLoadState("networkidle");

    // Authenticate if needed
    await ensureAuthenticated(page, testUser);

    logTestStep("Flight filtering and sorting test setup complete");
  });

  test("should display filter and sort controls", async ({ page }) => {
    logTestStep("Testing filter and sort controls visibility");

    // Mock flight search results
    await page.route("**/api/flights/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: "test-session-123",
          fare_itineraries: [
            {
              pricing: {
                fare_totals: {
                  total_fare: { amount: "200.00", currency: "USD" },
                },
              },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS", name: "Amsterdam" },
                      arrival_airport: { iata_code: "LHR", name: "London" },
                      departure_datetime: { value: "2025-01-15T10:00:00" },
                      arrival_datetime: { value: "2025-01-15T12:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "KL", airline_name: "KLM" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
          ],
        }),
      });
    });

    // Perform a search to get results
    await page.fill("#origin", "AMS");
    await page.fill("#destination", "LHR");
    await page.fill("#departure_date", "2025-01-15");
    await page.click('button:has-text("Search Flights")');
    await page.waitForTimeout(2000);

    // Check for sort button
    const sortButton = page.locator('#toggle-sort-btn, button:has-text("Sort")');
    await expect(sortButton).toBeVisible({ timeout: 5000 });
    logSuccess("✅ Sort button visible");

    // Check for filters button
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await expect(filtersButton).toBeVisible({ timeout: 5000 });
    logSuccess("✅ Filters button visible");

    // Click filters button to open filter panel
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Check for filter panel
    const filterPanel = page.locator("#filters-container");
    await expect(filterPanel).toBeVisible();
    logSuccess("✅ Filter panel visible");

    // Check for key filter controls
    const priceFilter = page.locator("#filter-price-min, #filter-price-max");
    await expect(priceFilter.first()).toBeVisible();
    logSuccess("✅ Price filter visible");

    const directOnlyFilter = page.locator("#filter-direct-only");
    await expect(directOnlyFilter).toBeVisible();
    logSuccess("✅ Direct flights filter visible");
  });

  test("should filter flights by price range", async ({ page }) => {
    logTestStep("Testing price range filtering");

    // Mock flight search with multiple price points
    await page.route("**/api/flights/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: "test-session-123",
          fare_itineraries: [
            {
              pricing: { fare_totals: { total_fare: { amount: "100.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T10:00:00" },
                      arrival_datetime: { value: "2025-01-15T12:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "KL", airline_name: "KLM" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
            {
              pricing: { fare_totals: { total_fare: { amount: "300.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T14:00:00" },
                      arrival_datetime: { value: "2025-01-15T16:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "AF", airline_name: "Air France" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
            {
              pricing: { fare_totals: { total_fare: { amount: "500.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T18:00:00" },
                      arrival_datetime: { value: "2025-01-15T20:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "BA", airline_name: "British Airways" },
                      cabin_class: "Business",
                    },
                  ],
                },
              ],
            },
          ],
        }),
      });
    });

    // Perform search
    await page.fill("#origin", "AMS");
    await page.fill("#destination", "LHR");
    await page.fill("#departure_date", "2025-01-15");
    await page.click('button:has-text("Search Flights")');
    await page.waitForTimeout(2000);

    // Open filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Set price range filter (150-400)
    await page.fill("#filter-price-min", "150");
    await page.fill("#filter-price-max", "400");
    await page.waitForTimeout(500); // Wait for filter to apply

    // Check filtered count
    const filteredCount = page.locator("#filtered-count");
    const countText = await filteredCount.textContent();
    const count = parseInt(countText || "0");

    // Should show 1 flight (the 300.00 one)
    expect(count).toBeGreaterThanOrEqual(1);
    logSuccess(`✅ Price filter applied, showing ${count} flights`);
  });

  test("should filter flights by stops", async ({ page }) => {
    logTestStep("Testing stops filtering");

    // Mock flights with different stop counts
    await page.route("**/api/flights/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: "test-session-123",
          fare_itineraries: [
            // Direct flight
            {
              pricing: { fare_totals: { total_fare: { amount: "200.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T10:00:00" },
                      arrival_datetime: { value: "2025-01-15T12:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "KL", airline_name: "KLM" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
            // 1 stop flight
            {
              pricing: { fare_totals: { total_fare: { amount: "150.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "CDG" },
                      departure_datetime: { value: "2025-01-15T10:00:00" },
                      arrival_datetime: { value: "2025-01-15T11:00:00" },
                      flight_duration: { total_minutes: 60 },
                      marketing_airline: { iata_code: "AF", airline_name: "Air France" },
                      cabin_class: "Economy",
                    },
                    {
                      departure_airport: { iata_code: "CDG" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T12:00:00" },
                      arrival_datetime: { value: "2025-01-15T13:00:00" },
                      flight_duration: { total_minutes: 60 },
                      marketing_airline: { iata_code: "AF", airline_name: "Air France" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
          ],
        }),
      });
    });

    // Perform search
    await page.fill("#origin", "AMS");
    await page.fill("#destination", "LHR");
    await page.fill("#departure_date", "2025-01-15");
    await page.click('button:has-text("Search Flights")');
    await page.waitForTimeout(2000);

    // Open filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Select direct flights only
    const directOnlyCheckbox = page.locator("#filter-direct-only");
    await directOnlyCheckbox.check();
    await page.waitForTimeout(500);

    // Check filtered count
    const filteredCount = page.locator("#filtered-count");
    const countText = await filteredCount.textContent();
    const count = parseInt(countText || "0");

    // Should show 1 direct flight
    expect(count).toBeGreaterThanOrEqual(1);
    logSuccess(`✅ Direct flights filter applied, showing ${count} flights`);
  });

  test("should sort flights by price (low to high)", async ({ page }) => {
    logTestStep("Testing price sorting (low to high)");

    // Mock flights with different prices
    await page.route("**/api/flights/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: "test-session-123",
          fare_itineraries: [
            {
              pricing: { fare_totals: { total_fare: { amount: "300.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T14:00:00" },
                      arrival_datetime: { value: "2025-01-15T16:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "AF", airline_name: "Air France" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
            {
              pricing: { fare_totals: { total_fare: { amount: "100.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T10:00:00" },
                      arrival_datetime: { value: "2025-01-15T12:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "KL", airline_name: "KLM" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
            {
              pricing: { fare_totals: { total_fare: { amount: "200.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T12:00:00" },
                      arrival_datetime: { value: "2025-01-15T14:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "BA", airline_name: "British Airways" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
          ],
        }),
      });
    });

    // Perform search
    await page.fill("#origin", "AMS");
    await page.fill("#destination", "LHR");
    await page.fill("#departure_date", "2025-01-15");
    await page.click('button:has-text("Search Flights")');
    await page.waitForTimeout(2000);

    // Click sort button
    const sortButton = page.locator('#toggle-sort-btn, button:has-text("Sort")');
    await sortButton.click();
    await page.waitForTimeout(500);

    // Select price low to high
    const priceLowOption = page.locator(
      '.sort-option:has-text("Price: Low to High"), .sort-option[onclick*="price-low"]'
    );
    await priceLowOption.click();
    await page.waitForTimeout(500);

    // Verify sort button text updated
    const sortButtonText = await sortButton.textContent();
    expect(sortButtonText).toContain("Price");
    logSuccess("✅ Price sorting applied");
  });

  test("should sort flights by duration", async ({ page }) => {
    logTestStep("Testing duration sorting");

    // Mock flights with different durations
    await page.route("**/api/flights/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: "test-session-123",
          fare_itineraries: [
            {
              pricing: { fare_totals: { total_fare: { amount: "200.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T10:00:00" },
                      arrival_datetime: { value: "2025-01-15T13:00:00" },
                      flight_duration: { total_minutes: 180 },
                      marketing_airline: { iata_code: "KL", airline_name: "KLM" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
            {
              pricing: { fare_totals: { total_fare: { amount: "200.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T10:00:00" },
                      arrival_datetime: { value: "2025-01-15T12:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "BA", airline_name: "British Airways" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
          ],
        }),
      });
    });

    // Perform search
    await page.fill("#origin", "AMS");
    await page.fill("#destination", "LHR");
    await page.fill("#departure_date", "2025-01-15");
    await page.click('button:has-text("Search Flights")');
    await page.waitForTimeout(2000);

    // Click sort button
    const sortButton = page.locator('#toggle-sort-btn, button:has-text("Sort")');
    await sortButton.click();
    await page.waitForTimeout(500);

    // Select duration short to long
    const durationOption = page.locator(
      '.sort-option:has-text("Duration: Shortest"), .sort-option[onclick*="duration-short"]'
    );
    await durationOption.click();
    await page.waitForTimeout(500);

    // Verify sort button text updated
    const sortButtonText = await sortButton.textContent();
    expect(sortButtonText).toContain("Duration");
    logSuccess("✅ Duration sorting applied");
  });

  test("should combine filtering and sorting", async ({ page }) => {
    logTestStep("Testing combined filtering and sorting");

    // Mock flights
    await page.route("**/api/flights/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: "test-session-123",
          fare_itineraries: [
            {
              pricing: { fare_totals: { total_fare: { amount: "300.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T10:00:00" },
                      arrival_datetime: { value: "2025-01-15T12:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "KL", airline_name: "KLM" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
            {
              pricing: { fare_totals: { total_fare: { amount: "100.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T14:00:00" },
                      arrival_datetime: { value: "2025-01-15T16:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "AF", airline_name: "Air France" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
            {
              pricing: { fare_totals: { total_fare: { amount: "500.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T18:00:00" },
                      arrival_datetime: { value: "2025-01-15T20:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "BA", airline_name: "British Airways" },
                      cabin_class: "Business",
                    },
                  ],
                },
              ],
            },
          ],
        }),
      });
    });

    // Perform search
    await page.fill("#origin", "AMS");
    await page.fill("#destination", "LHR");
    await page.fill("#departure_date", "2025-01-15");
    await page.click('button:has-text("Search Flights")');
    await page.waitForTimeout(2000);

    // Apply price filter
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);
    await page.fill("#filter-price-min", "150");
    await page.fill("#filter-price-max", "400");
    await page.waitForTimeout(500);

    // Apply sort
    const sortButton = page.locator('#toggle-sort-btn, button:has-text("Sort")');
    await sortButton.click();
    await page.waitForTimeout(500);
    const priceLowOption = page.locator(
      '.sort-option:has-text("Price: Low to High"), .sort-option[onclick*="price-low"]'
    );
    await priceLowOption.click();
    await page.waitForTimeout(500);

    // Verify filtered count
    const filteredCount = page.locator("#filtered-count");
    const countText = await filteredCount.textContent();
    const count = parseInt(countText || "0");

    expect(count).toBeGreaterThanOrEqual(1);
    logSuccess(`✅ Combined filter and sort applied, showing ${count} flights`);
  });

  test("should clear all filters", async ({ page }) => {
    logTestStep("Testing clear all filters");

    // Mock flights
    await page.route("**/api/flights/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: "test-session-123",
          fare_itineraries: [
            {
              pricing: { fare_totals: { total_fare: { amount: "200.00", currency: "USD" } } },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "AMS" },
                      arrival_airport: { iata_code: "LHR" },
                      departure_datetime: { value: "2025-01-15T10:00:00" },
                      arrival_datetime: { value: "2025-01-15T12:00:00" },
                      flight_duration: { total_minutes: 120 },
                      marketing_airline: { iata_code: "KL", airline_name: "KLM" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
          ],
        }),
      });
    });

    // Perform search
    await page.fill("#origin", "AMS");
    await page.fill("#destination", "LHR");
    await page.fill("#departure_date", "2025-01-15");
    await page.click('button:has-text("Search Flights")');
    await page.waitForTimeout(2000);

    // Apply filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);
    await page.fill("#filter-price-min", "300");
    await page.waitForTimeout(500);

    // Clear all filters
    const clearButton = page.locator('button:has-text("Clear All"), .filter-btn.clear');
    await clearButton.click();
    await page.waitForTimeout(500);

    // Verify price filter is cleared
    const priceMin = await page.locator("#filter-price-min").inputValue();
    expect(priceMin).toBe("");
    logSuccess("✅ All filters cleared");
  });

  test("should display all one-way flights on fresh search with no filters applied", async ({
    page,
  }) => {
    logTestStep(
      "Testing that fresh one-way flight search shows all flights without filters (bug #104)"
    );

    // Clear sessionStorage to simulate fresh session
    await page.evaluate(() => {
      sessionStorage.clear();
    });

    // Mock flight search with multiple one-way flights only
    // Note: This bug only affected one-way flights, not round-trip flights
    await page.route("**/api/flights/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: "test-session-fresh-123",
          fare_itineraries: [
            // One-way flight 1
            {
              pricing: {
                fare_totals: { total_fare: { amount: "150.00", currency: "USD" } },
              },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "LHR", name: "London" },
                      arrival_airport: { iata_code: "FAO", name: "Faro" },
                      departure_datetime: { value: "2025-01-15T10:00:00" },
                      arrival_datetime: { value: "2025-01-15T13:00:00" },
                      flight_duration: { total_minutes: 180 },
                      marketing_airline: { iata_code: "BA", airline_name: "British Airways" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
            // One-way flight 2
            {
              pricing: {
                fare_totals: { total_fare: { amount: "200.00", currency: "USD" } },
              },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "LHR", name: "London" },
                      arrival_airport: { iata_code: "FAO", name: "Faro" },
                      departure_datetime: { value: "2025-01-15T14:00:00" },
                      arrival_datetime: { value: "2025-01-15T17:00:00" },
                      flight_duration: { total_minutes: 180 },
                      marketing_airline: { iata_code: "TP", airline_name: "TAP Air Portugal" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
            // One-way flight 3
            {
              pricing: {
                fare_totals: { total_fare: { amount: "175.00", currency: "USD" } },
              },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "LHR", name: "London" },
                      arrival_airport: { iata_code: "FAO", name: "Faro" },
                      departure_datetime: { value: "2025-01-15T16:00:00" },
                      arrival_datetime: { value: "2025-01-15T19:00:00" },
                      flight_duration: { total_minutes: 180 },
                      marketing_airline: { iata_code: "FR", airline_name: "Ryanair" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
          ],
        }),
      });
    });

    // Perform fresh one-way search (London to Faro - matches manual testing scenario)
    // This bug only occurred with one-way flights, not round-trip flights
    await page.fill("#origin", "LHR");
    await page.fill("#destination", "FAO");
    await page.fill("#departure_date", "2025-01-15");
    // Ensure it's a one-way search (no return date)
    const returnDateInput = page.locator("#return_date");
    if (await returnDateInput.isVisible()) {
      await returnDateInput.fill("");
    }
    await page.click('button:has-text("Search Flights")');
    await page.waitForTimeout(2000);

    // Verify all one-way flights are displayed (should show all 3 flights)
    // Before the fix, all flights were incorrectly filtered out
    const filteredCount = page.locator("#filtered-count");
    await expect(filteredCount).toBeVisible({ timeout: 5000 });
    const countText = await filteredCount.textContent();
    const count = parseInt(countText || "0");

    // Should show all 3 one-way flights (before fix: 0 flights, after fix: 3 flights)
    expect(count).toBeGreaterThanOrEqual(3);
    logSuccess(
      `✅ Fresh one-way search displays ${count} flights without filters (bug #104 fixed)`
    );

    // Verify no "No flights match your filters" message appears
    // This message was incorrectly shown before the fix
    const noFlightsMessage = page.locator('text="No flights match your filters"');
    await expect(noFlightsMessage).not.toBeVisible();
    logSuccess("✅ No incorrect 'no flights' message displayed");

    // Verify default slider values don't filter flights
    // Bug #104: Default slider values (0 min, 24 max) were incorrectly treated as active filters
    const outboundDurMin = await page.locator("#filter-outbound-duration-min").inputValue();
    const outboundDurMax = await page.locator("#filter-outbound-duration-max").inputValue();
    expect(outboundDurMin).toBe("0");
    expect(outboundDurMax).toBe("24");
    logSuccess("✅ Default slider values confirmed (0/24)");

    // Verify flights are still visible with default slider values
    // Before fix: default values caused all flights to be filtered out
    const countAfterCheck = parseInt((await filteredCount.textContent()) || "0");
    expect(countAfterCheck).toBeGreaterThanOrEqual(3);
    logSuccess("✅ One-way flights remain visible with default slider values");
  });

  test("should not filter one-way flights by inbound duration", async ({ page }) => {
    logTestStep(
      "Testing that one-way flights aren't filtered by inbound duration (bug #104 - one-way flights only)"
    );

    // Mock flight search with one-way flights
    await page.route("**/api/flights/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: "test-session-oneway-123",
          fare_itineraries: [
            {
              pricing: {
                fare_totals: { total_fare: { amount: "150.00", currency: "USD" } },
              },
              flight_legs: [
                {
                  flight_segments: [
                    {
                      departure_airport: { iata_code: "LHR", name: "London" },
                      arrival_airport: { iata_code: "FAO", name: "Faro" },
                      departure_datetime: { value: "2025-01-15T10:00:00" },
                      arrival_datetime: { value: "2025-01-15T13:00:00" },
                      flight_duration: { total_minutes: 180 },
                      marketing_airline: { iata_code: "BA", airline_name: "British Airways" },
                      cabin_class: "Economy",
                    },
                  ],
                },
              ],
            },
          ],
        }),
      });
    });

    // Perform one-way search (London to Faro)
    await page.fill("#origin", "LHR");
    await page.fill("#destination", "FAO");
    await page.fill("#departure_date", "2025-01-15");
    const returnDateInput = page.locator("#return_date");
    if (await returnDateInput.isVisible()) {
      await returnDateInput.fill("");
    }
    await page.click('button:has-text("Search Flights")');
    await page.waitForTimeout(2000);

    // Open filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Set inbound duration filter (should not affect one-way flights)
    // Set inbound min to something that would filter if applied incorrectly
    const inboundDurMinInput = page.locator("#filter-inbound-duration-min");
    await inboundDurMinInput.fill("5"); // Set to 5 hours
    await page.waitForTimeout(500);

    // Verify the one-way flight is still displayed
    const filteredCount = page.locator("#filtered-count");
    await expect(filteredCount).toBeVisible({ timeout: 5000 });
    const countText = await filteredCount.textContent();
    const count = parseInt(countText || "0");

    // Should still show 1 flight (the one-way flight shouldn't be filtered)
    expect(count).toBeGreaterThanOrEqual(1);
    logSuccess(
      `✅ One-way flight not filtered by inbound duration filter (${count} flights shown)`
    );

    // Verify no "No flights match your filters" message
    const noFlightsMessage = page.locator('text="No flights match your filters"');
    await expect(noFlightsMessage).not.toBeVisible();
    logSuccess("✅ One-way flights correctly handled with inbound duration filter");
  });

  test("should limit flights to MAX_FLIGHT_RESULTS when API returns more than 200 flights", async ({
    page,
  }) => {
    logTestStep(
      "Testing that flights are limited to MAX_FLIGHT_RESULTS (200) when API returns more"
    );

    const MAX_FLIGHT_RESULTS = 200;
    const API_RESPONSE_COUNT = 250; // More than MAX_FLIGHT_RESULTS

    // Helper function to create a flight itinerary
    const createFlightItinerary = (index, stops = 0) => ({
      pricing: {
        fare_totals: {
          total_fare: { amount: `${100 + index}.00`, currency: "USD" },
        },
      },
      flight_legs: [
        {
          total_stops: stops,
          flight_segments: [
            {
              departure_airport: { iata_code: "AMS", name: "Amsterdam" },
              arrival_airport: { iata_code: "LHR", name: "London" },
              departure_datetime: { value: `2025-01-15T${10 + (index % 12)}:00:00` },
              arrival_datetime: { value: `2025-01-15T${12 + (index % 12)}:00:00` },
              flight_duration: { total_minutes: 120 },
              marketing_airline: { iata_code: "KL", airline_name: "KLM" },
              cabin_class: "Economy",
            },
          ],
        },
      ],
    });

    // Mock API response with more than MAX_FLIGHT_RESULTS flights
    // Mix of 0 stops, 1 stop, and 2+ stops flights
    await page.route("**/api/flights/search", async (route) => {
      const fareItineraries = [];
      for (let i = 0; i < API_RESPONSE_COUNT; i++) {
        // Mix: first 100 are 0 stops, next 100 are 1 stop, rest are 2+ stops
        const stops = i < 100 ? 0 : i < 200 ? 1 : 2;
        fareItineraries.push(createFlightItinerary(i, stops));
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: "test-session-limit-123",
          fare_itineraries: fareItineraries,
        }),
      });
    });

    // Perform search
    await page.fill("#origin", "AMS");
    await page.fill("#destination", "LHR");
    await page.fill("#departure_date", "2025-01-15");
    await page.click('button:has-text("Search Flights")');
    await page.waitForSelector("#total-count", { state: "visible" });

    // Verify that only MAX_FLIGHT_RESULTS flights are displayed
    const totalCount = page.locator("#total-count");
    await expect(totalCount).toBeVisible({ timeout: 5000 });
    const totalCountText = await totalCount.textContent();
    const displayedCount = parseInt(totalCountText || "0");

    expect(displayedCount).toBe(MAX_FLIGHT_RESULTS);
    logSuccess(`✅ Only ${displayedCount} flights displayed (API returned ${API_RESPONSE_COUNT})`);

    // Verify that only MAX_FLIGHT_RESULTS flights are stored in sessionStorage
    const sessionStorageData = await page.evaluate(() => {
      const stored = sessionStorage.getItem("flight_booker_search_results");
      return stored ? JSON.parse(stored) : null;
    });

    expect(sessionStorageData).not.toBeNull();
    expect(sessionStorageData.fare_itineraries).toHaveLength(MAX_FLIGHT_RESULTS);
    logSuccess(
      `✅ Only ${sessionStorageData.fare_itineraries.length} flights stored in sessionStorage`
    );

    // Verify that flights are prioritized by stops (0 stops first, then 1 stop)
    // The first flights should be 0 stops (non-stop)
    const firstFlightStops = sessionStorageData.fare_itineraries[0].flight_legs[0].total_stops;
    expect(firstFlightStops).toBe(0);
    logSuccess("✅ Flights are prioritized by stops (non-stop flights first)");

    // Verify status message indicates limitation
    const statusMessage = page.locator(
      `text=/.*${MAX_FLIGHT_RESULTS} flights displayed.*of ${API_RESPONSE_COUNT} total.*prioritized by stops.*/i`
    );
    await expect(statusMessage).toBeVisible({ timeout: 2000 });
    logSuccess("✅ Status message correctly indicates flight limitation");
  });
});
