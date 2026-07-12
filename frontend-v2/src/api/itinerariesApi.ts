import { baseApi } from './baseApi';
import { toCamelCase, toSnakeCase } from '@/utils/transforms';
import type { SavedItinerary, SaveItineraryRequest } from '@/types/itineraries';
import type { TripMeta } from '@/store/slices/uiSlice';

export interface GenerateItineraryResult {
  savedItineraryId: string;
  structuredItinerary: Record<string, unknown>;
  tripMeta: TripMeta;
}

export interface GenerateItineraryBody {
  destination: string;
  origin?: string;
  departureDate?: string;
  returnDate?: string;
  numDays?: number;
  adults?: number;
  children?: number;
  interests?: string[];
}

export const itinerariesApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * List saved itineraries for the current user.
     */
    getItineraries: builder.query<SavedItinerary[], void>({
      query: () => 'itineraries',
      providesTags: (result) =>
        result
          ? [
              ...result.map(({ id }) => ({
                type: 'SavedItineraries' as const,
                id,
              })),
              { type: 'SavedItineraries', id: 'LIST' },
            ]
          : [{ type: 'SavedItineraries', id: 'LIST' }],
      transformResponse: (response: unknown) =>
        (Array.isArray(response)
          ? response.map((item) => toCamelCase(item))
          : []) as SavedItinerary[],
    }),

    /**
     * Get single saved itinerary by ID.
     */
    getItinerary: builder.query<SavedItinerary, string>({
      query: (id) => `itineraries/${id}`,
      providesTags: (_, __, id) => [{ type: 'SavedItineraries', id }],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as SavedItinerary,
    }),

    /**
     * Save an itinerary (from chat).
     */
    saveItinerary: builder.mutation<SavedItinerary, SaveItineraryRequest>({
      query: (body) => ({
        url: 'itineraries',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      invalidatesTags: (result) =>
        result
          ? [
              { type: 'SavedItineraries', id: 'LIST' },
              { type: 'SavedItineraries', id: result.id },
            ]
          : [{ type: 'SavedItineraries', id: 'LIST' }],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as SavedItinerary,
    }),

    /**
     * Generate an itinerary directly from the Day Plan form (no chat overhead).
     */
    generateItinerary: builder.mutation<GenerateItineraryResult, GenerateItineraryBody>({
      query: (body) => ({
        url: 'itinerary/generate',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      invalidatesTags: [{ type: 'SavedItineraries', id: 'LIST' }],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as GenerateItineraryResult,
    }),

    /**
     * Delete a saved itinerary.
     */
    deleteItinerary: builder.mutation<void, string>({
      query: (id) => ({
        url: `itineraries/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (_, __, id) => [
        { type: 'SavedItineraries', id },
        { type: 'SavedItineraries', id: 'LIST' },
      ],
    }),
  }),
});

export const {
  useGetItinerariesQuery,
  useLazyGetItinerariesQuery,
  useGetItineraryQuery,
  useLazyGetItineraryQuery,
  useSaveItineraryMutation,
  useGenerateItineraryMutation,
  useDeleteItineraryMutation,
} = itinerariesApi;
