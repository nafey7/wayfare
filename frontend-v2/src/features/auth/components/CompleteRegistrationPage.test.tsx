import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';

import authReducer from '@/store/slices/authSlice';
import { mantineTheme } from '@/theme';
import type { AuthCredentials } from '@/types/auth';
import { ROUTES } from '@/features/routing';
import {
  clearPublicChatPendingCompleteRegistration,
  setPublicChatPendingCompleteRegistration,
} from '@/features/chat/utils/publicChatSignupIntent';
import { stashPublicChatReturnTo } from '@/features/chat/utils/publicChatReturnRoute';

import { CompleteRegistrationPage } from './CompleteRegistrationPage';

const RETURN_TO_KEY = 'voya_public_chat_return_to';

const mockCredentials: AuthCredentials = {
  accessToken: 'access',
  refreshToken: 'refresh',
  tokenType: 'bearer',
  expiresIn: 3600,
  sessionId: 'sess-1',
  isNew: true,
  user: {
    id: 'u1',
    email: 'user@example.com',
    firstName: 'U',
    lastName: 'Ser',
    emailVerified: true,
    createdAt: '',
    updatedAt: '',
  },
};

const mockValidate = vi.fn(() => ({
  unwrap: () => Promise.resolve(undefined),
}));

const mockComplete = vi.fn(() => ({
  unwrap: () => Promise.resolve(mockCredentials),
}));

const mockRefetch = vi.fn().mockResolvedValue({ data: undefined });

vi.mock('@/api', () => ({
  useValidateRegistrationTokenMutation: () => [mockValidate, { isLoading: false }],
  useCompleteRegistrationMutation: () => [mockComplete, { isLoading: false }],
  useGetFrontendConfigQuery: () => ({
    data: {
      chatFeedbackEnabled: false,
      publicChatEnabled: true,
      langgraphFlightsEnabled: false,
      langgraphHotelsEnabled: false,
      environment: 'test',
    },
    refetch: mockRefetch,
  }),
}));

vi.mock('@/utils/gtm', () => ({
  trackEvent: vi.fn(),
}));

vi.mock('@/utils/devLog', () => ({
  devLog: vi.fn(),
}));

function createStore() {
  return configureStore({
    reducer: { auth: authReducer },
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

function renderAtCompleteRegistration(path = `${ROUTES.COMPLETE_REGISTRATION}?token=tok`) {
  const store = createStore();
  const utils = render(
    <MantineProvider theme={mantineTheme}>
      <Provider store={store}>
        <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={ROUTES.COMPLETE_REGISTRATION} element={<CompleteRegistrationPage />} />
          <Route path={ROUTES.CHAT} element={<div data-testid="chat-page">chat</div>} />
          <Route
            path={ROUTES.FLIGHTS_SEARCH}
            element={<div data-testid="flight-recs">flights</div>}
          />
        </Routes>
      </MemoryRouter>
      </Provider>
    </MantineProvider>
  );
  return { ...utils, store };
}

describe('CompleteRegistrationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    clearPublicChatPendingCompleteRegistration();
  });

  it('navigates to stashed return-to when return-to is present even without pending registration flag', async () => {
    const user = userEvent.setup();
    stashPublicChatReturnTo(ROUTES.FLIGHTS_SEARCH);

    renderAtCompleteRegistration();

    await waitFor(() => {
      expect(screen.getByLabelText(/^Password$/)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(/^Password$/), 'Password1a');
    await user.type(screen.getByLabelText(/Confirm Password/i), 'Password1a');
    await user.click(screen.getByRole('button', { name: /complete registration/i }));

    await waitFor(() => {
      expect(screen.getByTestId('flight-recs')).toBeInTheDocument();
    });
    expect(localStorage.getItem(RETURN_TO_KEY)).toBeNull();
  });

  it('navigates to stashed return-to when public-chat handoff and return-to are present', async () => {
    const user = userEvent.setup();
    setPublicChatPendingCompleteRegistration();
    stashPublicChatReturnTo(ROUTES.FLIGHTS_SEARCH);

    renderAtCompleteRegistration();

    await waitFor(() => {
      expect(screen.getByLabelText(/^Password$/)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(/^Password$/), 'Password1a');
    await user.type(screen.getByLabelText(/Confirm Password/i), 'Password1a');
    await user.click(screen.getByRole('button', { name: /complete registration/i }));

    await waitFor(() => {
      expect(screen.getByTestId('flight-recs')).toBeInTheDocument();
    });
    expect(localStorage.getItem(RETURN_TO_KEY)).toBeNull();
  });

  it('navigates to /chat when handoff is set but no return-to is stored', async () => {
    const user = userEvent.setup();
    setPublicChatPendingCompleteRegistration();

    renderAtCompleteRegistration();

    await waitFor(() => {
      expect(screen.getByLabelText(/^Password$/)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(/^Password$/), 'Password1a');
    await user.type(screen.getByLabelText(/Confirm Password/i), 'Password1a');
    await user.click(screen.getByRole('button', { name: /complete registration/i }));

    await waitFor(() => {
      expect(screen.getByTestId('chat-page')).toBeInTheDocument();
    });
  });

  it('navigates to /chat when return-to envelope is expired', async () => {
    const user = userEvent.setup();
    setPublicChatPendingCompleteRegistration();
    localStorage.setItem(
      RETURN_TO_KEY,
      JSON.stringify({
        path: ROUTES.FLIGHTS_SEARCH,
        timestamp: Date.now() - 25 * 60 * 60 * 1000,
      })
    );

    renderAtCompleteRegistration();

    await waitFor(() => {
      expect(screen.getByLabelText(/^Password$/)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(/^Password$/), 'Password1a');
    await user.type(screen.getByLabelText(/Confirm Password/i), 'Password1a');
    await user.click(screen.getByRole('button', { name: /complete registration/i }));

    await waitFor(() => {
      expect(screen.getByTestId('chat-page')).toBeInTheDocument();
    });
  });

  describe('post-signup redirect integration', () => {
    it('completes registration to the same path as stashPublicChatReturnTo would use after a public content visit', async () => {
      const user = userEvent.setup();
      setPublicChatPendingCompleteRegistration();
      stashPublicChatReturnTo(ROUTES.HOTELS_SEARCH, '?q=paris');

      render(
        <MantineProvider theme={mantineTheme}>
          <Provider store={createStore()}>
            <MemoryRouter
              initialEntries={[`${ROUTES.COMPLETE_REGISTRATION}?token=tok`]}
            >
              <Routes>
                <Route path={ROUTES.COMPLETE_REGISTRATION} element={<CompleteRegistrationPage />} />
                <Route path={ROUTES.HOTELS_SEARCH} element={<div data-testid="hotel-search">hotels</div>} />
                <Route path={ROUTES.CHAT} element={<div data-testid="chat-page">chat</div>} />
              </Routes>
            </MemoryRouter>
          </Provider>
        </MantineProvider>
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/^Password$/)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/^Password$/), 'Password1a');
      await user.type(screen.getByLabelText(/Confirm Password/i), 'Password1a');
      await user.click(screen.getByRole('button', { name: /complete registration/i }));

      await waitFor(() => {
        expect(screen.getByTestId('hotel-search')).toBeInTheDocument();
      });
    });
  });
});
