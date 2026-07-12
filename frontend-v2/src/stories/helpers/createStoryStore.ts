import { configureStore } from '@reduxjs/toolkit';
import { baseApi } from '@/api/baseApi';
import { strapiApi } from '@/api/strapiApi';
import authReducer, { setCredentials } from '@/store/slices/authSlice';
import chatReducer from '@/store/slices/chatSlice';
import uiReducer from '@/store/slices/uiSlice';
import flightBookingReducer from '@/store/slices/flightBookingSlice';
import hotelBookingReducer from '@/store/slices/hotelBookingSlice';
import type { AuthCredentials } from '@/types/auth';

/** Mirrors the store created in .storybook/preview.tsx for use in story-level decorators that need preloaded RTK Query state. */
export function createStoryStore() {
  return configureStore({
    reducer: {
      [baseApi.reducerPath]: baseApi.reducer,
      [strapiApi.reducerPath]: strapiApi.reducer,
      auth: authReducer,
      chat: chatReducer,
      ui: uiReducer,
      flightBooking: flightBookingReducer,
      hotelBooking: hotelBookingReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: {
          ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
        },
      }).concat(baseApi.middleware, strapiApi.middleware),
  });
}

export type StoryStore = ReturnType<typeof createStoryStore>;

const DEFAULT_STORY_CREDENTIALS: AuthCredentials = {
  accessToken: 'story-token',
  refreshToken: 'story-refresh',
  tokenType: 'bearer',
  expiresIn: 3600,
  sessionId: 'story-session',
  isNew: false,
  user: {
    id: 'u1',
    email: 'story@example.com',
    firstName: 'Story',
    lastName: 'User',
    emailVerified: true,
    role: 'user',
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
  },
};

/**
 * Creates a store with auth credentials already dispatched but without writing
 * to localStorage, so later stories in the same Playwright browser session don't
 * inherit an authenticated state.
 */
export function createAuthenticatedStoryStore(credentials: Partial<AuthCredentials> = {}): StoryStore {
  const store = createStoryStore();
  const origSetItem = localStorage.setItem.bind(localStorage);
  localStorage.setItem = (_k: string, _v: string) => {};
  try {
    store.dispatch(setCredentials({ ...DEFAULT_STORY_CREDENTIALS, ...credentials }));
  } finally {
    localStorage.setItem = origSetItem;
  }
  return store;
}
