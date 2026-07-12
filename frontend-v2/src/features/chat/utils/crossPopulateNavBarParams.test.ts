import { describe, it, expect, beforeEach, vi } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import type { AppDispatch } from '@/store';
import flightBookingReducer, {
  setCachedFlightResults,
  type FlightSearchFormParams,
} from '@/store/slices/flightBookingSlice';
import hotelBookingReducer, {
  setCachedHotelResults,
} from '@/store/slices/hotelBookingSlice';
import type { HotelSearchFormParams } from '@/types/hotels';
import uiReducer from '@/store/slices/uiSlice';
import {
  crossPopulateHotelFromFlightParams,
  crossPopulateFlightFromHotelParams,
} from './crossPopulateNavBarParams';

function makeStore() {
  return configureStore({
    reducer: {
      flightBooking: flightBookingReducer,
      hotelBooking: hotelBookingReducer,
      ui: uiReducer,
    },
  });
}

beforeEach(() => {
  vi.stubGlobal('localStorage', {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
});

describe('crossPopulateHotelFromFlightParams', () => {
  it('overwrites hotel form params with the derived trip and leaves the existing hotel cache untouched', () => {
    const store = makeStore();

    const cachedHotelParams: HotelSearchFormParams = {
      destination: 'Lisbon',
      checkin: '2026-09-15',
      checkout: '2026-09-20',
      rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
      nationality: 'US',
    };
    store.dispatch(
      setCachedHotelResults({
        data: {
          sessionId: 'h-1',
          hotels: [],
          totalResults: 0,
          searchParams: {
            checkin: '2026-09-15',
            checkout: '2026-09-20',
            cityName: 'Lisbon',
            occupancy: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
            nationality: 'US',
          },
        },
        params: cachedHotelParams,
      })
    );

    (store.dispatch as AppDispatch)(
      crossPopulateHotelFromFlightParams({
        origin: 'Dublin',
        destination: 'Lisbon, Portugal',
        departure_date: '2026-09-15',
        return_date: '2026-09-20',
        journey_type: 'RoundTrip',
        passengers: { adults: 2, children: 0, infants: 0 },
      })
    );

    const hotelState = store.getState().hotelBooking;
    // Form takes the derived (verbose) destination — always overwrite.
    expect(hotelState.searchFormParams.destination).toBe('Lisbon, Portugal');
    // Cache untouched — the slice `trusted` flag governs page behavior, not cross-populate.
    expect(hotelState.cachedHotelResults).not.toBeNull();
  });

  it('overwrites hotel form when the flight trip describes a different destination (does NOT proactively clear cache)', () => {
    const store = makeStore();

    store.dispatch(
      setCachedHotelResults({
        data: {
          sessionId: 'h-1',
          hotels: [],
          totalResults: 0,
          searchParams: {
            checkin: '2026-09-15',
            checkout: '2026-09-20',
            cityName: 'Lisbon',
            occupancy: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
            nationality: 'US',
          },
        },
        params: {
          destination: 'Lisbon',
          checkin: '2026-09-15',
          checkout: '2026-09-20',
          rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
          nationality: 'US',
        },
      })
    );

    (store.dispatch as AppDispatch)(
      crossPopulateHotelFromFlightParams({
        origin: 'Dublin',
        destination: 'Rome',
        departure_date: '2026-10-01',
        return_date: '2026-10-08',
        journey_type: 'RoundTrip',
        passengers: { adults: 2, children: 0, infants: 0 },
      })
    );

    const hotelState = store.getState().hotelBooking;
    expect(hotelState.searchFormParams.destination).toBe('Rome');
    // Cache is NOT proactively cleared — strict equality on HotelSearchPage handles refetch.
    expect(hotelState.cachedHotelResults).not.toBeNull();
  });

  it('is a no-op when flight params omit destination', () => {
    const store = makeStore();
    const before = store.getState().hotelBooking.searchFormParams;

    (store.dispatch as AppDispatch)(
      crossPopulateHotelFromFlightParams({
        origin: 'Dublin',
        destination: '',
        departure_date: '2026-09-15',
        return_date: null,
        journey_type: 'OneWay',
        passengers: { adults: 1, children: 0, infants: 0 },
      })
    );

    expect(store.getState().hotelBooking.searchFormParams).toEqual(before);
  });
});

describe('crossPopulateFlightFromHotelParams', () => {
  it('overwrites flight form params (empty origin) with the derived trip and leaves the existing flight cache untouched', () => {
    const store = makeStore();

    const cachedFlightParams: FlightSearchFormParams = {
      tripType: 'round-trip',
      from: '',
      to: 'Lisbon',
      date: '2026-09-15',
      returnDate: '2026-09-20',
      travellers: { adults: 2, children: 0, infants: 0, cabinClass: 'Economy' },
      destinationIsCity: true,
    };
    store.dispatch(
      setCachedFlightResults({
        data: { sessionId: 'f-1', fareItineraries: [] },
        params: cachedFlightParams,
      })
    );

    (store.dispatch as AppDispatch)(
      crossPopulateFlightFromHotelParams({
        destination_city: 'Lisbon, Portugal',
        check_in_date: '2026-09-15',
        check_out_date: '2026-09-20',
        adults: 2,
        children: 0,
      })
    );

    const flightState = store.getState().flightBooking;
    // Form takes the derived (verbose) destination — always overwrite.
    expect(flightState.searchFormParams.from).toBe('');
    expect(flightState.searchFormParams.to).toBe('Lisbon, Portugal');
    expect(flightState.searchFormParams.tripType).toBe('round-trip');
    // Cache untouched.
    expect(flightState.cachedFlightResults).not.toBeNull();
  });

  it('overwrites flight form when the hotel trip describes a different destination (does NOT proactively clear cache)', () => {
    const store = makeStore();

    store.dispatch(
      setCachedFlightResults({
        data: { sessionId: 'f-1', fareItineraries: [] },
        params: {
          tripType: 'round-trip',
          from: 'Dublin',
          to: 'Lisbon',
          date: '2026-09-15',
          returnDate: '2026-09-20',
          travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
        },
      })
    );

    (store.dispatch as AppDispatch)(
      crossPopulateFlightFromHotelParams({
        destination_city: 'Rome',
        check_in_date: '2026-10-01',
        check_out_date: '2026-10-08',
        adults: 2,
        children: 0,
      })
    );

    const flightState = store.getState().flightBooking;
    expect(flightState.searchFormParams.to).toBe('Rome');
    // Cache is NOT proactively cleared — strict equality on FlightSearchPage handles refetch.
    expect(flightState.cachedFlightResults).not.toBeNull();
  });

  it('is a no-op when hotel params omit destination', () => {
    const store = makeStore();
    const before = store.getState().flightBooking.searchFormParams;

    (store.dispatch as AppDispatch)(
      crossPopulateFlightFromHotelParams({
        destination_city: '',
        check_in_date: '2026-09-15',
        check_out_date: '2026-09-20',
        adults: 2,
        children: 0,
      })
    );

    expect(store.getState().flightBooking.searchFormParams).toEqual(before);
  });
});
