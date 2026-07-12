import type { Action } from 'redux';
import type { ThunkAction } from 'redux-thunk';
import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';
import { baseApi } from '@/api/baseApi';
import { strapiApi } from '@/api/strapiApi';
import authReducer from './slices/authSlice';
import type { AuthState } from './slices/authSlice';
import chatReducer from './slices/chatSlice';
import uiReducer from './slices/uiSlice';
import flightBookingReducer from './slices/flightBookingSlice';
import hotelBookingReducer from './slices/hotelBookingSlice';
import onboardingReducer from './slices/onboardingSlice';
import { authLogoutListener } from './authLogoutListener';
import { authOnboardingPreferencesListener } from './authOnboardingPreferencesListener';
import { guestItineraryListener } from './guestItineraryListener';

/**
 * Redux store configuration
 *
 * Includes:
 * - RTK Query API middleware for caching and invalidation
 * - Auth, Chat, UI, FlightBooking, HotelBooking, and Onboarding slices
 * - DevTools enabled in development
 */
export const store = configureStore({
  reducer: {
    // RTK Query API reducer
    [baseApi.reducerPath]: baseApi.reducer,
    [strapiApi.reducerPath]: strapiApi.reducer,
    // App slices
    auth: authReducer,
    chat: chatReducer,
    ui: uiReducer,
    flightBooking: flightBookingReducer,
    hotelBooking: hotelBookingReducer,
    onboarding: onboardingReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types for RTK Query
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }).concat(
      baseApi.middleware,
      strapiApi.middleware,
      authLogoutListener.middleware,
      authOnboardingPreferencesListener.middleware,
      guestItineraryListener.middleware,
    ),
  devTools: import.meta.env.DEV,
});

// Enable refetchOnFocus and refetchOnReconnect
setupListeners(store.dispatch);

// Infer types from store; patch auth to AuthState (RTK Query can infer auth as unknown)
export type RootState = Omit<ReturnType<typeof store.getState>, 'auth'> & {
  auth: AuthState;
};
export type AppDispatch = typeof store.dispatch;

/** Standard AppThunk type for synchronous thunks (dispatch, getState) => void */
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  Action<string>
>;

// Re-export hooks
export { useAppDispatch, useAppSelector } from './hooks';

/** Creates a fresh, isolated store instance — use in tests to prevent state leaking between cases. */
export function makeTestStore() {
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
      getDefaultMiddleware({
        serializableCheck: {
          ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
        },
      }).concat(
        baseApi.middleware,
        strapiApi.middleware,
        authLogoutListener.middleware,
        authOnboardingPreferencesListener.middleware,
        guestItineraryListener.middleware,
      ),
  });
}
