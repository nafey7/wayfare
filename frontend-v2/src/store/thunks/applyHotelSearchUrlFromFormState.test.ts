import { describe, it, expect, beforeEach, vi } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import type { AppDispatch } from '@/store';
import hotelBookingReducer from '@/store/slices/hotelBookingSlice';
import uiReducer from '@/store/slices/uiSlice';
import { setSearchFormParams } from '@/store/slices/hotelBookingSlice';
import { applyHotelSearchUrlFromFormState } from './applyHotelSearchUrlFromFormState';

describe('applyHotelSearchUrlFromFormState', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  it('returns null and does not update lastHotelPath when hotel params cannot build a URL', () => {
    const store = configureStore({
      reducer: { hotelBooking: hotelBookingReducer, ui: uiReducer },
    });
    const before = store.getState().ui.lastHotelPath;

    const path = (store.dispatch as AppDispatch)(applyHotelSearchUrlFromFormState());

    expect(path).toBeNull();
    expect(store.getState().ui.lastHotelPath).toBe(before);
  });

  it('dispatches lastHotelPath and returns the search path when params are complete', () => {
    const store = configureStore({
      reducer: { hotelBooking: hotelBookingReducer, ui: uiReducer },
    });

    store.dispatch(
      setSearchFormParams({
        destination: 'Paris',
        checkin: '2026-06-01',
        checkout: '2026-06-05',
        rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
        nationality: 'US',
      })
    );

    const path = (store.dispatch as AppDispatch)(applyHotelSearchUrlFromFormState());

    expect(path).toMatch(/^\/hotels\/search\?q=/);
    expect(store.getState().ui.lastHotelPath).toBe(path);
  });
});
