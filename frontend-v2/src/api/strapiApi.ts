import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { mapInspirationRailsResponse, type InspirationRailsData } from './strapi/mapInspirationRails';
import { getStrapiBaseUrl, strapiRequestHeaders } from './strapi/strapiHttp';

/**
 * Builds a Strapi 5–compatible `populate` query string: `populate[0]=…&populate[1]=…`
 * with dot paths for nested components and media.
 *
 * Strapi v4–style `populate[hero][populate]=*` chains are not equivalent on Strapi 5 and
 * can return HTTP 500. See {@link https://docs.strapi.io/cms/api/rest/populate-select}.
 */
export function encodeStrapi5Populate(paths: readonly string[]): string {
  return paths
    .map((path, index) => `populate[${index}]=${encodeURIComponent(path)}`)
    .join('&');
}

/** Populate paths for `GET /api/landing-pages` (Strapi 5 collection type). */
export const LANDING_PAGE_POPULATE_PATHS: readonly string[] = [
  'weekendTrips',
  'weekendTrips.image',
  'fromCityTrips',
  'fromCityTrips.image',
  'adventureTrips',
  'adventureTrips.image',
  'beachTrips',
  'beachTrips.image',
  'natureTrips',
  'natureTrips.image',
  'foodTrips',
  'foodTrips.image',
  'cultureTrips',
  'cultureTrips.image',
  'hiddenTrips',
  'hiddenTrips.image',
  'voyaPicksImage',
  'heroAvatarImage',
];

export const LANDING_PAGE_POPULATE = encodeStrapi5Populate(LANDING_PAGE_POPULATE_PATHS);

const strapiRawBaseQuery = fetchBaseQuery({
  baseUrl: '/',
});

async function fetchLandingPage(filter: string): Promise<{ data: InspirationRailsData }> {
  const base = getStrapiBaseUrl();
  if (!base) return { data: {} };
  const url = `${base}/api/landing-pages?${filter}&status=published&${LANDING_PAGE_POPULATE}`;
  try {
    const res = await fetch(url, { headers: strapiRequestHeaders() });
    if (!res.ok) {
      console.warn('[strapiApi] landing-pages request failed', { status: res.status, statusText: res.statusText, url });
      return { data: {} };
    }
    return { data: mapInspirationRailsResponse(await res.json() as unknown, base) };
  } catch (err) {
    console.warn('[strapiApi] landing-pages fetch error', err);
    return { data: {} };
  }
}

export const strapiApi = createApi({
  reducerPath: 'strapiApi',
  baseQuery: strapiRawBaseQuery,
  tagTypes: ['LandingPage'],
  keepUnusedDataFor: 120,
  endpoints: (builder) => ({
    /**
     * Fetch the default landing page from Strapi.
     * Queries the landing-pages collection type filtered by isDefault=true.
     * Returns empty object when Strapi is not configured — callers fall back to hardcoded data.
     */
    getLandingPage: builder.query<InspirationRailsData, void>({
      queryFn: () => fetchLandingPage('filters[isDefault][$eq]=true'),
      providesTags: [{ type: 'LandingPage', id: 'DEFAULT' }],
    }),

    /**
     * Fetch a landing page by its slug from Strapi.
     * - Returns `null` when Strapi responds with an empty data array (slug not found).
     *   Callers should treat `null` as a hard miss and redirect rather than fall back to hardcoded data.
     * - Returns `{}` when Strapi is not configured or unreachable — callers fall back to hardcoded data.
     */
    getLandingPageBySlug: builder.query<InspirationRailsData | null, string>({
      keepUnusedDataFor: 30,
      async queryFn(slug) {
        const base = getStrapiBaseUrl();
        if (!base) return { data: {} };
        const url = `${base}/api/landing-pages?filters[slug][$eq]=${encodeURIComponent(slug)}&status=published&${LANDING_PAGE_POPULATE}`;
        try {
          const res = await fetch(url, { headers: strapiRequestHeaders() });
          if (!res.ok) {
            console.warn('[strapiApi] landing-pages by slug request failed', {
              status: res.status,
              statusText: res.statusText,
              url,
            });
            return { data: {} };
          }
          const json: unknown = await res.json();
          const dataField =
            json !== null && typeof json === 'object' && !Array.isArray(json)
              ? (json as Record<string, unknown>).data
              : undefined;
          if (Array.isArray(dataField) && dataField.length === 0) {
            console.warn('[strapiApi] slug not found in Strapi', { slug, url });
            return { data: null };
          }
          return { data: mapInspirationRailsResponse(json, base) };
        } catch (err) {
          console.warn('[strapiApi] landing-pages by slug fetch error', err);
          return { data: {} };
        }
      },
      providesTags: (_, __, slug) => [{ type: 'LandingPage', id: slug }],
    }),
  }),
});

export const { useGetLandingPageQuery, useGetLandingPageBySlugQuery } = strapiApi;
