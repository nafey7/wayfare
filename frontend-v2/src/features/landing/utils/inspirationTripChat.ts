import type { InspirationTrip } from '../data/inspirationTrips';

/**
 * Popular origin cities appended to Strapi-sourced chatPrompts.
 * Marketing writes the destination/experience part; the codebase injects a random origin
 * so the AI has enough context to search flights.
 */
export const POPULAR_ORIGIN_CITIES: readonly string[] = [
  'London', 'Paris', 'New York', 'Amsterdam', 'Dubai',
  'Singapore', 'Bangkok', 'Barcelona', 'Rome', 'Berlin',
  'Sydney', 'Tokyo', 'Istanbul', 'Toronto', 'Los Angeles',
];

const SESSION_ORIGIN_KEY = 'voya_chat_origin';
let _cachedOrigin: string | null = null;

/** Returns a stable origin city for the session, picked once and cached in sessionStorage. */
function getSessionOrigin(): string {
  if (_cachedOrigin) return _cachedOrigin;
  try {
    const stored = sessionStorage.getItem(SESSION_ORIGIN_KEY);
    if (stored) { _cachedOrigin = stored; return stored; }
  } catch { /* sessionStorage unavailable (SSR / private mode) */ }
  const city = POPULAR_ORIGIN_CITIES[Math.floor(Math.random() * POPULAR_ORIGIN_CITIES.length)]!;
  _cachedOrigin = city;
  try { sessionStorage.setItem(SESSION_ORIGIN_KEY, city); } catch { /* ignore */ }
  return city;
}

/**
 * Append an origin city to a Strapi chatPrompt.
 *
 * Origin precedence:
 *   1. `explicitOrigin` — caller-supplied (typically IP-detected user location).
 *   2. Session-cached random pick from `POPULAR_ORIGIN_CITIES` (stable per session).
 *
 * Pass `destination` to guarantee the origin differs from it.
 */
export function appendOriginToPrompt(
  prompt: string,
  destination?: string,
  explicitOrigin?: string,
): string {
  const baseOrigin = explicitOrigin?.trim() || getSessionOrigin();
  // If the chosen origin equals the destination (e.g. user in Berlin clicks a Berlin
  // trip), swap to the first non-matching popular city — usually London — so the
  // prompt isn't nonsensical ("from Berlin to Berlin"). The swap is intentionally
  // simple; the AI will re-ask the user for a real origin when relevant.
  const city =
    destination && baseOrigin.toLowerCase() === destination.toLowerCase()
      ? (POPULAR_ORIGIN_CITIES.find((c) => c.toLowerCase() !== destination.toLowerCase()) ?? baseOrigin)
      : baseOrigin;
  return `${prompt}. My origin is ${city}`;
}

const AIRPORT_TO_CITY: Record<string, string> = {
  LHR: 'London', LGW: 'London', LCY: 'London', STN: 'London',
  CDG: 'Paris',  ORY: 'Paris',
  JFK: 'New York', EWR: 'New York', LGA: 'New York',
  AMS: 'Amsterdam', BRU: 'Brussels', MAD: 'Madrid', BCN: 'Barcelona',
  FCO: 'Rome',   MXP: 'Milan',   MUC: 'Munich',  FRA: 'Frankfurt',
  DXB: 'Dubai',  SIN: 'Singapore', HND: 'Tokyo',   NRT: 'Tokyo',
  DPS: 'Bali',   BKK: 'Bangkok', KUL: 'Kuala Lumpur',
};

function airportToCity(code: string): string {
  return AIRPORT_TO_CITY[code.trim().toUpperCase()] ?? code.trim();
}

function parseDurationNights(duration: string): number {
  const match = duration.match(/(\d+)/);
  return match ? parseInt(match[1] ?? '2', 10) : 2;
}

function dateHintForNights(nights: number): string {
  if (nights <= 2) return 'this weekend, Friday to Sunday';
  if (nights === 3) return 'this weekend, Friday to Monday';
  if (nights <= 5) return 'in 2 weeks, Saturday to Wednesday';
  if (nights <= 7) return 'in 3 weeks, Saturday to Saturday';
  if (nights <= 9) return 'in 4 weeks';
  return 'next month';
}

export function buildInspirationTripPrompt(trip: InspirationTrip): string {
  const dest = trip.destinationCity ?? '';

  // Prefer explicit originCity; fall back to parsing the flight route
  let origin = trip.originCity;
  if (!origin) {
    const rawOriginCode = trip.flightRoute?.split(/[→,]/)[0]?.trim();
    origin = rawOriginCode ? airportToCity(rawOriginCode) : 'London';
  }

  const nights = parseDurationNights(trip.duration);
  const dateHint = dateHintForNights(nights);

  return `Plan a ${trip.duration} trip from ${origin} to ${dest} ${dateHint}, for 2 adults`;
}
