import { baseApi } from './baseApi';
import { toCamelCase, toSnakeCase } from '@/utils/transforms';
import type {
  HotelSearchRequest,
  HotelSearchResponse,
  RoomRatesResponse,
  RateRulesResponse,
  HotelBookingRequest,
  HotelBookingResponse,
  HotelBookingDetailsResponse,
  HotelTripDetailsResponse,
  HotelSessionResponse,
  SelectHotelRequest,
  SelectHotelResponse,
  HotelSearchRedirectRequest,
  HotelMyBookingListItem,
  MultistayBookingGroupResponse,
} from '@/types/hotels';
import { parseCoord } from '@/utils/parseCoord';

/** Response from hotel booking-auth (exchange auth_token for access token). */
export interface HotelBookingAuthResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  userId: string;
  sessionId: string | null;
}

export const hotelsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * Search for hotels
     * Uses query (not mutation) for RTK Query caching - enables back/forward navigation
     * to restore results from cache without refetching.
     */
    searchHotels: builder.query<HotelSearchResponse, HotelSearchRequest>({
      query: (body) => ({
        url: '/hotels/search',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => {
        const data = toCamelCase(response) as Record<string, unknown>;
        // Backend returns list as "itineraries"; normalize to "hotels" for frontend contract.
        const list = Array.isArray(data.itineraries) ? data.itineraries : data.hotels;
        if (Array.isArray(list)) {
          data.hotels = list.map((h: Record<string, unknown>) => {
            const lat = parseCoord(h.latitude ?? h.lat);
            const lng = parseCoord(h.longitude ?? h.lng ?? h.lon);
            return {
              ...h,
              id: h.id ?? h.hotelId ?? '',
              name: h.name ?? h.hotelName ?? '',
              starRating: h.starRating ?? h.hotelRating ?? 0,
              latitude: Number.isNaN(lat) ? undefined : lat,
              longitude: Number.isNaN(lng) ? undefined : lng,
              nearbyDistanceKm: typeof h.nearbyDistanceKm === 'number' ? h.nearbyDistanceKm : undefined,
            };
          });
        }
        return data as unknown as HotelSearchResponse;
      },
      keepUnusedDataFor: 0,
    }),

    /**
     * Get more hotel results
     */
    getMoreResults: builder.mutation<
      HotelSearchResponse,
      { sessionId: string; nextToken: string; maxResult?: number; nearbyLocation?: { lat: number; lng: number } }
    >({
      query: (body) => ({
        url: '/hotels/more-results',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => {
        const data = toCamelCase(response) as Record<string, unknown>;
        const list = Array.isArray(data.itineraries) ? data.itineraries : data.hotels;
        if (Array.isArray(list)) {
          data.hotels = list.map((h: Record<string, unknown>) => {
            const lat = parseCoord(h.latitude ?? h.lat);
            const lng = parseCoord(h.longitude ?? h.lng ?? h.lon);
            return {
              ...h,
              id: h.id ?? h.hotelId ?? '',
              name: h.name ?? h.hotelName ?? '',
              starRating: h.starRating ?? h.hotelRating ?? 0,
              latitude: Number.isNaN(lat) ? undefined : lat,
              longitude: Number.isNaN(lng) ? undefined : lng,
              nearbyDistanceKm: typeof h.nearbyDistanceKm === 'number' ? h.nearbyDistanceKm : undefined,
            };
          });
        }
        return data as unknown as HotelSearchResponse;
      },
    }),

    /**
     * Get room rates for a hotel.
     * Backend requires sessionId, tokenId, productId, hotelId.
     */
    getRoomRates: builder.mutation<
      RoomRatesResponse,
      { sessionId: string; tokenId: string; productId: string; hotelId: string }
    >({
      query: (body) => ({
        url: '/hotels/room-rates',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as RoomRatesResponse,
    }),

    /**
     * Get rate rules (cancellation policy, etc.)
     */
    getRateRules: builder.mutation<
      RateRulesResponse,
      {
        sessionId: string;
        tokenId: string;
        productId: string;
        rateBasisId: string;
        internalSessionId: string;
      }
    >({
      query: ({ internalSessionId, ...body }) => ({
        url: `/hotels/rate-rules?internal_session_id=${internalSessionId}`,
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as RateRulesResponse,
    }),

    /**
     * Get hotel session details (for payment/email link flow).
     */
    getHotelSession: builder.query<HotelSessionResponse, string>({
      query: (sessionId) => ({
        url: `/hotels/session/${sessionId}`,
        method: 'POST',
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as HotelSessionResponse,
    }),

    /**
     * Book hotel
     */
    bookHotel: builder.mutation<HotelBookingResponse, HotelBookingRequest>({
      query: (body) => ({
        url: '/hotels/book',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as HotelBookingResponse,
      invalidatesTags: ['Bookings'],
    }),

    /**
     * Get hotel booking details (supplier confirmation + reference number).
     * Used by admin hotel detail page when event has hotelReferenceNumber.
     */
    getHotelBookingDetails: builder.mutation<
      HotelBookingDetailsResponse,
      { supplierConfirmationNum: string; referenceNum: string }
    >({
      query: (body) => ({
        url: '/hotels/booking-details',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as HotelBookingDetailsResponse,
    }),

    /**
     * Get hotel booking details by VOYA reference (user-facing).
     * Used by HotelBookingDetailsPage (e.g. from email link).
     * Backend resolves supplier refs from booking event and calls supplier API.
     */
    getHotelTripDetails: builder.mutation<
      HotelTripDetailsResponse,
      { voyaBookingReference: string; authToken?: string | null }
    >({
      query: (body) => ({
        url: '/hotels/trip-details',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as HotelTripDetailsResponse,
    }),

    /**
     * Exchange short-lived booking token for access token (email link flow).
     * Same contract as flights booking-auth.
     */
    exchangeHotelBookingToken: builder.mutation<
      HotelBookingAuthResponse,
      { authToken: string }
    >({
      query: (body) => ({
        url: '/hotels/booking-auth',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as HotelBookingAuthResponse,
    }),

    /**
     * Select hotel from chat results and get redirect URL to hotel-booker (Select rooms step).
     * Requires session_id from hotel search (e.g. localStorage sessionId).
     */
    selectHotel: builder.mutation<SelectHotelResponse, SelectHotelRequest>({
      query: (body) => ({
        url: '/hotels/select',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as SelectHotelResponse,
    }),

    /**
     * Get redirect URL for full hotel search results (hotel-booker with auto_search).
     * Used by "Click to see full results" in chat.
     * Named hotelSearchRedirect to avoid RTK Query collision with flightsApi.searchRedirect.
     */
    hotelSearchRedirect: builder.mutation<
      { redirectUrl: string },
      HotelSearchRedirectRequest
    >({
      query: (body) => ({
        url: '/hotels/search-redirect',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as { redirectUrl: string },
    }),

    /**
     * GET /hotels/my-bookings — booking_events HOTEL rows (newest first).
     * Amounts are major units when present on events (not payment cents).
     */
    getMyHotelBookings: builder.query<HotelMyBookingListItem[], { limit?: number }>({
      query: ({ limit = 10 }) => `/hotels/my-bookings?limit=${limit}`,
      transformResponse: (response: unknown) =>
        toCamelCase(response) as HotelMyBookingListItem[],
      providesTags: ['Bookings'],
    }),

    /**
     * GET /hotels/multistay-booking-context — fetch all legs of a multi-stay booking group.
     */
    getMultistayBookingContext: builder.query<
      MultistayBookingGroupResponse,
      { voyaBookingReference: string }
    >({
      query: ({ voyaBookingReference }) =>
        `/hotels/multistay-booking-context?voya_booking_reference=${encodeURIComponent(voyaBookingReference)}`,
      transformResponse: (response: unknown) =>
        toCamelCase(response) as MultistayBookingGroupResponse,
    }),
  }),
});

export const {
  useSearchHotelsQuery,
  useLazySearchHotelsQuery,
  useGetMoreResultsMutation,
  useGetRoomRatesMutation,
  useGetRateRulesMutation,
  useGetHotelSessionQuery,
  useBookHotelMutation,
  useGetHotelBookingDetailsMutation,
  useGetHotelTripDetailsMutation,
  useExchangeHotelBookingTokenMutation,
  useSelectHotelMutation,
  useGetMyHotelBookingsQuery,
  useLazyGetMultistayBookingContextQuery,
} = hotelsApi;
