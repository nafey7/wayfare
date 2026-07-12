import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  SEARCH_RESULTS_TTL_MS,
  isSearchCacheExpired,
  areFlightParamsEqual,
  areHotelParamsEqual,
} from './searchResultsCache';
import type { FlightSearchFormParams } from '@/store/slices/flightBookingSlice';
import type { HotelSearchFormParams } from '@/types/hotels';

afterEach(() => {
  vi.restoreAllMocks();
});

const baseTravellers = { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' as const };

const baseFlightParams: FlightSearchFormParams = {
  tripType: 'one-way',
  from: 'LHR',
  to: 'JFK',
  date: '2026-08-01',
  returnDate: null,
  travellers: baseTravellers,
};

const baseHotelParams: HotelSearchFormParams = {
  destination: 'Paris',
  checkin: '2026-08-01',
  checkout: '2026-08-05',
  rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
  nationality: 'US',
};

describe('isSearchCacheExpired', () => {
  it('returns true when timestamp is null', () => {
    expect(isSearchCacheExpired(null)).toBe(true);
  });

  it('returns false for a fresh timestamp', () => {
    vi.spyOn(Date, 'now').mockReturnValue(1000000);
    const freshTimestamp = 1000000 - (SEARCH_RESULTS_TTL_MS - 1000);
    expect(isSearchCacheExpired(freshTimestamp)).toBe(false);
  });

  it('returns true for an expired timestamp (exactly at TTL boundary)', () => {
    vi.spyOn(Date, 'now').mockReturnValue(1000000);
    const expiredTimestamp = 1000000 - SEARCH_RESULTS_TTL_MS;
    expect(isSearchCacheExpired(expiredTimestamp)).toBe(true);
  });

  it('returns true for a timestamp older than TTL', () => {
    vi.spyOn(Date, 'now').mockReturnValue(1000000);
    const oldTimestamp = 1000000 - SEARCH_RESULTS_TTL_MS - 1;
    expect(isSearchCacheExpired(oldTimestamp)).toBe(true);
  });
});

describe('areFlightParamsEqual', () => {
  it('returns true for identical params', () => {
    expect(areFlightParamsEqual(baseFlightParams, { ...baseFlightParams })).toBe(true);
  });

  it('returns true when both are null', () => {
    expect(areFlightParamsEqual(null, null)).toBe(true);
  });

  it('returns false when one is null', () => {
    expect(areFlightParamsEqual(baseFlightParams, null)).toBe(false);
    expect(areFlightParamsEqual(null, baseFlightParams)).toBe(false);
  });

  it('returns false when tripType differs', () => {
    expect(areFlightParamsEqual(baseFlightParams, { ...baseFlightParams, tripType: 'round-trip' })).toBe(false);
  });

  it('returns false when origin differs', () => {
    expect(areFlightParamsEqual(baseFlightParams, { ...baseFlightParams, from: 'CDG' })).toBe(false);
  });

  it('returns false when destination differs', () => {
    expect(areFlightParamsEqual(baseFlightParams, { ...baseFlightParams, to: 'LAX' })).toBe(false);
  });

  it('returns false when date differs', () => {
    expect(areFlightParamsEqual(baseFlightParams, { ...baseFlightParams, date: '2026-09-01' })).toBe(false);
  });

  it('returns false when returnDate differs', () => {
    expect(areFlightParamsEqual(baseFlightParams, { ...baseFlightParams, returnDate: '2026-08-15' })).toBe(false);
  });

  it('returns false when travellers differ', () => {
    expect(
      areFlightParamsEqual(baseFlightParams, {
        ...baseFlightParams,
        travellers: { ...baseTravellers, adults: 2 },
      })
    ).toBe(false);
  });

  it('returns false when segments differ', () => {
    const withSegments = {
      ...baseFlightParams,
      tripType: 'multi-city' as const,
      segments: [{ from: 'LHR', to: 'CDG', date: '2026-08-01' }],
    };
    const withDifferentSegments = {
      ...withSegments,
      segments: [{ from: 'LHR', to: 'AMS', date: '2026-08-01' }],
    };
    expect(areFlightParamsEqual(withSegments, withDifferentSegments)).toBe(false);
  });

  it('treats params with shuffled key-insertion order as equal (stableStringify)', () => {
    const shuffledTravellers = {
      cabinClass: 'Economy' as const,
      infants: 0,
      children: 0,
      adults: 1,
    };
    expect(areFlightParamsEqual(baseFlightParams, { ...baseFlightParams, travellers: shuffledTravellers })).toBe(true);
  });

  it('ignores non-cache-key fields (fromAirport, toAirport, originIsCity)', () => {
    const withAirport = {
      ...baseFlightParams,
      fromAirport: { iata: 'LHR', name: 'Heathrow', city: 'London', country: 'GB' },
      originIsCity: true,
    };
    expect(areFlightParamsEqual(baseFlightParams, withAirport)).toBe(true);
  });
});

describe('areHotelParamsEqual', () => {
  it('returns true for identical params', () => {
    expect(areHotelParamsEqual(baseHotelParams, { ...baseHotelParams })).toBe(true);
  });

  it('returns true when both are null', () => {
    expect(areHotelParamsEqual(null, null)).toBe(true);
  });

  it('returns false when one is null', () => {
    expect(areHotelParamsEqual(baseHotelParams, null)).toBe(false);
    expect(areHotelParamsEqual(null, baseHotelParams)).toBe(false);
  });

  it('returns false when destination differs', () => {
    expect(areHotelParamsEqual(baseHotelParams, { ...baseHotelParams, destination: 'Rome' })).toBe(false);
  });

  it('returns false when checkin differs', () => {
    expect(areHotelParamsEqual(baseHotelParams, { ...baseHotelParams, checkin: '2026-09-01' })).toBe(false);
  });

  it('returns false when checkout differs', () => {
    expect(areHotelParamsEqual(baseHotelParams, { ...baseHotelParams, checkout: '2026-09-05' })).toBe(false);
  });

  it('returns false when rooms differ', () => {
    expect(
      areHotelParamsEqual(baseHotelParams, {
        ...baseHotelParams,
        rooms: [{ roomNo: 1, adult: 3, child: 0, childAge: [0] }],
      })
    ).toBe(false);
  });

  it('returns false when nationality differs', () => {
    expect(areHotelParamsEqual(baseHotelParams, { ...baseHotelParams, nationality: 'GB' })).toBe(false);
  });
});
