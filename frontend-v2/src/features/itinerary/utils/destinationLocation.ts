import type { DestinationLocation } from '@/types/chat';
import type { TripMeta } from '@/types/itineraries';

/**
 * Single default map center when trip meta has no valid backend `destination_location`.
 * Not tied to any product city; only used when coordinates are missing or invalid.
 */
export const DEFAULT_ITINERARY_MAP_FALLBACK = { lat: 34.0522, lng: -118.2437 } as const;

/**
 * Parse and validate destination_location from API/extraData.
 * Returns undefined when input is invalid or out of valid bounds.
 */
export function parseDestinationLocation(loc: unknown): DestinationLocation | undefined {
  if (!loc || typeof loc !== 'object') return undefined;
  const o = loc as Record<string, unknown>;
  const lat = Number(o.latitude);
  const lng = Number(o.longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return undefined;
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return undefined;
  return { latitude: lat, longitude: lng };
}

export interface ItineraryMapCenter {
  centerLatitude: number;
  centerLongitude: number;
  zoomLevel: number;
}

/**
 * Map center for ItineraryPage: backend coordinates only, then a single default.
 * Accepts saved-itinerary `TripMeta` (camelCase from API) or chat navigation `tripMeta` (snake_case dates + `destination_location`).
 */
export function getItineraryMapCenterFromTripMeta(
  tripMeta: TripMeta | null | undefined
): ItineraryMapCenter {
  const fromCoords = parseDestinationLocation(
    tripMeta?.destination_location ?? tripMeta?.destinationLocation
  );
  if (fromCoords) {
    return {
      centerLatitude: fromCoords.latitude,
      centerLongitude: fromCoords.longitude,
      zoomLevel: 10,
    };
  }

  return {
    centerLatitude: DEFAULT_ITINERARY_MAP_FALLBACK.lat,
    centerLongitude: DEFAULT_ITINERARY_MAP_FALLBACK.lng,
    zoomLevel: 10,
  };
}
