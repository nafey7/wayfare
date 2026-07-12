import { describe, it, expect, vi } from 'vitest';
import type { AppDispatch } from '@/store';
import { hydrateHotelSearchResultsFromPayload } from './hydrateHotelRecommendationsFromChatResponse';
import type { RoomOccupancy } from '@/types/hotels';

const emptyCategories = {
  cheapest: { label: 'Cheapest', hotels: [] },
  highest_rated: { label: 'Highest Rated', hotels: [] },
  best_value: { label: 'Best Value', hotels: [] },
};

const emptyPayload = (overrides: Record<string, unknown> = {}) => ({
  search_params: {
    destination_city: 'Paris',
    check_in_date: '2026-06-01',
    check_out_date: '2026-06-05',
    rooms: 1,
    adults: 2,
    children: 0,
    ...overrides,
  },
  summary: { total_hotels: 0, nights: 4, price_range: { min: 0, max: 0 } },
  categories: emptyCategories,
  hotels: [],
  session_id: 'test-session',
});

function findSetSearchParamsPayload(dispatch: ReturnType<typeof vi.fn>) {
  const call = dispatch.mock.calls
    .map(([action]) => action as { type: string; payload: unknown })
    .find((a) => a.type === 'hotelBooking/setSearchFormParams');
  return call?.payload as Record<string, unknown> | undefined;
}

describe('hydrateHotelSearchResultsFromPayload', () => {
  it('returns null for invalid payload', () => {
    const dispatch = vi.fn() as unknown as AppDispatch;
    expect(hydrateHotelSearchResultsFromPayload(dispatch, null)).toBeNull();
    expect(hydrateHotelSearchResultsFromPayload(dispatch, {})).toBeNull();
    expect(hydrateHotelSearchResultsFromPayload(dispatch, 'invalid')).toBeNull();
  });

  it('returns extracted data on success', () => {
    const dispatch = vi.fn();
    const result = hydrateHotelSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload()
    );
    expect(result).not.toBeNull();
  });

  it('distributes adults evenly across rooms when divisible', () => {
    const dispatch = vi.fn();
    hydrateHotelSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({ rooms: 3, adults: 6, children: 0 })
    );
    const payload = findSetSearchParamsPayload(dispatch);
    const rooms = payload?.rooms as RoomOccupancy[];
    expect(rooms).toHaveLength(3);
    expect(rooms.every((r) => r.adult === 2)).toBe(true);
    expect(rooms.reduce((s, r) => s + r.adult, 0)).toBe(6);
  });

  it('puts the remainder adults in the first room when not evenly divisible', () => {
    const dispatch = vi.fn();
    hydrateHotelSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({ rooms: 3, adults: 5, children: 0 })
    );
    const payload = findSetSearchParamsPayload(dispatch);
    const rooms = payload?.rooms as RoomOccupancy[];
    expect(rooms).toHaveLength(3);
    expect(rooms[0]!.adult).toBeGreaterThan(rooms[1]!.adult);
    expect(rooms.reduce((s, r) => s + r.adult, 0)).toBe(5);
  });

  it('preserves total adults count with uneven distribution (5 adults, 3 rooms)', () => {
    const dispatch = vi.fn();
    hydrateHotelSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({ rooms: 3, adults: 5, children: 0 })
    );
    const payload = findSetSearchParamsPayload(dispatch);
    const rooms = payload?.rooms as RoomOccupancy[];
    const total = rooms.reduce((s, r) => s + r.adult, 0);
    expect(total).toBe(5);
  });

  it('clamps remainder to zero when totalAdults < roomCount (1 adult, 3 rooms)', () => {
    const dispatch = vi.fn();
    hydrateHotelSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({ rooms: 3, adults: 1, children: 0 })
    );
    const payload = findSetSearchParamsPayload(dispatch);
    const rooms = payload?.rooms as RoomOccupancy[];
    expect(rooms).toHaveLength(3);
    expect(rooms.every((r) => r.adult >= 1)).toBe(true);
  });

  it('uses destination_city for destination field', () => {
    const dispatch = vi.fn();
    hydrateHotelSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({ destination_city: 'Paris' })
    );
    const payload = findSetSearchParamsPayload(dispatch);
    expect(payload?.destination).toBe('Paris');
  });

  it('falls back to city_name when destination_city is absent', () => {
    const dispatch = vi.fn();
    hydrateHotelSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({ destination_city: undefined, city_name: 'Lyon' })
    );
    const payload = findSetSearchParamsPayload(dispatch);
    expect(payload?.destination).toBe('Lyon');
  });

  it('falls back to destination when both city fields are absent', () => {
    const dispatch = vi.fn();
    hydrateHotelSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({ destination_city: undefined, city_name: undefined, destination: 'Marseille' })
    );
    const payload = findSetSearchParamsPayload(dispatch);
    expect(payload?.destination).toBe('Marseille');
  });

  it('maps check_in_date and check_out_date to checkin/checkout', () => {
    const dispatch = vi.fn();
    hydrateHotelSearchResultsFromPayload(
      dispatch as unknown as AppDispatch,
      emptyPayload({ check_in_date: '2026-07-10', check_out_date: '2026-07-15' })
    );
    const payload = findSetSearchParamsPayload(dispatch);
    expect(payload?.checkin).toBe('2026-07-10');
    expect(payload?.checkout).toBe('2026-07-15');
  });
});
