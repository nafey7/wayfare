import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import {
  MemoryRouter,
  Route,
  Routes,
  RouterProvider,
  createMemoryRouter,
} from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { MantineProvider } from '@mantine/core';
import { lightTheme, mantineTheme } from '@/theme';
import { store } from '@/store';
import { ROUTES } from '@/features/routing';
import { serializeSearchParamsToUrl } from '../utils/urlParams';
import type { FlightSearchParamsUI } from '@/types/flights';
import { resetBooking } from '@/store/slices/flightBookingSlice';

vi.mock('@mui/icons-material', () => {
  const Stub = () => null;
  return {
    SwapHoriz: Stub,
    FlightTakeoff: Stub,
    FlightLand: Stub,
    CalendarToday: Stub,
    Add: Stub,
    Delete: Stub,
    Close: Stub,
    FilterList: Stub,
    SwapVert: Stub,
    ExpandMore: Stub,
    Flight: Stub,
    InfoOutlined: Stub,
  };
});

vi.mock('@mui/x-date-pickers/DatePicker', () => ({
  DatePicker: () => null,
}));

vi.mock('@mantine/hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@mantine/hooks')>();
  return {
    ...actual,
    useMediaQuery: () => true,
  };
});

vi.mock('@/api/flightsApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/flightsApi')>();
  const emptySearchResponse = {
    sessionId: 'test-session',
    fareItineraries: [],
  };
  return {
    ...actual,
    useSearchFlightsQuery: () => ({
      data: emptySearchResponse,
      isLoading: false,
      isFetching: false,
      error: undefined,
      refetch: vi.fn(),
    }),
    useLazySearchFlightsQuery: () => [
      vi.fn().mockResolvedValue({ data: emptySearchResponse }),
      { data: emptySearchResponse, isLoading: false, error: undefined },
    ],
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

function renderFlightSearchWithQuery(q: string) {
  return render(
    <ThemeProvider theme={lightTheme}>
      <MantineProvider theme={mantineTheme} env="test">
        <Provider store={store}>
          <MemoryRouter initialEntries={[`/flights/search?q=${encodeURIComponent(q)}`]}>
            <Routes>
              <Route path="/flights/search" element={<FlightSearchPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
      </MantineProvider>
    </ThemeProvider>,
  );
}

describe('FlightSearchPage (mobile filters)', () => {
  it('opens the filters dialog when Filters is tapped on a narrow viewport', async () => {
    const user = userEvent.setup();
    const params: FlightSearchParamsUI = {
      tripType: 'one-way',
      from: 'LHR',
      to: 'CDG',
      date: new Date('2026-06-15T12:00:00.000Z'),
      returnDate: null,
      travellers: {
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: 'Economy',
      },
    };
    const q = serializeSearchParamsToUrl(params);
    renderFlightSearchWithQuery(q);

    // Mobile toolbar renders first in DOM; desktop right-column also has a Filters button but
    // is hidden via CSS in a real browser. JSDOM doesn't apply media queries so both are present —
    // pick the first one (mobile toolbar always precedes the right column in source order).
    const filtersBtns = await waitFor(() => screen.getAllByRole('button', { name: /^filters$/i }));
    await user.click(filtersBtns[0]!);

    expect(await screen.findByRole('button', { name: /close filters/i })).toBeInTheDocument();
  });

  it('closes the filters dialog when Close filters is clicked', async () => {
    const user = userEvent.setup();
    const params: FlightSearchParamsUI = {
      tripType: 'one-way',
      from: 'LHR',
      to: 'CDG',
      date: new Date('2026-06-15T12:00:00.000Z'),
      returnDate: null,
      travellers: {
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: 'Economy',
      },
    };
    const q = serializeSearchParamsToUrl(params);
    renderFlightSearchWithQuery(q);

    const filtersBtns = await waitFor(() => screen.getAllByRole('button', { name: /^filters$/i }));
    await user.click(filtersBtns[0]!);

    const closeBtn = await screen.findByRole('button', { name: /close filters/i });
    await user.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /close filters/i })).not.toBeInTheDocument();
    });
  });

  it('keeps the selected mobile sort when reopening the sort menu', async () => {
    const user = userEvent.setup();
    const params: FlightSearchParamsUI = {
      tripType: 'one-way',
      from: 'LHR',
      to: 'CDG',
      date: new Date('2026-06-15T12:00:00.000Z'),
      returnDate: null,
      travellers: {
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: 'Economy',
      },
    };
    const q = serializeSearchParamsToUrl(params);
    renderFlightSearchWithQuery(q);

    await waitFor(() => screen.getByRole('button', { name: /^sort$/i }));

    await user.click(screen.getByRole('button', { name: /^sort$/i }));
    await user.click(
      await screen.findByRole('menuitem', { name: /price:\s*high to low/i }),
    );

    await user.click(screen.getByRole('button', { name: /^sort$/i }));
    const highToLow = await screen.findByRole('menuitem', { name: /price:\s*high to low/i });
    expect(highToLow.dataset.selected).toBe('true');
  });
});

describe('FlightSearchPage (?q= removal)', () => {
  it('resets to the pre-search empty state when ?q= is cleared', async () => {
    const params: FlightSearchParamsUI = {
      tripType: 'one-way',
      from: 'LHR',
      to: 'CDG',
      date: new Date('2026-06-15T12:00:00.000Z'),
      returnDate: null,
      travellers: {
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: 'Economy',
      },
    };
    const q = serializeSearchParamsToUrl(params);
    const router = createMemoryRouter(
      [
        {
          path: ROUTES.FLIGHTS_SEARCH,
          element: (
            <ThemeProvider theme={lightTheme}>
              <MantineProvider theme={mantineTheme} env="test">
                <Provider store={store}>
                  <FlightSearchPage />
                </Provider>
              </MantineProvider>
            </ThemeProvider>
          ),
        },
      ],
      { initialEntries: [`${ROUTES.FLIGHTS_SEARCH}?q=${encodeURIComponent(q)}`] },
    );
    render(<RouterProvider router={router} />);

    await waitFor(() => {
      expect(screen.getByText(/0 flights found/i)).toBeInTheDocument();
    });

    // The auto-search effect re-fires when ?q= drops (see PR #1121
    // chat-nav-sync), so clear Redux form params first to mimic a clean
    // landing on /flights/search and assert the pre-search empty state.
    store.dispatch(resetBooking());

    await router.navigate(ROUTES.FLIGHTS_SEARCH);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /^search flights$/i })).toBeInTheDocument();
    });
    expect(screen.queryByText(/flights found/i)).not.toBeInTheDocument();
  });
});
