/**
 * Public + authenticated itinerary place images (Phase 6 — E2E with HTTP mocks).
 *
 * Mocks chat and photo proxy responses so CI does not call Gemini or Google Places.
 * Covers: guest session headers + public photo URL, JWT + authenticated photo URL,
 * guest Places lazy load (scroll root–aware IO; no fetch until card is near/in view).
 */

import { test, expect } from '@playwright/test';
import { URLS } from '../../../utils/constants.js';

const TAG = '@mock-required';

/** 1×1 transparent PNG */
const TINY_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64'
);

function structuredItineraryWithImageOnLastDay(frontOrigin, lastDay) {
  const items = [];
  for (let day = 1; day < lastDay; day += 1) {
    items.push({
      day,
      title: `Stop ${day}`,
      description: 'Explore the area.',
      iconType: 'place',
    });
  }
  items.push({
    day: lastDay,
    title: 'Photo stop',
    description: 'This card carries a Places image URL.',
    iconType: 'place',
    imageUrl: `${frontOrigin}/api/places/photos/places/ChIJ_e2e_test/photos/AWn5SU_test/media?maxWidthPx=400`,
  });
  return { itineraryItems: items };
}

function itineraryChatResponse(frontOrigin, { useGuestToken }) {
  const lastDay = 20;
  const structured = structuredItineraryWithImageOnLastDay(frontOrigin, lastDay);
  return {
    message: 'Here is your itinerary (E2E mock).',
    chat_id: '00000000-0000-4000-8000-0000000000e2',
    intent_name: 'itinerary',
    confidence: 1,
    type: 'itinerary_results',
    places_session_token: useGuestToken ? 'e2e-mock-places-session-token' : null,
    data: {
      destination: 'E2E Destination',
      structured_itinerary: structured,
    },
  };
}

async function installConfigRoute(page) {
  await page.route('**/api/config', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        chat_feedback_enabled: false,
        public_chat_enabled: true,
        langgraph_flights_enabled: false,
        langgraph_hotels_enabled: false,
        environment: 'test',
      }),
    });
  });
}

async function installPhotoMocks(page) {
  await page.route('**/api/public/places/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'image/png',
      body: TINY_PNG,
    });
  });
  await page.route('**/api/places/photos/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'image/png',
      body: TINY_PNG,
    });
  });
}

test.describe('Itinerary place images (mocked APIs)', { tag: TAG }, () => {
  test('guest: public chat returns itinerary; place image loads after scroll (lazy)', async ({
    page,
  }) => {
    const origin = URLS.FRONTEND;
    const chatJson = itineraryChatResponse(origin, { useGuestToken: true });

    await installConfigRoute(page);
    await installPhotoMocks(page);
    await page.route('**/api/public/chat/message', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(chatJson),
      });
    });

    let photoRequests = 0;
    page.on('request', (req) => {
      if (req.url().includes('/api/public/places/')) photoRequests += 1;
    });

    await page.goto(`${origin}/public/chat`);
    await page.waitForLoadState('domcontentloaded');

    const input = page.locator('input[placeholder="Type your message..."], textarea[placeholder*="message"]').first();
    await input.waitFor({ state: 'visible', timeout: 30000 });
    await input.fill('Plan a weekend in E2E City');
    await input.press('Enter');

    await page.waitForURL(/\/public\/chat\/itinerary/, { timeout: 30000 });

    const lastDay = chatJson.data.structured_itinerary.itineraryItems.length;

    await expect(page.getByRole('img', { name: `Day ${lastDay}` })).toHaveCount(0);
    expect(photoRequests, 'no public Places fetch until the image card is in view').toBe(0);

    await page.getByText(`Day ${lastDay}: Photo stop`).scrollIntoViewIfNeeded();

    const img = page.getByRole('img', { name: `Day ${lastDay}` });
    await expect(img).toBeVisible({ timeout: 20000 });
    const naturalWidth = await img.evaluate((el) => el.naturalWidth);
    expect(naturalWidth).toBeGreaterThan(0);
    expect(photoRequests).toBeGreaterThan(0);
  });

  test('authenticated: chat itinerary loads JWT-proxied place image', async ({
    page,
    request,
  }) => {
    const login = await request.post(`${URLS.API_BASE}/auth/login`, {
      data: {
        email: 'testuser@example.com',
        password: 'Test123!', // pragma: allowlist secret
      },
    });
    test.skip(!login.ok(), `login failed: HTTP ${login.status()}`);
    const { access_token: accessToken } = await login.json();
    expect(accessToken).toBeTruthy();

    const origin = URLS.FRONTEND;
    const chatJson = itineraryChatResponse(origin, { useGuestToken: false });

    await installConfigRoute(page);
    await installPhotoMocks(page);
    await page.route('**/api/chat/message', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(chatJson),
      });
    });

    await page.goto(`${origin}/chat`);
    await page.waitForLoadState('domcontentloaded');
    await page.evaluate((token) => {
      localStorage.setItem('Authorization', token);
    }, accessToken);
    await page.reload();
    await page.waitForLoadState('networkidle');

    const input = page.locator('input[placeholder="Type your message..."], textarea[placeholder*="message"]').first();
    await input.waitFor({ state: 'visible', timeout: 30000 });
    await input.fill('Weekend itinerary please');
    await input.press('Enter');

    await page.waitForURL(/\/itinerary(\?|$)/, { timeout: 30000 });

    const lastDay = chatJson.data.structured_itinerary.itineraryItems.length;
    await page.getByText(`Day ${lastDay}: Photo stop`).scrollIntoViewIfNeeded();
    const img = page.getByRole('img', { name: `Day ${lastDay}` });
    await expect(img).toBeVisible({ timeout: 20000 });
    const naturalWidth = await img.evaluate((el) => el.naturalWidth);
    expect(naturalWidth).toBeGreaterThan(0);
  });
});
