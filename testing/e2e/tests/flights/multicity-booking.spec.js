/**
 * Multi-city (Circle) flight booking — per-leg selection and combined payment.
 *
 * Explicitly out of scope for automated E2E until the CI test stack provides
 * deterministic multicity search data and payment mocks.
 * Full happy-path E2E requires FlightLogic + Revolut sandbox and stable routes.
 *
 * Tracking: https://github.com/myvoya/voya/issues/657 (label `testing`).
 */

import { test, expect } from '@playwright/test';

test.describe('Multi-city flight booking', { tag: '@mock-required' }, () => {
  test.skip(
    true,
    'Requires dedicated multicity test data and payment mocks; enable when CI stack is ready. See https://github.com/myvoya/voya/issues/657'
  );

  test('placeholder: search Circle, select legs, pay once, see group on details', async ({
    page,
  }) => {
    await page.goto('/flights/search');
    await expect(page.getByRole('heading', { name: /flight/i })).toBeVisible();
  });
});
