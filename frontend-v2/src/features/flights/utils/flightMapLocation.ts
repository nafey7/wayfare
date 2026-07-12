import type { MapComponentProps, MapMarker } from '@/features/itinerary/components';
import type { ExtractedFlightSearchData, LocationCoordinates } from '@/types/api.helpers';

const DEFAULT_MAP_CENTER: LocationCoordinates = {
  latitude: 34.0522,
  longitude: -118.2437,
};

const FLIGHT_LOCATION_FALLBACKS: Record<string, LocationCoordinates> = {
  ams: { latitude: 52.3676, longitude: 4.9041 },
  amsterdam: { latitude: 52.3676, longitude: 4.9041 },
  bcn: { latitude: 41.3851, longitude: 2.1734 },
  barcelona: { latitude: 41.3851, longitude: 2.1734 },
  cdg: { latitude: 48.8566, longitude: 2.3522 },
  paris: { latitude: 48.8566, longitude: 2.3522 },
  dxb: { latitude: 25.2048, longitude: 55.2708 },
  dubai: { latitude: 25.2048, longitude: 55.2708 },
  fco: { latitude: 41.9028, longitude: 12.4964 },
  rome: { latitude: 41.9028, longitude: 12.4964 },
  jfk: { latitude: 40.6413, longitude: -73.7781 },
  'new york': { latitude: 40.7128, longitude: -74.006 },
  lax: { latitude: 33.9416, longitude: -118.4085 },
  'los angeles': { latitude: 34.0522, longitude: -118.2437 },
  lhr: { latitude: 51.47, longitude: -0.4543 },
  london: { latitude: 51.5074, longitude: -0.1278 },
  nrt: { latitude: 35.772, longitude: 140.3929 },
  tokyo: { latitude: 35.6762, longitude: 139.6503 },
};

function normalizeLocationKey(value: string): string {
  return value.trim().toLowerCase();
}

function lookupFallbackCoordinate(
  ...candidates: Array<string | null | undefined>
): LocationCoordinates | undefined {
  for (const candidate of candidates) {
    if (!candidate) continue;
    const fallback = FLIGHT_LOCATION_FALLBACKS[normalizeLocationKey(candidate)];
    if (fallback) {
      return fallback;
    }
  }
  return undefined;
}

function getMapMarker(
  label: string,
  coordinates: LocationCoordinates | undefined
): MapMarker | null {
  if (!coordinates) return null;
  return {
    latitude: coordinates.latitude,
    longitude: coordinates.longitude,
    label,
  };
}

function getRouteCenter(markers: MapMarker[]): LocationCoordinates {
  if (markers.length === 0) return DEFAULT_MAP_CENTER;
  if (markers.length === 1) {
    return {
      latitude: markers[0]!.latitude,
      longitude: markers[0]!.longitude,
    };
  }

  const latitude =
    markers.reduce((sum, marker) => sum + marker.latitude, 0) / markers.length;
  const longitude =
    markers.reduce((sum, marker) => sum + marker.longitude, 0) / markers.length;

  return { latitude, longitude };
}

export type FlightRecommendationsMapCoordinateOverrides = {
  origin?: LocationCoordinates | null;
  destination?: LocationCoordinates | null;
};

type TripMetaLike = {
  origin?: string;
  destination?: string;
  origin_location?: { latitude: number; longitude: number } | null;
  originLocation?: { latitude: number; longitude: number } | null;
  destination_location?: { latitude: number; longitude: number } | null;
  destinationLocation?: { latitude: number; longitude: number } | null;
} | null | undefined;

function normalizeCityName(value: string | null | undefined): string {
  return (value ?? '').trim().toLowerCase();
}

/**
 * Build a set of comparable tokens from a location string: the full normalized
 * string and the first comma-separated segment, so that "Barcelona, Spain"
 * matches "Barcelona" and vice versa.
 */
function locationMatchTokens(
  ...values: Array<string | null | undefined>
): Set<string> {
  const tokens = new Set<string>();
  for (const value of values) {
    const normalized = normalizeCityName(value);
    if (!normalized) continue;
    tokens.add(normalized);
    const firstSegment = normalized.split(',')[0]?.trim();
    if (firstSegment) tokens.add(firstSegment);
  }
  return tokens;
}

function tokensIntersect(a: Set<string>, b: Set<string>): boolean {
  for (const token of a) {
    if (b.has(token)) return true;
  }
  return false;
}

/**
 * Build map coordinate overrides from a saved-itinerary tripMeta, used to seed
 * the flight-search page map with the exact city-center lat/lng from the
 * itinerary (instead of relying on the small static FLIGHT_LOCATION_FALLBACKS
 * table) before the user runs a search.
 *
 * Stale-itinerary guard: we only emit overrides for a side (origin/destination)
 * when the tripMeta string matches the current nav-bar string. Matching is
 * case-insensitive and accepts: full-string equality, first-comma-segment
 * equality ("Barcelona, Spain" ↔ "Barcelona"), or an IATA-code match against
 * the optional fromIata/toIata in currentParams. If the user has edited the
 * nav-bar away from the itinerary's city, the override is dropped for that
 * side so the pin can't lag on the old city.
 */
export function getItineraryMapOverrideFromTripMeta(
  tripMeta: TripMetaLike,
  currentParams: {
    from?: string | null;
    to?: string | null;
    fromIata?: string | null;
    toIata?: string | null;
  }
): FlightRecommendationsMapCoordinateOverrides | null {
  if (!tripMeta) return null;

  const destinationCoords =
    tripMeta.destination_location ?? tripMeta.destinationLocation ?? null;
  const originCoords = tripMeta.origin_location ?? tripMeta.originLocation ?? null;

  const result: FlightRecommendationsMapCoordinateOverrides = {};

  const tripDestTokens = locationMatchTokens(tripMeta.destination);
  const currentToTokens = locationMatchTokens(currentParams.to, currentParams.toIata);
  if (
    destinationCoords &&
    tripDestTokens.size > 0 &&
    currentToTokens.size > 0 &&
    tokensIntersect(tripDestTokens, currentToTokens)
  ) {
    result.destination = {
      latitude: destinationCoords.latitude,
      longitude: destinationCoords.longitude,
    };
  }

  const tripOriginTokens = locationMatchTokens(tripMeta.origin);
  const currentFromTokens = locationMatchTokens(currentParams.from, currentParams.fromIata);
  if (
    originCoords &&
    tripOriginTokens.size > 0 &&
    currentFromTokens.size > 0 &&
    tokensIntersect(tripOriginTokens, currentFromTokens)
  ) {
    result.origin = {
      latitude: originCoords.latitude,
      longitude: originCoords.longitude,
    };
  }

  return Object.keys(result).length > 0 ? result : null;
}

/**
 * Build map props for the flight search page from form params (IATA + city name lookups).
 *
 * Coordinate priority (highest → lowest):
 *   1. coordinateOverrides — explicit coords (e.g. resolved from search response)
 *   2. IATA code fallback  — from form params or resolved airport
 *   3. City name fallback  — from the static FLIGHT_LOCATION_FALLBACKS table
 */
export function getFlightSearchPageMapProps(
  params: { from: string; to: string; fromIata?: string; toIata?: string },
  coordinateOverrides?: { origin?: LocationCoordinates | null; destination?: LocationCoordinates | null } | null
): MapComponentProps {
  const originCoordinates =
    coordinateOverrides?.origin ?? lookupFallbackCoordinate(params.fromIata, params.from);
  const destinationCoordinates =
    coordinateOverrides?.destination ?? lookupFallbackCoordinate(params.toIata, params.to);

  const markers = [
    getMapMarker(`Origin: ${params.from}`, originCoordinates),
    getMapMarker(`Destination: ${params.to}`, destinationCoordinates),
  ].filter((marker): marker is MapMarker => Boolean(marker));

  const center = getRouteCenter(markers);
  const routePath =
    originCoordinates && destinationCoordinates
      ? [originCoordinates, destinationCoordinates]
      : undefined;

  return {
    centerLatitude: center.latitude,
    centerLongitude: center.longitude,
    zoomLevel: routePath ? 4 : 10,
    markers,
    routePath,
  };
}

/**
 * Build map props for chat-driven flight recommendations.
 *
 * Coordinate priority (highest → lowest):
 *   1. coordinateOverrides  — explicit pin from /airports/resolve (most precise)
 *   2. origin_city fallback — user's searched city; wins over backend coords so the
 *      map always shows the city the user searched, not the alternative airport the
 *      backend may have resolved to (e.g. Amsterdam, not Rotterdam).
 *   3. backend origin/destination_location — correct when no alternative-airport substitution occurred
 *   4. search_params.origin/destination_location — secondary backend field
 *   5. IATA / city name fallback — last resort from the static table
 */
export function getFlightRecommendationsMapProps(
  flightSearchData: ExtractedFlightSearchData | null | undefined,
  coordinateOverrides?: FlightRecommendationsMapCoordinateOverrides | null
): MapComponentProps {
  if (!flightSearchData) {
    return {
      centerLatitude: DEFAULT_MAP_CENTER.latitude,
      centerLongitude: DEFAULT_MAP_CENTER.longitude,
      zoomLevel: 10,
      markers: [],
    };
  }

  const searchParams = flightSearchData.data.search_params;
  const originCoordinates =
    coordinateOverrides?.origin ??
    lookupFallbackCoordinate(searchParams.origin_city) ??
    flightSearchData.origin_location ??
    searchParams.origin_location ??
    lookupFallbackCoordinate(
      searchParams.origin_iata,
      searchParams.origin
    );
  const destinationCoordinates =
    coordinateOverrides?.destination ??
    lookupFallbackCoordinate(searchParams.destination_city) ??
    flightSearchData.destination_location ??
    searchParams.destination_location ??
    lookupFallbackCoordinate(
      searchParams.destination_iata,
      searchParams.destination
    );

  const markers = [
    getMapMarker(`Origin: ${searchParams.origin_city ?? searchParams.origin}`, originCoordinates),
    getMapMarker(
      `Destination: ${searchParams.destination_city ?? searchParams.destination}`,
      destinationCoordinates
    ),
  ].filter((marker): marker is MapMarker => Boolean(marker));

  const center = getRouteCenter(markers);
  const routePath =
    originCoordinates && destinationCoordinates
      ? [originCoordinates, destinationCoordinates]
      : undefined;

  return {
    centerLatitude: center.latitude,
    centerLongitude: center.longitude,
    zoomLevel: routePath ? 4 : 10,
    markers,
    routePath,
  };
}
