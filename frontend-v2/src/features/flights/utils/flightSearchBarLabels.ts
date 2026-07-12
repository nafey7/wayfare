import type { SerializableAirportOption } from '@/store/slices/flightBookingSlice';

/** Minimal airport fields for label helpers; other SerializableAirportOption fields optional. */
type AirportLabelInput =
  | (Pick<SerializableAirportOption, 'city' | 'iata'> &
      Partial<Omit<SerializableAirportOption, 'city' | 'iata'>>)
  | undefined;

/**
 * True when the user picked a city-wide search (all airports in city), not one specific airport.
 * Prefer `isCityOption`; also detect from stored form text (`segment.from` / `segment.to` is the
 * city name for city-wide picks) or legacy `"City (Any)"` display names when flags were not persisted.
 *
 * When `isCityOption` is explicitly `false`, we only treat the row as city-wide if the display
 * name still ends with `(Any)` — so a specific airport (`isCityOption: false`) is not mislabeled
 * when segment text happens to equal the city (e.g. odd free-text input).
 */
export function isCityWideAirportSelection(
  airport: AirportLabelInput,
  segmentEndpointText: string
): boolean {
  if (!airport?.city?.trim() || !airport?.iata?.trim()) return false;
  if (airport.isCityOption === true) return true;
  const nameAny = /\s*\(Any\)\s*$/i.test(airport.name?.trim() ?? '');
  if (airport.isCityOption === false) {
    return nameAny;
  }
  const city = airport.city.trim();
  const text = segmentEndpointText.trim();
  if (text && text.toLowerCase() === city.toLowerCase()) return true;
  return nameAny;
}

/** Chip / heading labels for the single-leg route row (From — To). */
export function routeEndpointDisplayLabel(
  airport: AirportLabelInput,
  segmentEndpointText: string,
  incompleteFallback: string
): string {
  if (!airport?.city?.trim() || !airport?.iata?.trim()) {
    return segmentEndpointText?.trim() || incompleteFallback;
  }
  return isCityWideAirportSelection(airport, segmentEndpointText)
    ? airport.city.trim()
    : `${airport.city} (${airport.iata})`;
}

/** Short token for multi-city summary chain (IATA for specific airports, city name for city-wide). */
export function multicityChainEndpointLabel(
  airport: SerializableAirportOption | undefined,
  textFallback: string
): string {
  const fb = textFallback.trim();
  if (airport?.city?.trim() && airport?.iata?.trim()) {
    return isCityWideAirportSelection(airport, fb)
      ? airport.city.trim()
      : airport.iata.trim();
  }
  return airport?.iata?.trim() || fb;
}
