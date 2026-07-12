import type { ReactNode } from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { DatesProvider } from '@mantine/dates';

import authReducer from '@/store/slices/authSlice';
import onboardingReducer from '@/store/slices/onboardingSlice';
import { OnboardingScreen3 } from './OnboardingScreen3';

const sp = vi.hoisted(() => ({
  isGuestAwaitingChatConfig: false,
  startPlanning: vi.fn(),
  continueToChat: vi.fn(),
}));

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

vi.mock('../useStartPlanning', () => ({
  useStartPlanning: () => ({
    startPlanning: sp.startPlanning,
    continueToChat: sp.continueToChat,
    get isGuestAwaitingChatConfig() {
      return sp.isGuestAwaitingChatConfig;
    },
  }),
}));

function renderScreen() {
  const store = configureStore({
    reducer: { auth: authReducer, onboarding: onboardingReducer },
  });
  render(
    <MantineProvider env="test">
      <DatesProvider settings={{}}>
        <Provider store={store}>
          <MemoryRouter>
            <OnboardingScreen3 />
          </MemoryRouter>
        </Provider>
      </DatesProvider>
    </MantineProvider>
  );
  return store;
}

describe('OnboardingScreen3', () => {
  beforeEach(() => {
    sp.isGuestAwaitingChatConfig = false;
    sp.startPlanning.mockClear();
    sp.continueToChat.mockClear();
  });

  it('renders the trip form and primary CTAs', () => {
    sp.isGuestAwaitingChatConfig = false;
    renderScreen();
    expect(
      screen.getByRole('heading', { name: /tell us about your trip/i })
    ).toBeInTheDocument();
    const start = screen.getByRole('button', { name: /start planning/i });
    const skip = screen.getByRole('button', { name: /continue straight to chat/i });
    expect(start).toBeDisabled();
    fireEvent.click(skip);
    expect(sp.continueToChat).toHaveBeenCalled();
  });

  it('disables trip CTAs while guest chat config is loading', () => {
    sp.isGuestAwaitingChatConfig = true;
    renderScreen();
    expect(
      screen.getByRole('button', { name: /start planning/i })
    ).toBeDisabled();
    expect(
      screen.getByRole('button', { name: /continue straight to chat/i })
    ).toBeDisabled();
  });

  it('marks origin city field as optional', () => {
    sp.isGuestAwaitingChatConfig = false;
    renderScreen();
    // Mantine `Autocomplete` renders the label as a sibling text node, so the
    // visible label text appears in the DOM (we just want to confirm "(optional)"
    // is in the accessible name somewhere).
    const labels = screen.getAllByText(/flying from \(optional\)/i);
    expect(labels.length).toBeGreaterThan(0);
  });
});
