import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import type { ReactNode } from 'react';

import { makeTestStore } from '@/store';
import { setCredentials } from '@/store/slices/authSlice';
import {
  setError as setFlightError,
  resetBooking as resetFlightBooking,
} from '@/store/slices/flightBookingSlice';
import {
  setInternalSessionId as setHotelInternalSessionId,
  resetBooking as resetHotelBooking,
} from '@/store/slices/hotelBookingSlice';
import {
  ANON_CHAT_KEY,
  setLastItineraryState,
  setTripMeta,
  setActiveSavedItineraryIdForBooking,
  selectLastItineraryState,
  selectTripMeta,
} from '@/store/slices/uiSlice';
import { useStartNewChat, NEW_CHAT_PENDING_KEY } from './useStartNewChat';

vi.mock('@/features/chat/utils/publicChatSession', () => ({
  clearPublicChatId: vi.fn(),
}));

describe('useStartNewChat', () => {
  let testStore: ReturnType<typeof makeTestStore>;

  function makeWrapper() {
    return function Wrapper({ children }: { children: ReactNode }) {
      return <Provider store={testStore}>{children}</Provider>;
    };
  }

  beforeEach(() => {
    // Freeze time so `new Date()` inside slice defaults (e.g.
    // flightBookingSlice's searchFormParams.date) is identical between the
    // reference reset and the reset triggered via useStartNewChat.
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));
    testStore = makeTestStore();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('resets flight + hotel booking state when starting a new chat', () => {
    // Build the expected post-reset snapshot on a parallel fresh store so any
    // non-deterministic defaults (e.g. `new Date()` inside resetBooking) match
    // what useStartNewChat will produce on the test store.
    const referenceStore = makeTestStore();
    referenceStore.dispatch(resetFlightBooking());
    referenceStore.dispatch(resetHotelBooking());
    const expectedFlight = referenceStore.getState().flightBooking;
    const expectedHotel = referenceStore.getState().hotelBooking;

    // Mutate flight + hotel booking slices to non-initial state.
    testStore.dispatch(setFlightError('boom'));
    testStore.dispatch(setHotelInternalSessionId('hotel-session-xyz'));

    expect(testStore.getState().flightBooking.error).toBe('boom');
    expect(testStore.getState().hotelBooking.internalSessionId).toBe('hotel-session-xyz');

    const { result } = renderHook(() => useStartNewChat(), { wrapper: makeWrapper() });
    act(() => {
      result.current();
    });

    // After start-new-chat, both slices are fully reset (catches partial-reset
    // regressions in any field, not just `error` / `internalSessionId`).
    expect(testStore.getState().flightBooking).toEqual(expectedFlight);
    expect(testStore.getState().hotelBooking).toEqual(expectedHotel);
  });

  it('clears active itinerary state (lastItineraryState, tripMeta, active saved id)', () => {
    testStore.dispatch(
      setLastItineraryState({
        chatId: ANON_CHAT_KEY,
        state: {
          structuredItinerary: { days: [] } as never,
          tripMeta: null,
        } as never,
      }),
    );
    testStore.dispatch(
      setTripMeta({
        chatId: ANON_CHAT_KEY,
        meta: { destination: 'Barcelona', departure_date: '2026-06-01', return_date: '2026-06-05' },
      }),
    );
    testStore.dispatch(setActiveSavedItineraryIdForBooking('itin-123'));

    expect(selectLastItineraryState(testStore.getState())).not.toBeNull();
    expect(selectTripMeta(testStore.getState())).not.toBeNull();
    expect(testStore.getState().ui.activeSavedItineraryIdForBooking).toBe('itin-123');

    const { result } = renderHook(() => useStartNewChat(), { wrapper: makeWrapper() });
    act(() => {
      result.current();
    });

    expect(selectLastItineraryState(testStore.getState())).toBeNull();
    expect(selectTripMeta(testStore.getState())).toBeNull();
    expect(testStore.getState().ui.activeSavedItineraryIdForBooking).toBeNull();
  });

  it('sets the new-chat pending sessionStorage flag for authenticated users', () => {
    // Seed auth so selectIsAuthenticated returns true.
    testStore.dispatch(
      setCredentials({
        accessToken: 'tok',
        refreshToken: 'rtok',
        tokenType: 'bearer',
        expiresIn: 3600,
        sessionId: 's1',
        isNew: false,
        user: {
          id: 'u1',
          email: 'a@b.com',
          firstName: 'A',
          lastName: 'B',
          emailVerified: true,
          createdAt: '',
          updatedAt: '',
        },
      }),
    );

    const { result } = renderHook(() => useStartNewChat(), { wrapper: makeWrapper() });
    act(() => {
      result.current();
    });

    expect(sessionStorage.getItem(NEW_CHAT_PENDING_KEY)).toBe('1');
  });
});
