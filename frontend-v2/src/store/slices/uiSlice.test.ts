import { describe, it, expect, vi, beforeEach } from 'vitest';
import uiReducer, {
  setLastFlightPath,
  setLastHotelPath,
  setLastItineraryPath,
  setLastItineraryState,
  setTripMeta,
  setActiveSavedItineraryIdForBooking,
  clearActiveSavedItineraryIdForBooking,
  selectLastFlightPath,
  selectLastHotelPath,
  selectLastItineraryPath,
  selectLastItineraryState,
  selectTripMeta,
  selectActiveSavedItineraryIdForBooking,
  setChatState,
  setChatOpen,
  selectChatState,
} from './uiSlice';

function getInitialUIState(): ReturnType<typeof uiReducer> {
  return uiReducer(undefined, { type: 'init' });
}

/** Build a minimal root state for per-chat selectors. */
function rootState(ui: ReturnType<typeof uiReducer>, chatId: string | null = 'chat-1') {
  return { ui, chat: { chatId } };
}

describe('uiSlice', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
    vi.stubGlobal('sessionStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  describe('setLastFlightPath', () => {
    it('updates lastFlightPath state', () => {
      const state = getInitialUIState();
      const next = uiReducer(state, setLastFlightPath('/flights/details/xyz?q=foo'));
      expect(next.lastFlightPath).toBe('/flights/details/xyz?q=foo');
      expect(selectLastFlightPath({ ui: next })).toBe('/flights/details/xyz?q=foo');
    });

    it('calls localStorage.setItem with path', () => {
      const setItem = vi.fn();
      vi.stubGlobal('localStorage', {
        getItem: vi.fn(() => null),
        setItem,
        removeItem: vi.fn(),
      });
      const state = getInitialUIState();
      uiReducer(state, setLastFlightPath('/flights/search'));
      expect(setItem).toHaveBeenCalledWith('voya_last_flight_path', '/flights/search');
    });
  });

  describe('setLastHotelPath', () => {
    it('updates lastHotelPath state', () => {
      const state = getInitialUIState();
      const next = uiReducer(state, setLastHotelPath('/hotels/details/123'));
      expect(next.lastHotelPath).toBe('/hotels/details/123');
      expect(selectLastHotelPath({ ui: next })).toBe('/hotels/details/123');
    });

    it('calls localStorage.setItem with path', () => {
      const setItem = vi.fn();
      vi.stubGlobal('localStorage', {
        getItem: vi.fn(() => null),
        setItem,
        removeItem: vi.fn(),
      });
      const state = getInitialUIState();
      uiReducer(state, setLastHotelPath('/hotels/search'));
      expect(setItem).toHaveBeenCalledWith('voya_last_hotel_path', '/hotels/search');
    });
  });

  describe('setLastItineraryPath', () => {
    it('updates itineraryStateByChatId for the given chatId', () => {
      const state = getInitialUIState();
      const next = uiReducer(
        state,
        setLastItineraryPath({ chatId: 'chat-1', path: '/itinerary?destination=Paris' })
      );
      expect(next.itineraryStateByChatId['chat-1']?.lastItineraryPath).toBe(
        '/itinerary?destination=Paris'
      );
      expect(selectLastItineraryPath(rootState(next, 'chat-1'))).toBe(
        '/itinerary?destination=Paris'
      );
    });

    it('calls localStorage.setItem with voya_itinerary_state_by_chat key', () => {
      const setItem = vi.fn();
      vi.stubGlobal('localStorage', {
        getItem: vi.fn(() => null),
        setItem,
        removeItem: vi.fn(),
      });
      const state = getInitialUIState();
      uiReducer(state, setLastItineraryPath({ chatId: 'chat-1', path: '/itinerary' }));
      expect(setItem).toHaveBeenCalledWith(
        'voya_itinerary_state_by_chat',
        expect.any(String)
      );
    });
  });

  describe('setLastItineraryState', () => {
    it('updates itineraryStateByChatId with valid state', () => {
      const state = getInitialUIState();
      const itineraryState = {
        structuredItinerary: {
          itineraryItems: [{ day: 1, title: 'Day 1 in Paris' }],
        },
        tripMeta: { destination: 'Paris', departure_date: '2026-03-20' },
      };
      const next = uiReducer(
        state,
        setLastItineraryState({ chatId: 'chat-1', state: itineraryState })
      );
      expect(next.itineraryStateByChatId['chat-1']?.lastItineraryState).toEqual(itineraryState);
      expect(selectLastItineraryState(rootState(next, 'chat-1'))).toEqual(itineraryState);
    });

    it('clears when passed null', () => {
      const state = getInitialUIState();
      const withState = uiReducer(
        state,
        setLastItineraryState({
          chatId: 'chat-1',
          state: { structuredItinerary: { itineraryItems: [] }, tripMeta: { destination: 'Paris' } },
        })
      );
      const next = uiReducer(withState, setLastItineraryState({ chatId: 'chat-1', state: null }));
      expect(next.itineraryStateByChatId['chat-1']?.lastItineraryState).toBeNull();
      expect(selectLastItineraryState(rootState(next, 'chat-1'))).toBeNull();
    });
  });

  describe('setTripMeta', () => {
    it('updates itineraryStateByChatId with valid meta', () => {
      const state = getInitialUIState();
      const meta = {
        origin: 'LHR',
        destination: 'JFK',
        departure_date: '2026-03-15',
        return_date: '2026-03-22',
      };
      const next = uiReducer(state, setTripMeta({ chatId: 'chat-1', meta }));
      expect(next.itineraryStateByChatId['chat-1']?.tripMeta).toEqual(meta);
      expect(selectTripMeta(rootState(next, 'chat-1'))).toEqual(meta);
    });

    it('clears tripMeta when passed null', () => {
      const state = getInitialUIState();
      const withMeta = uiReducer(
        state,
        setTripMeta({ chatId: 'chat-1', meta: { origin: 'LHR', destination: 'JFK' } })
      );
      const next = uiReducer(withMeta, setTripMeta({ chatId: 'chat-1', meta: null }));
      expect(next.itineraryStateByChatId['chat-1']?.tripMeta).toBeNull();
      expect(selectTripMeta(rootState(next, 'chat-1'))).toBeNull();
    });

    it('calls localStorage.setItem with voya_itinerary_state_by_chat key when clearing tripMeta', () => {
      const setItem = vi.fn();
      vi.stubGlobal('localStorage', {
        getItem: vi.fn(() => null),
        setItem,
        removeItem: vi.fn(),
      });
      const state = getInitialUIState();
      const withMeta = uiReducer(
        state,
        setTripMeta({ chatId: 'chat-1', meta: { origin: 'LHR', destination: 'JFK' } })
      );
      uiReducer(withMeta, setTripMeta({ chatId: 'chat-1', meta: null }));
      expect(setItem).toHaveBeenCalledWith(
        'voya_itinerary_state_by_chat',
        expect.any(String)
      );
    });
  });

  describe('activeSavedItineraryIdForBooking', () => {
    const testSavedItineraryOid = '507f1f77bcf86cd799439022'; // pragma: allowlist secret

    it('updates state and persists to sessionStorage on set', () => {
      const setItem = vi.fn();
      vi.stubGlobal('sessionStorage', {
        getItem: vi.fn(() => null),
        setItem,
        removeItem: vi.fn(),
      });
      const state = getInitialUIState();
      const id = testSavedItineraryOid;
      const next = uiReducer(
        state,
        setActiveSavedItineraryIdForBooking(id)
      );
      expect(next.activeSavedItineraryIdForBooking).toBe(id);
      expect(selectActiveSavedItineraryIdForBooking({ ui: next })).toBe(id);
      expect(setItem).toHaveBeenCalledWith(
        'voya_active_saved_itinerary_id_for_booking',
        id
      );
    });

    it('clears state and removes sessionStorage key', () => {
      const removeItem = vi.fn();
      vi.stubGlobal('sessionStorage', {
        getItem: vi.fn(() => null),
        setItem: vi.fn(),
        removeItem,
      });
      const state = getInitialUIState();
      const withId = uiReducer(
        state,
        setActiveSavedItineraryIdForBooking(testSavedItineraryOid)
      );
      const next = uiReducer(withId, clearActiveSavedItineraryIdForBooking());
      expect(next.activeSavedItineraryIdForBooking).toBeNull();
      expect(removeItem).toHaveBeenCalledWith(
        'voya_active_saved_itinerary_id_for_booking'
      );
    });
  });

  describe('setChatState', () => {
    it("'resting' sets chatState, closes chatOpen, clears chatFullScreen", () => {
      const state = getInitialUIState();
      // Start from an open state
      const opened = uiReducer(state, setChatState('full'));
      const next = uiReducer(opened, setChatState('resting'));
      expect(next.chatState).toBe('resting');
      expect(next.chatOpen).toBe(false);
      expect(next.chatFullScreen).toBe(false);
      expect(selectChatState({ ui: next })).toBe('resting');
    });

    it("'full' sets chatState, opens chatOpen, sets chatFullScreen", () => {
      const state = getInitialUIState();
      const next = uiReducer(state, setChatState('full'));
      expect(next.chatState).toBe('full');
      expect(next.chatOpen).toBe(true);
      expect(next.chatFullScreen).toBe(true);
    });
  });

  describe('setChatOpen syncs chatState', () => {
    it('setChatOpen(true) sets chatState to full', () => {
      const state = getInitialUIState();
      const next = uiReducer(state, setChatOpen(true));
      expect(next.chatState).toBe('full');
      expect(next.chatOpen).toBe(true);
    });

    it('setChatOpen(false) sets chatState to resting', () => {
      const state = getInitialUIState();
      const opened = uiReducer(state, setChatOpen(true));
      const next = uiReducer(opened, setChatOpen(false));
      expect(next.chatState).toBe('resting');
      expect(next.chatOpen).toBe(false);
    });
  });

  describe('localStorage corruption robustness', () => {
    it('returns empty map when localStorage contains invalid data', async () => {
      vi.resetModules();
      vi.stubGlobal('localStorage', {
        getItem: vi.fn((key: string) =>
          key === 'voya_itinerary_state_by_chat' ? '[1,2,3]' : null
        ),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      });
      const { default: reducer } = await import('./uiSlice');
      const state = reducer(undefined, { type: 'init' });
      expect(state.itineraryStateByChatId).toEqual({});
    });
  });
});
