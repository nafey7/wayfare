import { baseApi } from './baseApi';
import type { DetectedLocation } from '@/types/onboarding';
import { findCountryByCode } from '@/features/onboarding/locationData';

interface IpapiResponse {
  city?: string;
  /** Country _name_ (e.g. "Germany"). Distinct from `country` which is the ISO-2 code. */
  country_name?: string;
  /** ISO 3166-1 alpha-2 country code (e.g. "DE"). */
  country_code?: string;
  /** ipapi.co alias for `country_code` — also ISO-2, NOT the country name. */
  country?: string;
  error?: boolean;
}

const IPAPI_ENDPOINT = 'https://ipapi.co/json/';
const REQUEST_TIMEOUT_MS = 4000;

function toDetectedLocation(payload: IpapiResponse): DetectedLocation | null {
  const city = payload.city?.trim();
  // `country` is the ISO-2 alias of `country_code`; `country_name` is the human name.
  const countryCode = (payload.country_code ?? payload.country ?? '').trim().toUpperCase();
  const country = payload.country_name?.trim() ?? '';
  if (!city || countryCode.length !== 2) return null;

  const catalog = findCountryByCode(countryCode);
  return {
    city,
    country: country || catalog?.name || '',
    countryCode,
    iata: '',
    currency: catalog?.currency ?? '',
    currencySymbol: catalog?.currencySymbol ?? '',
  };
}

async function fetchIpLocation(): Promise<DetectedLocation | null> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(IPAPI_ENDPOINT, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
    if (!response.ok) return null;
    const payload = (await response.json()) as IpapiResponse;
    if (payload.error) return null;
    return toDetectedLocation(payload);
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

export const locationApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    detectLocation: builder.query<DetectedLocation, void>({
      queryFn: async () => {
        const detected = await fetchIpLocation();
        if (detected) return { data: detected };
        return {
          error: {
            status: 'CUSTOM_ERROR' as const,
            error: 'location-unavailable',
            data: { message: 'Could not detect location.' },
          },
        };
      },
    }),
  }),
});

export const { useDetectLocationQuery, useLazyDetectLocationQuery } = locationApi;
