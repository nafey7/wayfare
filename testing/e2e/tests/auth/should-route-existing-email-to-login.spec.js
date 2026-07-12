// spec: testing/specs/auth.md — Section 1, Scenario 1.5
// seed: testing/seed.spec.js
//
// Note: the plan tags §1.5 `@mock-required`, but the `authenticatedUser`
// fixture is env-aware (local: MailHog register; staging: login with
// STAGING_TEST_USER_* env vars) and this assertion set only reads the email +
// checks the login-step DOM (non-destructive). Leaving the tag off so the
// post-staging-deploy E2E job exercises real staging auth on every deploy.

import { test, expect } from '../../../fixtures/auth-fixtures.js';
import { AuthModalPage } from '../../pages/AuthModalPage.js';

test.describe('Auth — Email Check', () => {
  test(
    'should route an existing verified email to the login step (§1.5)',
    async ({ authenticatedUser, page }) => {
      const auth = new AuthModalPage(page);
      const { email } = authenticatedUser;

      await auth.open();

      const response = await auth.submitEmail(email);
      expect(response.status()).toBe(200);
      expect((await response.json()).exists).toBe(true);

      await auth.expectLoginStep(email);

      // Info alert carries the "please enter your password" copy. Scope to the
      // alert role — the same text also appears in a sibling <p> in the dialog.
      await expect(
        auth.dialog.getByRole('alert').filter({ hasText: /please enter your password/i }),
      ).toBeVisible();
    },
  );
});
