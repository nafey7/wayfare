import type { MapComponentProps } from '@/features/itinerary/components';
import type { LocationCoordinates } from '@/types/api.helpers';

/** Same city/IATA fallbacks as flights for destination-only centering when hotels lack coords. */
const CITY_FALLBACKS: Record<string, LocationCoordinates> = {
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

function normalizeKey(value: string): string {
  return value.trim().toLowerCase();
}

function lookupCityCenter(
  ...candidates: Array<string | null | undefined>
): LocationCoordinates | undefined {
  for (const c of candidates) {
    if (!c) continue;
    const hit = CITY_FALLBACKS[normalizeKey(c)];
    if (hit) return hit;
  }
  return undefined;
}

/**
 * Map props for the hotel search page right-column city pin.
 * Returns null when the destination city is not in CITY_FALLBACKS.
 */
export function getHotelSearchPageMapProps(
  destination: string | null | undefined
): MapComponentProps | null {
  const coords = lookupCityCenter(destination ?? '');
  if (!coords) return null;
  return {
    centerLatitude: coords.latitude,
    centerLongitude: coords.longitude,
    zoomLevel: 12,
    markers: [
      {
        latitude: coords.latitude,
        longitude: coords.longitude,
        label: destination ?? 'Destination',
      },
    ],
  };
}
