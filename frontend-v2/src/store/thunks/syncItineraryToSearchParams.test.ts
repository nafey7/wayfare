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
import { syncItineraryToSearchParams } from './syncItineraryToSearchParams';

describe('syncItineraryToSearchParams (hotel branch)', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  it('defaults checkout to the day after check-in when return_date is empty', () => {
    const store = configureStore({
      reducer: {
        flightBooking: flightBookingReducer,
        hotelBooking: hotelBookingReducer,
      },
    });

    (store.dispatch as AppDispatch)(
      syncItineraryToSearchParams({
        destination: 'Berlin',
        departure_date: '2026-09-15',
        return_date: null,
      })
    );

    const hotel = store.getState().hotelBooking.searchFormParams;
    expect(hotel.destination).toBe('Berlin');
    expect(hotel.checkin).toBe('2026-09-15');
    expect(hotel.checkout).toBe('2026-09-16');
  });

  it('uses return_date as checkout when provided', () => {
    const store = configureStore({
      reducer: {
        flightBooking: flightBookingReducer,
        hotelBooking: hotelBookingReducer,
      },
    });

    (store.dispatch as AppDispatch)(
      syncItineraryToSearchParams({
        destination: 'Berlin',
        departure_date: '2026-09-15',
        return_date: '2026-09-20',
      })
    );

    expect(store.getState().hotelBooking.searchFormParams.checkout).toBe('2026-09-20');
  });

  it('treats whitespace-only return_date as missing and fills next day', () => {
    const store = configureStore({
      reducer: {
        flightBooking: flightBookingReducer,
        hotelBooking: hotelBookingReducer,
      },
    });

    (store.dispatch as AppDispatch)(
      syncItineraryToSearchParams({
        destination: 'Berlin',
        departure_date: '2026-09-15',
        return_date: '   ',
      })
    );

    expect(store.getState().hotelBooking.searchFormParams.checkout).toBe('2026-09-16');
  });

  it("promotes hotel tripType to 'single' and defaults flight cabinClass to Economy when payload omits cabin_class", () => {
    const store = configureStore({
      reducer: {
        flightBooking: flightBookingReducer,
        hotelBooking: hotelBookingReducer,
      },
    });

    expect(store.getState().hotelBooking.tripType).toBeNull();

    (store.dispatch as AppDispatch)(
      syncItineraryToSearchParams({
        origin: 'Dublin',
        destination: 'Berlin',
        departure_date: '2026-09-15',
        return_date: '2026-09-20',
      })
    );

    expect(store.getState().hotelBooking.tripType).toBe('single');
    expect(
      store.getState().flightBooking.searchFormParams.travellers.cabinClass
    ).toBe('Economy');
  });

  it('sets ui.lastHotelPath to encoded /hotels/search when destination and dates are complete', () => {
    const store = configureStore({
      reducer: {
        flightBooking: flightBookingReducer,
        hotelBooking: hotelBookingReducer,
        ui: uiReducer,
      },
    });

    (store.dispatch as AppDispatch)(
      syncItineraryToSearchParams({
        destination: 'Berlin',
        departure_date: '2026-09-15',
        return_date: '2026-09-20',
      })
    );

    expect(store.getState().ui.lastHotelPath).toMatch(/^\/hotels\/search\?q=/);
  });
});

describe('syncItineraryToSearchParams (cache keep-or-clear by canonical trip equality)', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  function makeStore() {
    return configureStore({
      reducer: {
        flightBooking: flightBookingReducer,
        hotelBooking: hotelBookingReducer,
        ui: uiReducer,
      },
    });
  }

  it('overwrites flight searchFormParams with the itinerary trip and keeps cache when canonical trip matches', () => {
    const store = makeStore();

    // Pre-seed cache to mirror itinerary side-search prefetch: cached params use bare city names.
    const hydratedParams: FlightSearchFormParams = {
      tripType: 'round-trip',
      from: 'Dublin',
      to: 'Lisbon',
      date: '2026-09-15',
      returnDate: '2026-09-20',
      travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
    };
    store.dispatch(
      setCachedFlightResults({
        data: { sessionId: 'sess-1', fareItineraries: [] },
        params: hydratedParams,
        trusted: true,
      })
    );
    store.dispatch({ type: 'flightBooking/setSearchFormParams', payload: hydratedParams });

    // Itinerary payload provides verbose place names; form takes the verbose
    // values (always overwrite). The cache's `trusted` flag is what tells the
    // page to render cached results, so the thunk emits the clean route.
    (store.dispatch as AppDispatch)(
      syncItineraryToSearchParams({
        origin: 'Dublin, Ireland',
        destination: 'Lisbon, Portugal',
        departure_date: '2026-09-15',
        return_date: '2026-09-20',
        trip_type: 'round_trip',
      })
    );

    const flightState = store.getState().flightBooking;
    // Form overwritten with the itinerary's verbose values.
    expect(flightState.searchFormParams.from).toBe('Dublin, Ireland');
    expect(flightState.searchFormParams.to).toBe('Lisbon, Portugal');
    // Cache untouched; trust flag still true.
    expect(flightState.cachedFlightResults).not.toBeNull();
    expect(flightState.cachedFlightResultsTrusted).toBe(true);
    // Clean route — page mount-only effect will honor the trust flag.
    expect(store.getState().ui.lastFlightPath).toBe('/flights/search');
  });

  it('overwrites flight form and uses encoded path when the itinerary trip differs from the cached trip (does NOT proactively clear cache — strict equality on the page handles refetch)', () => {
    const store = makeStore();

    const cached: FlightSearchFormParams = {
      tripType: 'round-trip',
      from: 'Dublin',
      to: 'Lisbon',
      date: '2026-09-15',
      returnDate: '2026-09-20',
      travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
    };
    store.dispatch(
      setCachedFlightResults({
        data: { sessionId: 'sess-1', fareItineraries: [] },
        params: cached,
      })
    );

    // Itinerary for a *different* trip (Paris → Rome).
    (store.dispatch as AppDispatch)(
      syncItineraryToSearchParams({
        origin: 'Paris, France',
        destination: 'Rome, Italy',
        departure_date: '2026-10-01',
        return_date: '2026-10-08',
        trip_type: 'round_trip',
      })
    );

    const flightState = store.getState().flightBooking;
    expect(flightState.searchFormParams.from).toBe('Paris, France');
    expect(flightState.searchFormParams.to).toBe('Rome, Italy');
    // Cache is NOT proactively cleared — FlightSearchPage's strict mount-equality
    // will see form ≠ cached params and refetch, naturally overwriting the cache.
    expect(flightState.cachedFlightResults).not.toBeNull();
    expect(store.getState().ui.lastFlightPath).toMatch(/^\/flights\/search\?q=/);
  });

  it('overwrites flight searchFormParams normally when no cached flight results exist', () => {
    const store = makeStore();

    (store.dispatch as AppDispatch)(
      syncItineraryToSearchParams({
        origin: 'Dublin, Ireland',
        destination: 'Lisbon, Portugal',
        departure_date: '2026-09-15',
        return_date: '2026-09-20',
        trip_type: 'round_trip',
      })
    );

    const flightForm = store.getState().flightBooking.searchFormParams;
    expect(flightForm.from).toBe('Dublin, Ireland');
    expect(flightForm.to).toBe('Lisbon, Portugal');
    // No cache → encoded ?q= path
    expect(store.getState().ui.lastFlightPath).toMatch(/^\/flights\/search\?q=/);
  });

  it('overwrites hotel searchFormParams with the itinerary trip and keeps cache when canonical trip matches', () => {
    const store = makeStore();

    const hydratedHotelParams: HotelSearchFormParams = {
      destination: 'Lisbon',
      checkin: '2026-09-15',
      checkout: '2026-09-20',
      rooms: [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }],
      nationality: 'US',
    };
    store.dispatch(
      setCachedHotelResults({
        data: {
          sessionId: 'sess-2',
          hotels: [],
          totalResults: 0,
          searchParams: {
            checkin: '2026-09-15',
            checkout: '2026-09-20',
            cityName: 'Lisbon',
            occupancy: [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }],
            nationality: 'US',
          },
        },
        params: hydratedHotelParams,
        trusted: true,
      })
    );
    store.dispatch({ type: 'hotelBooking/setSearchFormParams', payload: hydratedHotelParams });

    (store.dispatch as AppDispatch)(
      syncItineraryToSearchParams({
        destination: 'Lisbon, Portugal',
        departure_date: '2026-09-15',
        return_date: '2026-09-20',
      })
    );

    const hotelState = store.getState().hotelBooking;
    // Form overwritten with the itinerary's verbose values.
    expect(hotelState.searchFormParams.destination).toBe('Lisbon, Portugal');
    // Cache untouched; trust flag still true.
    expect(hotelState.cachedHotelResults).not.toBeNull();
    expect(hotelState.cachedHotelResultsTrusted).toBe(true);
    // Clean route — page mount-only effect will honor the trust flag.
    expect(store.getState().ui.lastHotelPath).toBe('/hotels/search');
  });

  it('overwrites hotel form and uses encoded path when the itinerary trip differs from the cached trip (does NOT proactively clear cache)', () => {
    const store = makeStore();

    const cached: HotelSearchFormParams = {
      destination: 'Lisbon',
      checkin: '2026-09-15',
      checkout: '2026-09-20',
      rooms: [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }],
      nationality: 'US',
    };
    store.dispatch(
      setCachedHotelResults({
        data: {
          sessionId: 'sess-2',
          hotels: [],
          totalResults: 0,
          searchParams: {
            checkin: '2026-09-15',
            checkout: '2026-09-20',
            cityName: 'Lisbon',
            occupancy: [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }],
            nationality: 'US',
          },
        },
        params: cached,
      })
    );

    (store.dispatch as AppDispatch)(
      syncItineraryToSearchParams({
        destination: 'Rome, Italy',
        departure_date: '2026-10-01',
        return_date: '2026-10-08',
      })
    );

    const hotelState = store.getState().hotelBooking;
    expect(hotelState.searchFormParams.destination).toBe('Rome, Italy');
    // Cache is NOT proactively cleared — HotelSearchPage's strict mount-equality handles refetch.
    expect(hotelState.cachedHotelResults).not.toBeNull();
    expect(store.getState().ui.lastHotelPath).toMatch(/^\/hotels\/search\?q=/);
  });

  it('overwrites hotel searchFormParams and uses encoded path when no cache exists', () => {
    const store = makeStore();

    (store.dispatch as AppDispatch)(
      syncItineraryToSearchParams({
        destination: 'Lisbon, Portugal',
        departure_date: '2026-09-15',
        return_date: '2026-09-20',
      })
    );

    const hotelForm = store.getState().hotelBooking.searchFormParams;
    expect(hotelForm.destination).toBe('Lisbon, Portugal');
    expect(store.getState().ui.lastHotelPath).toMatch(/^\/hotels\/search\?q=/);
  });
});
