import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import authReducer, { setCredentials } from './slices/authSlice';
import uiReducer, { setLastItineraryState } from './slices/uiSlice';
import chatReducer from './slices/chatSlice';
import { guestItineraryListener } from './guestItineraryListener';
import {
  clearGuestItineraries,
  getGuestItineraries,
} from '@/features/chat/utils/guestItineraries';
import { baseApi } from '@/api/baseApi';
import { strapiApi } from '@/api/strapiApi';
import flightBookingReducer from './slices/flightBookingSlice';
import hotelBookingReducer from './slices/hotelBookingSlice';
import onboardingReducer from './slices/onboardingSlice';
import type { AuthCredentials } from '@/types/auth';

function makeCredentials(): AuthCredentials {
  return {
    accessToken: 'tok',
    refreshToken: 'ref',
    tokenType: 'bearer',
    expiresIn: 3600,
    sessionId: 'sess-1',
    isNew: false,
    user: {
      id: '1',
      email: 'a@b.com',
      firstName: 'A',
      lastName: null,
      emailVerified: true,
      createdAt: '2024-01-01',
      updatedAt: '2024-01-01',
    },
  };
}

const ITINERARY = { itineraryItems: [{ day: 1, activities: ['Tour'] }] };
const GUEST_KEY = 'voya_guest_itineraries';

function makeStore() {
  return configureStore({
    reducer: {
      [baseApi.reducerPath]: baseApi.reducer,
      [strapiApi.reducerPath]: strapiApi.reducer,
      auth: authReducer,
      chat: chatReducer,
      ui: uiReducer,
      flightBooking: flightBookingReducer,
      hotelBooking: hotelBookingReducer,
      onboarding: onboardingReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(
        baseApi.middleware,
        strapiApi.middleware,
        guestItineraryListener.middleware,
      ),
  });
}

beforeEach(() => {
  localStorage.removeItem(GUEST_KEY);
  vi.stubGlobal('sessionStorage', {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  clearGuestItineraries();
});

describe('guestItineraryListener — setLastItineraryState', () => {
  it('appends to localStorage when user is not authenticated', () => {
    const store = makeStore();
    // Default auth state has isAuthenticated: false (no token in localStorage)
    store.dispatch(
      setLastItineraryState({
        chatId: 'chat-1',
        state: { structuredItinerary: ITINERARY, tripMeta: undefined },
      }),
    );
    expect(getGuestItineraries()).toHaveLength(1);
    expect(getGuestItineraries()[0]?.structuredItinerary).toEqual(ITINERARY);
  });

  it('does NOT append when user is authenticated', () => {
    const store = makeStore();
    store.dispatch(setCredentials(makeCredentials()));
    store.dispatch(
      setLastItineraryState({
        chatId: 'chat-1',
        state: { structuredItinerary: ITINERARY, tripMeta: undefined },
      }),
    );
    expect(getGuestItineraries()).toHaveLength(0);
  });

  it('does nothing when structuredItinerary is missing', () => {
    const store = makeStore();
    store.dispatch(
      setLastItineraryState({
        chatId: 'chat-1',
        state: { structuredItinerary: undefined as never, tripMeta: undefined },
      }),
    );
    expect(getGuestItineraries()).toHaveLength(0);
  });
});

describe('guestItineraryListener — setCredentials sync', () => {
  it('does nothing when there are no pending guest itineraries', async () => {
    const store = makeStore();
    store.dispatch(setCredentials(makeCredentials()));
    // Allow microtasks to settle
    await new Promise((r) => setTimeout(r, 0));
    // No guest itineraries should have been created or cleared
    expect(getGuestItineraries()).toHaveLength(0);
  });

  it('keeps entries in localStorage when backend save throws (partial failure protection)', async () => {
    // Populate two entries with distinct timestamps
    localStorage.setItem(
      'voya_guest_itineraries',
      JSON.stringify({
        entries: [
          { structuredItinerary: ITINERARY, createdAt: Date.now() },
          { structuredItinerary: { itineraryItems: [{ day: 2 }] }, createdAt: Date.now() - 1000 },
        ],
      }),
    );

    const store = makeStore();
    store.dispatch(setCredentials(makeCredentials()));

    // Allow microtasks to settle — the listener will fail (no real API) and catch
    await new Promise((r) => setTimeout(r, 50));

    // Since the API isn't available in unit tests and throws, entries should stay
    // (per-entry removal only happens on success, not on failure)
    expect(getGuestItineraries().length).toBe(2);
  });
});
