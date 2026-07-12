import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, render } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import authReducer, { setCredentials } from '@/store/slices/authSlice';
import chatReducer from '@/store/slices/chatSlice';
import uiReducer from '@/store/slices/uiSlice';
import { baseApi } from '@/api/baseApi';
import type { AuthCredentials } from '@/types/auth';

const mockConsumeIntent = vi.fn();
const mockConsumePending = vi.fn();
const mockTrackEvent = vi.fn();
const mockShowSuccessToast = vi.fn();
const mockShowWarningToast = vi.fn();

vi.mock('@/features/chat/utils/publicChatSession', () => ({
  consumePublicChatConversionIntent: () => mockConsumeIntent(),
}));

vi.mock('@/features/chat/utils/pendingItinerarySave', () => ({
  consumePendingItinerarySave: () => mockConsumePending(),
}));

vi.mock('@/utils/gtm', () => ({
  trackEvent: (...args: unknown[]) => mockTrackEvent(...args),
}));

vi.mock('@/utils/toast', () => ({
  showSuccessToast: (...args: unknown[]) => mockShowSuccessToast(...args),
  showWarningToast: (...args: unknown[]) => mockShowWarningToast(...args),
}));

import { PublicChatPostAuthConversionTracker } from './PublicChatPostAuthConversionTracker';

const TEST_CREDENTIALS: AuthCredentials = {
  accessToken: 'tok',
  refreshToken: 'rt',
  tokenType: 'bearer',
  expiresIn: 3600,
  user: {
    id: '1',
    email: 'a@b.com',
    firstName: 'Test',
    lastName: 'User',
    emailVerified: true,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
  },
  sessionId: 'sess-1',
  isNew: false,
};

function createGuestStore() {
  return configureStore({
    reducer: {
      [baseApi.reducerPath]: baseApi.reducer,
      auth: authReducer,
      chat: chatReducer,
      ui: uiReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({ serializableCheck: false }).concat(baseApi.middleware),
    preloadedState: {
      auth: {
        user: null,
        token: null,
        refreshToken: null,
        isAuthenticated: false,
        loading: false,
        error: null,
      },
    },
  });
}

describe('PublicChatPostAuthConversionTracker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fires analytics when intent exists on auth transition', () => {
    mockConsumeIntent.mockReturnValue('flight_book_now');
    const store = createGuestStore();

    const { rerender } = render(
      <Provider store={store}>
        <PublicChatPostAuthConversionTracker />
      </Provider>
    );

    act(() => { store.dispatch(setCredentials(TEST_CREDENTIALS)); });

    rerender(
      <Provider store={store}>
        <PublicChatPostAuthConversionTracker />
      </Provider>
    );

    expect(mockConsumeIntent).toHaveBeenCalled();
    expect(mockTrackEvent).toHaveBeenCalledWith('public_chat_post_auth_conversion', {
      intent: 'flight_book_now',
    });
  });

  it('does not fire when no intent is stored', () => {
    mockConsumeIntent.mockReturnValue(null);
    const store = createGuestStore();

    const { rerender } = render(
      <Provider store={store}>
        <PublicChatPostAuthConversionTracker />
      </Provider>
    );

    act(() => { store.dispatch(setCredentials(TEST_CREDENTIALS)); });

    rerender(
      <Provider store={store}>
        <PublicChatPostAuthConversionTracker />
      </Provider>
    );

    expect(mockTrackEvent).not.toHaveBeenCalled();
  });

  it('consumes pending itinerary data on itinerary_save intent', () => {
    mockConsumeIntent.mockReturnValue('itinerary_save');
    mockConsumePending.mockReturnValue({
      structured_itinerary: { itineraryItems: [{ day: 1 }] },
      trip_meta: { destination: 'Paris' },
    });

    const store = createGuestStore();

    const { rerender } = render(
      <Provider store={store}>
        <PublicChatPostAuthConversionTracker />
      </Provider>
    );

    act(() => { store.dispatch(setCredentials(TEST_CREDENTIALS)); });

    rerender(
      <Provider store={store}>
        <PublicChatPostAuthConversionTracker />
      </Provider>
    );

    expect(mockConsumePending).toHaveBeenCalled();
  });

  it('does not attempt save when no pending data for itinerary_save', () => {
    mockConsumeIntent.mockReturnValue('itinerary_save');
    mockConsumePending.mockReturnValue(null);

    const store = createGuestStore();

    const { rerender } = render(
      <Provider store={store}>
        <PublicChatPostAuthConversionTracker />
      </Provider>
    );

    act(() => { store.dispatch(setCredentials(TEST_CREDENTIALS)); });

    rerender(
      <Provider store={store}>
        <PublicChatPostAuthConversionTracker />
      </Provider>
    );

    expect(mockConsumePending).toHaveBeenCalled();
    expect(mockShowSuccessToast).not.toHaveBeenCalled();
    expect(mockShowWarningToast).not.toHaveBeenCalled();
  });

  it('does not consume pending save for non-itinerary intents', () => {
    mockConsumeIntent.mockReturnValue('flight_book_now');
    const store = createGuestStore();

    const { rerender } = render(
      <Provider store={store}>
        <PublicChatPostAuthConversionTracker />
      </Provider>
    );

    act(() => { store.dispatch(setCredentials(TEST_CREDENTIALS)); });

    rerender(
      <Provider store={store}>
        <PublicChatPostAuthConversionTracker />
      </Provider>
    );

    expect(mockConsumePending).not.toHaveBeenCalled();
  });

  it('does not fire on initial render when already authenticated', () => {
    mockConsumeIntent.mockReturnValue('flight_book_now');

    const store = configureStore({
      reducer: {
        [baseApi.reducerPath]: baseApi.reducer,
        auth: authReducer,
        chat: chatReducer,
        ui: uiReducer,
      },
      middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({ serializableCheck: false }).concat(baseApi.middleware),
      preloadedState: {
        auth: {
          user: null,
          token: 'tok',
          refreshToken: 'rt',
          isAuthenticated: true,
          loading: false,
          error: null,
        },
      },
    });

    render(
      <Provider store={store}>
        <PublicChatPostAuthConversionTracker />
      </Provider>
    );

    expect(mockConsumeIntent).not.toHaveBeenCalled();
  });
});
