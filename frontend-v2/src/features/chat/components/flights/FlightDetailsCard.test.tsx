import type { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import { store } from '@/store';
import { clearAuth, setCredentials } from '@/store/slices/authSlice';
import { closeAuthModal } from '@/store/slices/uiSlice';
import { ChatContext } from '@/features/chat/context/ChatContext';
import { getStubChatContextValue } from '@/test/stubChatContextValue';
import type { AuthCredentials } from '@/types/auth';
import type { MappedFlight } from '@/types/flight';
import { FlightDetailsCard } from './FlightDetailsCard';

const revalidateFlightTrigger = vi.fn();

vi.mock('@/api/flightsApi', () => ({
  useRevalidateFlightMutation: () => [
    (...args: unknown[]) => {
      revalidateFlightTrigger(...args);
      return {
        unwrap: () =>
          Promise.resolve({
            isFareAvailable: true,
          }),
      };
    },
    { isLoading: false },
  ],
  useResolveAirportQuery: () => ({ data: null }),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function makeTestCredentials(): AuthCredentials {
  return {
    accessToken: 'test-access-token',
    refreshToken: 'test-refresh-token',
    tokenType: 'bearer',
    expiresIn: 3600,
    sessionId: 'sess-1',
    isNew: false,
    user: {
      id: 'u1',
      email: 't@example.com',
      firstName: 'T',
      lastName: 'User',
      emailVerified: true,
      createdAt: '',
      updatedAt: '',
    },
  };
}

function makeFlight(): MappedFlight {
  return {
    id: 'fare-src-1',
    price: 99,
    currency: 'USD',
    airline_names: ['Test Air'],
    is_round_trip: false,
    outbound: {
      duration: '2h',
      stops: 0,
      layovers: [],
    },
  } as MappedFlight;
}

function TestWrapper({ children }: { children: ReactNode }) {
  return (
    <Provider store={store}>
      <MemoryRouter>
        <MantineProvider theme={mantineTheme}>
          <ChatContext.Provider value={getStubChatContextValue()}>{children}</ChatContext.Provider>
        </MantineProvider>
      </MemoryRouter>
    </Provider>
  );
}

describe('FlightDetailsCard conversion gate', () => {
  beforeEach(() => {
    revalidateFlightTrigger.mockClear();
    mockNavigate.mockClear();
    localStorage.removeItem('sessionId');
    store.dispatch(clearAuth());
    store.dispatch(closeAuthModal());
  });

  it('does not revalidate when guest clicks Book Now', async () => {
    localStorage.setItem('sessionId', 'flight-sess');
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <FlightDetailsCard flight={makeFlight()} />
      </TestWrapper>
    );
    await user.click(screen.getByText('$99 total'));
    expect(store.getState().ui.authModalOpen).toBe(true);
    expect(revalidateFlightTrigger).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('revalidates and navigates when authenticated user clicks Book Now', async () => {
    localStorage.setItem('sessionId', 'flight-sess');
    store.dispatch(setCredentials(makeTestCredentials()));
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <FlightDetailsCard flight={makeFlight()} />
      </TestWrapper>
    );
    await user.click(screen.getByText('$99 total'));
    expect(revalidateFlightTrigger).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalled();
  });
});
