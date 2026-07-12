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
import { serializeHotelSearchParamsToUrl } from '../utils/urlParams';
import type { HotelSearchResponse, HotelSearchRequest } from '@/types/hotels';

vi.mock('@mui/icons-material', () => {
  const Stub = () => null;
  return {
    Close: Stub,
    List: Stub,
    Map: Stub,
    FilterList: Stub,
    SwapVert: Stub,
    CalendarToday: Stub,
    Place: Stub,
    Search: Stub,
    People: Stub,
    KeyboardArrowDown: Stub,
    Star: Stub,
    AttachMoney: Stub,
    EmojiEvents: Stub,
    ExpandMore: Stub,
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

const mockSearchParams: HotelSearchRequest = {
  checkin: '2026-06-15',
  checkout: '2026-06-16',
  cityName: 'Paris',
  countryName: 'France',
  nationality: 'US',
  occupancy: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
};

const mockSearchResponse: HotelSearchResponse = {
  sessionId: 'test-session',
  hotels: [],
  totalResults: 0,
  nextToken: undefined,
  searchParams: mockSearchParams,
};

vi.mock('@/api/hotelsApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/hotelsApi')>();
  const triggerSearch = vi.fn(() => Promise.resolve(mockSearchResponse));
  return {
    ...actual,
    useLazySearchHotelsQuery: () => [
      triggerSearch,
      {
        data: mockSearchResponse,
        isLoading: false,
        isFetching: false,
        error: undefined,
      },
    ],
    useGetMoreResultsMutation: () => [vi.fn(), { isLoading: false }],
    useGetRoomRatesMutation: () => [vi.fn()],
  };
});

vi.mock('@/api/geocodingApi', () => ({
  useLazyResolveCityQuery: () => [
    vi.fn().mockReturnValue({
      unwrap: async () => ({
        city: 'Paris',
        country: 'France',
        country_code: 'FR',
        formatted_address: 'Paris, France',
        lat: 48.8566,
        lng: 2.3522,
      }),
    }),
    { isLoading: false, isFetching: false },
  ],
}));

vi.mock('@/features/chat/hooks/usePublicChatConversionGate', () => ({
  usePublicChatConversionGate: () => ({ ensureAuthenticated: () => true }),
}));

import { HotelSearchPage } from './HotelSearchPage';

function renderHotelSearchWithQuery(q: string) {
  return render(
    <ThemeProvider theme={lightTheme}>
      <MantineProvider theme={mantineTheme} env="test">
        <Provider store={store}>
          <MemoryRouter initialEntries={[`/hotels/search?q=${encodeURIComponent(q)}`]}>
            <Routes>
              <Route path="/hotels/search" element={<HotelSearchPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
      </MantineProvider>
    </ThemeProvider>,
  );
}

describe('HotelSearchPage (mobile filters)', () => {
  it('opens the filters dialog when Filters is tapped on a narrow viewport', async () => {
    const user = userEvent.setup();
    const q = serializeHotelSearchParamsToUrl({
      destination: 'Paris',
      checkin: '2026-06-15',
      checkout: '2026-06-16',
      rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
      nationality: 'US',
    });
    renderHotelSearchWithQuery(q);

    const filtersBtn = await waitFor(() =>
      screen.getByRole('button', { name: /^filters$/i }),
    );
    await user.click(filtersBtn);

    expect(await screen.findByRole('button', { name: /show \d+ hotels?/i })).toBeInTheDocument();
  });

  it('closes the filters dialog when Show hotels is clicked', async () => {
    const user = userEvent.setup();
    const q = serializeHotelSearchParamsToUrl({
      destination: 'Paris',
      checkin: '2026-06-15',
      checkout: '2026-06-16',
      rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
      nationality: 'US',
    });
    renderHotelSearchWithQuery(q);

    const filtersBtn = await waitFor(() =>
      screen.getByRole('button', { name: /^filters$/i }),
    );
    await user.click(filtersBtn);

    const showBtn = await screen.findByRole('button', { name: /show \d+ hotels?/i });
    await user.click(showBtn);

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /show \d+ hotels?/i })).not.toBeInTheDocument();
    });
  });

});

describe('HotelSearchPage (?q= removal)', () => {
  it('resets to the pre-search empty state when ?q= is cleared', async () => {
    const q = serializeHotelSearchParamsToUrl({
      destination: 'Paris',
      checkin: '2026-06-15',
      checkout: '2026-06-16',
      rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
      nationality: 'US',
    });
    const router = createMemoryRouter(
      [
        {
          path: ROUTES.HOTELS_SEARCH,
          element: (
            <ThemeProvider theme={lightTheme}>
              <MantineProvider theme={mantineTheme} env="test">
                <Provider store={store}>
                  <HotelSearchPage />
                </Provider>
              </MantineProvider>
            </ThemeProvider>
          ),
        },
      ],
      { initialEntries: [`${ROUTES.HOTELS_SEARCH}?q=${encodeURIComponent(q)}`] },
    );
    render(<RouterProvider router={router} />);

    // Mobile view shows count as a plain div: "0 hotels found" (not a heading)
    await waitFor(() => {
      expect(screen.getByText(/^0 hotels found$/i)).toBeInTheDocument();
    });

    await router.navigate(ROUTES.HOTELS_SEARCH);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /^search hotels$/i })).toBeInTheDocument();
    });
    expect(screen.queryByText(/^0 hotels found$/i)).not.toBeInTheDocument();
  });
});
