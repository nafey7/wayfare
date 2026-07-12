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
const { mockShowErrorToast } = vi.hoisted(() => ({ mockShowErrorToast: vi.fn() }));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('@/utils/toast', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/utils/toast')>();
  return { ...actual, showErrorToast: mockShowErrorToast };
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
          initiate: vi.fn(() => ({ type: 'mock/flights/search' })),
          select: vi.fn(() => () => ({ status: 'uninitialized', data: undefined })),
        },
      },
    },
    useSearchFlightsQuery: () => ({
      data: { sessionId: 'test', fareItineraries: [] },
      isLoading: false,
      isFetching: false,
      error: undefined,
      refetch: vi.fn(),
    }),
    useSearchAirportsQuery: () => ({ data: [], isFetching: false }),
    useRevalidateFlightMutation: () => [vi.fn(), { isLoading: false }],
    useLazyResolveAirportQuery: () => [
      vi.fn(() => ({ unwrap: vi.fn().mockResolvedValue({ iataCode: 'LHR' }) })),
      { isLoading: false, isFetching: false },
    ],
  };
});

vi.mock('@/features/chat/hooks/usePublicChatConversionGate', () => ({
  usePublicChatConversionGate: () => ({ ensureAuthenticated: () => true }),
}));

import { FlightSearchPage } from './FlightSearchPage';

const travellers = { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' as const };

function renderPage() {
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

describe('FlightSearchPage handleSearch — past-date validation', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    mockShowErrorToast.mockClear();
    store.dispatch(resetBooking());
  });

  it('shows error toast and skips search for one-way with past departure date', async () => {
    const params: FlightSearchFormParams = {
      tripType: 'one-way',
      from: 'LHR',
      to: 'CDG',
      date: '2020-01-01T00:00:00.000Z',
      returnDate: null,
      travellers,
    };
    store.dispatch(setSearchFormParams(params));
    renderPage();
    await waitFor(() => {
      expect(mockShowErrorToast).toHaveBeenCalledWith('Departure date cannot be in the past.');
    });
    const searchCalls = mockNavigate.mock.calls.filter(
      (args) => typeof args[0] === 'string' && (args[0] as string).includes('/flights/search?q='),
    );
    expect(searchCalls).toHaveLength(0);
  });

  it('shows error toast and skips search for round-trip with past departure date', async () => {
    const params: FlightSearchFormParams = {
      tripType: 'round-trip',
      from: 'LHR',
      to: 'CDG',
      date: '2020-01-01T00:00:00.000Z',
      returnDate: '2026-08-10T00:00:00.000Z',
      travellers,
    };
    store.dispatch(setSearchFormParams(params));
    renderPage();
    await waitFor(() => {
      expect(mockShowErrorToast).toHaveBeenCalledWith('Departure date cannot be in the past.');
    });
    const searchCalls = mockNavigate.mock.calls.filter(
      (args) => typeof args[0] === 'string' && (args[0] as string).includes('/flights/search?q='),
    );
    expect(searchCalls).toHaveLength(0);
  });

  it('shows error toast and skips search for round-trip with past return date', async () => {
    const params: FlightSearchFormParams = {
      tripType: 'round-trip',
      from: 'LHR',
      to: 'CDG',
      date: '2026-08-01T00:00:00.000Z',
      returnDate: '2020-01-10T00:00:00.000Z',
      travellers,
    };
    store.dispatch(setSearchFormParams(params));
    renderPage();
    await waitFor(() => {
      expect(mockShowErrorToast).toHaveBeenCalledWith('Return date cannot be in the past.');
    });
    const searchCalls = mockNavigate.mock.calls.filter(
      (args) => typeof args[0] === 'string' && (args[0] as string).includes('/flights/search?q='),
    );
    expect(searchCalls).toHaveLength(0);
  });

  it('shows error toast and skips search for multi-city with a past segment date', async () => {
    const params: FlightSearchFormParams = {
      tripType: 'multi-city',
      from: '',
      to: '',
      date: null,
      returnDate: null,
      travellers,
      segments: [
        { from: 'LHR', to: 'CDG', date: '2020-01-01T00:00:00.000Z' },
        { from: 'CDG', to: 'AMS', date: '2026-08-10T00:00:00.000Z' },
      ],
    };
    store.dispatch(setSearchFormParams(params));
    renderPage();
    await waitFor(() => {
      expect(mockShowErrorToast).toHaveBeenCalledWith(
        'Leg 1: departure date cannot be in the past.',
      );
    });
    const searchCalls = mockNavigate.mock.calls.filter(
      (args) => typeof args[0] === 'string' && (args[0] as string).includes('/flights/search?q='),
    );
    expect(searchCalls).toHaveLength(0);
  });
});
