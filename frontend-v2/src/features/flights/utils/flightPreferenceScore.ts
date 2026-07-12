import type { FilterableFlight } from './flightFilters';
import type { FlightsPreferences } from '@/types/profile';
import { getFlightPrice, timeToMinutes } from './flightSort';

function _scoreAirlines(flight: FilterableFlight, airlines: string[]): 0 | 1 {
  if (airlines.length === 0) return 0;
  for (const leg of flight.legs ?? []) {
    for (const info of leg.airlinesInfo ?? []) {
      for (const pref of airlines) {
        if (info.code && info.code.toLowerCase() === pref.toLowerCase()) return 1;
        if (info.name && info.name.toLowerCase().includes(pref.toLowerCase())) return 1;
      }
    }
  }
  return 0;
}

function _scoreStops(flight: FilterableFlight, maxStops: string | null | undefined): 0 | 1 {
  if (!maxStops || maxStops === 'any') return 0;
  const stops = flight.legs[0]?.stops ?? Infinity;
  if (maxStops === 'nonstop' && stops === 0) return 1;
  if (maxStops === '1stop' && stops <= 1) return 1;
  if (maxStops === '2stops' && stops <= 2) return 1;
  return 0;
}

function _scoreDepartureWindow(
  flight: FilterableFlight,
  window: [string, string]
): 0 | 1 {
  const minMinutes = timeToMinutes(window[0]);
  const maxMinutes = timeToMinutes(window[1]);
  if (minMinutes === null || maxMinutes === null) {
    return 0;
  }
  // Default full-day window — no preference expressed
  if (minMinutes === 0 && maxMinutes === 23 * 60 + 59) {
    return 0;
  }
  const rawDepTime = flight.legs[0]?.departure?.time;
  const depMinutes = timeToMinutes(rawDepTime);
  if (depMinutes === null) {
    return 0;
  }
  // Midnight-spanning window (e.g. 22:00–06:00)
  if (minMinutes > maxMinutes) {
    return depMinutes >= minMinutes || depMinutes <= maxMinutes ? 1 : 0;
  }
  return depMinutes >= minMinutes && depMinutes <= maxMinutes ? 1 : 0;
}

export function computePreferenceScore(
  flight: FilterableFlight,
  prefs: FlightsPreferences | null
): number {
  if (!prefs) return 0;
  const airlineScore = _scoreAirlines(flight, prefs.preferredAirlines ?? []);
  const stopsScore = _scoreStops(flight, prefs.maxStops);
  const depScore = _scoreDepartureWindow(flight, prefs.departureWindow ?? ['00:00', '23:59']);
  return airlineScore + stopsScore + depScore;
}

export function sortFlightsByPreference<T extends FilterableFlight>(
  flights: T[],
  prefs: FlightsPreferences | null
): T[] {
  const sorted = [...flights];
  sorted.sort((a, b) => {
    const scoreA = computePreferenceScore(a, prefs);
    const scoreB = computePreferenceScore(b, prefs);
    if (scoreB !== scoreA) return scoreB - scoreA;
    return getFlightPrice(a) - getFlightPrice(b);
  });
  return sorted;
}
