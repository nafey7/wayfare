import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import type { CredentialResponse } from '@react-oauth/google';

import authReducer from '@/store/slices/authSlice';
import { mantineTheme } from '@/theme';
import { trackEvent } from '@/utils/gtm';

import { GoogleAuthButton } from './GoogleAuthButton';

// Capture the onSuccess/onError callbacks rendered by GoogleLogin
let capturedOnSuccess: ((r: CredentialResponse) => void) | null = null;
let capturedOnError: (() => void) | null = null;

vi.mock('@react-oauth/google', () => ({
  GoogleOAuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  GoogleLogin: ({
    onSuccess,
    onError,
  }: {
    onSuccess: (r: CredentialResponse) => void;
    onError: () => void;
  }) => {
    capturedOnSuccess = onSuccess;
    capturedOnError = onError;
    return <button data-testid="google-login-btn">Sign in with Google</button>;
  },
}));

vi.mock('@/utils/gtm', () => ({ trackEvent: vi.fn() }));
vi.mock('@/utils/toast', () => ({
  showErrorToast: vi.fn(),
  showErrorToastFromError: vi.fn(),
}));
vi.mock('@/utils/devLog', () => ({ devLog: vi.fn() }));
vi.mock('@/features/chat/utils/publicChatReturnRoute', () => ({
  clearPublicChatReturnTo: vi.fn(),
}));
vi.mock('@/features/chat/utils/publicChatSession', () => ({
  shouldPostAuthPreferChatOverHome: vi.fn(() => false),
}));
vi.mock('@/features/auth/utils/authRedirectUtils', () => ({
  getRedirectToChatAfterAuth: vi.fn(() => ({ redirect: 'home' })),
}));

const mockGoogleAuth = vi.fn();

vi.mock('@/api', () => ({
  useGoogleAuthMutation: () => [mockGoogleAuth, { isLoading: false }],
  useGetGoogleConfigQuery: () => ({
    data: { enabled: true, clientId: 'test-client-id' },
    isLoading: false,
  }),
}));

vi.mock('@/store/slices/chatSlice', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/store/slices/chatSlice')>();
  return {
    ...actual,
    selectChatConfig: () => ({ publicChatEnabled: false }),
    selectConfigLoaded: () => true,
  };
});

const baseUser = {
  id: 'u1',
  email: 'user@example.com',
  firstName: 'U',
  lastName: 'Ser',
  emailVerified: true,
  createdAt: '',
  updatedAt: '',
};

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

function renderButton() {
  const store = createStore();
  render(
    <MantineProvider theme={mantineTheme}>
      <Provider store={store}>
        <MemoryRouter>
          <GoogleAuthButton />
        </MemoryRouter>
      </Provider>
    </MantineProvider>
  );
  return store;
}

describe('GoogleAuthButton GTM tracking', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedOnSuccess = null;
    capturedOnError = null;
  });

  it('fires user_registered before user_registration_completed for new signups', async () => {
    mockGoogleAuth.mockReturnValue({
      unwrap: () =>
        Promise.resolve({
          accessToken: 'tok',
          refreshToken: 'ref',
          tokenType: 'bearer',
          expiresIn: 3600,
          sessionId: 's1',
          isNew: true,
          user: baseUser,
        }),
    });

    renderButton();
    expect(screen.getByTestId('google-login-btn')).toBeInTheDocument();

    await act(async () => {
      capturedOnSuccess!({ credential: 'google-id-token' });
    });

    const eventNames = (trackEvent as ReturnType<typeof vi.fn>).mock.calls.map(([e]) => e);
    expect(eventNames).toContain('user_login');
    expect(eventNames).toContain('user_registered');
    expect(eventNames).toContain('user_registration_completed');
    expect(eventNames.indexOf('user_registered')).toBeLessThan(
      eventNames.indexOf('user_registration_completed')
    );
  });

  it('does not fire user_registered or user_registration_completed for returning users', async () => {
    mockGoogleAuth.mockReturnValue({
      unwrap: () =>
        Promise.resolve({
          accessToken: 'tok',
          refreshToken: 'ref',
          tokenType: 'bearer',
          expiresIn: 3600,
          sessionId: 's1',
          isNew: false,
          user: baseUser,
        }),
    });

    renderButton();

    await act(async () => {
      capturedOnSuccess!({ credential: 'google-id-token' });
    });

    const eventNames = (trackEvent as ReturnType<typeof vi.fn>).mock.calls.map(([e]) => e);
    expect(eventNames).toContain('user_login');
    expect(eventNames).not.toContain('user_registered');
    expect(eventNames).not.toContain('user_registration_completed');
  });

  it('fires user_login_failed when the Google button itself errors', async () => {
    renderButton();

    await act(async () => {
      capturedOnError!();
    });

    expect(trackEvent).toHaveBeenCalledWith('user_login_failed', {
      method: 'google',
      error: 'Google Sign-In failed',
    });
  });
});
