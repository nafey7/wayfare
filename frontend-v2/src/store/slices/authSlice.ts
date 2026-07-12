import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { User, AuthCredentials, PhotoUrls } from '@/types/auth';
import { clearPublicChatReturnTo } from '@/features/chat/utils/publicChatReturnRoute';
import { clearPendingItinerarySave } from '@/features/chat/utils/pendingItinerarySave';
import { clearGuestItineraries } from '@/features/chat/utils/guestItineraries';
import { clearPersistedLastItineraryNavigationState } from './uiSlice';
import { removeWithTTL } from '@/utils/localStorageWithTTL';

// Storage keys (match old frontend)
const TOKEN_KEY = 'Authorization';
const REFRESH_TOKEN_KEY = 'refreshToken';
const USER_KEY = 'user';

/**
 * Load initial auth state from localStorage
 */
function loadAuthState(): {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;
} {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    const userJson = localStorage.getItem(USER_KEY);
    const user = userJson ? JSON.parse(userJson) : null;

    return {
      token,
      refreshToken,
      user,
      isAuthenticated: !!token,
    };
  } catch {
    return {
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
    };
  }
}

/**
 * Auth state shape (exported for RootState typing)
 */
export interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

const persistedState = loadAuthState();

const initialState: AuthState = {
  user: persistedState.user,
  token: persistedState.token,
  refreshToken: persistedState.refreshToken,
  isAuthenticated: persistedState.isAuthenticated,
  loading: false,
  error: null,
};

/**
 * Auth slice for managing authentication state
 */
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    /**
     * Set credentials after successful login/register
     */
    setCredentials: (state, action: PayloadAction<AuthCredentials>) => {
      state.user = action.payload.user;
      state.token = action.payload.accessToken;
      state.refreshToken = action.payload.refreshToken;
      state.isAuthenticated = true;
      state.error = null;

      // Persist to localStorage
      localStorage.setItem(TOKEN_KEY, action.payload.accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, action.payload.refreshToken);
      localStorage.setItem(USER_KEY, JSON.stringify(action.payload.user));
    },

    /**
     * Update user profile
     */
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload;
      // Persist to localStorage
      localStorage.setItem(USER_KEY, JSON.stringify(action.payload));
    },

    /**
     * Patch the current user's profile photo fields (after upload/delete).
     * Pass null to clear.
     */
    setUserPhoto: (
      state,
      action: PayloadAction<{
        photoKey: string | null;
        photoUrls: PhotoUrls | null;
      }>
    ) => {
      if (!state.user) return;
      state.user.photoKey = action.payload.photoKey;
      state.user.photoUrls = action.payload.photoUrls;
      localStorage.setItem(USER_KEY, JSON.stringify(state.user));
    },

    /**
     * Update tokens (e.g., after refresh)
     */
    setTokens: (
      state,
      action: PayloadAction<{ accessToken: string; refreshToken: string }>
    ) => {
      state.token = action.payload.accessToken;
      state.refreshToken = action.payload.refreshToken;
      state.isAuthenticated = true;

      // Persist to localStorage
      localStorage.setItem(TOKEN_KEY, action.payload.accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, action.payload.refreshToken);
    },

    /**
     * Set loading state
     */
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },

    /**
     * Set error state
     */
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },

    /**
     * Clear auth state (logout)
     */
    clearAuth: (state) => {
      state.user = null;
      state.token = null;
      state.refreshToken = null;
      state.isAuthenticated = false;
      state.loading = false;
      state.error = null;

      // Clear from localStorage
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      // Clear flight booking session so stale sessionId is not reused after logout
      localStorage.removeItem('sessionId');
      // Scrub stale hotel recommendations data left by the pre-removal code path
      removeWithTTL('voya_hotel_recommendations');
      clearPersistedLastItineraryNavigationState();
      clearPublicChatReturnTo();
      clearPendingItinerarySave();
      clearGuestItineraries();
      // Clear new-chat pending flag so a stale flag from before logout doesn't suppress
      // auto-select on the next login in the same tab.
      sessionStorage.removeItem('voya_new_chat_pending');
    },
  },
});

export const {
  setCredentials,
  setUser,
  setUserPhoto,
  setTokens,
  setLoading,
  setError,
  clearAuth,
} = authSlice.actions;

export default authSlice.reducer;

// Selectors (self-contained typing avoids circular import with store)
export const selectCurrentUser = (state: { auth: AuthState }) => state.auth.user;
export const selectIsAuthenticated = (state: { auth: AuthState }) => state.auth.isAuthenticated;
export const selectAuthToken = (state: { auth: AuthState }) => state.auth.token;
export const selectAuthLoading = (state: { auth: AuthState }) => state.auth.loading;
export const selectAuthError = (state: { auth: AuthState }) => state.auth.error;
