import type { ReactNode } from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';

import authReducer from '@/store/slices/authSlice';
import uiReducer from '@/store/slices/uiSlice';
import { ROUTES } from '@/features/routing/constants';
import { OnboardingScreen1 } from './OnboardingScreen1';

vi.mock('@/features/onboarding/components/OnboardingLayout', () => ({
  OnboardingLayout: ({
    children,
    title,
    showTitle = true,
  }: {
    children: ReactNode;
    title: string;
    showTitle?: boolean;
  }) => (
    <div>
      {showTitle ? <h1>{title}</h1> : null}
      {children}
    </div>
  ),
}));

function renderScreen(authenticated: boolean) {
  const store = configureStore({
    reducer: { auth: authReducer, ui: uiReducer },
    preloadedState: {
      auth: {
        user: authenticated
          ? {
              id: '1',
              email: 'a@b.com',
              firstName: 'A',
              lastName: 'B',
              emailVerified: true,
              createdAt: '',
              updatedAt: '',
            }
          : null,
        token: authenticated ? 't' : null,
        refreshToken: null,
        isAuthenticated: authenticated,
        loading: false,
        error: null,
      },
    },
  });
  return {
    store,
    ...render(
      <MantineProvider env="test">
        <Provider store={store}>
          <MemoryRouter>
            <OnboardingScreen1 />
          </MemoryRouter>
        </Provider>
      </MantineProvider>
    ),
  };
}

describe('OnboardingScreen1', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('renders the default headline for new users', () => {
    renderScreen(false);
    expect(
      screen.getByRole('heading', { name: /plan your perfect trip with voya ai/i })
    ).toBeInTheDocument();
  });

  it('stashes post-auth path and opens auth modal when a guest uses sign in', () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem');
    const { store } = renderScreen(false);
    fireEvent.click(screen.getByRole('button', { name: /sign in with google/i }));
    expect(setItem).toHaveBeenCalledWith(
      'voya_post_auth_onboarding_path',
      ROUTES.ONBOARDING_TRIP
    );
    expect(store.getState().ui.authModalOpen).toBe(true);
    setItem.mockRestore();
  });
});
