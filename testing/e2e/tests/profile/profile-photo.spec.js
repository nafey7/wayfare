/**
 * E2E: Profile photo upload, persistence, and delete.
 *
 * Hits the live MinIO + imgproxy stack defined in compose.test.yaml
 * (or compose.dev.yaml for local runs) — no AWS calls.
 *
 * Flow:
 *   1. Login.
 *   2. Navigate to /profile.
 *   3. Upload a small generated JPEG → header avatar switches to <img>.
 *   4. Reload — avatar persists.
 *   5. Click Remove → confirm → avatar reverts to initials fallback.
 */

import { test, expect } from '@playwright/test';
import { URLS, TIMEOUTS } from '../../../utils/constants.js';
import { navigateToApp } from '../../../helpers/navigation-helpers.js';
import { openAuthModal, loginUser } from '../../../helpers/auth-helpers.js';

const TEST_USER = {
  email: 'testuser@example.com',
  password: 'Test123!', // pragma: allowlist secret
};

// Minimal valid JPEG (red 2x2 pixel) — enough to pass Pillow validation server-side.
const TINY_JPEG_BASE64 =
  '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAACAAIBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAAB//EABoQAAEFAQAAAAAAAAAAAAAAAAQAAQIDExX/2gAIAQEAAD8AsXIzPRsq8//Z';

test.describe('Profile Photo Upload', { tag: '@mock-required' }, () => {
  test.beforeEach(async ({ page }) => {
    await navigateToApp(page);
  });

  test('Upload → persists across reload → delete reverts to initials', async ({
    page,
  }) => {
    await openAuthModal(page);
    await loginUser(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL(/\/(home|voya|profile|flights)/, {
      timeout: TIMEOUTS.PAGE_LOAD,
    });

    await page.goto(`${URLS.FRONTEND}/profile`, { waitUntil: 'networkidle' });

    const uploadButton = page
      .getByRole('button', { name: /upload profile photo|change profile photo/i })
      .first();
    await expect(uploadButton).toBeVisible({ timeout: 5000 });

    // Use the hidden file input directly — drag/drop is flaky in headless.
    const fileInput = page.getByTestId('avatar-upload-input');
    await fileInput.setInputFiles({
      name: 'avatar-valid.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.from(TINY_JPEG_BASE64, 'base64'),
    });

    // Header avatar should switch from initials to an <img> whose src goes via imgproxy.
    const avatarImg = page.locator('img[alt*="profile photo"]').first();
    await expect(avatarImg).toBeVisible({ timeout: 10_000 });
    await expect(avatarImg).toHaveAttribute('src', /\/imgproxy\//);

    // Reload — the new photo should still be there.
    await page.reload({ waitUntil: 'networkidle' });
    await expect(page.locator('img[alt*="profile photo"]').first()).toBeVisible();

    // Delete flow (confirm dialog).
    page.once('dialog', (dialog) => dialog.accept());
    await page
      .getByRole('button', { name: /remove profile photo/i })
      .click();

    await expect(
      page.getByRole('button', { name: /upload profile photo/i })
    ).toBeVisible({ timeout: 5000 });
  });
});
