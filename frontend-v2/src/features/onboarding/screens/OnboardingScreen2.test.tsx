import type { ReactNode } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';

import onboardingReducer from '@/store/slices/onboardingSlice';
import { OnboardingScreen2 } from './OnboardingScreen2';

/**
 * RTK-style hooks return an object whose fields may be used in useEffect deps.
 * OnboardingScreen2 depends on `data`; the mock must return stable references
 * or every render gets a new `data` and the effect loops (max update depth / hang).
 */
const { detectQueryReturn } = vi.hoisted(() => {
  const data = {
    country: 'United Kingdom',
    countryCode: 'GB',
    city: 'London',
    iata: 'LON',
    currency: 'GBP',
    currencySymbol: '£',
  };
  return {
    detectQueryReturn: {
      data,
      isLoading: false,
      isError: false,
    },
  };
});

vi.mock('@/features/onboarding/components/OnboardingLayout', () => ({
  OnboardingLayout: ({
    children,
    title,
  }: {
    children: ReactNode;
    title: string;
  }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

vi.mock('@/api/locationApi', () => ({
  useDetectLocationQuery: () => detectQueryReturn,
}));

function renderScreen() {
  const store = configureStore({ reducer: { onboarding: onboardingReducer } });
  render(
    <MantineProvider env="test">
      <Provider store={store}>
        <MemoryRouter>
          <OnboardingScreen2 />
        </MemoryRouter>
      </Provider>
    </MantineProvider>
  );
  return store;
}

describe('OnboardingScreen2', () => {
  it('renders the location step and confirm stores London as origin', () => {
    const store = renderScreen();
    expect(
      screen.getByRole('heading', { name: /where are you based/i })
    ).toBeInTheDocument();

    // Label is "That's right" — `/that.right/i` wrongly matches "that" + . + "right" (no "s").
    const confirm = screen.getByRole('button', { name: /that.s right/i });
    fireEvent.click(confirm);

    expect(store.getState().onboarding.detectedLocation?.city).toBe('London');
    expect(store.getState().onboarding.detectedLocation?.iata).toBe('');
    expect(store.getState().onboarding.tripDetails.origin).toBe(
      'London · United Kingdom'
    );
  });
});
