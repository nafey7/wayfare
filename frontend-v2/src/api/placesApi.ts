import { baseApi } from './baseApi';

export interface PlaceImageUrlResponse {
  imageUrl: string;
}

export interface PlacePhotoRef {
  name: string;
  widthPx?: number | null;
  heightPx?: number | null;
}

export interface PlaceSearchResult {
  id: string;
  displayName: string;
  formattedAddress?: string | null;
  photos: PlacePhotoRef[];
  rating?: number | null;
}

export interface PlaceSearchResponse {
  places: PlaceSearchResult[];
  nextPageToken?: string | null;
}

/**
 * Build a proxy media URL for a Place photo reference.
 * The backend serves it through `/api/places/photos/{resource_name}/media`,
 * which requires JWT — pair with `AuthenticatedImage`.
 */
export function buildPlacePhotoProxyUrl(
  photoName: string,
  maxWidthPx = 800,
): string {
  // photoName is a slash-delimited resource path (e.g. "places/.../photos/..."); do not encodeURIComponent.
  return `/api/places/photos/${photoName}/media?max_width_px=${maxWidthPx}`;
}

export const placesApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * Resolve place name to proxy image URL via Google Places.
     * Use HotelName, City for better match quality.
     * JWT required. Returns protected URL; fetch with Authorization for blob render.
     */
    getPlaceImageUrl: builder.query<
      PlaceImageUrlResponse,
      { place: string; maxWidthPx?: number }
    >({
      query: ({ place, maxWidthPx = 400 }) => ({
        url: '/places/image-url',
        params: {
          place: place.trim(),
          max_width_px: maxWidthPx,
        },
      }),
      keepUnusedDataFor: 1800,
    }),

    /**
     * Text-search for a place and return its photo references.
     * Used by the hotel detail gallery to populate multiple thumbnails
     * (each ref is rendered via `buildPlacePhotoProxyUrl` + AuthenticatedImage).
     */
    searchPlace: builder.query<
      PlaceSearchResponse,
      { textQuery: string; pageSize?: number }
    >({
      query: ({ textQuery, pageSize = 1 }) => ({
        url: '/places/search',
        method: 'POST',
        body: {
          textQuery: textQuery.trim(),
          pageSize,
        },
      }),
      keepUnusedDataFor: 1800,
    }),
  }),
});

export const { useLazyGetPlaceImageUrlQuery, useLazySearchPlaceQuery } = placesApi;
