// spec: testing/specs/auth.md — Section 3, Scenario 3.1
// seed: testing/seed.spec.js
//
// Note: the plan tags §3.1 `@mock-required`, but the `authenticatedUser`
// fixture is env-aware (local: MailHog register; staging: login with
// STAGING_TEST_USER_* env vars). Login is non-destructive against a shared
// staging user, so we drop the tag and let this run on every staging deploy.

import { test, expect } from '../../../fixtures/auth-fixtures.js';
import { AuthModalPage } from '../../pages/AuthModalPage.js';

test.describe('Auth — Login', () => {
  test('should log in with correct credentials from the modal', async ({
    authenticatedUser,
    page,
  }) => {
    const auth = new AuthModalPage(page);
    const { email, password } = authenticatedUser;

    await auth.open();

    const checkEmailResponse = await auth.submitEmail(email);
    expect(checkEmailResponse.status()).toBe(200);

    await auth.expectLoginStep();

    const loginResponse = await auth.submitLoginPassword(password);
    expect(loginResponse.status()).toBe(200);

    await auth.expectDialogClosed();
    await auth.expectPostLoginRedirect();
  });
});
