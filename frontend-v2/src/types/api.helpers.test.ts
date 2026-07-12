import { describe, expect, it } from 'vitest';
import {
  extractFlightSearchResults,
  extractHotelSearchResults,
  hasCompleteHotelSearchCategories,
  hasAnyHotelSearchCategory,
  type FlightSearchResultsEnvelope,
} from './api.helpers';

function makeFlightSearchResultsData(): FlightSearchResultsEnvelope {
  return {
    session_id: 'sess-123',
    flights: [],
    data: {
      search_params: {
        origin: 'LHR',
        destination: 'JFK',
        departure_date: '2026-06-01',
        return_date: null,
        journey_type: 'OneWay',
        passengers: {
          adults: 1,
          children: 0,
          infants: 0,
        },
      },
      summary: {
        total_flights: 12,
        direct_count: 4,
        price_range: {
          min: 300,
          max: 900,
          currency: 'USD',
        },
      },
      categories: {
        cheapest: { label: 'Cheapest', flights: [] },
        fastest: { label: 'Fastest', flights: [] },
        best_value: { label: 'Best Value', flights: [] },
      },
    },
  };
}

describe('extractFlightSearchResults', () => {
  it('extracts origin and destination coordinates from top-level response fields', () => {
    const data = makeFlightSearchResultsData();
    data.origin_location = { latitude: 51.47, longitude: -0.4543 };
    data.destination_location = { latitude: 40.6413, longitude: -73.7781 };

    const extracted = extractFlightSearchResults(data);

    expect(extracted?.origin_location).toEqual({
      latitude: 51.47,
      longitude: -0.4543,
    });
    expect(extracted?.destination_location).toEqual({
      latitude: 40.6413,
      longitude: -73.7781,
    });
  });

  it('falls back to nested search_params coordinates when top-level fields are absent', () => {
    const data = makeFlightSearchResultsData();
    data.data.search_params.origin_location = { latitude: 41.3851, longitude: 2.1734 };
    data.data.search_params.destination_location = { latitude: 48.8566, longitude: 2.3522 };

    const extracted = extractFlightSearchResults(data);

    expect(extracted?.origin_location).toEqual({
      latitude: 41.3851,
      longitude: 2.1734,
    });
    expect(extracted?.destination_location).toEqual({
      latitude: 48.8566,
      longitude: 2.3522,
    });
  });

  it('ignores invalid coordinate payloads', () => {
    const data = makeFlightSearchResultsData();
    const invalidData = data as unknown as Record<string, unknown>;
    invalidData.origin_location = { latitude: 'nope', longitude: 'still nope' };

    const extracted = extractFlightSearchResults(invalidData);

    expect(extracted?.origin_location).toBeUndefined();
    expect(extracted?.destination_location).toBeUndefined();
  });

  /**
   * Some chat APIs send search_params / summary / categories on ChatResponse.data
   * without an extra `data` wrapper (nested shape uses data.data.*).
   */
  it('extracts flat ChatResponse.data shape and builds flights from categories when flights omitted', () => {
    const flat = {
      search_params: {
        origin: 'LHR',
        destination: 'JFK',
        departure_date: '2026-04-26',
        return_date: null,
        journey_type: 'OneWay',
        passengers: { adults: 1, children: 0, infants: 0 },
      },
      summary: {
        total_flights: 48,
        direct_count: 6,
        price_range: { min: 500, max: 900, currency: 'USD' },
      },
      categories: {
        cheapest: {
          label: 'Cheapest',
          flights: [
            {
              id: 'a',
              departure_time: '10:00',
              departure_date: '2026-04-26',
              arrival_time: '13:00',
              arrival_date: '2026-04-26',
              origin_code: 'LHR',
              destination_code: 'JFK',
              duration: '8h',
              duration_minutes: 480,
              stops: 0,
              price: 600,
              currency: 'USD',
              airline: 'AA',
              airline_code: 'AA',
            },
          ],
        },
        fastest: {
          label: 'Fastest',
          flights: [
            {
              id: 'b',
              departure_time: '11:00',
              departure_date: '2026-04-26',
              arrival_time: '14:00',
              arrival_date: '2026-04-26',
              origin_code: 'LHR',
              destination_code: 'JFK',
              duration: '8h',
              duration_minutes: 480,
              stops: 0,
              price: 700,
              currency: 'USD',
              airline: 'BA',
              airline_code: 'BA',
            },
          ],
        },
        best_value: { label: 'Best Value', flights: [] },
      },
    };

    const extracted = extractFlightSearchResults(flat);

    expect(extracted).not.toBeNull();
    expect(extracted?.data.search_params.origin).toBe('LHR');
    expect(extracted?.flights.length).toBeGreaterThan(0);
  });

  it('dedupes the same flight id across categories when building flights from categories', () => {
    const shared = {
      id: 'same-flight',
      departure_time: '10:00',
      departure_date: '2026-04-26',
      arrival_time: '13:00',
      arrival_date: '2026-04-26',
      origin_code: 'LHR',
      destination_code: 'JFK',
      duration: '8h',
      duration_minutes: 480,
      stops: 0,
      price: 600,
      currency: 'USD',
      airline: 'AA',
      airline_code: 'AA',
    };
    const flat = {
      search_params: {
        origin: 'LHR',
        destination: 'JFK',
        departure_date: '2026-04-26',
        return_date: null,
        journey_type: 'OneWay' as const,
        passengers: { adults: 1, children: 0, infants: 0 },
      },
      summary: {
        total_flights: 1,
        direct_count: 1,
        price_range: { min: 600, max: 600, currency: 'USD' },
      },
      categories: {
        cheapest: { label: 'Cheapest', flights: [shared] },
        fastest: { label: 'Fastest', flights: [shared] },
        best_value: { label: 'Best Value', flights: [] },
      },
    };

    const extracted = extractFlightSearchResults(flat);

    expect(extracted?.flights).toHaveLength(1);
    expect(extracted?.flights?.[0]?.id).toBe('same-flight');
  });

  it('dedupes across categories when id is missing (fallback key excludes category)', () => {
    const flightA = {
      id: '',
      departure_time: '10:00',
      departure_date: '2026-04-26',
      arrival_time: '13:00',
      arrival_date: '2026-04-26',
      origin_code: 'LHR',
      destination_code: 'JFK',
      duration: '8h',
      duration_minutes: 480,
      stops: 0,
      price: 600,
      currency: 'USD',
      airline: 'AA',
      airline_code: 'AA',
    };
    const flat = {
      search_params: {
        origin: 'LHR',
        destination: 'JFK',
        departure_date: '2026-04-26',
        return_date: null,
        journey_type: 'OneWay' as const,
        passengers: { adults: 1, children: 0, infants: 0 },
      },
      summary: {
        total_flights: 1,
        direct_count: 1,
        price_range: { min: 600, max: 600, currency: 'USD' },
      },
      categories: {
        cheapest: { label: 'Cheapest', flights: [flightA] },
        fastest: { label: 'Fastest', flights: [{ ...flightA }] },
        best_value: { label: 'Best Value', flights: [] },
      },
    };

    const extracted = extractFlightSearchResults(flat);

    expect(extracted?.flights).toHaveLength(1);
  });
});

function makeHotelRaw(id: string) {
  return {
    hotel_id: id,
    token_id: `t-${id}`,
    product_id: `p-${id}`,
    hotel_name: `Hotel ${id}`,
    city: 'Paris',
    country: 'FR',
    latitude: '48.85',
    longitude: '2.35',
    total_price: 100,
    currency: 'EUR',
  };
}

describe('extractHotelSearchResults', () => {
  it('extracts nested envelope shape', () => {
    const h = makeHotelRaw('a');
    const data = {
      session_id: 'hsess-1',
      data: {
        search_params: {
          destination_city: 'Paris',
          check_in_date: '2026-06-01',
          check_out_date: '2026-06-03',
          rooms: 1,
          adults: 2,
        },
        summary: {
          total_hotels: 3,
          nights: 2,
          price_range: { min: 90, max: 200, currency: 'EUR' },
        },
        categories: {
          cheapest: { label: 'Cheapest', hotels: [h] },
          highest_rated: { label: 'Top', hotels: [h] },
          best_value: { label: 'Best', hotels: [h] },
        },
      },
    };

    const extracted = extractHotelSearchResults(data);
    expect(extracted).not.toBeNull();
    expect(extracted?.session_id).toBe('hsess-1');
    expect(extracted?.data.search_params.destination_city).toBe('Paris');
    expect(extracted?.hotels.length).toBeGreaterThan(0);
    expect(hasCompleteHotelSearchCategories(extracted)).toBe(true);
  });

  it('extracts flat ChatResponse.data shape and builds hotels from categories when hotels omitted', () => {
    const h1 = makeHotelRaw('x');
    const h2 = makeHotelRaw('y');
    const flat = {
      session_id: 'flat-1',
      search_params: {
        destination: 'London',
        check_in_date: '2026-07-01',
        check_out_date: '2026-07-05',
        rooms: 1,
        adults: 1,
      },
      summary: {
        total_found: 2,
        nights: 4,
        price_range: { min: 50, max: 300, currency: 'GBP' },
      },
      categories: {
        cheapest: { label: 'Cheapest', hotels: [h1] },
        highest_rated: { label: 'Top', hotels: [h2] },
        best_value: { label: 'Best', hotels: [h1] },
      },
    };

    const extracted = extractHotelSearchResults(flat);

    expect(extracted).not.toBeNull();
    expect(extracted?.hotels.length).toBeGreaterThan(0);
  });

  it('returns null for invalid payload', () => {
    expect(extractHotelSearchResults(null)).toBeNull();
    expect(extractHotelSearchResults({ foo: 1 })).toBeNull();
  });

  it('hasAnyHotelSearchCategory is true when only one bucket has hotels', () => {
    const h = makeHotelRaw('solo');
    const partial = {
      session_id: 'p1',
      data: {
        search_params: { destination_city: 'Paris' },
        summary: { total_hotels: 1, nights: 1 },
        categories: {
          cheapest: { hotels: [h] },
          highest_rated: { hotels: [] },
          best_value: { hotels: [] },
        },
      },
    };
    const extracted = extractHotelSearchResults(partial);
    expect(extracted).not.toBeNull();
    expect(hasAnyHotelSearchCategory(extracted)).toBe(true);
    expect(hasCompleteHotelSearchCategories(extracted)).toBe(false);
  });

  it('hasAnyHotelSearchCategory is false when all buckets are empty', () => {
    const emptyBuckets = {
      session_id: 'e1',
      data: {
        search_params: { destination_city: 'Paris' },
        summary: { total_hotels: 0, nights: 1 },
        categories: {
          cheapest: { hotels: [] },
          highest_rated: { hotels: [] },
          best_value: { hotels: [] },
        },
      },
    };
    const extracted = extractHotelSearchResults(emptyBuckets);
    expect(extracted).not.toBeNull();
    expect(hasAnyHotelSearchCategory(extracted)).toBe(false);
  });
});
