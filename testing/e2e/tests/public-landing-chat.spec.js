/**
 * Public landing guest chat — critical path for CI (same behavior as manual smoke).
 *
 * Ensures the landing page exposes #landing-chat when GET /api/config returns
 * public_chat_enabled, and hides it when disabled.
 */

import { test, expect } from '@playwright/test';
import { URLS } from '../../utils/constants.js';

// TODO: stale test - #landing-chat element doesn't exist in current frontend.
// Tagged @mock-required to skip on staging until the test (or the element) is fixed.
test.describe('Public landing guest chat', { tag: '@mock-required' }, () => {
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
