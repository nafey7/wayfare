import { baseApi } from './baseApi';
import { toCamelCase } from '@/utils/transforms';

/** Single booking event (camelCase from API transformResponse) */
export interface AdminBookingEvent {
  id: string;
  userId: string;
  /** User email from users collection; "Unknown" if not found */
  userDisplayName?: string;
  voyaBookingReference: string;
  externalBookingReference: string;
  action: 'BOOKED' | 'CANCELLED';
  timestamp: string;
  eventType: 'FLIGHT' | 'HOTEL';
  /** GDS or LCC (WebFare) for flight bookings; null for hotel or legacy events */
  carrierType?: 'GDS' | 'LCC' | null;
  contactEmail?: string | null;
  airlinePnrCode?: string | null;
  airlinePnrAirlineCode?: string | null;
  airlinePnrAirlineName?: string | null;
  airlinePnrStatus?: string | null;
  paymentIntentId?: string | null;
  /** Reference number from hotel book API; required for hotel booking details API */
  hotelReferenceNumber?: string | null;
  /** Stored payload for admin retry (hotel book API body); only present for admin by-reference */
  payload?: Record<string, unknown> | null;
  /** When the booking was confirmed by the supplier (UTC ISO string) */
  dateBooked?: string | null;
  /** When payment was completed successfully (UTC ISO string) */
  datePaid?: string | null;
  /** When tickets/confirmation was issued (UTC ISO string) */
  dateTicketsIssued?: string | null;
  /** Total original amount of the booking (flight or hotel) */
  amount?: number | null;
  /** True if the booking/ticket confirmation email was sent successfully */
  confirmationEmailSent?: boolean;
  /** Airline PNR codes from trip details (flights; may vary per segment) */
  pnr?: string[] | null;
}

/** Admin all-bookings response */
export interface AdminBookingsResponse {
  events: AdminBookingEvent[];
  total: number;
  limit: number;
  offset: number;
}

/** Admin retry response */
export interface AdminBookingRetryResponse {
  success: boolean;
  voyaBookingReference: string;
  externalBookingReference: string;
}

export const adminBookingsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getAdminBookings: builder.query<
      AdminBookingsResponse,
      { limit?: number; offset?: number }
    >({
      query: ({ limit = 50, offset = 0 }) =>
        `/admin/bookings?limit=${limit}&offset=${offset}`,
      transformResponse: (response: unknown) =>
        toCamelCase(response) as AdminBookingsResponse,
    }),
    getAdminBookingEventByReference: builder.query<
      AdminBookingEvent,
      string
    >({
      query: (voyaBookingReference) =>
        `/admin/bookings/by-reference/${encodeURIComponent(voyaBookingReference)}`,
      transformResponse: (response: unknown) =>
        toCamelCase(response) as AdminBookingEvent,
    }),
    adminRetryBooking: builder.mutation<
      AdminBookingRetryResponse,
      { bookingEventId: string }
    >({
      query: (body) => ({
        url: '/admin/bookings/retry',
        method: 'POST',
        body: { booking_event_id: body.bookingEventId },
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as AdminBookingRetryResponse,
    }),
  }),
});

export const {
  useGetAdminBookingsQuery,
  useGetAdminBookingEventByReferenceQuery,
  useAdminRetryBookingMutation,
} = adminBookingsApi;
