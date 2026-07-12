import { describe, it, expect, vi } from 'vitest';
import type { AppDispatch } from '@/store';
import { hydrateFlightSearchResultsFromPayload } from './hydrateFlightRecommendationsFromChatResponse';

const baseSearchParams = {
  origin: 'LHR',
  destination: 'JFK',
  departure_date: '2026-05-01',
  return_date: null as string | null,
  journey_type: 'OneWay' as 'OneWay' | 'Return' | 'RoundTrip',
  passengers: { adults: 1, children: 0, infants: 0 },
};

const emptyCategories = {
  cheapest: { label: 'Cheapest', flights: [] },
  fastest: { label: 'Fastest', flights: [] },
  best_value: { label: 'Best Value', flights: [] },
};

const emptyPayload = (overrides: Partial<typeof baseSearchParams> = {}) => ({
  search_params: { ...baseSearchParams, ...overrides },
  summary: { total_flights: 0, direct_count: 0, price_range: { min: 0, max: 0 } },
  categories: emptyCategories,
  flights: [],
  session_id: 'test-session',
});

function findSetSearchParamsPayload(dispatch: ReturnType<typeof vi.fn>) {
  const call = dispatch.mock.calls
    .map(([action]) => action as { type: string; payload: unknown })
    .find((a) => a.type === 'flightBooking/setSearchFormParams');
  return call?.payload as Record<string, unknown> | undefined;
}

describe('hydrateFlightSearchResultsFromPayload', () => {
  it('returns null for invalid payload', () => {
    const dispatch = vi.fn() as unknown as AppDispatch;
    expect(hydrateFlightSearchResultsFromPayload(dispatch, null)).toBeNull();
    expect(hydrateFlightSearchResultsFromPayload(dispatch, {})).toBeNull();
    expect(hydrateFlightSearchResultsFromPayload(dispatch, 'invalid')).toBeNull();
  });

  it('maps journey_type Return to round-trip', () => {
    const dispatch = vi.fn();
    hydrateFlightSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({ journey_type: 'Return', return_date: '2026-05-15' })
    );
    const payload = findSetSearchParamsPayload(dispatch);
    expect(payload?.tripType).toBe('round-trip');
  });

  it('maps journey_type RoundTrip to round-trip', () => {
    const dispatch = vi.fn();
    hydrateFlightSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({ journey_type: 'RoundTrip', return_date: '2026-05-15' })
    );
    const payload = findSetSearchParamsPayload(dispatch);
    expect(payload?.tripType).toBe('round-trip');
  });

  it('maps journey_type OneWay to one-way', () => {
    const dispatch = vi.fn();
    hydrateFlightSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({ journey_type: 'OneWay' })
    );
    const payload = findSetSearchParamsPayload(dispatch);
    expect(payload?.tripType).toBe('one-way');
  });

  it('uses origin_city and destination_city for from/to when present', () => {
    const dispatch = vi.fn();
    hydrateFlightSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({
        origin_city: 'London',
        destination_city: 'New York',
        origin_iata: 'LHR',
        destination_iata: 'JFK',
      } as Partial<typeof baseSearchParams>)
    );
    const payload = findSetSearchParamsPayload(dispatch);
    expect(payload?.from).toBe('London');
    expect(payload?.to).toBe('New York');
    expect((payload?.fromAirport as { city?: string })?.city).toBe('London');
    expect((payload?.toAirport as { city?: string })?.city).toBe('New York');
  });

  it('falls back to IATA code for from/to when city fields are absent', () => {
    const dispatch = vi.fn();
    hydrateFlightSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({
        origin_iata: 'LHR',
        destination_iata: 'JFK',
      } as Partial<typeof baseSearchParams>)
    );
    const payload = findSetSearchParamsPayload(dispatch);
    expect(payload?.from).toBe('LHR');
    expect(payload?.to).toBe('JFK');
  });

  it('sets fromAirport to undefined when origin_iata is absent', () => {
    const dispatch = vi.fn();
    hydrateFlightSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload()
    );
    const payload = findSetSearchParamsPayload(dispatch);
    expect(payload?.fromAirport).toBeUndefined();
    expect(payload?.toAirport).toBeUndefined();
  });

  it('sets fromAirport.iata when origin_iata is present', () => {
    const dispatch = vi.fn();
    hydrateFlightSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({
        origin_iata: 'LHR',
        destination_iata: 'JFK',
      } as Partial<typeof baseSearchParams>)
    );
    const payload = findSetSearchParamsPayload(dispatch);
    expect((payload?.fromAirport as { iata?: string })?.iata).toBe('LHR');
    expect((payload?.toAirport as { iata?: string })?.iata).toBe('JFK');
  });

  it('returns extracted data on success', () => {
    const dispatch = vi.fn();
    const result = hydrateFlightSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload()
    );
    expect(result).not.toBeNull();
    expect(result?.data.search_params.origin).toBe('LHR');
  });

  it('dispatches setCachedFlightResults (not setLastFlightRecommendationsData)', () => {
    const dispatch = vi.fn();
    hydrateFlightSearchResultsFromPayload(dispatch as unknown as AppDispatch, emptyPayload());
    const types = dispatch.mock.calls.map(([a]) => (a as { type: string }).type);
    expect(types).toContain('flightBooking/setCachedFlightResults');
    expect(types).not.toContain('flightBooking/setLastFlightRecommendationsData');
  });
});
