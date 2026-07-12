import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import type { ReactNode } from 'react';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';

import authReducer from '@/store/slices/authSlice';
import chatReducer from '@/store/slices/chatSlice';
import onboardingReducer from '@/store/slices/onboardingSlice';
import type { AuthState } from '@/store/slices/authSlice';
import type { ChatState } from '@/store/slices/chatSlice';
import type { OnboardingState } from '@/types/onboarding';
import type { FrontendConfig } from '@/types/chat';
import uiReducer from '@/store/slices/uiSlice';
import { setTripDetails } from '@/store/slices/onboardingSlice';
import { ROUTES } from '@/features/routing/constants';
import { useStartPlanning } from './useStartPlanning';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const defaultChatConfig: FrontendConfig = {
  chatFeedbackEnabled: false,
  publicChatEnabled: false,
  langgraphFlightsEnabled: false,
  langgraphHotelsEnabled: false,
  environment: 'development',
};

const emptyTrip: OnboardingState['tripDetails'] = {
  origin: '',
  destination: 'Sydney',
  departureDate: null,
  returnDate: null,
  passengers: { adults: 1, children: 0, infants: 0 },
  tripType: 'roundTrip',
  budgetMindset: null,
  travelPace: null,
  primaryGoals: [],
  freeText: '',
};

function createStore(options: {
  auth: AuthState;
  chat: Partial<ChatState> & Pick<ChatState, 'config' | 'configLoaded'>;
  onboarding: OnboardingState;
}) {
  const chat: ChatState = {
    messages: [],
    chatId: null,
    loading: false,
    feedbackSubmitted: {},
    conversations: [],
    conversationsLoaded: false,
    conversationSidebarOpen: false,
    streamingItinerary: { partial: null, active: false },
    ...options.chat,
    config: options.chat.config ?? defaultChatConfig,
    configLoaded: options.chat.configLoaded ?? false,
  };
  return configureStore({
    reducer: {
      auth: authReducer,
      chat: chatReducer,
      onboarding: onboardingReducer,
      ui: uiReducer,
    },
    preloadedState: {
      auth: options.auth,
      chat,
      onboarding: options.onboarding,
    },
  });
}

function wrapperFor(store: ReturnType<typeof createStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter>
        <Provider store={store}>{children}</Provider>
      </MemoryRouter>
    );
  };
}

describe('useStartPlanning', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    localStorage.removeItem('voya_pending_onboarding_preferences_sync');
    localStorage.removeItem('voya_pending_onboarding_preferences_payload');
  });

  it('does not reset onboarding when guest and config is not loaded yet', () => {
    const store = createStore({
      auth: {
        user: null,
        token: null,
        refreshToken: null,
        isAuthenticated: false,
        loading: false,
        error: null,
      },
      chat: { config: defaultChatConfig, configLoaded: false },
      onboarding: {
        step: 3,
        detectedLocation: null,
        locationSkipped: true,
        tripDetails: { ...emptyTrip },
      },
    });
    const { result } = renderHook(() => useStartPlanning(), {
      wrapper: wrapperFor(store),
    });
    expect(result.current.isGuestAwaitingChatConfig).toBe(true);
    act(() => {
      result.current.startPlanning();
    });
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(store.getState().onboarding.tripDetails.destination).toBe('Sydney');
  });

  it('navigates guest to public chat when config is loaded and commits reset', () => {
    const store = createStore({
      auth: {
        user: null,
        token: null,
        refreshToken: null,
        isAuthenticated: false,
        loading: false,
        error: null,
      },
      chat: {
        config: { ...defaultChatConfig, publicChatEnabled: true },
        configLoaded: true,
      },
      onboarding: {
        step: 3,
        detectedLocation: null,
        locationSkipped: true,
        tripDetails: {
          ...emptyTrip,
          travelPace: 'balanced',
          primaryGoals: ['food'],
        },
      },
    });
    const { result } = renderHook(() => useStartPlanning(), {
      wrapper: wrapperFor(store),
    });
    expect(result.current.isGuestAwaitingChatConfig).toBe(false);
    act(() => {
      store.dispatch(
        setTripDetails({ travelPace: 'balanced', primaryGoals: ['food'] })
      );
    });
    act(() => {
      result.current.startPlanning();
    });
    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        pathname: ROUTES.PUBLIC_CHAT,
        search: expect.stringMatching(/^\?prompt=/),
      })
    );
    expect(store.getState().onboarding.tripDetails.destination).toBe('');
    const raw = localStorage.getItem('voya_pending_onboarding_preferences_payload');
    expect(raw).toBeTruthy();
    expect(JSON.parse(raw!)).toEqual({
      travelStyle: {
        travelPace: 'balanced',
        primaryGoals: ['food'],
      },
    });
  });

  it('opens auth modal when guest, config loaded, and public chat disabled; keeps onboarding (for post-signup preference sync)', () => {
    const store = createStore({
      auth: {
        user: null,
        token: null,
        refreshToken: null,
        isAuthenticated: false,
        loading: false,
        error: null,
      },
      chat: {
        config: { ...defaultChatConfig, publicChatEnabled: false },
        configLoaded: true,
      },
      onboarding: {
        step: 3,
        detectedLocation: null,
        locationSkipped: true,
        tripDetails: { ...emptyTrip },
      },
    });
    const { result } = renderHook(() => useStartPlanning(), {
      wrapper: wrapperFor(store),
    });
    expect(result.current.isGuestAwaitingChatConfig).toBe(false);
    act(() => {
      result.current.continueToChat();
    });
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(store.getState().ui.authModalOpen).toBe(true);
    expect(store.getState().onboarding.tripDetails.destination).toBe('Sydney');
  });

  it('navigates authenticated user to chat and resets', () => {
    const store = createStore({
      auth: {
        user: {
          id: '1',
          email: 'a@b.com',
          firstName: 'A',
          lastName: 'B',
          emailVerified: true,
          createdAt: '',
          updatedAt: '',
        },
        token: 't',
        refreshToken: 'r',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
      chat: { config: defaultChatConfig, configLoaded: false },
      onboarding: {
        step: 3,
        detectedLocation: null,
        locationSkipped: true,
        tripDetails: { ...emptyTrip, destination: 'Berlin' },
      },
    });
    const { result } = renderHook(() => useStartPlanning(), {
      wrapper: wrapperFor(store),
    });
    expect(result.current.isGuestAwaitingChatConfig).toBe(false);
    act(() => {
      result.current.startPlanning();
    });
    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        pathname: ROUTES.CHAT,
        search: expect.stringMatching(/^\?prompt=/),
      })
    );
    expect(store.getState().onboarding.tripDetails.destination).toBe('');
  });
});
