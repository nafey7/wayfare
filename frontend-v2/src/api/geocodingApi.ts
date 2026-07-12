import { baseApi } from './baseApi';

/** Backend returns snake_case (GeocodingResolveResponse) */
export interface GeocodingResolveResponse {
  city: string;
  country: string;
  country_code: string;
  formatted_address: string;
  lat: number;
  lng: number;
}

export const geocodingApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * Resolve city name to country and location (for hotel search: backend requires city_name + country_name).
     */
    resolveCity: builder.query<GeocodingResolveResponse, string>({
      query: (city) => ({
        url: '/geocoding/resolve',
        params: { city: city.trim() },
      }),
    }),
  }),
});

export const { useLazyResolveCityQuery } = geocodingApi;
