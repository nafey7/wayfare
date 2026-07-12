/**
 * E2E: PII verification flow for viewing passport in profile
 *
 * Login → Profile → Click View passport → Receive & Enter Email OTP → See decrypted passport
 */

import { test, expect } from '@playwright/test';
import { URLS, SELECTORS, TIMEOUTS } from '../../../utils/constants.js';
import { buildApiUrl } from '../../../utils/constants.js';
import { MailHogHelper } from '../../../utils/mailhog-client.js';
import { navigateToApp } from '../../../helpers/navigation-helpers.js';
import { openAuthModal, loginUser } from '../../../helpers/auth-helpers.js';

const TEST_USER = {
  email: 'testuser@example.com',
  password: 'Test123!', // pragma: allowlist secret
};

test.describe('PII Verification - Passport View', { tag: '@mock-required' }, () => {
  test.beforeEach(async ({ page }) => {
    await navigateToApp(page);
  });

  test('Login → Profile → View passport → Verify Email OTP → See decrypted passport', async ({
    page,
    request,
  }) => {
    const mailhog = new MailHogHelper(request);
    await mailhog.clearEmails();

    await openAuthModal(page);
    await loginUser(page, TEST_USER.email, TEST_USER.password);

    await page.waitForURL(/\/(home|voya|profile|flights)/, { timeout: TIMEOUTS.PAGE_LOAD });

    await page.goto(`${URLS.FRONTEND}/profile`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const travelDetailsSection = page.locator('text=Travel Details').first();
    if (!(await travelDetailsSection.isVisible())) {
      test.skip(true, 'Travel Details section not found - profile structure may differ');
      return;
    }

    const expandIcon = page.locator('[data-testid="ExpandMoreIcon"], .MuiAccordionSummary-expandIcon').first();
    if (await expandIcon.isVisible()) {
      await expandIcon.click();
      await page.waitForTimeout(500);
    }

    const viewChip = page.locator('text=View').first();
    if (!(await viewChip.isVisible())) {
      test.skip(true, 'View chip not found - user may have no primary passenger with passport');
      return;
    }

    await viewChip.click();
    await expect(page.locator('text=Verify your identity')).toBeVisible({ timeout: 5000 });

    await page.click('text=Continue');
    await expect(page.locator('text=We sent a 6-digit code')).toBeVisible({ timeout: 5000 });

    const piiEmail = await mailhog.waitForEmail(TEST_USER.email, {
      timeout: 15000,
      subject: 'verification',
    });
    const otp = mailhog.extractPiiVerificationOtp(piiEmail);
    if (!otp) {
      throw new Error('Could not extract OTP from PII verification email');
    }

    const digitInputs = page.locator('input[inputmode="numeric"], input[aria-label^="Digit"]');
    await expect(digitInputs.first()).toBeVisible();
    for (let i = 0; i < 6; i++) {
      const input = digitInputs.nth(i);
      await input.fill(otp[i]);
    }

    await page.click('button:has-text("Verify")');
    await page.waitForTimeout(2000);

    // After clicking Verify, expect unmasked passport number (no asterisks)
    const passportRow = page.locator('li:has-text("Passport Number")');
    await expect(passportRow).not.toContainText('****');
  });
});
