/**
 * Homepage smoke test - asserts the public landing page renders
 * the expected hero content. Works on local and staging.
 */
import { test, expect } from '@playwright/test';

test.describe('Public landing page', () => {
  test('renders hero with expected headline and CTA', async ({ page }) => {
    await page.goto('/');

    // Hero headline
    await expect(
      page.getByRole('heading', { level: 1, name: 'Your next trip, planned in minutes.' })
    ).toBeVisible();

    // Primary CTA — the V2 landing hero chat input. The page now renders
    // multiple inputs with the same "Chat with Voya AI" aria-label (hero,
    // closing section, chat panel), so target the hero by its stable id.
    await expect(page.locator('#landing-hero-search-input')).toBeVisible();
  });
});
