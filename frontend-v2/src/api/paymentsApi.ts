import { baseApi } from './baseApi';
import { toCamelCase, toSnakeCase } from '@/utils/transforms';

/**
 * Booking expiry check request (camelCase; API layer sends snake_case)
 */
export interface BookingExpiryCheckRequest {
  voyaBookingReference: string;
}

/**
 * Booking expiry check response (camelCase from transformResponse)
 */
export interface BookingExpiryCheckResponse {
  isValid: boolean;
  timeRemainingSeconds?: number;
  message?: string;
}

export const paymentsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * Check if booking has expired before confirming payment (GDS flights).
     */
    checkBookingExpiry: builder.mutation<BookingExpiryCheckResponse, BookingExpiryCheckRequest>({
      query: (body) => ({
        url: '/payments/check-booking-expiry',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as BookingExpiryCheckResponse,
    }),
  }),
});

export const { useCheckBookingExpiryMutation } = paymentsApi;
