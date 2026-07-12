import type { FlightSearchFormParams } from '@/store/slices/flightBookingSlice';
import type { HotelSearchFormParams } from '@/types/hotels';

export const SEARCH_RESULTS_TTL_MS = 5 * 60 * 1000; // 5 minutes

export function isSearchCacheExpired(timestamp: number | null): boolean {
  if (timestamp === null) return true;
  return Date.now() - timestamp >= SEARCH_RESULTS_TTL_MS;
}

// Normalize a date string to YYYY-MM-DD so ISO timestamps ("2024-06-15T00:00:00.000Z") and
// plain date strings ("2024-06-15") compare equal — chat and UI serialize dates differently.
function normalizeDate(d: string | null | undefined): string | null {
  if (d == null) return null;
  return d.substring(0, 10);
}

// Sort keys alphabetically so JSON.stringify is order-insensitive across different construction paths
// (URL deserialization vs Redux action vs object spread can insert properties in different orders).
function stableStringify(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(',')}]`;
  }
  if (value !== null && typeof value === 'object') {
    const sorted = Object.keys(value as Record<string, unknown>)
      .sort()
      .map((k) => `${JSON.stringify(k)}:${stableStringify((value as Record<string, unknown>)[k])}`);
    return `{${sorted.join(',')}}`;
  }
  return JSON.stringify(value);
}

type FlightCacheKey = Pick<
  FlightSearchFormParams,
  'tripType' | 'from' | 'to' | 'date' | 'returnDate' | 'travellers' | 'segments'
>;

function extractFlightKey(p: FlightSearchFormParams): FlightCacheKey {
  return {
    tripType: p.tripType,
    from: p.from,
    to: p.to,
    date: normalizeDate(p.date),
    returnDate: normalizeDate(p.returnDate),
    travellers: p.travellers,
    segments: p.segments?.map((seg) => ({ ...seg, date: normalizeDate(seg.date) })),
  };
}

export function areFlightParamsEqual(
  a: FlightSearchFormParams | null,
  b: FlightSearchFormParams | null
): boolean {
  if (a === null && b === null) return true;
  if (a === null || b === null) return false;
  return stableStringify(extractFlightKey(a)) === stableStringify(extractFlightKey(b));
}

type HotelCacheKey = Pick<
  HotelSearchFormParams,
  'destination' | 'checkin' | 'checkout' | 'rooms' | 'nationality'
>;

function extractHotelKey(p: HotelSearchFormParams): HotelCacheKey {
  return {
    destination: p.destination,
    checkin: p.checkin,
    checkout: p.checkout,
    rooms: p.rooms,
    nationality: p.nationality,
  };
}

export function areHotelParamsEqual(
  a: HotelSearchFormParams | null,
  b: HotelSearchFormParams | null
): boolean {
  if (a === null && b === null) return true;
  if (a === null || b === null) return false;
  return stableStringify(extractHotelKey(a)) === stableStringify(extractHotelKey(b));
}
