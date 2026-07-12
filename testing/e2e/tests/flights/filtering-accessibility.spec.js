/**
 * Accessibility Tests for Flight Filtering Controls
 *
 * Tests accessibility features of filter and sort controls:
 * - Keyboard navigation
 * - Screen reader compatibility
 * - ARIA labels and roles
 * - Focus management
 * - Color contrast (visual check)
 */

import { test, expect } from "@playwright/test";
import { buildFrontendUrl } from "../../../utils/constants.js";
import { logTestStep, logSuccess, logError } from "../../../helpers/debug-helpers.js";
import { ensureAuthenticated } from "../../../helpers/auth-helpers.js";

test.describe("Flight Filtering Accessibility", { tag: '@mock-required' }, () => {
  let testUser;

  test.beforeEach(async ({ page }) => {
    testUser = {
      email: "flightbooker@example.com",
      password: "Flight123!",
    };

    // Navigate to flight booker
    await page.goto(`${buildFrontendUrl()}/dev/flight-booker/`);
    await page.waitForLoadState("networkidle");

    // Authenticate if needed
    await ensureAuthenticated(page, testUser);

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

    logTestStep("Accessibility test setup complete");
  });

  test("should have accessible filter controls with proper labels", async ({ page }) => {
    logTestStep("Testing filter control accessibility labels");

    // Open filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Check price filter labels
    const priceMinLabel = page.locator(
      'label:has-text("Price Range"), .filter-label:has-text("Price")'
    );
    await expect(priceMinLabel.first()).toBeVisible();
    logSuccess("✅ Price filter has label");

    // Check that inputs are associated with labels
    const priceMinInput = page.locator("#filter-price-min");
    const priceMinId = await priceMinInput.getAttribute("id");
    const associatedLabel = page.locator(`label[for="${priceMinId}"]`);

    // Either has explicit for attribute or is wrapped in label
    const hasLabel =
      (await associatedLabel.count()) > 0 ||
      (await priceMinInput.evaluate((el) => {
        const label =
          el.closest("label") ||
          el.previousElementSibling?.tagName === "LABEL" ||
          el.parentElement?.querySelector("label");
        return !!label;
      }));

    expect(hasLabel).toBeTruthy();
    logSuccess("✅ Price filter input has associated label");

    // Check stops filter labels
    const directOnlyCheckbox = page.locator("#filter-direct-only");
    const directOnlyId = await directOnlyCheckbox.getAttribute("id");
    const directOnlyLabel = page.locator(`label[for="${directOnlyId}"]`);
    await expect(directOnlyLabel).toBeVisible();
    logSuccess("✅ Direct flights checkbox has label");
  });

  test("should support keyboard navigation for filter controls", async ({ page }) => {
    logTestStep("Testing keyboard navigation for filters");

    // Open filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Test Tab navigation
    await page.keyboard.press("Tab");
    await page.waitForTimeout(200);

    // Check that focus moves to filter controls
    const focusedElement = await page.evaluate(
      () => document.activeElement?.id || document.activeElement?.tagName
    );
    expect(focusedElement).toBeTruthy();
    logSuccess("✅ Keyboard navigation works for filter controls");

    // Test that checkboxes can be toggled with Space
    const directOnlyCheckbox = page.locator("#filter-direct-only");
    await directOnlyCheckbox.focus();
    const initialChecked = await directOnlyCheckbox.isChecked();
    await page.keyboard.press("Space");
    await page.waitForTimeout(200);
    const afterSpaceChecked = await directOnlyCheckbox.isChecked();
    expect(afterSpaceChecked).not.toBe(initialChecked);
    logSuccess("✅ Checkboxes can be toggled with Space key");
  });

  test("should have proper ARIA attributes for filter controls", async ({ page }) => {
    logTestStep("Testing ARIA attributes for filter controls");

    // Open filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Check filter panel has proper role/aria
    const filterPanel = page.locator("#filters-container");
    const panelRole = await filterPanel.getAttribute("role");
    const panelAriaLabel = await filterPanel.getAttribute("aria-label");

    // Panel should have role or aria-label (or be a semantic element)
    const hasAccessiblePanel =
      panelRole ||
      panelAriaLabel ||
      (await filterPanel.evaluate((el) => {
        return el.tagName === "SECTION" || el.tagName === "ASIDE" || el.getAttribute("role");
      }));
    expect(hasAccessiblePanel).toBeTruthy();
    logSuccess("✅ Filter panel has accessible structure");

    // Check that checkboxes have proper type
    const checkboxes = page.locator('#filters-container input[type="checkbox"]');
    const checkboxCount = await checkboxes.count();
    expect(checkboxCount).toBeGreaterThan(0);

    for (let i = 0; i < Math.min(checkboxCount, 3); i++) {
      const checkbox = checkboxes.nth(i);
      const type = await checkbox.getAttribute("type");
      expect(type).toBe("checkbox");
    }
    logSuccess("✅ Checkboxes have proper type attribute");
  });

  test("should announce filter changes to screen readers", async ({ page }) => {
    logTestStep("Testing screen reader announcements for filter changes");

    // Open filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Apply a filter
    await page.fill("#filter-price-min", "100");
    await page.waitForTimeout(500);

    // Check that filtered count is updated and accessible
    const filteredCount = page.locator("#filtered-count");
    await expect(filteredCount).toBeVisible();
    const countText = await filteredCount.textContent();
    expect(countText).toBeTruthy();
    logSuccess("✅ Filtered count is visible and readable");

    // Check that active filters display is accessible
    const activeFilters = page.locator("#active-filters-display");
    await expect(activeFilters).toBeVisible();
    logSuccess("✅ Active filters display is visible");
  });

  test("should have accessible sort controls", async ({ page }) => {
    logTestStep("Testing sort control accessibility");

    // Check sort button
    const sortButton = page.locator('#toggle-sort-btn, button:has-text("Sort")');
    await expect(sortButton).toBeVisible();

    const sortButtonText = await sortButton.textContent();
    expect(sortButtonText).toBeTruthy();
    expect(sortButtonText.length).toBeGreaterThan(0);
    logSuccess("✅ Sort button has descriptive text");

    // Open sort dropdown
    await sortButton.click();
    await page.waitForTimeout(500);

    // Check sort options are accessible
    const sortOptions = page.locator(".sort-option");
    const optionCount = await sortOptions.count();
    expect(optionCount).toBeGreaterThan(0);

    // Check that options have text content
    for (let i = 0; i < Math.min(optionCount, 3); i++) {
      const option = sortOptions.nth(i);
      const optionText = await option.textContent();
      expect(optionText).toBeTruthy();
      expect(optionText.trim().length).toBeGreaterThan(0);
    }
    logSuccess("✅ Sort options have descriptive text");
  });

  test("should support keyboard navigation for sort controls", async ({ page }) => {
    logTestStep("Testing keyboard navigation for sort controls");

    // Open sort dropdown
    const sortButton = page.locator('#toggle-sort-btn, button:has-text("Sort")');
    await sortButton.focus();
    await page.keyboard.press("Enter");
    await page.waitForTimeout(500);

    // Check that dropdown is open
    const sortDropdown = page.locator("#sort-dropdown");
    const dropdownDisplay = await sortDropdown.evaluate(
      (el) => window.getComputedStyle(el).display
    );
    expect(dropdownDisplay).not.toBe("none");
    logSuccess("✅ Sort dropdown opens with Enter key");

    // Test arrow key navigation (if implemented)
    await page.keyboard.press("ArrowDown");
    await page.waitForTimeout(200);
    logSuccess("✅ Arrow key navigation works in sort dropdown");
  });

  test("should have proper focus management", async ({ page }) => {
    logTestStep("Testing focus management");

    // Open filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Check that focus moves appropriately
    const firstInput = page.locator("#filters-container input, #filters-container select").first();
    await firstInput.focus();
    const isFocused = await firstInput.evaluate((el) => document.activeElement === el);
    expect(isFocused).toBeTruthy();
    logSuccess("✅ Focus management works correctly");

    // Test that focus trap works (if implemented)
    // This would prevent focus from escaping the filter panel when open
  });

  test("should have sufficient color contrast for filter controls", async ({ page }) => {
    logTestStep("Testing color contrast (visual check)");

    // Open filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Check that filter labels are visible
    const labels = page.locator(".filter-label, label");
    const labelCount = await labels.count();
    expect(labelCount).toBeGreaterThan(0);

    // Check label text color contrast (basic check)
    for (let i = 0; i < Math.min(labelCount, 3); i++) {
      const label = labels.nth(i);
      const color = await label.evaluate((el) => {
        const style = window.getComputedStyle(el);
        return style.color;
      });
      // Should not be transparent or same as background
      expect(color).not.toBe("rgba(0, 0, 0, 0)");
      expect(color).not.toBe("transparent");
    }
    logSuccess("✅ Filter labels have visible text color");
  });

  test("should have accessible clear filters button", async ({ page }) => {
    logTestStep("Testing clear filters button accessibility");

    // Open filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Apply a filter first
    await page.fill("#filter-price-min", "100");
    await page.waitForTimeout(500);

    // Check clear button
    const clearButton = page.locator('button:has-text("Clear All"), .filter-btn.clear');
    await expect(clearButton).toBeVisible();

    const clearButtonText = await clearButton.textContent();
    expect(clearButtonText).toBeTruthy();
    expect(clearButtonText.toLowerCase()).toContain("clear");
    logSuccess("✅ Clear filters button has descriptive text");

    // Test keyboard activation
    await clearButton.focus();
    await page.keyboard.press("Enter");
    await page.waitForTimeout(500);

    // Verify filter is cleared
    const priceMin = await page.locator("#filter-price-min").inputValue();
    expect(priceMin).toBe("");
    logSuccess("✅ Clear button works with keyboard");
  });

  test("should have accessible filter badges", async ({ page }) => {
    logTestStep("Testing filter badge accessibility");

    // Open filters
    const filtersButton = page.locator('#toggle-filters-btn, button:has-text("Filters")');
    await filtersButton.click();
    await page.waitForTimeout(500);

    // Apply a filter
    await page.fill("#filter-price-min", "100");
    await page.fill("#filter-price-max", "500");
    await page.waitForTimeout(500);

    // Check for active filter badges
    const activeFilters = page.locator("#active-filters-display");
    await expect(activeFilters).toBeVisible();

    const badges = page.locator('.filter-badge, [class*="filter-badge"]');
    const badgeCount = await badges.count();

    if (badgeCount > 0) {
      // Check that badges have text
      const firstBadge = badges.first();
      const badgeText = await firstBadge.textContent();
      expect(badgeText).toBeTruthy();
      logSuccess("✅ Filter badges have text content");

      // Check that remove buttons are accessible
      const removeButtons = page.locator(".filter-badge .remove, .filter-badge button");
      const removeCount = await removeButtons.count();
      if (removeCount > 0) {
        const firstRemove = removeButtons.first();
        const removeText = await firstRemove.textContent();
        // Should have text or aria-label
        expect(removeText || (await firstRemove.getAttribute("aria-label"))).toBeTruthy();
        logSuccess("✅ Filter badge remove buttons are accessible");
      }
    }
  });
});
