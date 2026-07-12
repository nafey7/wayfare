import { describe, it, expect } from 'vitest';
import {
  sortFlights,
  getFlightPrice,
  getTotalDurationMinutes,
  getDepartureTimeMinutes,
  getArrivalTimeMinutes,
  DEFAULT_FLIGHT_SORT,
  FALLBACK_FLIGHT_SORT,
  FLIGHT_SORT_OPTIONS,
  type FlightSortOption,
} from './flightSort';
import type { FilterableFlight } from './flightFilters';

function makeFlight(overrides: Partial<FilterableFlight> & { price: number; legs: FilterableFlight['legs'] }): FilterableFlight {
  return {
    id: 'f1',
    ...overrides,
  } as FilterableFlight;
}

describe('flightSort', () => {
  const leg = (_price: number, duration: string, dep: string, arr: string) => ({
    stops: 0,
    departure: { time: dep },
    arrival: { time: arr },
    duration,
    totalTimeDisplay: duration,
    airlinesInfo: [],
  });

  describe('DEFAULT_FLIGHT_SORT and FLIGHT_SORT_OPTIONS', () => {
    it('default is preference-match', () => {
      expect(DEFAULT_FLIGHT_SORT).toBe('preference-match');
    });
    it('fallback is price-low', () => {
      expect(FALLBACK_FLIGHT_SORT).toBe('price-low');
    });
    it('FLIGHT_SORT_OPTIONS includes all sort options', () => {
      expect(FLIGHT_SORT_OPTIONS).toContain('price-low');
      expect(FLIGHT_SORT_OPTIONS).toContain('duration-short');
      expect(FLIGHT_SORT_OPTIONS).toContain('preference-match');
      expect(FLIGHT_SORT_OPTIONS).toHaveLength(9);
    });
  });

  describe('getFlightPrice', () => {
    it('returns flight price or 0', () => {
      expect(getFlightPrice(makeFlight({ price: 199, legs: [] }))).toBe(199);
      expect(getFlightPrice(makeFlight({ price: 0, legs: [] }))).toBe(0);
    });
  });

  describe('getTotalDurationMinutes', () => {
    it('parses "2h 30m" to 150 minutes', () => {
      const f = makeFlight({ price: 100, legs: [leg(100, '2h 30m', '10:00', '12:30')] });
      expect(getTotalDurationMinutes(f)).toBe(150);
    });
    it('sums multiple legs', () => {
      const f = makeFlight({
        price: 100,
        legs: [
          leg(100, '2h', '10:00', '12:00'),
          leg(100, '1h 30m', '14:00', '15:30'),
        ],
      });
      expect(getTotalDurationMinutes(f)).toBe(210);
    });
  });

  describe('getDepartureTimeMinutes and getArrivalTimeMinutes', () => {
    it('parses HH:MM to minutes since midnight', () => {
      const f = makeFlight({ price: 100, legs: [leg(100, '2h', '10:30', '12:30')] });
      expect(getDepartureTimeMinutes(f)).toBe(10 * 60 + 30);
      expect(getArrivalTimeMinutes(f)).toBe(12 * 60 + 30);
    });
    it('returns null for missing time', () => {
      const f = makeFlight({ price: 100, legs: [{ stops: 0, departure: { time: 'TBD' }, arrival: { time: 'TBD' }, airlinesInfo: [] }] });
      expect(getDepartureTimeMinutes(f)).toBeNull();
    });
  });

  describe('sortFlights', () => {
    it('sorts by price-low', () => {
      const flights: FilterableFlight[] = [
        makeFlight({ price: 300, legs: [leg(300, '2h', '10:00', '12:00')] }),
        makeFlight({ price: 100, legs: [leg(100, '2h', '10:00', '12:00')] }),
        makeFlight({ price: 200, legs: [leg(200, '2h', '10:00', '12:00')] }),
      ];
      const result = sortFlights(flights, 'price-low');
      expect(result.map((f) => f.price)).toEqual([100, 200, 300]);
    });

    it('sorts by price-high', () => {
      const flights: FilterableFlight[] = [
        makeFlight({ price: 100, legs: [leg(100, '2h', '10:00', '12:00')] }),
        makeFlight({ price: 300, legs: [leg(300, '2h', '10:00', '12:00')] }),
      ];
      const result = sortFlights(flights, 'price-high');
      expect(result.map((f) => f.price)).toEqual([300, 100]);
    });

    it('sorts by duration-short', () => {
      const short = makeFlight({ price: 200, legs: [leg(200, '1h', '10:00', '11:00')] });
      const long = makeFlight({ price: 100, legs: [leg(100, '5h 30m', '10:00', '15:30')] });
      const result = sortFlights([long, short], 'duration-short');
      expect(result[0]!.id).toBe(short.id);
    });

    it('sorts by duration-long', () => {
      const short = makeFlight({ price: 200, legs: [leg(200, '1h', '10:00', '11:00')] });
      const long = makeFlight({ price: 100, legs: [leg(100, '5h', '10:00', '15:00')] });
      const result = sortFlights([short, long], 'duration-long');
      expect(result[0]!.id).toBe(long.id);
    });

    it('sorts by departure-early and departure-late', () => {
      const early = makeFlight({ price: 100, legs: [leg(100, '2h', '06:00', '08:00')] });
      const late = makeFlight({ price: 100, legs: [leg(100, '2h', '22:00', '00:00')] });
      const earlyResult = sortFlights([late, early], 'departure-early');
      expect(earlyResult[0]!.legs[0]!.departure!.time).toBe('06:00');
      const lateResult = sortFlights([early, late], 'departure-late');
      expect(lateResult[0]!.legs[0]!.departure!.time).toBe('22:00');
    });

    it('sorts by arrival-early and arrival-late', () => {
      const early = makeFlight({ price: 100, legs: [leg(100, '2h', '10:00', '11:00')] });
      const late = makeFlight({ price: 100, legs: [leg(100, '2h', '10:00', '18:00')] });
      const earlyResult = sortFlights([late, early], 'arrival-early');
      expect(earlyResult[0]!.legs[0]!.arrival!.time).toBe('11:00');
      const lateResult = sortFlights([early, late], 'arrival-late');
      expect(lateResult[0]!.legs[0]!.arrival!.time).toBe('18:00');
    });

    it('does not mutate input array', () => {
      const flights: FilterableFlight[] = [
        makeFlight({ price: 200, legs: [leg(200, '2h', '10:00', '12:00')] }),
        makeFlight({ price: 100, legs: [leg(100, '2h', '10:00', '12:00')] }),
      ];
      const copy = [...flights];
      sortFlights(flights, 'price-low');
      expect(flights[0]!.price).toBe(200);
      expect(flights).toEqual(copy);
    });

    it('defaults to price-low for unknown sort option', () => {
      const flights: FilterableFlight[] = [
        makeFlight({ price: 200, legs: [leg(200, '2h', '10:00', '12:00')] }),
        makeFlight({ price: 100, legs: [leg(100, '2h', '10:00', '12:00')] }),
      ];
      const result = sortFlights(flights, 'unknown' as FlightSortOption);
      expect(result.map((f) => f.price)).toEqual([100, 200]);
    });
  });
});
