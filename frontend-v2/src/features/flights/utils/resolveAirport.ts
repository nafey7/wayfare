/**
 * Resolve city/airport input to IATA code.
 * Mirrors flight-booker (backend_python/dev_ui/flight-booker) resolveAirport logic
 * so the search API always receives iata_code in the payload.
 */

import type { AirportOption } from '@/types/flights';

/**
 * Detect if input is likely a city name (vs airport code).
 * Matches flight-booker isCityName() logic.
 */
function isCityName(input: string): boolean {
  const trimmed = input.trim();
  if (!trimmed) return false;

  // Exactly 3 letters = airport code
  if (trimmed.length === 3 && /^[A-Za-z]{3}$/.test(trimmed)) {
    return false;
  }

  // Contains "(XXX)" at end = airport selection
  if (/\([A-Za-z]{3}\)\s*$/.test(trimmed)) {
    return false;
  }

  // Spaces, >3 chars, or 1-2 chars = treat as city
  return true;
}

/** Minimal airport shape for resolution (from autocomplete selection) */
export interface AirportSelectionLike {
  iata?: string;
  isCityOption?: boolean;
}

/**
 * Resolve origin/destination input to IATA code.
 * Priority order (matches flight-booker):
 * 1. Stored IATA from autocomplete (fromAirport.iata when 3 chars)
 * 2. Input is already 3-letter IATA
 * 3. Extract from "Airport Name (IATA)" format
 * 4. Call resolve API (handled by caller - this returns hint for that)
 */
export function resolveToIata(
  inputValue: string,
  selectedAirport?: AirportOption | AirportSelectionLike | null
): { iata: string; needsResolve: boolean; cityWise: boolean } {
  const trimmed = (inputValue || '').trim();
  if (!trimmed) {
    return { iata: '', needsResolve: false, cityWise: false };
  }

  const upper = trimmed.toUpperCase();

  // Priority 1: Stored IATA from autocomplete
  if (selectedAirport?.iata && selectedAirport.iata.trim().length === 3) {
    return {
      iata: selectedAirport.iata.trim().toUpperCase(),
      needsResolve: false,
      cityWise: selectedAirport.isCityOption === true,
    };
  }

  // Priority 2: Already a 3-letter IATA code
  if (upper.length === 3 && /^[A-Z]{3}$/.test(upper)) {
    return { iata: upper, needsResolve: false, cityWise: false };
  }

  // Priority 3: Extract from "Airport Name (IATA)" or "Name (XXX)" format
  const iataMatch = trimmed.match(/\(([A-Za-z]{3})\)/);
  if (iataMatch?.[1]) {
    return {
      iata: iataMatch[1].toUpperCase(),
      needsResolve: false,
      cityWise: false,
    };
  }

  // Priority 4: Need to call resolve API
  return {
    iata: upper,
    needsResolve: true,
    cityWise: isCityName(trimmed),
  };
}

/**
 * Returns true if the input would yield a valid 3-letter IATA without calling the resolve API.
 * Use to validate multi-city segments where per-segment resolution is not yet implemented.
 */
export function hasValidIataWithoutResolve(input: string): boolean {
  const r = resolveToIata(input, undefined);
  return !r.needsResolve && r.iata.length === 3;
}
