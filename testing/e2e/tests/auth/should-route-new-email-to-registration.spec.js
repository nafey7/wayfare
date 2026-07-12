// spec: testing/specs/auth.md — Section 1, Scenario 1.4
// seed: testing/seed.spec.js

import { test, expect } from '../../../fixtures/auth-fixtures.js';
import { generateTestEmail } from '../../../utils/constants.js';
import { AuthModalPage } from '../../pages/AuthModalPage.js';

test.describe('Auth — Email Check', () => {
  test(
    'should route a new email address to the registration step (§1.4)',
    { tag: '@mock-required' },
    async ({ page }) => {
      const auth = new AuthModalPage(page);
      const newEmail = generateTestEmail('new');

      await auth.open();

      const response = await auth.submitEmail(newEmail);
      expect(response.status()).toBe(200);
      expect((await response.json()).exists).toBe(false);

      await auth.expectRegistrationStep(newEmail);
    },
  );
});
