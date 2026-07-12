import { describe, expect, it, vi } from 'vitest';

import { areHotelParamsEqual } from '@/utils/searchResultsCache';

import {
  hydrateFlightSideSearchFromItinerary,
  hydrateHotelSideSearchFromItinerary,
} from './hydrateItinerarySideSearches';

// Real action creators — no mocking. We inspect the dispatched action objects
// instead, which is simpler than mocking the slice modules (whose default
// exports are reducers the store relies on).
const FLIGHT_CACHE_ACTION_TYPE = 'flightBooking/setCachedFlightResults';
const FLIGHT_FORM_ACTION_TYPE = 'flightBooking/setSearchFormParams';
const HOTEL_CACHE_ACTION_TYPE = 'hotelBooking/setCachedHotelResults';
const HOTEL_FORM_ACTION_TYPE = 'hotelBooking/setSearchFormParams';
const FLIGHT_PATH_ACTION_TYPE = 'ui/setLastFlightPath';
const HOTEL_PATH_ACTION_TYPE = 'ui/setLastHotelPath';

describe('hydrateFlightSideSearchFromItinerary', () => {
  it('no-ops when flights array is missing', () => {
    const dispatch = vi.fn();
    hydrateFlightSideSearchFromItinerary(dispatch, {});
    expect(dispatch).not.toHaveBeenCalled();
  });

  it('no-ops when flights array is empty', () => {
    const dispatch = vi.fn();
    hydrateFlightSideSearchFromItinerary(dispatch, { flights: [] });
    expect(dispatch).not.toHaveBeenCalled();
  });

  it('dispatches recommendations data + last-path when flights present', () => {
    const dispatch = vi.fn();
    hydrateFlightSideSearchFromItinerary(dispatch, {
      flights: [
        { id: 'f1', price: 250, currency: 'USD', stops: 0 },
        { id: 'f2', price: 320, currency: 'USD', stops: 1 },
      ],
      flight_session_id: 'fs-abc',
      flight_search_params: {
        origin: 'LHR',
        destination: 'CDG',
        departure_date: '2026-06-20',
        return_date: '2026-06-25',
        journey_type: 'Return',
      },
    });
    expect(dispatch).toHaveBeenCalledTimes(3);

    const cacheAction = dispatch.mock.calls[0]![0];
    expect(cacheAction.type).toBe(FLIGHT_CACHE_ACTION_TYPE);
    // The converter wraps in { data: FlightSearchResponseCamel, params: FlightSearchFormParams }
    expect(cacheAction.payload.data.sessionId).toBe('fs-abc');
    expect(cacheAction.payload.data.fareItineraries).toHaveLength(2);
    expect(cacheAction.payload.params.from).toBeTruthy();

    // setSearchFormParams must carry the same params so areFlightParamsEqual returns true on FlightSearchPage mount
    const formAction = dispatch.mock.calls[1]![0];
    expect(formAction.type).toBe(FLIGHT_FORM_ACTION_TYPE);
    expect(formAction.payload).toEqual(cacheAction.payload.params);

    const pathAction = dispatch.mock.calls[2]![0];
    expect(pathAction.type).toBe(FLIGHT_PATH_ACTION_TYPE);
    expect(pathAction.payload).toBe('/flights/search');
  });

  it('uses search_params fallback when flight_search_params absent', () => {
    const dispatch = vi.fn();
    hydrateFlightSideSearchFromItinerary(dispatch, {
      flights: [{ id: 'f1', price: 200, currency: 'EUR', stops: 0 }],
      search_params: { origin: 'AMS', destination: 'NRT' },
    });
    const first = dispatch.mock.calls[0]![0];
    // setCachedFlightResults receives { data: FlightSearchResponseCamel, params }
    // The origin is reflected in params.from (mapped from origin field via searchParamsToFormParams)
    expect(first.payload.params.from).toBeTruthy();
  });
});

describe('hydrateHotelSideSearchFromItinerary', () => {
  it('no-ops when hotels array is missing', () => {
    const dispatch = vi.fn();
    hydrateHotelSideSearchFromItinerary(dispatch, {});
    expect(dispatch).not.toHaveBeenCalled();
  });

  it('dispatches cached results + form params + last-path when hotels present', () => {
    const dispatch = vi.fn();
    hydrateHotelSideSearchFromItinerary(dispatch, {
      hotels: [
        { hotel_id: 'h1', token_id: 't1', product_id: 'p1', per_night_price: 120, total_price: 240, currency: 'USD' },
        { hotel_id: 'h2', token_id: 't2', product_id: 'p2', per_night_price: 250, total_price: 500, currency: 'USD' },
      ],
      hotel_session_id: 'hs-xyz',
      hotel_search_params: {
        destination_city: 'Tokyo',
        country: 'JP',
        check_in_date: '2026-06-20',
        check_out_date: '2026-06-25',
        rooms: 1,
        adults: 2,
      },
    });
    expect(dispatch).toHaveBeenCalledTimes(4);

    const cacheAction = dispatch.mock.calls[0]![0];
    expect(cacheAction.type).toBe(HOTEL_CACHE_ACTION_TYPE);
    expect(cacheAction.payload.data.sessionId).toBe('hs-xyz');
    expect(cacheAction.payload.data.hotels).toHaveLength(2);
    expect(cacheAction.payload.data.totalResults).toBe(2);
    expect(cacheAction.payload.params.destination).toBe('Tokyo');
    expect(cacheAction.payload.params.checkin).toBe('2026-06-20');
    expect(cacheAction.payload.params.checkout).toBe('2026-06-25');

    const formAction = dispatch.mock.calls[1]![0];
    expect(formAction.type).toBe(HOTEL_FORM_ACTION_TYPE);
    expect(formAction.payload.destination).toBe('Tokyo');

    const tripTypeAction = dispatch.mock.calls[2]![0];
    expect(tripTypeAction.type).toBe('hotelBooking/setTripType');
    expect(tripTypeAction.payload).toBe('single');

    const pathAction = dispatch.mock.calls[3]![0];
    expect(pathAction.type).toBe(HOTEL_PATH_ACTION_TYPE);
    expect(pathAction.payload).toBe('/hotels/search');
  });

  it('searchFormParams and cachedHotelResultsParams satisfy areHotelParamsEqual (warm-cache contract)', () => {
    const dispatch = vi.fn();
    hydrateHotelSideSearchFromItinerary(dispatch, {
      hotels: [
        { hotel_id: 'h1', token_id: 't1', product_id: 'p1', per_night_price: 99, total_price: 198, currency: 'USD' },
      ],
      hotel_session_id: 'hs-contract',
      hotel_search_params: {
        destination_city: 'Paris',
        country: 'FR',
        check_in_date: '2026-07-01',
        check_out_date: '2026-07-05',
        rooms: 1,
        adults: 2,
      },
    });
    const cacheAction = dispatch.mock.calls[0]![0];
    const formAction = dispatch.mock.calls[1]![0];
    expect(areHotelParamsEqual(cacheAction.payload.params, formAction.payload)).toBe(true);
  });

  it('produces HotelItinerary records with required FlightLogic IDs', () => {
    const dispatch = vi.fn();
    hydrateHotelSideSearchFromItinerary(dispatch, {
      hotels: [
        { hotel_id: 'h1', token_id: 't1', product_id: 'p1', hotel_name: 'Hotel A', per_night_price: 120, currency: 'USD' },
      ],
      hotel_search_params: { destination_city: 'Rome' },
    });
    const cacheAction = dispatch.mock.calls[0]![0];
    const hotel = cacheAction.payload.data.hotels[0];
    expect(hotel.id).toBe('h1');
    expect(hotel.tokenId).toBe('t1');
    expect(hotel.productId).toBe('p1');
  });
});
