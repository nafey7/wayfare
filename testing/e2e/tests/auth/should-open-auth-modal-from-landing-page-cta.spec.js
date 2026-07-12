// spec: testing/specs/auth.md — Section 1, Scenario 1.1
// seed: testing/seed.spec.js

import { test, expect } from '../../../fixtures/auth-fixtures.js';
import { AuthModalPage } from '../../pages/AuthModalPage.js';

test.describe('Auth — Email Check', () => {
  test('should open auth modal from the landing page CTA', async ({ page }) => {
    const auth = new AuthModalPage(page);

    // Landing hero is visible before the modal covers it.
    await auth.navigate();
    await expect(auth.landingHeroHeading).toBeVisible();
    await expect(auth.landingHeroCta).toBeVisible();

    await auth.openModal();
    await auth.expectEmailStep();

    // Plan §1.1 also calls for a "Google sign-in button is visible" assertion,
    // but GoogleAuthButton renders null when /api/config/google reports
    // `enabled: false` (the default in compose.test.yaml). Presence depends on
    // env config, so we don't assert it here. Scenario 3.7 owns the manual
    // Google OAuth presence check.
  });
});
