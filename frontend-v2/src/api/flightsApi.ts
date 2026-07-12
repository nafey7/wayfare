import { baseApi } from './baseApi';
import { toCamelCase, toSnakeCase } from '@/utils/transforms';
import type {
  FlightSelectRequest,
  FlightBookingResponse,
  FlightBookingListItem,

} from '@/types/flights';
import type {
  FlightSearchRequestBackend,
  FlightSearchResponseCamel,
  FlightFareRulesResponseCamel,
} from '@/types/flightBackend';

/** Revalidation response in camelCase (from API transformResponse) */
export interface RevalidateFlightResponse {
  sessionId: string;
  fareSourceCode: string;
  returnFareSourceCode?: string | null;
  isFareAvailable: boolean;
  validatedFareItineraries: unknown[];
  availableExtraServices?: unknown | null;
  errors?: unknown[] | null;
}

/** Flight book payload in camelCase; API layer converts to snake_case */
export type FlightBookRequestCamel = Record<string, unknown>;

export const flightsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * Search for flights
     * Backend returns snake_case (session_id, fare_itineraries).
     * Converted to query for automatic caching (back/forward navigation)
     */
    searchFlights: builder.query<
      FlightSearchResponseCamel,
      FlightSearchRequestBackend
    >({
      query: (body) => ({
        url: '/flights/search',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as FlightSearchResponseCamel,
      keepUnusedDataFor: 0,
    }),

    /**
     * Select a flight and create booking session
     */
    selectFlight: builder.mutation<{ sessionId: string; redirectUrl: string }, FlightSelectRequest>(
      {
        query: (body) => ({
          url: '/flights/select',
          method: 'POST',
          body: toSnakeCase(body),
        }),
        transformResponse: (response: unknown) => toCamelCase(response) as { sessionId: string; redirectUrl: string },
      }
    ),

    /**
     * Revalidate flight fare
     */
    revalidateFlight: builder.mutation<
      RevalidateFlightResponse,
      {
        sessionId: string;
        fareSourceCode: string;
        adults: number;
        children?: number;
        infants?: number;
      }
    >({
      query: (body) => ({
        url: '/flights/revalidate',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as RevalidateFlightResponse,
    }),

    /**
     * Get fare rules
     */
    getFareRules: builder.mutation<
      FlightFareRulesResponseCamel,
      { sessionId: string; fareSourceCode: string }
    >({
      query: (body) => ({
        url: '/flights/fare-rules',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as FlightFareRulesResponseCamel,
    }),

    /**
     * Get flight session details
     */
    getFlightSession: builder.query<
      { sessionId: string; selectedFlight: unknown; searchParams: unknown; userData: unknown },
      string
    >({
      query: (sessionId) => `/flights/session/${sessionId}`,
      transformResponse: (response: unknown) =>
        toCamelCase(response) as { sessionId: string; selectedFlight: unknown; searchParams: unknown; userData: unknown },
    }),

    /**
     * Book flight from session
     */
    bookFlightFromSession: builder.mutation<
      FlightBookingResponse,
      { sessionId: string; passengerData: { passengers: unknown[]; paymentIntentId?: string } }
    >({
      query: ({ sessionId, passengerData }) => ({
        url: `/flights/book-from-session/${sessionId}`,
        method: 'POST',
        body: toSnakeCase(passengerData),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as FlightBookingResponse,
      invalidatesTags: ['Bookings'],
    }),

    /**
     * Book flight directly.
     * Accepts camelCase payload; API layer converts to snake_case.
     */
    bookFlight: builder.mutation<FlightBookingResponse, FlightBookRequestCamel>({
      query: (body) => ({
        url: '/flights/book',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as FlightBookingResponse,
      invalidatesTags: ['Bookings'],
    }),

    /**
     * GET /flights/my-bookings — stable list contract (`FlightBookingListItem` / OpenAPI).
     * Amounts are major units when present on booking_events (not payment cents).
     */
    getMyBookings: builder.query<FlightBookingListItem[], { limit?: number }>({
      query: ({ limit = 10 }) => `/flights/my-bookings?limit=${limit}`,
      transformResponse: (response: unknown) =>
        toCamelCase(response) as FlightBookingListItem[],

      providesTags: ['Bookings'],
    }),

    /**
     * Exchange short-lived booking auth token (from email link) for session tokens.
     * No auth header required; used when user opens /flights/bookings/:ref or /flights/payment/:ref with ?auth_token=...
     */
    exchangeBookingToken: builder.mutation<
      { accessToken: string; refreshToken: string; tokenType: string; userId: string; sessionId: string | null },
      { authToken: string }
    >({
      query: (body) => ({
        url: '/flights/booking-auth',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as {
          accessToken: string;
          refreshToken: string;
          tokenType: string;
          userId: string;
          sessionId: string | null;
        },
    }),

    /**
     * Multicity: Mongo-backed group (parent ref + all leg VOYA refs) for booking details UI.
     */
    getMulticityBookingContext: builder.query<
      {
        parentVoyaBookingReference: string | null;
        legs: Array<{
          voyaBookingReference: string;
          externalBookingReference?: string | null;
          ticketStatus?: string | null;
          departureAirportIata?: string | null;
        }>;
      },
      { voyaBookingReference: string }
    >({
      query: ({ voyaBookingReference }) =>
        `/flights/multicity-booking-context?voya_booking_reference=${encodeURIComponent(voyaBookingReference)}`,
      transformResponse: (response: unknown) =>
        toCamelCase(response) as {
          parentVoyaBookingReference: string | null;
          legs: Array<{
            voyaBookingReference: string;
            externalBookingReference?: string | null;
            ticketStatus?: string | null;
            departureAirportIata?: string | null;
          }>;
        },
    }),

    /**
     * Report partial multicity leg booking after payment (server logs + Slack in production).
     */
    reportMulticityPartialBooking: builder.mutation<
      { status: string },
      {
        multicityGroupReference: string;
        revolutOrderId: string;
        legsBookedCount: number;
        legsTotal: number;
        lastError: string;
        bookedVoyaReferences: string[];
      }
    >({
      query: (body) => ({
        url: '/flights/multicity-partial-booking-report',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as { status: string },
    }),

    /**
     * Get trip details
     */
    getTripDetails: builder.mutation<
      unknown,
      { externalBookingReference?: string; voyaBookingReference?: string }
    >({
      query: (body) => ({
        url: '/flights/trip-details',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response),
    }),

    /**
     * Issue tickets for a GDS booking (after payment).
     */
    issueTicket: builder.mutation<
      { success: boolean; externalBookingReference: string; environment?: string; errors?: unknown[] },
      { voyaBookingReference: string; paymentId: string }
    >({
      query: (body) => ({
        url: '/flights/issue_ticket',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as { success: boolean; externalBookingReference: string; environment?: string; errors?: unknown[] },
      invalidatesTags: ['Bookings'],
    }),

    /**
     * Get search redirect URL to full flight search results
     */
    searchRedirect: builder.mutation<{ redirectUrl: string }, { sessionId: string }>({
      query: (body) => ({
        url: '/flights/search-redirect',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as { redirectUrl: string },
    }),

    /**
     * Search airports by query
     */
    searchAirports: builder.query<
      Array<{
        iata: string;
        name: string;
        city: string;
        state?: string;
        country: string;
      }>,
      { query: string; limit?: number }
    >({
      query: ({ query, limit = 50 }) =>
        `/airports/search?query=${encodeURIComponent(query)}&limit=${limit}`,
    }),

    /**
     * Resolve city/airport name to IATA code (mirrors flight-booker resolveAirport).
     * Used when user enters city name so search API receives iata_code.
     */
    resolveAirport: builder.query<
      {
        iataCode: string;
        name?: string;
        city?: string;
        country?: string;
        latitude?: number | null;
        longitude?: number | null;
      },
      string
    >({
      query: (query) =>
        `/airports/resolve?query=${encodeURIComponent(query)}`,
      transformResponse: (response: unknown) => {
        const raw = response as {
          iata_code?: string;
          name?: string;
          city?: string;
          country?: string;
          latitude?: number | null;
          longitude?: number | null;
        };
        return {
          iataCode: raw.iata_code ?? '',
          name: raw.name,
          city: raw.city,
          country: raw.country,
          latitude: raw.latitude ?? null,
          longitude: raw.longitude ?? null,
        };
      },
    }),
  }),
});

export const {
  useSearchFlightsQuery,
  useLazySearchFlightsQuery,
  useSelectFlightMutation,
  useRevalidateFlightMutation,
  useGetFareRulesMutation,
  useGetFlightSessionQuery,
  useBookFlightFromSessionMutation,
  useBookFlightMutation,
  useGetMyBookingsQuery,
  useGetMulticityBookingContextQuery,
  useReportMulticityPartialBookingMutation,
  useGetTripDetailsMutation,
  useIssueTicketMutation,
  useSearchRedirectMutation,
  useSearchAirportsQuery,
  useResolveAirportQuery,
  useLazyResolveAirportQuery,
  useExchangeBookingTokenMutation,
} = flightsApi;
