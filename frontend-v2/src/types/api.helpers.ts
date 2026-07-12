/**
 * API Type Helpers
 *
 * This file provides properly typed interfaces for API responses,
 * especially for discriminated union types like ChatResponse.data
 * which the OpenAPI spec types as Dict[str, Any].
 *
 * Types use snake_case to match the actual API responses (no transformation).
 * This ensures types match runtime data and OpenAPI documentation.
 *
 * Re-exports useful types from the auto-generated api.generated.ts
 */

import type { components } from './api.generated';

// Re-export commonly used types from generated file
export type FlightInfoGenerated = components['schemas']['FlightInfo'];
export type FlightSearchSummary = components['schemas']['FlightSearchSummary'];
export type CuratedFlight = components['schemas']['CuratedFlight'];
export type ChatResponse = components['schemas']['ChatResponse'];
export type ChatRequest = components['schemas']['ChatRequest'];

/**
 * Flight info (snake_case to match API)
 */
export interface FlightInfo {
  id: string;
  departure_time: string;
  departure_date: string;
  arrival_time: string;
  arrival_date: string;
  origin_code: string;
  origin_city?: string | null;
  origin_airport?: string | null;
  destination_code: string;
  destination_city?: string | null;
  destination_airport?: string | null;
  duration: string;
  duration_minutes: number;
  stops: number;
  price: number;
  currency: string;
  airline: string;
  airline_code: string;
  flight_number?: string;
  is_round_trip?: boolean;
  segments?: FlightSegmentInfo[];
  validating_airline?: {
    airline_name: string;
    iata_code: string;
  };
}

/**
 * Flight segment info (snake_case).
 * Mirrors the dict produced by backend `_extract_segment`.
 * "departure_code" etc. are legacy aliases kept for fixture/mock compatibility —
 * real backend responses use "origin_code"/"origin_city"/"origin_airport".
 */
export interface FlightSegmentInfo {
  /** Backend field: origin IATA code (also aliased as departure_code in legacy mocks). */
  origin_code?: string;
  origin_city?: string;
  origin_airport?: string;
  /** Legacy alias for origin_code — present in mocks, absent from real backend responses. */
  departure_code?: string;
  departure_city?: string;
  departure_airport?: string;
  destination_code: string;
  destination_city?: string;
  destination_airport?: string;
  departure_time: string;
  departure_date: string;
  arrival_time: string;
  arrival_date: string;
  duration: string;
  duration_minutes?: number;
  airline?: string;
  airline_code?: string;
  /** Airline logo URL enriched by backend _enrich_airline_logos (FlightLogic airline list). */
  logo_url?: string;
  flight_number?: string;
  aircraft_type?: string;
  cabin_class?: string;
  /** Leg index (0 = outbound, 1 = return). Present in chat results to reconstruct multi-leg structure. */
  leg_index?: number;
}

/**
 * Flight category with label and flights array
 */
export interface FlightCategory {
  label: string;
  flights: FlightInfo[];
}

/**
 * Generic coordinates payload for map points.
 */
export interface LocationCoordinates {
  latitude: number;
  longitude: number;
}

/**
 * Search parameters for flight search (snake_case)
 */
export interface FlightSearchParams {
  origin: string;
  destination: string;
  departure_date: string;
  return_date: string | null;
  // 'MultiCity' is injected by the backend supervisor for country multi-hub
  // destinations — not a FlightLogic value (FlightLogic uses 'Circle').
  journey_type: 'OneWay' | 'Return' | 'RoundTrip' | 'Circle' | 'MultiCity';
  passengers: {
    adults: number;
    children: number;
    infants: number;
  };
  origin_city?: string | null;
  destination_city?: string | null;
  origin_iata?: string;
  destination_iata?: string;
  origin_is_city?: boolean;
  destination_is_city?: boolean;
  origin_location?: LocationCoordinates;
  destination_location?: LocationCoordinates;
  cabin_class?: string;
  direct_flight?: number;
  max_stops?: number | null;
  price_min?: number | null;
  price_max?: number | null;
  preferred_airline?: string | null;
  max_outbound_duration?: number | null;
  max_inbound_duration?: number | null;
}

/**
 * Flight search results summary (snake_case)
 */
export interface FlightResultsSummary {
  total_flights: number;
  direct_count: number;
  price_range: {
    min: number;
    max: number;
    currency?: string;
  };
}

/**
 * Flight categories (snake_case - best_value)
 */
export interface FlightCategories {
  cheapest: FlightCategory;
  fastest: FlightCategory;
  best_value: FlightCategory;
}

/**
 * Inner data structure for flight search results
 * This is the structure inside ChatResponse.data.data
 */
export interface FlightSearchResultsInner {
  search_params: FlightSearchParams;
  summary: FlightResultsSummary;
  /** @deprecated Removed by backend issue #1034 — flights now arrive as a flat top-level array. */
  categories?: FlightCategories;
}

/**
 * Nested envelope: inner payload under `data`, plus top-level flights/session.
 * This is what's in ChatResponse.data when type === 'flight_search_results' (nested shape).
 */
export interface FlightSearchResultsEnvelope {
  data: FlightSearchResultsInner;
  flights: FlightInfo[];
  session_id: string;
  flight?: Record<string, unknown>;
  origin_location?: LocationCoordinates;
  destination_location?: LocationCoordinates;
}

/**
 * Flat variant: `search_params` / `summary` / `categories` on ChatResponse.data with no `data` wrapper.
 * @see extractFlightSearchResults — normalizes both envelope and flat shapes to {@link ExtractedFlightSearchData}.
 */
export interface FlightSearchResultsFlat {
  search_params: FlightSearchParams;
  summary: FlightResultsSummary;
  /** @deprecated Removed by backend issue #1034. */
  categories?: FlightCategories;
  flights?: FlightInfo[];
  session_id?: string;
  flight?: Record<string, unknown>;
  origin_location?: LocationCoordinates;
  destination_location?: LocationCoordinates;
}

/**
 * Chat flight_search_results payload: nested envelope or flat inner fields.
 * Normalize with {@link extractFlightSearchResults}.
 */
export type FlightSearchResultsData =
  | FlightSearchResultsEnvelope
  | FlightSearchResultsFlat;

/**
 * Extracted flight search data (return shape of extractFlightSearchResults).
 * Used for passing between chat, recommendations page, and Redux.
 */
export interface ExtractedFlightSearchData {
  data: FlightSearchResultsInner;
  flights: FlightInfo[];
  session_id: string;
  origin_location?: LocationCoordinates;
  destination_location?: LocationCoordinates;
}

export function parseLocationCoordinates(location: unknown): LocationCoordinates | undefined {
  if (!location || typeof location !== 'object') return undefined;

  const record = location as Record<string, unknown>;
  const latitude = Number(record.latitude ?? record.lat);
  const longitude = Number(record.longitude ?? record.lng ?? record.long ?? record.lon);

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    return undefined;
  }
  if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
    return undefined;
  }

  return { latitude, longitude };
}

function hasFlightSearchInnerFields(inner: Record<string, unknown>): boolean {
  // Backend issue #1034 dropped `categories`; recognise either the legacy
  // shape (categories present) or the new flat shape (just search_params +
  // summary, flights at top level of the envelope).
  return 'search_params' in inner && 'summary' in inner;
}

/**
 * Nested: { data: { search_params, summary, categories }, flights?, session_id?, ... }
 * Flat:   { search_params, summary, categories, flights?, session_id?, ... }
 */
function resolveFlightSearchPayload(record: Record<string, unknown>): {
  inner: FlightSearchResultsInner;
  flights: FlightInfo[];
  session_id: string;
  origin_location?: unknown;
  destination_location?: unknown;
} | null {
  const nested = record.data;
  if (
    nested &&
    typeof nested === 'object' &&
    hasFlightSearchInnerFields(nested as Record<string, unknown>)
  ) {
    return {
      inner: nested as FlightSearchResultsInner,
      flights: (record.flights as FlightInfo[]) || [],
      session_id: (record.session_id as string) || '',
      origin_location: record.origin_location,
      destination_location: record.destination_location,
    };
  }
  if (hasFlightSearchInnerFields(record)) {
    return {
      inner: {
        search_params: record.search_params,
        summary: record.summary,
        categories: record.categories,
      } as FlightSearchResultsInner,
      flights: (record.flights as FlightInfo[]) || [],
      session_id: (record.session_id as string) || '',
      origin_location: record.origin_location,
      destination_location: record.destination_location,
    };
  }
  return null;
}

/** When API omits top-level `flights`, derive a deduped list from category buckets. */
export function flightsFromCategories(inner: FlightSearchResultsInner): FlightInfo[] {
  const cats = inner.categories;
  if (!cats) return [];
  const seen = new Set<string>();
  const out: FlightInfo[] = [];
  for (const key of ['cheapest', 'fastest', 'best_value'] as const) {
    const cat = cats[key];
    if (!cat?.flights?.length) continue;
    for (const f of cat.flights) {
      const dedupeKey =
        (f.id && f.id.trim()) ||
        `${f.departure_time}-${f.arrival_time}-${f.price}-${f.airline_code}`;
      if (seen.has(dedupeKey)) continue;
      seen.add(dedupeKey);
      out.push(f);
    }
  }
  return out;
}

/**
 * True when chat `data` is nested or flat flight search results (see FlightSearchResultsData).
 */
export function isFlightSearchResultsData(data: unknown): boolean {
  if (!data || typeof data !== 'object') return false;
  return resolveFlightSearchPayload(data as Record<string, unknown>) !== null;
}

/**
 * Safely extract flight search results from chat response data
 * Returns null if data doesn't match expected structure
 */
export function extractFlightSearchResults(
  extraData: unknown
): ExtractedFlightSearchData | null {
  if (!extraData || typeof extraData !== 'object') return null;

  const resolved = resolveFlightSearchPayload(extraData as Record<string, unknown>);
  if (!resolved) return null;

  const { inner, origin_location, destination_location, session_id } = resolved;
  let flights = resolved.flights;
  if (!flights.length) {
    flights = flightsFromCategories(inner);
  }

  const searchParamsRecord = inner.search_params as unknown as Record<string, unknown>;

  return {
    data: inner,
    flights,
    session_id,
    origin_location: parseLocationCoordinates(
      origin_location ?? searchParamsRecord.origin_location
    ),
    destination_location: parseLocationCoordinates(
      destination_location ?? searchParamsRecord.destination_location
    ),
  };
}

// --- Hotel search results (chat) — mirrors flight nested vs flat shapes ---

/** Search parameters for hotel chat results (snake_case; tolerant of aliases). */
export interface HotelSearchParams {
  destination_city?: string | null;
  destination?: string | null;
  city_name?: string | null;
  country?: string | null;
  country_name?: string | null;
  check_in_date?: string | null;
  check_out_date?: string | null;
  checkin?: string | null;
  checkout?: string | null;
  rooms?: number | null;
  adults?: number | null;
  children?: number | null;
}

export interface HotelResultsSummary {
  total_hotels?: number;
  total_found?: number;
  nights?: number;
  price_range?: {
    min?: number;
    max?: number;
    currency?: string;
  };
}

/**
 * Hotel info coming through the chat ``hotels`` array (snake_case, mirrors
 * the dict shape produced by ``_build_hotel_response`` on the backend).
 *
 * All fields are optional so this works against the chat response, the
 * pre-fetched #1038 itinerary side-search, and the legacy categories shape
 * without per-call type guards. Components reading from this should still
 * defensively check the fields they consume.
 */
export interface ChatHotelInfo {
  hotel_id?: string;
  token_id?: string;
  product_id?: string;
  hotel_name?: string;
  /** Alternative name field — some legacy payloads use ``name`` instead of ``hotel_name``. */
  name?: string;
  city?: string;
  country?: string;
  address?: string;
  locality?: string;
  hotel_rating?: number | string;
  trip_advisor_rating?: number | string;
  trip_advisor_reviews?: number;
  total_price?: number;
  per_night_price?: number;
  currency?: string;
  fare_type?: string;
  nights?: number;
  original_total_fare?: number;
  platform_fee_percentage?: number;
  facilities?: string[];
  property_type?: string;
  thumbnail_url?: string;
  latitude?: string | number;
  longitude?: string | number;
  distance_value?: string | number;
  distance_unit?: string;
  nearby_distance_km?: number;
}

export interface HotelCategory {
  label?: string;
  hotels?: Record<string, unknown>[];
}

export interface HotelCategories {
  cheapest: HotelCategory;
  highest_rated: HotelCategory;
  best_value: HotelCategory;
}

export interface HotelSearchResultsInner {
  search_params: HotelSearchParams;
  summary: HotelResultsSummary;
  /** @deprecated Removed by backend issue #1034 — hotels now arrive as a flat top-level array. */
  categories?: HotelCategories;
}

export interface HotelSearchResultsEnvelope {
  data: HotelSearchResultsInner;
  hotels?: Record<string, unknown>[];
  session_id?: string;
}

export interface HotelSearchResultsFlat {
  search_params: HotelSearchParams;
  summary: HotelResultsSummary;
  /** @deprecated Removed by backend issue #1034. */
  categories?: HotelCategories;
  hotels?: Record<string, unknown>[];
  session_id?: string;
}

export type HotelSearchResultsData = HotelSearchResultsEnvelope | HotelSearchResultsFlat;

export interface ExtractedHotelSearchData {
  data: HotelSearchResultsInner;
  hotels: Record<string, unknown>[];
  session_id: string;
}

function hasHotelSearchInnerFields(inner: Record<string, unknown>): boolean {
  // Backend issue #1034 dropped `categories`; the new shape only has
  // search_params + summary in `data`, with the full hotels array at the
  // envelope top level. Legacy shape (categories present) also accepted.
  return 'search_params' in inner && 'summary' in inner;
}

function resolveHotelSearchPayload(record: Record<string, unknown>): {
  inner: HotelSearchResultsInner;
  hotels: Record<string, unknown>[];
  session_id: string;
} | null {
  const nested = record.data;
  if (
    nested &&
    typeof nested === 'object' &&
    hasHotelSearchInnerFields(nested as Record<string, unknown>)
  ) {
    return {
      inner: nested as HotelSearchResultsInner,
      hotels: (record.hotels as Record<string, unknown>[]) || [],
      session_id:
        (record.session_id as string) ||
        (record.sessionId as string) ||
        '',
    };
  }
  if (hasHotelSearchInnerFields(record)) {
    return {
      inner: {
        search_params: record.search_params,
        summary: record.summary,
        categories: record.categories,
      } as HotelSearchResultsInner,
      hotels: (record.hotels as Record<string, unknown>[]) || [],
      session_id:
        (record.session_id as string) ||
        (record.sessionId as string) ||
        '',
    };
  }
  return null;
}

function hotelsFromCategories(inner: HotelSearchResultsInner): Record<string, unknown>[] {
  const cats = inner.categories;
  if (!cats) return [];
  const seen = new Set<string>();
  const out: Record<string, unknown>[] = [];
  for (const key of ['best_value', 'cheapest', 'highest_rated'] as const) {
    const cat = cats[key];
    if (!cat?.hotels?.length) continue;
    for (const h of cat.hotels) {
      if (!h || typeof h !== 'object') continue;
      const raw = h as Record<string, unknown>;
      const id =
        (raw.hotel_id as string | undefined)?.trim() ||
        (raw.hotelId as string | undefined)?.trim() ||
        '';
      const dedupeKey =
        id ||
        `${raw.token_id ?? raw.tokenId ?? ''}-${raw.hotel_name ?? raw.name ?? ''}-${raw.total_price ?? raw.totalPrice}`;
      if (seen.has(dedupeKey)) continue;
      seen.add(dedupeKey);
      out.push(raw);
    }
  }
  return out;
}

export function isHotelSearchResultsData(data: unknown): boolean {
  if (!data || typeof data !== 'object') return false;
  return resolveHotelSearchPayload(data as Record<string, unknown>) !== null;
}

/**
 * Safely extract hotel search results from chat response data.
 */
export function extractHotelSearchResults(
  extraData: unknown
): ExtractedHotelSearchData | null {
  if (!extraData || typeof extraData !== 'object') return null;

  const resolved = resolveHotelSearchPayload(extraData as Record<string, unknown>);
  if (!resolved) return null;

  let hotels = resolved.hotels;
  if (!hotels.length) {
    hotels = hotelsFromCategories(resolved.inner);
  }

  return {
    data: resolved.inner,
    hotels,
    session_id: resolved.session_id,
  };
}


/**
 * Per-date flight search result from date-range search.
 *
 * Post backend #1034: each date carries its own flat ``flights`` array;
 * ``categories`` is legacy and may be absent.
 */
export interface DateRangeDateResult {
  date: string;
  day_name?: string;
  available: boolean;
  session_id?: string;
  /** @deprecated Removed by backend #1034. */
  categories?: FlightCategories;
  flights?: FlightInfo[];
  summary?: FlightResultsSummary;
  origin_location?: LocationCoordinates;
  destination_location?: LocationCoordinates;
}

/**
 * Extracted date-range flight search data.
 *
 * Post backend #1034: ``overall_best`` is a single ``FlightInfo | null``.
 * ``overall`` is retained as a legacy three-bucket shape but populated
 * from ``overall_best`` for backward compatibility with existing UI.
 */
export interface ExtractedDateRangeFlightData {
  dates: DateRangeDateResult[];
  overall_best: FlightInfo | null;
  /** @deprecated Use ``overall_best`` — kept for components still reading buckets. */
  overall: {
    cheapest: FlightInfo | null;
    fastest: FlightInfo | null;
    best_value: FlightInfo | null;
  };
  searched_from: string;
  searched_to: string;
  has_more: boolean;
  next_chunk_start?: string;
  next_chunk_end?: string;
}

/**
 * Extract date-range flight results from chat response data.
 * Returns null if data doesn't match the date-range structure.
 */
export function extractFlightDateRangeResults(
  extraData: unknown
): ExtractedDateRangeFlightData | null {
  if (!extraData || typeof extraData !== 'object') return null;
  let record = extraData as Record<string, unknown>;

  // Unwrap nested envelope: response.data may be { data: { dates, overall_best, ... } }
  if (!Array.isArray(record.dates) && record.data && typeof record.data === 'object') {
    record = record.data as Record<string, unknown>;
  }

  // Date-range results have a `dates` array
  const dates = record.dates as DateRangeDateResult[] | undefined;
  if (!Array.isArray(dates)) return null;

  // New shape (#1034): single `overall_best` field.
  // Legacy shape: `overall.{cheapest,fastest,best_value}`.
  const overallBest =
    (record.overall_best as FlightInfo | null | undefined) ?? null;
  const legacyOverall = (record.overall ?? {}) as Record<string, unknown>;
  const overall = {
    cheapest:
      overallBest ?? (legacyOverall.cheapest as FlightInfo) ?? null,
    fastest:
      overallBest ?? (legacyOverall.fastest as FlightInfo) ?? null,
    best_value:
      overallBest ?? (legacyOverall.best_value as FlightInfo) ?? null,
  };

  return {
    dates: dates.map((d) => ({
      ...d,
      origin_location: parseLocationCoordinates(d.origin_location),
      destination_location: parseLocationCoordinates(d.destination_location),
    })),
    overall_best: overallBest,
    overall,
    searched_from: (record.searched_from as string) ?? '',
    searched_to: (record.searched_to as string) ?? '',
    has_more: (record.has_more as boolean) ?? false,
    next_chunk_start: record.next_chunk_start as string | undefined,
    next_chunk_end: record.next_chunk_end as string | undefined,
  };
}

/**
 * Legacy: true when the response carried all three categories non-empty
 * (cheapest, highest_rated, best_value). Post backend #1034 the response is a
 * flat ``hotels`` array, so for flat-only payloads this returns true iff that
 * list has results — there are no buckets to be "incomplete". Existing callers
 * predate #1034; this preserves their semantics for legacy cached responses.
 */
export function hasCompleteHotelSearchCategories(
  extracted: ExtractedHotelSearchData | null | undefined
): boolean {
  if (!extracted) return false;
  const cats = extracted.data.categories;
  if (cats) {
    return (
      (cats.cheapest?.hotels?.length ?? 0) > 0 &&
      (cats.highest_rated?.hotels?.length ?? 0) > 0 &&
      (cats.best_value?.hotels?.length ?? 0) > 0
    );
  }
  return (extracted.hotels?.length ?? 0) > 0;
}

/**
 * True when the hotel search has at least one hotel result.
 *
 * Post backend #1034: the response is a flat list, no categories. Gating
 * just checks ``extracted.hotels.length > 0``. Legacy categories are still
 * tolerated as a fallback if a stale message format slips through.
 */
export function hasAnyHotelSearchCategory(
  extracted: ExtractedHotelSearchData | null | undefined
): boolean {
  if (!extracted) return false;
  if ((extracted.hotels?.length ?? 0) > 0) return true;
  // Legacy fallback (kept until all in-flight cached responses age out).
  const cats = extracted.data.categories;
  if (!cats) return false;
  return (
    (cats.cheapest?.hotels?.length ?? 0) > 0 ||
    (cats.highest_rated?.hotels?.length ?? 0) > 0 ||
    (cats.best_value?.hotels?.length ?? 0) > 0
  );
}

/**
 * Build ExtractedFlightSearchData from a single per-date entry in a date-range result.
 *
 * @param dateEntry - The per-date result to convert. If omitted, uses first available date from dateRange.
 * @param dateRange - The full date-range result (used to find first available when dateEntry is omitted).
 * @param baseData  - Optional existing ExtractedFlightSearchData to inherit search_params from.
 */
export function dateRangeToFlightSearchData(
  dateRange: ExtractedDateRangeFlightData,
  dateEntry?: DateRangeDateResult,
  baseData?: ExtractedFlightSearchData | null,
): ExtractedFlightSearchData | null {
  const entry = dateEntry ?? dateRange.dates.find((d) => d.available && d.categories);
  if (!entry?.available || !entry.categories) return null;

  const inner: FlightSearchResultsInner = {
    search_params: (baseData?.data?.search_params ?? {}) as FlightSearchParams,
    summary: (entry.summary ?? {}) as FlightResultsSummary,
    categories: entry.categories,
  };

  const flights = flightsFromCategories(inner);

  return {
    data: inner,
    flights,
    session_id: entry.session_id ?? '',
    origin_location: entry.origin_location ?? baseData?.origin_location,
    destination_location: entry.destination_location ?? baseData?.destination_location,
  };
}
