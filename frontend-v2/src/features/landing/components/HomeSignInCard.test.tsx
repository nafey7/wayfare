import type { ReactElement } from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

const mockIsMobile = vi.hoisted(() => vi.fn(() => true));

vi.mock('@mantine/hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@mantine/hooks')>();
  return {
    ...actual,
    // useMediaQuery('(min-width: 48em)') returns true on desktop; component negates it → isMobile
    useMediaQuery: ((..._args: unknown[]) => !mockIsMobile()) as typeof actual.useMediaQuery,
  };
});

vi.mock('lucide-react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('lucide-react')>();
  const Stub = () => null;
  return { ...actual, User: Stub, ChevronRight: Stub };
});

import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import authReducer from '@/store/slices/authSlice';
import uiReducer from '@/store/slices/uiSlice';
import chatReducer from '@/store/slices/chatSlice';
import type { User } from '@/types/auth';
import { HomeSignInCard } from './HomeSignInCard';

const mockUser: User = {
  id: 'u1',
  email: 'traveler@example.com',
  firstName: 'Test',
  lastName: 'User',
  emailVerified: true,
  createdAt: '',
  updatedAt: '',
};

function makeStore(authenticated: boolean) {
  return configureStore({
    reducer: { auth: authReducer, ui: uiReducer, chat: chatReducer },
    preloadedState: {
      auth: {
        user: authenticated ? mockUser : null,
        token: authenticated ? 'tok' : null,
        refreshToken: authenticated ? 'ref' : null,
        isAuthenticated: authenticated,
        loading: false,
        error: null,
      },
    },
  });
}

function renderCard(ui: ReactElement, authenticated = false) {
  const store = makeStore(authenticated);
  return {
    store,
    ...render(
      <Provider store={store}>
        <MantineProvider theme={mantineTheme}>{ui}</MantineProvider>
      </Provider>
    ),
  };
}

describe('HomeSignInCard', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
    mockIsMobile.mockReturnValue(true); // default: mobile viewport
  });

  it('renders sign-in prompt on mobile when unauthenticated', () => {
    renderCard(<HomeSignInCard />, false);
    expect(screen.getByText(/log in or sign up/i)).toBeInTheDocument();
    expect(screen.getByText(/save trips/i)).toBeInTheDocument();
  });

  it('does not render when authenticated', () => {
    renderCard(<HomeSignInCard />, true);
    expect(screen.queryByText(/log in or sign up/i)).not.toBeInTheDocument();
  });

  it('does not render on desktop when showOnDesktop is false (default)', () => {
    mockIsMobile.mockReturnValue(false); // desktop
    renderCard(<HomeSignInCard />, false);
    expect(screen.queryByText(/log in or sign up/i)).not.toBeInTheDocument();
  });

  it('renders on desktop when showOnDesktop is true', () => {
    mockIsMobile.mockReturnValue(false); // desktop
    renderCard(<HomeSignInCard showOnDesktop />, false);
    expect(screen.getByText(/log in or sign up/i)).toBeInTheDocument();
  });

  it('dispatches openAuthModal when the card is clicked', async () => {
    const user = userEvent.setup();
    const { store } = renderCard(<HomeSignInCard showOnDesktop />, false);
    expect(store.getState().ui.authModalOpen).toBe(false);
    await user.click(screen.getByText(/log in or sign up/i));
    expect(store.getState().ui.authModalOpen).toBe(true);
  });
});
