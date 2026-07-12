import { describe, it, expect } from 'vitest';
import {
  extractMulticityFlightSearchResults,
  legToExtractedSingleLeg,
} from './extractMulticityFlightSearchResults';
import type { FlightInfo } from '@/types/api.helpers';

const minimalFlight = (id: string): FlightInfo =>
  ({
    id,
    departure_time: '10:00',
    departure_date: '2026-04-01',
    arrival_time: '12:00',
    arrival_date: '2026-04-01',
    origin_code: 'LHR',
    destination_code: 'BCN',
    duration: '2h',
    duration_minutes: 120,
    stops: 0,
    price: 100,
    currency: 'USD',
    airline: 'BA',
    airline_code: 'BA',
  }) as FlightInfo;

const categoriesWithOneEach = {
  cheapest: { label: 'Cheapest', flights: [minimalFlight('c')] },
  fastest: { label: 'Fastest', flights: [minimalFlight('f')] },
  best_value: { label: 'Best Value', flights: [minimalFlight('b')] },
};

const tripSearchParams = {
  origin: 'LHR',
  destination: 'BCN',
  departure_date: '2026-04-01',
  return_date: null as string | null,
  journey_type: 'Circle' as const,
  passengers: { adults: 1, children: 0, infants: 0 },
};

describe('extractMulticityFlightSearchResults', () => {
  it('parses nested data.data with snake_case multicity_legs', () => {
    const raw = {
      data: {
        data: {
          search_params: tripSearchParams,
          multicity_parallel: true,
          multicity_legs: [
            {
              leg_index: 0,
              origin: 'LHR',
              destination: 'BCN',
              departure_date: '2026-04-01',
              session_id: 'sess-a',
              summary: { total_flights: 3, direct_count: 1, price_range: { min: 50, max: 200 } },
              categories: categoriesWithOneEach,
            },
            {
              leg_index: 1,
              origin: 'BCN',
              destination: 'LHR',
              departure_date: '2026-04-10',
              session_id: 'sess-b',
              summary: { total_flights: 2, direct_count: 0, price_range: { min: 60, max: 180 } },
              categories: categoriesWithOneEach,
            },
          ],
        },
      },
    };
    const out = extractMulticityFlightSearchResults(raw);
    expect(out).not.toBeNull();
    if (!out) return;
    expect(out.legs).toHaveLength(2);
    expect(out.searchParams.journey_type).toBe('Circle');
    expect(out.multicityParallel).toBe(true);
    expect(out.legs[0]?.sessionId).toBe('sess-a');
    expect(out.legs[1]?.departureDate).toBe('2026-04-10');
  });

  it('parses flat top-level multicity_legs', () => {
    const raw = {
      search_params: tripSearchParams,
      multicity_legs: [
        {
          legIndex: 0,
          origin: 'AMS',
          destination: 'CDG',
          departureDate: '2026-05-01',
          sessionId: 's0',
          summary: { total_flights: 1, direct_count: 1, price_range: { min: 1, max: 2 } },
          categories: categoriesWithOneEach,
        },
        {
          legIndex: 1,
          origin: 'CDG',
          destination: 'AMS',
          departureDate: '2026-05-10',
          sessionId: 's1',
          summary: { total_flights: 1, direct_count: 1, price_range: { min: 1, max: 2 } },
          categories: categoriesWithOneEach,
        },
      ],
    };
    const out = extractMulticityFlightSearchResults(raw);
    expect(out).not.toBeNull();
    if (!out) return;
    expect(out.legs[0]?.origin).toBe('AMS');
    expect(out.legs[1]?.sessionId).toBe('s1');
  });

  it('returns null when fewer than 2 legs', () => {
    expect(
      extractMulticityFlightSearchResults({
        search_params: tripSearchParams,
        multicity_legs: [
          {
            origin: 'A',
            destination: 'B',
            departure_date: '2026-01-01',
            session_id: 'x',
            summary: { total_flights: 0, direct_count: 0, price_range: { min: 0, max: 0 } },
            categories: categoriesWithOneEach,
          },
        ],
      })
    ).toBeNull();
  });
});

describe('legToExtractedSingleLeg', () => {
  it('merges trip params and sets per-leg session_id', () => {
    const leg = {
      legIndex: 1,
      origin: 'BCN',
      destination: 'LHR',
      departureDate: '2026-04-10',
      sessionId: 'leg-session-xyz',
      summary: { total_flights: 2, direct_count: 0, price_range: { min: 1, max: 9 } },
      categories: categoriesWithOneEach,
      flights: [],
    };
    const extracted = legToExtractedSingleLeg(tripSearchParams, leg);
    expect(extracted.session_id).toBe('leg-session-xyz');
    expect(extracted.data.search_params.origin).toBe('BCN');
    expect(extracted.data.search_params.destination).toBe('LHR');
    expect(extracted.data.search_params.departure_date).toBe('2026-04-10');
    expect(extracted.data.search_params.journey_type).toBe('Circle');
  });
});
