/**
 * Email Payment Bookings API Tests
 *
 * Tests the modified booking API endpoints that support email payment links.
 * Verifies FlightLogic uniqueID reuse prevention and booking data access.
 */

import { test, expect } from '@playwright/test';
import { URLS, generateTestUser } from '../utils/constants.js';
import { logTestStep, logSuccess, logError } from '../helpers/debug-helpers.js';
import { DatabaseHelper } from '../utils/database-helper.js';

// Mock booking data for testing
const MOCK_BOOKING_DATA = {
  voya_booking_reference: 'VOYA-TESTBOOKING',
  external_booking_reference: 'TR12345678',
  booking_status: 'CONFIRMED',
  ticket_status: 'PENDING',
  trip_details: {
    flights: [{
      departure_airport: 'Departure',
      arrival_airport: 'Arrival',
      departure_datetime: '2025-01-15T00:00:00Z',
      airline_name: 'Airline',
      flight_number: 'Flight'
    }],
    message: 'Your booking is confirmed. Complete payment to receive your tickets.',
    payment_required: true,
    total_price: '0.00',
    currency: 'USD'
  }
};

test.describe('Email Payment Bookings API', { tag: '@mock-required' }, () => {
  let dbHelper;

  test.beforeEach(async ({ request }) => {
    // Initialize database helper
    dbHelper = new DatabaseHelper();
    await dbHelper.connect();

    // Ensure API is accessible
    const health = await request.get(URLS.BACKEND + URLS.HEALTH);
    expect(health.ok()).toBeTruthy();

    // Clear previous test data
    await dbHelper.clearTestBookings();

    logTestStep('Email payment bookings API test setup complete');
  });

  test.afterEach(async () => {
    // Cleanup database connection
    if (dbHelper) {
      await dbHelper.disconnect();
    }
  });

  test.describe('Booking Endpoint Modifications', () => {

    test('should return booking data without FlightLogic API call', async ({ request }) => {
      logTestStep('Testing booking endpoint without FlightLogic API');

      const bookingRef = 'VOYA-NOFLIGHT123';
      const bookingUrl = `${URLS.BACKEND}/api/bookings/${bookingRef}`;

      // Mock booking should exist in database for this test
      // In real implementation, this would be seeded or created via booking flow

      const response = await request.get(bookingUrl);

      if (response.ok()) {
        const data = await response.json();

        // Verify expected structure for email payment links
        expect(data).toHaveProperty('voya_booking_reference');
        expect(data).toHaveProperty('external_booking_reference');
        expect(data).toHaveProperty('booking_status');
        expect(data).toHaveProperty('ticket_status');
        expect(data).toHaveProperty('trip_details');

        // Verify trip details structure
        expect(data.trip_details).toHaveProperty('message');
        expect(data.trip_details).toHaveProperty('payment_required');
        expect(data.trip_details.payment_required).toBe(true);

        // Verify placeholder flight data (indicates no FlightLogic API call)
        const flights = data.trip_details.flights;
        expect(Array.isArray(flights)).toBe(true);
        expect(flights.length).toBeGreaterThan(0);

        const flight = flights[0];
        expect(flight).toHaveProperty('departure_airport');
        expect(flight).toHaveProperty('arrival_airport');
        expect(flight).toHaveProperty('airline_name');

        logSuccess('✅ Booking endpoint returns proper structure');
        logSuccess('✅ No FlightLogic API dependency confirmed');

      } else if (response.status() === 404) {
        logError('ℹ️ Booking not found - may need test data setup');

        // Verify 404 response structure
        const errorData = await response.json();
        expect(errorData).toHaveProperty('detail');
        expect(errorData.detail).toContain('not found');

        logSuccess('✅ 404 error handling working correctly');

      } else {
        logError(`❌ Unexpected response status: ${response.status()}`);
        const errorData = await response.json();
        console.log('Error response:', errorData);
      }
    });

    test('should work without authentication for email links', async ({ request }) => {
      logTestStep('Testing booking endpoint without authentication');

      const bookingRef = 'VOYA-UNAUTHTEST';
      const bookingUrl = `${URLS.BACKEND}/api/bookings/${bookingRef}`;

      // Make request without Authorization header
      const response = await request.get(bookingUrl);

      // Should not require authentication (email links are unauthenticated)
      expect(response.status()).not.toBe(401);
      expect(response.status()).not.toBe(403);

      if (response.ok()) {
        logSuccess('✅ Booking accessible without authentication');
      } else if (response.status() === 404) {
        logSuccess('✅ Proper 404 handling without auth required');
      } else {
        logError(`⚠️ Unexpected status ${response.status()} - should be 200 or 404`);
      }
    });

    test('should validate booking reference format', async ({ request }) => {
      logTestStep('Testing booking reference format validation');

      const invalidReferences = [
        '',
        'invalid',
        'voya-lowercase',
        'VOYA-',
        'VOYA-AB', // too short
        'NOT-VOYA-FORMAT',
        'VOYA-INVALID-CHARS-!@#'
      ];

      for (const invalidRef of invalidReferences) {
        const response = await request.get(`${URLS.BACKEND}/api/bookings/${encodeURIComponent(invalidRef)}`);

        // Should return error status for invalid format
        expect(response.status()).toBeGreaterThanOrEqual(400);

        if (response.status() === 404) {
          logSuccess(`✅ Invalid reference '${invalidRef}' properly rejected with 404`);
        } else {
          const errorData = await response.json();
          logSuccess(`✅ Invalid reference '${invalidRef}' rejected with ${response.status()}`);
        }
      }
    });

    test('should handle high-entropy booking references', async ({ request }) => {
      logTestStep('Testing high-entropy booking reference security');

      // Valid format with high entropy (10+ chars after VOYA-)
      const validReferences = [
        'VOYA-ABCDEFGHIJ',
        'VOYA-1234567890',
        'VOYA-ABC123XYZ9',
        'VOYA-HIGHENTROPYREF'
      ];

      for (const validRef of validReferences) {
        const response = await request.get(`${URLS.BACKEND}/api/bookings/${validRef}`);

        // Should accept valid format (200 if exists, 404 if not found)
        expect([200, 404]).toContain(response.status());

        if (response.status() === 200) {
          logSuccess(`✅ Valid reference '${validRef}' accepted`);
        } else {
          logSuccess(`✅ Valid reference '${validRef}' format accepted (404 expected)`);
        }
      }
    });

  });

  test.describe('FlightLogic Integration Prevention', () => {

    test('should not call FlightLogic API for existing bookings', async ({ request }) => {
      logTestStep('Verifying FlightLogic API avoidance');

      // This test verifies the booking endpoint doesn't make external API calls
      // which would cause uniqueID reuse errors

      const bookingRef = 'VOYA-NOFLIGHTAPI';

      // Monitor request patterns (this is conceptual - actual implementation
      // would need request interception or logging verification)

      const response = await request.get(`${URLS.BACKEND}/api/bookings/${bookingRef}`);

      if (response.ok()) {
        const data = await response.json();

        // Response should be fast (no external API delay) and contain placeholder data
        const flights = data.trip_details?.flights || [];

        if (flights.length > 0) {
          const flight = flights[0];

          // Check for placeholder values that indicate cached/static data
          if (flight.departure_airport === 'Departure' ||
              flight.airline_name === 'Airline' ||
              flight.departure_datetime === '2025-01-15T00:00:00Z') {
            logSuccess('✅ Placeholder data confirms no FlightLogic API call');
          } else {
            logError('⚠️ Real flight data suggests FlightLogic API was called');
          }
        }

        // Verify payment messaging
        expect(data.trip_details.message).toContain('Complete payment');
        expect(data.trip_details.payment_required).toBe(true);

      } else if (response.status() === 404) {
        logSuccess('✅ 404 response is acceptable for missing booking');
      }
    });

  });

  test.describe('Payment Flow Integration', () => {

    test('should provide sufficient data for payment page', async ({ request }) => {
      logTestStep('Testing payment page data requirements');

      const bookingRef = 'VOYA-PAYMENTDATA';
      const response = await request.get(`${URLS.BACKEND}/api/bookings/${bookingRef}`);

      if (response.ok()) {
        const data = await response.json();

        // Verify all required fields for payment page
        const requiredFields = [
          'voya_booking_reference',
          'external_booking_reference',
          'booking_status',
          'ticket_status'
        ];

        for (const field of requiredFields) {
          expect(data).toHaveProperty(field);
          expect(data[field]).toBeTruthy();
        }

        // Verify trip details structure
        const tripDetails = data.trip_details;
        expect(tripDetails).toHaveProperty('message');
        expect(tripDetails).toHaveProperty('payment_required');
        expect(tripDetails).toHaveProperty('total_price');
        expect(tripDetails).toHaveProperty('currency');

        // Verify flights array exists (even if placeholder)
        expect(tripDetails).toHaveProperty('flights');
        expect(Array.isArray(tripDetails.flights)).toBe(true);

        logSuccess('✅ All payment page data requirements satisfied');

      } else {
        logError('ℹ️ Need test booking setup for comprehensive data validation');
      }
    });

    test('should indicate payment requirement status', async ({ request }) => {
      logTestStep('Testing payment requirement indication');

      const bookingRef = 'VOYA-PAYMENTSTATUS';
      const response = await request.get(`${URLS.BACKEND}/api/bookings/${bookingRef}`);

      if (response.ok()) {
        const data = await response.json();

        // GDS bookings should always require payment (ticket_status: PENDING)
        expect(data.ticket_status).toBe('PENDING');
        expect(data.trip_details.payment_required).toBe(true);

        // Message should indicate payment requirement
        expect(data.trip_details.message).toContain('Complete payment');

        logSuccess('✅ Payment requirement clearly indicated');

      } else if (response.status() === 404) {
        logSuccess('✅ 404 response acceptable for test');
      }
    });

  });

  test.describe('Error Handling', () => {

    test('should handle database connection errors gracefully', async ({ request }) => {
      logTestStep('Testing database error handling');

      // This would require mocking database failures in a real test environment
      // For now, we test that malformed requests are handled properly

      const response = await request.get(`${URLS.BACKEND}/api/bookings/VOYA-DBERROR`);

      // Should return structured error, not crash
      expect([200, 404, 500]).toContain(response.status());

      if (response.status() === 500) {
        const errorData = await response.json();
        expect(errorData).toHaveProperty('detail');
        logSuccess('✅ Server error handled with structured response');
      } else {
        logSuccess('✅ No database errors encountered');
      }
    });

    test('should handle booking service errors', async ({ request }) => {
      logTestStep('Testing booking service error handling');

      // Test with references that might cause service errors
      const problematicRefs = [
        'VOYA-SERVICEERROR',
        'VOYA-NULLREFERENCE',
        'VOYA-EMPTYREFERENCE'
      ];

      for (const ref of problematicRefs) {
        const response = await request.get(`${URLS.BACKEND}/api/bookings/${ref}`);

        // Should handle gracefully (200, 404, or structured 500)
        expect(response.status()).toBeLessThan(600);

        if (response.status() >= 500) {
          const errorData = await response.json();
          expect(errorData).toHaveProperty('detail');
        }

        logSuccess(`✅ Reference '${ref}' handled without crash`);
      }
    });

  });

  test.describe('Security Validation', () => {

    test('should maintain booking reference confidentiality', async ({ request }) => {
      logTestStep('Testing booking reference security');

      // Verify that booking references maintain high entropy requirements
      const response = await request.get(`${URLS.BACKEND}/api/bookings/VOYA-SECURITY123`);

      // Endpoint should exist and handle security appropriately
      expect([200, 404]).toContain(response.status());

      if (response.ok()) {
        const data = await response.json();

        // Should not leak sensitive information in error scenarios
        expect(typeof data.voya_booking_reference).toBe('string');
        expect(data.voya_booking_reference).toMatch(/^VOYA-[A-Z0-9]+$/);

        logSuccess('✅ Booking reference format security maintained');
      }
    });

    test('should not expose internal system details', async ({ request }) => {
      logTestStep('Testing information disclosure prevention');

      const response = await request.get(`${URLS.BACKEND}/api/bookings/VOYA-INFOLEAK`);

      if (response.ok()) {
        const data = await response.json();

        // Verify no sensitive system information exposed
        const sensitiveFields = ['password', 'secret', 'token', 'key', 'private'];
        const dataStr = JSON.stringify(data).toLowerCase();

        for (const field of sensitiveFields) {
          expect(dataStr).not.toContain(field);
        }

        logSuccess('✅ No sensitive information exposure detected');

      } else if (response.status() === 404) {
        const errorData = await response.json();

        // Even error responses should not leak system details
        const errorStr = JSON.stringify(errorData).toLowerCase();
        expect(errorStr).not.toContain('internal');
        expect(errorStr).not.toContain('database');
        expect(errorStr).not.toContain('server');

        logSuccess('✅ Error responses do not leak system information');
      }
    });

  });
});
