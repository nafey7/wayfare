// spec: testing/specs/auth.md — Section 2, Scenario 2.1
// seed: testing/seed.spec.js

import { test, expect } from '../../../fixtures/auth-fixtures.js';
import { TIMEOUTS, generateTestUser } from '../../../utils/constants.js';
import { MailHogHelper } from '../../../utils/mailhog-client.js';
import { AuthModalPage } from '../../pages/AuthModalPage.js';

test.describe('Auth — Registration', () => {
  test(
    'should initiate new user registration and deliver a verification email',
    { tag: '@mock-required' },
    async ({ page, request }) => {
      // waitForEmail(email) filters by recipient, so no upfront inbox clear
      // is needed. A global clearEmails() here races with the authenticatedUser
      // fixture (used by §1.5 and §3.1) which polls for its own activation email
      // on the default workers: 3 — that email could vanish mid-flight.
      const mailhog = new MailHogHelper(request);
      const testUser = generateTestUser();
      const auth = new AuthModalPage(page);

      await auth.open();

      const checkEmailResponse = await auth.submitEmail(testUser.email);
      expect(checkEmailResponse.status()).toBe(200);

      await auth.expectRegistrationStep();

      const registerResponse = await auth.submitRegistrationDetails({
        firstName: testUser.firstName,
        lastName: testUser.lastName,
      });
      expect(registerResponse.status()).toBe(200);

      // Actual DOM copy: "Registration initiated. Please check your email to complete setup."
      await expect(auth.registrationSuccessAlert).toBeVisible({
        timeout: TIMEOUTS.MODAL_APPEAR,
      });
      await expect(auth.dialog.getByText(/registration initiated/i)).toBeVisible();
      await expect(auth.postRegistrationGotItButton).toBeVisible();

      const email = await mailhog.waitForEmail(testUser.email, {
        timeout: TIMEOUTS.EMAIL_DELIVERY,
      });
      expect(email).toBeTruthy();
    },
  );
});
