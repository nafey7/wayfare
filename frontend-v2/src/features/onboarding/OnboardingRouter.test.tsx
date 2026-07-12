import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

import authReducer from '@/store/slices/authSlice';
import type { AuthState } from '@/store/slices/authSlice';
import onboardingReducer from '@/store/slices/onboardingSlice';
import { ROUTES } from '@/features/routing/constants';
import { OnboardingRouter } from './OnboardingRouter';
import type { OnboardingState } from '@/types/onboarding';

const baseTrip: OnboardingState['tripDetails'] = {
  origin: '',
  destination: '',
  departureDate: null,
  returnDate: null,
  passengers: { adults: 1, children: 0, infants: 0 },
  tripType: 'roundTrip',
  budgetMindset: null,
  travelPace: null,
  primaryGoals: [],
  freeText: '',
};

function makeOnboarding(over: Partial<OnboardingState> = {}): OnboardingState {
  return {
    step: 1,
    detectedLocation: null,
    locationSkipped: false,
    tripDetails: { ...baseTrip },
    ...over,
  };
}

function createStore(authenticated: boolean, onboarding: OnboardingState) {
  const auth: AuthState = {
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
  };
  return configureStore({
    reducer: { auth: authReducer, onboarding: onboardingReducer },
    preloadedState: { auth, onboarding },
  });
}

function LocationReadout() {
  const { pathname } = useLocation();
  return <span data-testid="pathname">{pathname}</span>;
}

function renderOnboarding(authenticated: boolean, onboarding: OnboardingState) {
  const store = createStore(authenticated, onboarding);
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[ROUTES.ONBOARDING]}>
        <Routes>
          <Route path={ROUTES.ONBOARDING} element={<OnboardingRouter />} />
        </Routes>
        <LocationReadout />
      </MemoryRouter>
    </Provider>
  );
}

describe('OnboardingRouter', () => {
  it('redirects a guest with no location step to welcome', () => {
    renderOnboarding(
      false,
      makeOnboarding({ locationSkipped: false, detectedLocation: null })
    );
    expect(screen.getByTestId('pathname').textContent).toBe(ROUTES.ONBOARDING_WELCOME);
  });

  it('redirects a guest who skipped location to trip', () => {
    renderOnboarding(false, makeOnboarding({ locationSkipped: true }));
    expect(screen.getByTestId('pathname').textContent).toBe(ROUTES.ONBOARDING_TRIP);
  });

  it('redirects a signed-in user to trip (profile-location branch is TODO)', () => {
    renderOnboarding(
      true,
      makeOnboarding()
    );
    expect(screen.getByTestId('pathname').textContent).toBe(ROUTES.ONBOARDING_TRIP);
  });
});
