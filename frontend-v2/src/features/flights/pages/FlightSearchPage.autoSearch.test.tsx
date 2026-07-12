import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { MantineProvider } from '@mantine/core';
import { lightTheme } from '@/theme';
import { store } from '@/store';
import {
  setSearchFormParams,
  resetBooking,
  type FlightSearchFormParams,
} from '@/store/slices/flightBookingSlice';

const { mockNavigate } = vi.hoisted(() => ({ mockNavigate: vi.fn() }));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('@mui/icons-material', () => {
  const Stub = () => null;
  return {
    SwapHoriz: Stub, FlightTakeoff: Stub, FlightLand: Stub, CalendarToday: Stub,
    Add: Stub, Delete: Stub, Close: Stub, FilterList: Stub, SwapVert: Stub,
    ExpandMore: Stub, Flight: Stub, InfoOutlined: Stub,
  };
});

vi.mock('@mui/x-date-pickers/DatePicker', () => ({ DatePicker: () => null }));

vi.mock('@mantine/hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@mantine/hooks')>();
  return { ...actual, useMediaQuery: () => false };
});

const emptySearchResponse = { sessionId: 'test-session', fareItineraries: [] };

vi.mock('@/api/flightsApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/flightsApi')>();
  return {
    ...actual,
    flightsApi: {
      ...actual.flightsApi,
      endpoints: {
        ...actual.flightsApi.endpoints,
        searchFlights: {
          ...actual.flightsApi.endpoints.searchFlights,
          // Return a dispatchable plain action (not a thunk) so dispatch resolves immediately
          initiate: vi.fn(() => ({ type: 'mock/flights/search' })),
          select: vi.fn(() => () => ({ status: 'uninitialized', data: undefined })),
        },
      },
    },
    useSearchFlightsQuery: () => ({
      data: emptySearchResponse,
      isLoading: false,
      isFetching: false,
      error: undefined,
      refetch: vi.fn(),
    }),
    useSearchAirportsQuery: () => ({ data: [], isFetching: false }),
    useRevalidateFlightMutation: () => [vi.fn(), { isLoading: false }],
    useLazyResolveAirportQuery: () => [
      vi.fn(() => ({
        unwrap: vi.fn().mockResolvedValue({ iataCode: 'LHR' }),
      })),
      { isLoading: false, isFetching: false },
    ],
  };
});

vi.mock('@/features/chat/hooks/usePublicChatConversionGate', () => ({
  usePublicChatConversionGate: () => ({ ensureAuthenticated: () => true }),
}));

import { FlightSearchPage } from './FlightSearchPage';

const defaultTravellers = { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' as const };

const oneWayParams: FlightSearchFormParams = {
  tripType: 'one-way',
  from: 'LHR',
  to: 'CDG',
  date: '2026-06-15T00:00:00.000Z',
  returnDate: null,
  travellers: defaultTravellers,
};

const roundTripParams: FlightSearchFormParams = {
  tripType: 'round-trip',
  from: 'LHR',
  to: 'CDG',
  date: '2026-06-15T00:00:00.000Z',
  returnDate: '2026-06-20T00:00:00.000Z',
  travellers: defaultTravellers,
};

const multiCityParams: FlightSearchFormParams = {
  tripType: 'multi-city',
  from: '',
  to: '',
  date: null,
  returnDate: null,
  travellers: defaultTravellers,
  segments: [
    { from: 'LHR', to: 'CDG', date: '2026-06-15T00:00:00.000Z' },
    { from: 'CDG', to: 'AMS', date: '2026-06-20T00:00:00.000Z' },
  ],
};

function renderWithoutQuery() {
  return render(
    <ThemeProvider theme={lightTheme}>
      <MantineProvider>
      <Provider store={store}>
        <MemoryRouter initialEntries={['/flights/search']}>
          <Routes>
            <Route path="/flights/search" element={<FlightSearchPage />} />
          </Routes>
        </MemoryRouter>
      </Provider>
      </MantineProvider>
    </ThemeProvider>,
  );
}

describe('FlightSearchPage auto-search mount-effect guards', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    store.dispatch(resetBooking());
  });

  it('navigates to ?q= on mount for complete one-way params when URL is clean', async () => {
    store.dispatch(setSearchFormParams(oneWayParams));
    renderWithoutQuery();
    await waitFor(() => {
      const calls = mockNavigate.mock.calls as [string, unknown][];
      expect(calls.some(([url]) => typeof url === 'string' && url.includes('/flights/search?q='))).toBe(true);
    });
  });

  it('navigates to ?q= on mount for complete round-trip params', async () => {
    store.dispatch(setSearchFormParams(roundTripParams));
    renderWithoutQuery();
    await waitFor(() => {
      const calls = mockNavigate.mock.calls as [string, unknown][];
      expect(calls.some(([url]) => typeof url === 'string' && url.includes('/flights/search?q='))).toBe(true);
    });
  });

  it('navigates to ?q= on mount for complete multi-city params', async () => {
    store.dispatch(setSearchFormParams(multiCityParams));
    renderWithoutQuery();
    await waitFor(() => {
      const calls = mockNavigate.mock.calls as [string, unknown][];
      expect(calls.some(([url]) => typeof url === 'string' && url.includes('/flights/search?q='))).toBe(true);
    });
  });

  it('does NOT auto-search when URL already contains ?q=', async () => {
    store.dispatch(setSearchFormParams(oneWayParams));
    render(
      <ThemeProvider theme={lightTheme}>
        <MantineProvider>
        <Provider store={store}>
          <MemoryRouter initialEntries={['/flights/search?q=somevalue']}>
            <Routes>
              <Route path="/flights/search" element={<FlightSearchPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
        </MantineProvider>
      </ThemeProvider>,
    );
    // Effects settle — auto-search guard (encodedParams truthy) should have returned early
    await waitFor(() => {});
    const autoSearchCalls = (mockNavigate.mock.calls as [string, unknown][]).filter(
      ([url]) => typeof url === 'string' && url.includes('/flights/search?q='),
    );
    expect(autoSearchCalls).toHaveLength(0);
  });

  it('does NOT auto-search when origin is missing', async () => {
    store.dispatch(setSearchFormParams({ ...oneWayParams, from: '' }));
    renderWithoutQuery();
    await waitFor(() => {});
    const autoSearchCalls = (mockNavigate.mock.calls as [string, unknown][]).filter(
      ([url]) => typeof url === 'string' && url.includes('/flights/search?q='),
    );
    expect(autoSearchCalls).toHaveLength(0);
  });

  it('does NOT auto-search when destination is missing', async () => {
    store.dispatch(setSearchFormParams({ ...oneWayParams, to: '' }));
    renderWithoutQuery();
    await waitFor(() => {});
    const autoSearchCalls = (mockNavigate.mock.calls as [string, unknown][]).filter(
      ([url]) => typeof url === 'string' && url.includes('/flights/search?q='),
    );
    expect(autoSearchCalls).toHaveLength(0);
  });

  it('does NOT auto-search for round-trip when returnDate is missing', async () => {
    store.dispatch(setSearchFormParams({ ...roundTripParams, returnDate: null }));
    renderWithoutQuery();
    await waitFor(() => {});
    const autoSearchCalls = (mockNavigate.mock.calls as [string, unknown][]).filter(
      ([url]) => typeof url === 'string' && url.includes('/flights/search?q='),
    );
    expect(autoSearchCalls).toHaveLength(0);
  });

  it('does NOT auto-search for multi-city when fewer than 2 segments are present', async () => {
    store.dispatch(
      setSearchFormParams({
        ...multiCityParams,
        segments: [{ from: 'LHR', to: 'CDG', date: '2026-06-15T00:00:00.000Z' }],
      }),
    );
    renderWithoutQuery();
    await waitFor(() => {});
    const autoSearchCalls = (mockNavigate.mock.calls as [string, unknown][]).filter(
      ([url]) => typeof url === 'string' && url.includes('/flights/search?q='),
    );
    expect(autoSearchCalls).toHaveLength(0);
  });

  it('navigates exactly once for the same component instance (one-shot ref guard)', async () => {
    store.dispatch(setSearchFormParams(oneWayParams));
    const { rerender } = renderWithoutQuery();
    await waitFor(() => {
      const calls = mockNavigate.mock.calls as [string, unknown][];
      expect(calls.some(([url]) => typeof url === 'string' && url.includes('/flights/search?q='))).toBe(true);
    });
    const callCountAfterMount = mockNavigate.mock.calls.length;
    rerender(
      <ThemeProvider theme={lightTheme}>
        <MantineProvider>
        <Provider store={store}>
          <MemoryRouter initialEntries={['/flights/search']}>
            <Routes>
              <Route path="/flights/search" element={<FlightSearchPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
        </MantineProvider>
      </ThemeProvider>,
    );
    // mount-only effect does not re-fire on re-render; ref prevents a second call
    expect(mockNavigate.mock.calls).toHaveLength(callCountAfterMount);
  });
});
