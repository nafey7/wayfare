/**
 * Flight sorting utilities.
 * Replicates backend_python dev_ui flight-booker sort behavior (price, duration, departure, arrival).
 */

import type { FilterableFlight } from './flightFilters';

/** Sort option IDs matching backend dev_ui flight-booker (flight_sort). */
export type FlightSortOption =
  | 'preference-match'
  | 'price-low'
  | 'price-high'
  | 'duration-short'
  | 'duration-long'
  | 'departure-early'
  | 'departure-late'
  | 'arrival-early'
  | 'arrival-late';

/** Default sort for authenticated users with preferences. */
export const DEFAULT_FLIGHT_SORT: FlightSortOption = 'preference-match';
/** Fallback sort when preference-match is unavailable (unauthenticated / no prefs). */
export const FALLBACK_FLIGHT_SORT: FlightSortOption = 'price-low';

/** Labels for search results sort menus (flight search page). */
export const FLIGHT_SORT_MENU_ITEMS: { value: FlightSortOption; label: string }[] = [
  { value: 'preference-match', label: 'Your preferences' },
  { value: 'price-low', label: 'Price: Low to High' },
  { value: 'price-high', label: 'Price: High to Low' },
  { value: 'duration-short', label: 'Duration: Shortest first' },
  { value: 'duration-long', label: 'Duration: Longest first' },
  { value: 'departure-early', label: 'Departure: Earliest first' },
  { value: 'departure-late', label: 'Departure: Latest first' },
  { value: 'arrival-early', label: 'Arrival: Earliest first' },
  { value: 'arrival-late', label: 'Arrival: Latest first' },
];

/** All valid sort options for persistence/validation (single source of truth with menu labels) */
export const FLIGHT_SORT_OPTIONS: FlightSortOption[] = FLIGHT_SORT_MENU_ITEMS.map(
  (i) => i.value
);

/** Parse "Xh Ym" or "Xh" to total minutes */
function parseDurationToMinutes(text: string | null | undefined): number {
  if (!text || typeof text !== 'string') return 0;
  const hMatch = text.match(/(\d+)\s*h/);
  const mMatch = text.match(/(\d+)\s*m/);
  const hours = hMatch && hMatch[1] != null ? parseInt(hMatch[1], 10) : 0;
  const minutes = mMatch && mMatch[1] != null ? parseInt(mMatch[1], 10) : 0;
  return hours * 60 + minutes;
}

/** Time string "HH:MM" to minutes since midnight */
export function timeToMinutes(timeStr: string | null | undefined): number | null {
  if (!timeStr || timeStr === 'TBD') return null;
  const parts = timeStr.split(':').map(Number);
  if (parts.length < 2) return null;
  const h = parts[0];
  const m = parts[1];
  return h != null && m != null ? h * 60 + m : null;
}

/** Get flight price (same as backend getFlightPrice) */
export function getFlightPrice(flight: FilterableFlight): number {
  return flight.price ?? 0;
}

/** Total duration in minutes (all legs, flight + layover). Same logic as backend calculateTotalDuration. */
export function getTotalDurationMinutes(flight: FilterableFlight): number {
  return (flight.legs ?? []).reduce(
    (sum, leg) => sum + parseDurationToMinutes(leg.totalTimeDisplay ?? leg.duration),
    0
  );
}

/** First leg departure time as minutes since midnight (backend: getDepartureTimeMinutes). */
export function getDepartureTimeMinutes(flight: FilterableFlight): number | null {
  const firstLeg = flight.legs?.[0];
  const timeStr = firstLeg?.departure?.time;
  return timeToMinutes(timeStr);
}

/** First leg arrival time as minutes since midnight (backend: getArrivalTimeMinutes). */
export function getArrivalTimeMinutes(flight: FilterableFlight): number | null {
  const firstLeg = flight.legs?.[0];
  const timeStr = firstLeg?.arrival?.time;
  return timeToMinutes(timeStr);
}

/**
 * Sort flights by the given option. Matches backend sortFlights() behavior.
 * Returns a new sorted array; does not mutate input.
 */
export function sortFlights<T extends FilterableFlight>(
  flights: T[],
  sortBy: FlightSortOption
): T[] {
  const sorted = [...flights];
  switch (sortBy) {
    case 'price-low':
      sorted.sort((a, b) => getFlightPrice(a) - getFlightPrice(b));
      break;
    case 'price-high':
      sorted.sort((a, b) => getFlightPrice(b) - getFlightPrice(a));
      break;
    case 'duration-short':
      sorted.sort(
        (a, b) => getTotalDurationMinutes(a) - getTotalDurationMinutes(b)
      );
      break;
    case 'duration-long':
      sorted.sort(
        (a, b) => getTotalDurationMinutes(b) - getTotalDurationMinutes(a)
      );
      break;
    case 'departure-early':
      sorted.sort((a, b) => {
        const aTime = getDepartureTimeMinutes(a) ?? 0;
        const bTime = getDepartureTimeMinutes(b) ?? 0;
        return aTime - bTime;
      });
      break;
    case 'departure-late':
      sorted.sort((a, b) => {
        const aTime = getDepartureTimeMinutes(a) ?? 0;
        const bTime = getDepartureTimeMinutes(b) ?? 0;
        return bTime - aTime;
      });
      break;
    case 'arrival-early':
      sorted.sort((a, b) => {
        const aTime = getArrivalTimeMinutes(a) ?? 0;
        const bTime = getArrivalTimeMinutes(b) ?? 0;
        return aTime - bTime;
      });
      break;
    case 'arrival-late':
      sorted.sort((a, b) => {
        const aTime = getArrivalTimeMinutes(a) ?? 0;
        const bTime = getArrivalTimeMinutes(b) ?? 0;
        return bTime - aTime;
      });
      break;
    case 'preference-match':
      // Caller should sort via sortFlightsByPreference; falling through to price-low as a safe default.
      sorted.sort((a, b) => getFlightPrice(a) - getFlightPrice(b));
      break;
    default:
      sorted.sort((a, b) => getFlightPrice(a) - getFlightPrice(b));
  }
  return sorted;
}
