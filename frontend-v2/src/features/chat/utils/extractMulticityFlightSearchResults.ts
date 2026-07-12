import type { FlightSearchParamsUI } from '@/types/flights';
import type {
  ExtractedFlightSearchData,
  FlightCategory,
  FlightCategories,
  FlightInfo,
  FlightResultsSummary,
  FlightSearchParams,
  FlightSearchResultsInner,
  LocationCoordinates,
} from '@/types/api.helpers';
import {
  flightsFromCategories,
  parseLocationCoordinates,
} from '@/types/api.helpers';
import { mapCabinClass } from '@/features/chat/utils/chatSearchParamsToUI';

/**
 * One leg of a chat multicity (Circle) curated response — normalized for UI and synthetic single-leg extracts.
 */
export interface MulticityChatLegNormalized {
  legIndex: number;
  origin: string;
  destination: string;
  departureDate: string;
  sessionId: string;
  summary: FlightResultsSummary;
  categories: FlightCategories;
  flights: FlightInfo[];
  originLocation?: LocationCoordinates;
  destinationLocation?: LocationCoordinates;
  errors?: Array<{ message?: string; code?: string }> | null;
}

export interface MulticityChatPayloadNormalized {
  /** Trip-level search params (passengers, cabin, journey_type Circle, etc.) */
  searchParams: FlightSearchParams;
  multicityParallel?: boolean;
  legs: MulticityChatLegNormalized[];
}

function emptySummary(): FlightResultsSummary {
  return {
    total_flights: 0,
    direct_count: 0,
    price_range: { min: 0, max: 0, currency: 'USD' },
  };
}

function emptyCategories(): FlightCategories {
  const empty = (label: string): FlightCategory => ({ label, flights: [] });
  return {
    cheapest: empty('Cheapest'),
    fastest: empty('Fastest'),
    best_value: empty('Best Value'),
  };
}

function normalizeSummary(raw: unknown): FlightResultsSummary {
  if (!raw || typeof raw !== 'object') return emptySummary();
  const s = raw as Record<string, unknown>;
  const pr = s.price_range as Record<string, unknown> | undefined;
  return {
    total_flights: typeof s.total_flights === 'number' ? s.total_flights : 0,
    direct_count: typeof s.direct_count === 'number' ? s.direct_count : 0,
    price_range: {
      min: typeof pr?.min === 'number' ? pr.min : 0,
      max: typeof pr?.max === 'number' ? pr.max : 0,
      currency: typeof pr?.currency === 'string' ? pr.currency : 'USD',
    },
  };
}

function normalizeCategoryBucket(
  raw: unknown,
  fallbackLabel: string
): FlightCategory {
  if (!raw || typeof raw !== 'object') {
    return { label: fallbackLabel, flights: [] };
  }
  const b = raw as Record<string, unknown>;
  const label =
    typeof b.label === 'string' && b.label.trim() ? b.label : fallbackLabel;
  const flights = Array.isArray(b.flights)
    ? (b.flights as FlightInfo[])
    : [];
  return { label, flights };
}

function normalizeCategories(raw: unknown): FlightCategories {
  if (!raw || typeof raw !== 'object') return emptyCategories();
  const c = raw as Record<string, unknown>;
  return {
    cheapest: normalizeCategoryBucket(c.cheapest, 'Cheapest'),
    fastest: normalizeCategoryBucket(c.fastest, 'Fastest'),
    best_value: normalizeCategoryBucket(c.best_value ?? c.bestValue, 'Best Value'),
  };
}

function normalizeLeg(
  raw: Record<string, unknown>,
  index: number
): MulticityChatLegNormalized | null {
  const origin = String(raw.origin ?? raw.origin_iata ?? '').trim();
  const destination = String(raw.destination ?? raw.destination_iata ?? '').trim();
  const departureDate = String(
    raw.departure_date ?? raw.departureDate ?? ''
  ).trim();
  if (!origin || !destination || !departureDate) return null;

  const legIndex =
    typeof raw.leg_index === 'number'
      ? raw.leg_index
      : typeof raw.legIndex === 'number'
        ? raw.legIndex
        : index;

  const sessionId = String(raw.session_id ?? raw.sessionId ?? '').trim();

  const summary = normalizeSummary(raw.summary);
  const categories = normalizeCategories(raw.categories);

  const inner: FlightSearchResultsInner = {
    search_params: {} as FlightSearchParams,
    summary,
    categories,
  };
  let flights: FlightInfo[] = Array.isArray(raw.flights)
    ? (raw.flights as FlightInfo[])
    : [];
  if (!flights.length) {
    flights = flightsFromCategories(inner);
  }

  const errors = Array.isArray(raw.errors)
    ? (raw.errors as Array<{ message?: string; code?: string }>)
    : raw.errors === null
      ? null
      : undefined;

  return {
    legIndex,
    origin,
    destination,
    departureDate,
    sessionId,
    summary,
    categories,
    flights,
    originLocation:
      parseLocationCoordinates(raw.origin_location) ??
      parseLocationCoordinates(raw.originLocation),
    destinationLocation:
      parseLocationCoordinates(raw.destination_location) ??
      parseLocationCoordinates(raw.destinationLocation),
    errors,
  };
}

/**
 * Find the object that holds `multicity_legs` + trip `search_params` (nested or flat).
 */
function unwrapMulticityRoot(extraData: unknown): Record<string, unknown> | null {
  if (!extraData || typeof extraData !== 'object') return null;
  const root = extraData as Record<string, unknown>;

  const hasLegs = (r: Record<string, unknown>) =>
    Array.isArray(r.multicity_legs) || Array.isArray(r.multicityLegs);

  if (hasLegs(root)) return root;

  const data = root.data;
  if (data && typeof data === 'object') {
    const d = data as Record<string, unknown>;
    if (hasLegs(d)) return d;
    const inner = d.data;
    if (inner && typeof inner === 'object' && hasLegs(inner as Record<string, unknown>)) {
      return inner as Record<string, unknown>;
    }
  }
  return null;
}

function getTripSearchParams(root: Record<string, unknown>): FlightSearchParams | null {
  const sp = root.search_params ?? root.searchParams;
  if (!sp || typeof sp !== 'object') return null;
  return sp as FlightSearchParams;
}

/**
 * Parse chat `multicity_flight_search_results` payload into a normalized structure.
 * Supports nested `{ data: { multicity_legs, search_params } }`, flat top-level, and `data.data` double nesting.
 */
export function extractMulticityFlightSearchResults(
  extraData: unknown
): MulticityChatPayloadNormalized | null {
  const root = unwrapMulticityRoot(extraData);
  if (!root) return null;

  const trip = getTripSearchParams(root);
  if (!trip) return null;

  const legsRaw = (root.multicity_legs ?? root.multicityLegs) as unknown;
  if (!Array.isArray(legsRaw) || legsRaw.length < 2) return null;

  const legs: MulticityChatLegNormalized[] = [];
  for (let i = 0; i < legsRaw.length; i++) {
    const item = legsRaw[i];
    if (!item || typeof item !== 'object') continue;
    const leg = normalizeLeg(item as Record<string, unknown>, i);
    if (leg) legs.push(leg);
  }

  if (legs.length < 2) return null;

  return {
    searchParams: trip,
    multicityParallel: Boolean(root.multicity_parallel ?? root.multicityParallel),
    legs,
  };
}

export function legHasCuratedFlights(leg: MulticityChatLegNormalized): boolean {
  const { cheapest, fastest, best_value: best } = leg.categories;
  return (
    (cheapest?.flights?.length ?? 0) > 0 &&
    (fastest?.flights?.length ?? 0) > 0 &&
    (best?.flights?.length ?? 0) > 0
  );
}

/**
 * Build a single-leg {@link ExtractedFlightSearchData} for the recommendations panel / map.
 */
export function legToExtractedSingleLeg(
  tripSearchParams: FlightSearchParams,
  leg: MulticityChatLegNormalized
): ExtractedFlightSearchData {
  const mergedParams: FlightSearchParams = {
    ...tripSearchParams,
    origin: leg.origin,
    destination: leg.destination,
    departure_date: leg.departureDate,
    return_date: null,
    journey_type: 'Circle',
  };

  const inner: FlightSearchResultsInner = {
    search_params: mergedParams,
    summary: leg.summary,
    categories: leg.categories,
  };

  let flights = leg.flights;
  if (!flights.length) {
    flights = flightsFromCategories(inner);
  }

  return {
    data: inner,
    flights,
    session_id: leg.sessionId,
    origin_location:
      leg.originLocation ??
      parseLocationCoordinates(mergedParams.origin_location as unknown),
    destination_location:
      leg.destinationLocation ??
      parseLocationCoordinates(mergedParams.destination_location as unknown),
  };
}

export function multicityChatPayloadToSearchParamsUI(
  payload: MulticityChatPayloadNormalized
): FlightSearchParamsUI {
  const trip = payload.searchParams;
  const passengers = trip.passengers ?? { adults: 1, children: 0, infants: 0 };
  const segments = payload.legs.map((leg) => ({
    from: leg.origin,
    to: leg.destination,
    date: leg.departureDate ? new Date(leg.departureDate) : null,
  }));
  const first = payload.legs[0];
  const last = payload.legs[payload.legs.length - 1];
  return {
    tripType: 'multi-city',
    from: first?.origin ?? '',
    to: last?.destination ?? '',
    date: first?.departureDate ? new Date(first.departureDate) : null,
    returnDate: null,
    travellers: {
      adults: passengers.adults,
      children: passengers.children,
      infants: passengers.infants,
      cabinClass: mapCabinClass(trip.cabin_class),
    },
    segments,
    originIsCity: trip.origin_is_city ?? undefined,
    destinationIsCity: trip.destination_is_city ?? undefined,
    originIata: trip.origin_iata,
    destinationIata: trip.destination_iata,
  };
}
