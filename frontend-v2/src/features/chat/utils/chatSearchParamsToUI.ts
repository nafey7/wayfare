import type { FlightSearchParams } from '@/types/api.helpers';
import type { FlightSearchParamsUI, TripType, CabinClassUI } from '@/types/flights';
import type { FlightFilterState } from '@/features/flights/utils/flightFilters';
import { defaultFlightFilterState } from '@/features/flights/utils/flightFilters';

const DEFAULT_CABIN_CLASS: CabinClassUI = 'Economy';

/** Valid cabin class values accepted by the UI */
const VALID_CABIN_CLASSES: Record<string, CabinClassUI> = {
  economy: 'Economy',
  'premium economy': 'Premium Economy',
  business: 'Business',
  first: 'First',
};

/**
 * Chat flight filters extracted from backend search_params.
 * These are post-search filters applied client-side on the booker page.
 */
export interface ChatFlightFilters {
  priceMin: number | null;
  priceMax: number | null;
  directOnly: boolean;
  airlines: string[];
  outboundDurationMax: number | null;
  inboundDurationMax: number | null;
}

/**
 * Map chat/backend journey_type to Flight Search Page tripType.
 */
function journeyTypeToTripType(
  journeyType: FlightSearchParams['journey_type']
): TripType {
  switch (journeyType) {
    case 'OneWay':
      return 'one-way';
    case 'Return':
    case 'RoundTrip':
    case 'Circle':
      return 'round-trip';
    default:
      return 'one-way';
  }
}

/**
 * Map backend cabin_class string to CabinClassUI.
 * Falls back to Economy for unknown/missing values.
 */
export function mapCabinClass(cabinClass?: string): CabinClassUI {
  if (!cabinClass) return DEFAULT_CABIN_CLASS;
  return VALID_CABIN_CLASSES[cabinClass.toLowerCase()] ?? DEFAULT_CABIN_CLASS;
}

/**
 * Convert chat flight search params (from extraData.data.search_params) to
 * FlightSearchParamsUI so they can be serialized to URL and used by FlightSearchPage.
 */
export function chatSearchParamsToUI(params: FlightSearchParams): FlightSearchParamsUI {
  const date = params.departure_date ? new Date(params.departure_date) : null;
  const returnDate = params.return_date ? new Date(params.return_date) : null;

  // Prefer city names for display in search bar (e.g., "London" over "LHR")
  const from = params.origin_city || params.origin;
  const to = params.destination_city || params.destination;

  return {
    from,
    to,
    date,
    returnDate: returnDate ?? undefined,
    tripType: journeyTypeToTripType(params.journey_type),
    travellers: {
      adults: params.passengers?.adults ?? 1,
      children: params.passengers?.children ?? 0,
      infants: params.passengers?.infants ?? 0,
      cabinClass: mapCabinClass(params.cabin_class),
    },
    originIsCity: params.origin_is_city,
    destinationIsCity: params.destination_is_city,
    originIata: params.origin_iata,
    destinationIata: params.destination_iata,
  };
}

/**
 * Extract post-search filters from backend search_params.
 * Returns null if no filters are present (all default values).
 */
export function extractChatFilters(params: FlightSearchParams): ChatFlightFilters | null {
  const directOnly = params.direct_flight === 1 || params.max_stops === 0;
  const priceMin = params.price_min ?? null;
  const priceMax = params.price_max ?? null;
  const airlines = params.preferred_airline ? [params.preferred_airline] : [];
  // cabin_class is handled at the API level (travellers.cabinClass), not as a post-filter
  const outboundDurationMax = params.max_outbound_duration ?? null;
  const inboundDurationMax = params.max_inbound_duration ?? null;

  // Return null if no filters are set
  if (
    !directOnly &&
    priceMin === null &&
    priceMax === null &&
    airlines.length === 0 &&
    outboundDurationMax === null &&
    inboundDurationMax === null
  ) {
    return null;
  }

  return {
    priceMin,
    priceMax,
    directOnly,
    airlines,
    outboundDurationMax,
    inboundDurationMax,
  };
}

/**
 * Convert ChatFlightFilters to FlightFilterState by spreading over defaults.
 */
export function chatFiltersToFilterState(filters: ChatFlightFilters): FlightFilterState {
  return {
    ...defaultFlightFilterState,
    priceMin: filters.priceMin,
    priceMax: filters.priceMax,
    directOnly: filters.directOnly,
    airlines: filters.airlines,
    outboundDurationMax: filters.outboundDurationMax,
    inboundDurationMax: filters.inboundDurationMax,
  };
}
