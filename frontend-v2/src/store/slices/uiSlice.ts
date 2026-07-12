import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { ItineraryNavigationState } from '@/features/itinerary/types';
import type { DestinationLocation } from '@/types/chat';

export type ChatStateValue = 'resting' | 'full';

const LAST_FLIGHT_PATH_KEY = 'voya_last_flight_path';
const LAST_HOTEL_PATH_KEY = 'voya_last_hotel_path';
const ITINERARY_STATE_BY_CHAT_KEY = 'voya_itinerary_state_by_chat';
/** Key used when no chatId is available (e.g. public chat before first message). */
export const ANON_CHAT_KEY = '__anon__';
/** Session-scoped id of the saved itinerary the user is viewing; used to link bookings (last-write-wins across tabs). */
const ACTIVE_SAVED_ITINERARY_FOR_BOOKING_KEY = 'voya_active_saved_itinerary_id_for_booking';
/** Guest Places photo session JWT (tab session; public itinerary images). */
const PLACES_SESSION_TOKEN_KEY = 'voya_places_session_token';

/** Trip metadata for header chips (origin, destination, dates, passengers) */
export interface TripMeta {
  origin?: string;
  destination?: string;
  departure_date?: string;
  return_date?: string;
  adults?: number;
  children?: number;
  infants?: number;
  trip_type?: string;
  destination_location?: DestinationLocation;
  origin_location?: DestinationLocation;
}

export interface PerChatItineraryState {
  lastItineraryPath: string;
  lastItineraryState: ItineraryNavigationState | null;
  tripMeta: TripMeta | null;
}

const DEFAULT_CHAT_ITINERARY_STATE: PerChatItineraryState = {
  lastItineraryPath: '/itinerary',
  lastItineraryState: null,
  tripMeta: null,
};

function loadLastFlightPath(): string {
  try {
    return localStorage.getItem(LAST_FLIGHT_PATH_KEY) ?? '/flights/search';
  } catch {
    return '/flights/search';
  }
}

function loadLastHotelPath(): string {
  try {
    return localStorage.getItem(LAST_HOTEL_PATH_KEY) ?? '/hotels/search';
  } catch {
    return '/hotels/search';
  }
}

function saveLastFlightPath(path: string) {
  try {
    localStorage.setItem(LAST_FLIGHT_PATH_KEY, path);
  } catch {
    // Ignore storage errors
  }
}

function saveLastHotelPath(path: string) {
  try {
    localStorage.setItem(LAST_HOTEL_PATH_KEY, path);
  } catch {
    // Ignore storage errors
  }
}

const MAX_ITINERARY_CHAT_ENTRIES = 20;

function loadItineraryStateByChatId(): Record<string, PerChatItineraryState> {
  try {
    const raw = localStorage.getItem(ITINERARY_STATE_BY_CHAT_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    return parsed as Record<string, PerChatItineraryState>;
  } catch {
    return {};
  }
}

function saveItineraryStateByChatId(map: Record<string, PerChatItineraryState>) {
  try {
    const entries = Object.entries(map);
    // Cap at MAX_ITINERARY_CHAT_ENTRIES — keep the last N entries
    const capped =
      entries.length > MAX_ITINERARY_CHAT_ENTRIES
        ? Object.fromEntries(entries.slice(entries.length - MAX_ITINERARY_CHAT_ENTRIES))
        : map;
    localStorage.setItem(ITINERARY_STATE_BY_CHAT_KEY, JSON.stringify(capped));
  } catch {
    // Ignore storage errors
  }
}

/** Clear persisted itinerary navigation blob (logout). */
export function clearPersistedLastItineraryNavigationState(): void {
  try {
    localStorage.removeItem(ITINERARY_STATE_BY_CHAT_KEY);
  } catch {
    // Ignore storage errors
  }
}

function loadActiveSavedItineraryIdForBooking(): string | null {
  try {
    const v = sessionStorage.getItem(ACTIVE_SAVED_ITINERARY_FOR_BOOKING_KEY);
    return v && v.trim() ? v.trim() : null;
  } catch {
    return null;
  }
}

function saveActiveSavedItineraryIdForBooking(id: string | null) {
  try {
    if (id && id.trim()) {
      sessionStorage.setItem(ACTIVE_SAVED_ITINERARY_FOR_BOOKING_KEY, id.trim());
    } else {
      sessionStorage.removeItem(ACTIVE_SAVED_ITINERARY_FOR_BOOKING_KEY);
    }
  } catch {
    // Ignore storage errors
  }
}

function loadPlacesSessionToken(): string | null {
  try {
    const v = sessionStorage.getItem(PLACES_SESSION_TOKEN_KEY);
    return v && v.trim() ? v.trim() : null;
  } catch {
    return null;
  }
}

function savePlacesSessionToken(token: string | null) {
  try {
    if (token && token.trim()) {
      sessionStorage.setItem(PLACES_SESSION_TOKEN_KEY, token.trim());
    } else {
      sessionStorage.removeItem(PLACES_SESSION_TOKEN_KEY);
    }
  } catch {
    // Ignore storage errors
  }
}

/**
 * UI state shape
 */
interface UIState {
  sidebarOpen: boolean;
  chatOpen: boolean;
  chatFullScreen: boolean;
  authModalOpen: boolean;
  darkMode: boolean;
  soundEnabled: boolean;
  autoScroll: boolean;
  unreadCount: number;
  lastFlightPath: string;
  lastHotelPath: string;
  /** Per-chat itinerary state: keyed by chatId (or ANON_CHAT_KEY for unauthenticated). */
  itineraryStateByChatId: Record<string, PerChatItineraryState>;
  /** Set when viewing a saved itinerary by id; cleared when starting booking from chat cards. */
  activeSavedItineraryIdForBooking: string | null;
  /** Guest-only JWT for proxying Google Places images (see `places_session_token` on public chat). */
  placesSessionToken: string | null;
  /** When true the BottomNav slides off-screen (e.g. keyboard open, full-screen media). */
  bottomNavHidden: boolean;
  /** Mobile chat bottom-sheet snap position. */
  chatState: ChatStateValue;
}

const initialState: UIState = {
  sidebarOpen: true,
  chatOpen: false,
  chatFullScreen: false,
  authModalOpen: false,
  darkMode: false,
  soundEnabled: true,
  autoScroll: true,
  unreadCount: 0,
  lastFlightPath: loadLastFlightPath(),
  lastHotelPath: loadLastHotelPath(),
  itineraryStateByChatId: loadItineraryStateByChatId(),
  activeSavedItineraryIdForBooking: loadActiveSavedItineraryIdForBooking(),
  placesSessionToken: loadPlacesSessionToken(),
  bottomNavHidden: false,
  chatState: 'resting',
};

/**
 * UI slice for managing UI state
 */
const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    /**
     * Toggle sidebar
     */
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },

    /**
     * Set sidebar state
     */
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },

    /**
     * Toggle chat panel
     */
    toggleChat: (state) => {
      state.chatOpen = !state.chatOpen;
      state.chatState = state.chatOpen ? 'full' : 'resting';
    },

    /**
     * Set chat open state
     */
    setChatOpen: (state, action: PayloadAction<boolean>) => {
      state.chatOpen = action.payload;
      state.chatState = action.payload ? 'full' : 'resting';
    },

    /**
     * Toggle dark mode
     */
    toggleDarkMode: (state) => {
      state.darkMode = !state.darkMode;
    },

    /**
     * Set dark mode
     */
    setDarkMode: (state, action: PayloadAction<boolean>) => {
      state.darkMode = action.payload;
    },

    /**
     * Toggle sound
     */
    toggleSound: (state) => {
      state.soundEnabled = !state.soundEnabled;
    },

    /**
     * Set sound enabled
     */
    setSoundEnabled: (state, action: PayloadAction<boolean>) => {
      state.soundEnabled = action.payload;
    },

    /**
     * Toggle auto scroll
     */
    toggleAutoScroll: (state) => {
      state.autoScroll = !state.autoScroll;
    },

    /**
     * Set auto scroll
     */
    setAutoScroll: (state, action: PayloadAction<boolean>) => {
      state.autoScroll = action.payload;
    },

    /**
     * Toggle fullscreen mode
     */
    toggleFullScreen: (state) => {
      state.chatFullScreen = !state.chatFullScreen;
      if (state.chatOpen) {
        state.chatState = 'full';
      }
    },

    /**
     * Set fullscreen mode
     */
    setFullScreen: (state, action: PayloadAction<boolean>) => {
      state.chatFullScreen = action.payload;
      if (state.chatOpen) {
        state.chatState = 'full';
      }
    },

    /**
     * Set unread count
     */
    setUnreadCount: (state, action: PayloadAction<number>) => {
      state.unreadCount = action.payload;
    },

    /**
     * Increment unread count
     */
    incrementUnreadCount: (state) => {
      state.unreadCount += 1;
    },

    /**
     * Clear unread count
     */
    clearUnreadCount: (state) => {
      state.unreadCount = 0;
    },

    /**
     * Open auth modal
     */
    openAuthModal: (state) => {
      state.authModalOpen = true;
    },

    /**
     * Close auth modal
     */
    closeAuthModal: (state) => {
      state.authModalOpen = false;
    },

    /**
     * Set auth modal state
     */
    setAuthModalOpen: (state, action: PayloadAction<boolean>) => {
      state.authModalOpen = action.payload;
    },

    /**
     * Set last flight path (pathname + search) for tab resume
     */
    setLastFlightPath: (state, action: PayloadAction<string>) => {
      state.lastFlightPath = action.payload;
      saveLastFlightPath(action.payload);
    },

    /**
     * Set last hotel path (pathname + search) for tab resume
     */
    setLastHotelPath: (state, action: PayloadAction<string>) => {
      state.lastHotelPath = action.payload;
      saveLastHotelPath(action.payload);
    },

    /**
     * Set last itinerary path for a specific chat (pathname + search for tab resume)
     */
    setLastItineraryPath: (state, action: PayloadAction<{ chatId: string; path: string }>) => {
      const { chatId, path } = action.payload;
      state.itineraryStateByChatId[chatId] = {
        ...DEFAULT_CHAT_ITINERARY_STATE,
        ...state.itineraryStateByChatId[chatId],
        lastItineraryPath: path,
      };
      saveItineraryStateByChatId(state.itineraryStateByChatId);
    },

    /**
     * Set last itinerary navigation state for a specific chat (session-scoped, for tab resume)
     */
    setLastItineraryState: (
      state,
      action: PayloadAction<{ chatId: string; state: ItineraryNavigationState | null }>
    ) => {
      const { chatId, state: navState } = action.payload;
      state.itineraryStateByChatId[chatId] = {
        ...DEFAULT_CHAT_ITINERARY_STATE,
        ...state.itineraryStateByChatId[chatId],
        lastItineraryState: navState,
      };
      saveItineraryStateByChatId(state.itineraryStateByChatId);
    },

    /**
     * Set trip metadata for a specific chat (persisted to localStorage)
     */
    setTripMeta: (state, action: PayloadAction<{ chatId: string; meta: TripMeta | null }>) => {
      const { chatId, meta } = action.payload;
      state.itineraryStateByChatId[chatId] = {
        ...DEFAULT_CHAT_ITINERARY_STATE,
        ...state.itineraryStateByChatId[chatId],
        tripMeta: meta,
      };
      saveItineraryStateByChatId(state.itineraryStateByChatId);
    },

    /**
     * Remove itinerary state for a specific chat (e.g. when conversation is deleted).
     */
    pruneItineraryStateForChat: (state, action: PayloadAction<string>) => {
      delete state.itineraryStateByChatId[action.payload];
      saveItineraryStateByChatId(state.itineraryStateByChatId);
    },

    /**
     * Active saved itinerary id to attach on successful flight/hotel book flows.
     */
    setActiveSavedItineraryIdForBooking: (state, action: PayloadAction<string | null>) => {
      state.activeSavedItineraryIdForBooking = action.payload;
      saveActiveSavedItineraryIdForBooking(action.payload);
    },

    clearActiveSavedItineraryIdForBooking: (state) => {
      state.activeSavedItineraryIdForBooking = null;
      saveActiveSavedItineraryIdForBooking(null);
    },

    resetItineraryStateByChatId: (state) => {
      state.itineraryStateByChatId = {};
      saveItineraryStateByChatId({});
    },

    /**
     * Store short-lived Places session JWT from public chat (itinerary with images).
     */
    setPlacesSessionToken: (state, action: PayloadAction<string | null>) => {
      const next = action.payload && action.payload.trim() ? action.payload.trim() : null;
      state.placesSessionToken = next;
      savePlacesSessionToken(next);
    },

    clearPlacesSessionToken: (state) => {
      state.placesSessionToken = null;
      savePlacesSessionToken(null);
    },

    setBottomNavHidden: (state, action: PayloadAction<boolean>) => {
      state.bottomNavHidden = action.payload;
    },

    setChatState: (state, action: PayloadAction<ChatStateValue>) => {
      state.chatState = action.payload;
      // Keep legacy chatOpen / chatFullScreen in sync so ChatContext still works.
      state.chatOpen = action.payload !== 'resting';
      state.chatFullScreen = action.payload === 'full';
    },
  },
});

export const {
  toggleSidebar,
  setSidebarOpen,
  toggleChat,
  setChatOpen,
  toggleDarkMode,
  setDarkMode,
  toggleSound,
  setSoundEnabled,
  toggleAutoScroll,
  setAutoScroll,
  toggleFullScreen,
  setFullScreen,
  setUnreadCount,
  incrementUnreadCount,
  clearUnreadCount,
  openAuthModal,
  closeAuthModal,
  setAuthModalOpen,
  setLastFlightPath,
  setLastHotelPath,
  setLastItineraryPath,
  setLastItineraryState,
  setTripMeta,
  pruneItineraryStateForChat,
  setActiveSavedItineraryIdForBooking,
  clearActiveSavedItineraryIdForBooking,
  resetItineraryStateByChatId,
  setPlacesSessionToken,
  clearPlacesSessionToken,
  setBottomNavHidden,
  setChatState,
} = uiSlice.actions;

export default uiSlice.reducer;

// Selectors
export const selectSidebarOpen = (state: { ui: UIState }) => state.ui.sidebarOpen;
export const selectChatOpen = (state: { ui: UIState }) => state.ui.chatOpen;
export const selectChatFullScreen = (state: { ui: UIState }) => state.ui.chatFullScreen;
export const selectAuthModalOpen = (state: { ui: UIState }) => state.ui.authModalOpen;
export const selectDarkMode = (state: { ui: UIState }) => state.ui.darkMode;
export const selectSoundEnabled = (state: { ui: UIState }) => state.ui.soundEnabled;
export const selectAutoScroll = (state: { ui: UIState }) => state.ui.autoScroll;
export const selectUnreadCount = (state: { ui: UIState }) => state.ui.unreadCount;
export const selectLastFlightPath = (state: { ui: UIState }) =>
  state.ui.lastFlightPath;
export const selectLastHotelPath = (state: { ui: UIState }) =>
  state.ui.lastHotelPath;
export const selectActiveSavedItineraryIdForBooking = (state: { ui: UIState }) =>
  state.ui.activeSavedItineraryIdForBooking;
export const selectPlacesSessionToken = (state: { ui: UIState }) =>
  state.ui.placesSessionToken;
export const selectBottomNavHidden = (state: { ui: UIState }) =>
  state.ui.bottomNavHidden;
export const selectChatState = (state: { ui: UIState }) => state.ui.chatState;

// Per-chat itinerary selectors — read active chatId from state.chat.chatId
type ItineraryRootState = { ui: UIState; chat: { chatId: string | null } };

function getActiveChatItineraryState(state: ItineraryRootState): PerChatItineraryState {
  const chatId = state.chat.chatId ?? ANON_CHAT_KEY;
  return state.ui.itineraryStateByChatId[chatId] ?? DEFAULT_CHAT_ITINERARY_STATE;
}

export const selectLastItineraryPath = (state: ItineraryRootState) =>
  getActiveChatItineraryState(state).lastItineraryPath;
export const selectLastItineraryState = (state: ItineraryRootState) =>
  getActiveChatItineraryState(state).lastItineraryState;
export const selectTripMeta = (state: ItineraryRootState) =>
  getActiveChatItineraryState(state).tripMeta;
