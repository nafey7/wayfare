/**
 * Optional local smoke (same assertions as e2e/tests/public-landing-chat.spec.js).
 *
 * Excluded from automated CI via playwright.config.js testIgnore on manual-tests.
 * CI runs: e2e/tests/public-landing-chat.spec.js (npm run test:e2e / test:all).
 * Run manually: npx playwright test manual-tests/public-landing-chat.spec.js
 */

import { test, expect } from '@playwright/test';
import { URLS } from '../utils/constants.js';

test.describe('Public landing guest chat (manual smoke)', () => {
  test('landing loads; #landing-chat matches config public_chat_enabled', async ({
    page,
    request,
  }) => {
    const configRes = await request.get(`${URLS.API_BASE}/config`);
    expect(configRes.ok(), `config HTTP ${configRes.status()}`).toBeTruthy();
    const cfg = await configRes.json();
    const enabled = Boolean(cfg.public_chat_enabled);

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const landingChat = page.locator('#landing-chat');
    if (enabled) {
      await expect(landingChat).toBeVisible({ timeout: 20000 });
    } else {
      await expect(landingChat).toHaveCount(0);
    }
  });
});
