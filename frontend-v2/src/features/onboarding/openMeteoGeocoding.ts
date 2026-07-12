/**
 * City search using Open-Meteo Geocoding API (free, no key, search-as-you-type).
 * @see https://open-meteo.com/en/docs/geocoding-api
 *
 * (GeoDB / RapidAPI and Teleport are alternatives; this avoids bundle bloat and secret keys.)
 */

import { ALL_CITIES } from '@/features/onboarding/locationData';
import type { DetectedLocation } from '@/types/onboarding';

/**
 * User search strings are sent directly from the browser to Open-Meteo (third party), not
 * through Voya's backend. If this ships to production without change: ensure the privacy
 * policy covers that disclosure, or proxy geocoding through our API (deferred: onboarding
 * plan Phase 4/6; see also shared rate limits on the free tier - degradation surfaces as
 * empty results / search errors in the UI).
 */
const OPEN_METEO_GEO = 'https://geocoding-api.open-meteo.com/v1/search';

export interface OpenMeteoCityHit {
  id: number;
  name: string;
  country: string;
  country_code: string;
  feature_code: string;
  population?: number;
}

export interface CitySearchOption {
  value: string;
  label: string;
  /** Primary line for the itinerary / chat; includes country to disambiguate. */
  displayLine: string;
  /** Set when the option comes from Open-Meteo or the legacy city catalog. */
  cityName?: string;
  countryName?: string;
  countryCode?: string;
}

interface OpenMeteoSearchResponse {
  results?: OpenMeteoCityHit[];
}

function toOption(hit: OpenMeteoCityHit): CitySearchOption {
  const displayLine = `${hit.name} · ${hit.country}`;
  return {
    value: `om-${hit.id}`,
    label: displayLine,
    displayLine,
    cityName: hit.name,
    countryName: hit.country,
    countryCode: hit.country_code,
  };
}

/** Prefer cities / larger places; sort by population when present. */
function rankHits(hits: OpenMeteoCityHit[]): OpenMeteoCityHit[] {
  return [...hits]
    .filter((h) => h.feature_code?.startsWith('PPL') ?? true)
    .sort((a, b) => (b.population ?? 0) - (a.population ?? 0));
}

export async function searchCitiesOpenMeteo(
  namePrefix: string,
  signal?: AbortSignal,
  /** If set, only return places in this ISO 3166-1 alpha-2 country (e.g. home location step). */
  filterCountryCode?: string
): Promise<CitySearchOption[]> {
  const q = namePrefix.trim();
  if (q.length < 2) return [];

  const url = new URL(OPEN_METEO_GEO);
  url.searchParams.set('name', q);
  // Request more rows when filtering so we still get matches in the chosen country.
  url.searchParams.set('count', filterCountryCode ? '30' : '10');
  url.searchParams.set('language', 'en');
  url.searchParams.set('format', 'json');

  const res = await fetch(url.toString(), { signal, mode: 'cors' });
  if (!res.ok) {
    throw new Error(`Geocoding failed (${res.status})`);
  }
  const data: OpenMeteoSearchResponse = await res.json();
  const raw = data.results ?? [];
  const ranked = rankHits(raw);
  const useList = ranked.length > 0 ? ranked : raw;
  let list = useList.map(toOption);
  if (filterCountryCode?.trim()) {
    const want = filterCountryCode.trim().toUpperCase();
    list = list.filter((o) => o.countryCode?.toUpperCase() === want);
  }
  return list;
}

/**
 * Map persisted trip strings to autocomplete value: legacy catalog cities, or plain text from API search.
 */
export function tripCityOptionFromStored(stored: string): CitySearchOption | null {
  if (!stored.trim()) return null;
  const legacy = ALL_CITIES.find((c) => c.city === stored || c.value === stored);
  if (legacy) {
    return {
      value: legacy.value,
      label: legacy.label,
      displayLine: legacy.label,
      cityName: legacy.city,
      countryName: legacy.country,
      countryCode: legacy.countryCode,
    };
  }
  return {
    value: `text:${stored}`,
    label: stored,
    displayLine: stored,
  };
}

/**
 * Autocomplete value for the onboarding "home location" step from {@link DetectedLocation}.
 */
export function draftLocationToCityOption(
  draft: DetectedLocation
): CitySearchOption | null {
  if (!draft.city?.trim() || !draft.country?.trim()) return null;
  return {
    value: `draft:${draft.countryCode}|${draft.city}`,
    label: `${draft.city} · ${draft.country}`,
    displayLine: `${draft.city} · ${draft.country}`,
    cityName: draft.city,
    countryName: draft.country,
    countryCode: draft.countryCode,
  };
}
