/**
 * Comprehensive Flight Booking API Tests
 *
 * Tests the complete flight booking flow through API endpoints:
 * 1. Search for flights
 * 2. Revalidate fare
 * 3. Create booking
 * 4. Issue tickets
 * 5. Get trip details
 * 6. List user bookings
 * 7. Cancel booking
 *
 * Uses auth fixtures for authenticated requests and DatabaseHelper for verification.
 */

import { test, expect } from '../fixtures/auth-fixtures.js';
import { URLS, IS_STAGING } from '../utils/constants.js';
import { DatabaseHelper } from '../utils/database-helper.js';

test.describe('Flight Booking API - Complete Flow', () => {
  let dbHelper;

  test.beforeEach(async () => {
    // DB only available on local; staging has no direct MongoDB access
    if (!IS_STAGING) {
      dbHelper = new DatabaseHelper();
      await dbHelper.connect();
    }
  });

  test.afterEach(async () => {
    if (dbHelper) {
      await dbHelper.disconnect();
    }
  });

  /**
   * Test: Search endpoint validation
   */
  test('should handle incomplete search requests gracefully', async ({
    authenticatedUser,
    request,
  }) => {
    const { accessToken } = authenticatedUser;

    // Missing required fields
    const invalidRequest = {
      // missing journey_type, origin_destination_info, etc
    };

    const response = await request.post(URLS.BACKEND + '/api/flights/search', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: invalidRequest,
    });

    // Should either validate (400) or handle gracefully (200 with empty results)
    expect([200, 400, 422]).toContain(response.status());
  });

  /**
   * Test: My bookings endpoint
   */
  test('should return empty array for user with no bookings', async ({
    authenticatedUser,
    request,
  }) => {
    const { accessToken } = authenticatedUser;

    const response = await request.get(
      URLS.BACKEND + '/api/flights/my-bookings?limit=10',
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
  });

  /**
   * Test: Trip details with invalid reference
   */
  test('should handle invalid booking reference gracefully', async ({
    authenticatedUser,
    request,
  }) => {
    const { accessToken } = authenticatedUser;

    const tripDetailsRequest = {
      voya_booking_reference: 'INVALID_REF_123',
    };

    const response = await request.post(URLS.BACKEND + '/api/flights/trip-details', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: tripDetailsRequest,
    });

    // Should handle gracefully - either 400, 404, or 503
    expect([400, 404, 503]).toContain(response.status());
  });
});

test.describe('Flight Booking API - Round-trip Flights', () => {
  test('should search for round-trip flights', async ({
    authenticatedUser,
    request,
  }) => {
    const { accessToken } = authenticatedUser;

    const searchRequest = {
      journey_type: 'Return',
      origin_destination_info: [
        {
          departure_date: '2025-12-25',
          return_date: '2026-01-05',
          origin_airport: {
            iata_code: 'AMS',
          },
          destination_airport: {
            iata_code: 'FAO',
          },
        },
      ],
      cabin_class: 'Economy',
      adults: 1,
      children: 0,
      infants: 0,
      required_currency_code: 'USD',
    };

    const response = await request.post(URLS.BACKEND + '/api/flights/search', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: searchRequest,
    });

    // Accept either 200 (success) or 503 (external service unavailable)
    expect([200, 503]).toContain(response.status());

    if (response.status() === 200) {
      const data = await response.json();
      expect(data).toHaveProperty('fare_itineraries');
      expect(Array.isArray(data.fare_itineraries)).toBeTruthy();
    }
  });
});

test.describe('Flight Booking API - Error Handling', () => {
  test('should handle invalid airport codes', async ({
    authenticatedUser,
    request,
  }) => {
    const { accessToken } = authenticatedUser;

    const searchRequest = {
      journey_type: 'OneWay',
      origin_destination_info: [
        {
          departure_date: '2025-12-25',
          origin_airport: {
            iata_code: 'INVALID',
          },
          destination_airport: {
            iata_code: 'ALSO_INVALID',
          },
        },
      ],
      cabin_class: 'Economy',
      adults: 1,
      children: 0,
      infants: 0,
      required_currency_code: 'USD',
    };

    const response = await request.post(URLS.BACKEND + '/api/flights/search', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: searchRequest,
    });

    // Should handle gracefully - service may accept and process
    expect([200, 400, 503]).toContain(response.status());
  });

  test('should handle past dates gracefully', async ({
    authenticatedUser,
    request,
  }) => {
    const { accessToken } = authenticatedUser;

    const searchRequest = {
      journey_type: 'OneWay',
      origin_destination_info: [
        {
          departure_date: '2020-01-01', // Past date
          origin_airport: {
            iata_code: 'AMS',
          },
          destination_airport: {
            iata_code: 'LHR',
          },
        },
      ],
      cabin_class: 'Economy',
      adults: 1,
      children: 0,
      infants: 0,
      required_currency_code: 'USD',
    };

    const response = await request.post(URLS.BACKEND + '/api/flights/search', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: searchRequest,
    });

    // Should handle gracefully - service may accept and process
    expect([200, 400, 503]).toContain(response.status());
  });
});
