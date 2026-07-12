import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { MantineProvider } from '@mantine/core';
import { lightTheme, mantineTheme } from '@/theme';
import { store } from '@/store';
import {
  setSearchFormParams,
  setCachedHotelResults,
  resetBooking,
} from '@/store/slices/hotelBookingSlice';
import type { HotelSearchFormParams, HotelSearchResponse, HotelSearchRequest } from '@/types/hotels';

const { mockNavigate, mockTriggerSearch, mockResolveCity } = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
  mockTriggerSearch: vi.fn(),
  mockResolveCity: vi.fn(),
}));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('@mui/icons-material', () => {
  const Stub = () => null;
  return {
    Close: Stub, List: Stub, Map: Stub, FilterList: Stub, SwapVert: Stub,
    CalendarToday: Stub, Place: Stub, Search: Stub, People: Stub,
    KeyboardArrowDown: Stub, Star: Stub, AttachMoney: Stub, EmojiEvents: Stub, ExpandMore: Stub,
  };
});

vi.mock('@mui/x-date-pickers/DatePicker', () => ({ DatePicker: () => null }));

vi.mock('@mui/material', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@mui/material')>();
  return { ...actual, useMediaQuery: () => false };
});

const mockSearchResponse: HotelSearchResponse = {
  sessionId: 'test-session',
  hotels: [],
  totalResults: 0,
  nextToken: undefined,
  searchParams: {} as HotelSearchRequest,
};

vi.mock('@/api/hotelsApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/hotelsApi')>();
  return {
    ...actual,
    useLazySearchHotelsQuery: () => [
      mockTriggerSearch,
      { data: mockSearchResponse, isLoading: false, isFetching: false, error: undefined },
    ],
    useGetMoreResultsMutation: () => [vi.fn(), { isLoading: false }],
    useGetRoomRatesMutation: () => [vi.fn()],
  };
});

vi.mock('@/api/geocodingApi', () => ({
  useLazyResolveCityQuery: () => [mockResolveCity, { isLoading: false, isFetching: false }],
}));

vi.mock('@/features/chat/hooks/usePublicChatConversionGate', () => ({
  usePublicChatConversionGate: () => ({ ensureAuthenticated: () => true }),
}));

import { HotelSearchPage } from './HotelSearchPage';

const completeParams: HotelSearchFormParams = {
  destination: 'Paris',
  checkin: '2026-06-15',
  checkout: '2026-06-16',
  rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
  nationality: 'US',
};

function renderWithoutQuery() {
  return render(
    <ThemeProvider theme={lightTheme}>
      <MantineProvider theme={mantineTheme} env="test">
        <Provider store={store}>
          <MemoryRouter initialEntries={['/hotels/search']}>
            <Routes>
              <Route path="/hotels/search" element={<HotelSearchPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
      </MantineProvider>
    </ThemeProvider>,
  );
}

describe('HotelSearchPage auto-search mount-effect guards', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    mockTriggerSearch.mockClear();
    mockResolveCity.mockClear().mockReturnValue({
      unwrap: async () => ({
        city: 'Paris',
        country: 'France',
        country_code: 'FR',
        formatted_address: 'Paris, France',
        lat: 48.8566,
        lng: 2.3522,
      }),
    });
    store.dispatch(resetBooking());
  });

  it('navigates to ?q= on mount when Redux has complete params and URL is clean', async () => {
    store.dispatch(setSearchFormParams(completeParams));
    renderWithoutQuery();
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledOnce();
    });
    const [url, opts] = mockNavigate.mock.calls[0] as [string, unknown];
    expect(url).toMatch(/\/hotels\/search\?q=/);
    expect(opts).toEqual({ replace: true });
  });

  it('does NOT auto-navigate when URL already contains ?q=', async () => {
    store.dispatch(setSearchFormParams(completeParams));
    render(
      <ThemeProvider theme={lightTheme}>
        <MantineProvider theme={mantineTheme} env="test">
          <Provider store={store}>
            <MemoryRouter initialEntries={['/hotels/search?q=somevalue']}>
              <Routes>
                <Route path="/hotels/search" element={<HotelSearchPage />} />
              </Routes>
            </MemoryRouter>
          </Provider>
        </MantineProvider>
      </ThemeProvider>,
    );
    // Effects settle — auto-search guard should have fired and returned early
    await waitFor(() => {});
    const autoSearchCalls = (mockNavigate.mock.calls as [string, unknown][]).filter(
      ([url]) => typeof url === 'string' && url.includes('/hotels/search?q='),
    );
    expect(autoSearchCalls).toHaveLength(0);
  });

  it('does NOT auto-navigate when destination is empty', async () => {
    store.dispatch(setSearchFormParams({ ...completeParams, destination: '' }));
    renderWithoutQuery();
    await waitFor(() => {});
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('does NOT auto-navigate when checkin is null', async () => {
    store.dispatch(setSearchFormParams({ ...completeParams, checkin: null }));
    renderWithoutQuery();
    await waitFor(() => {});
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('does NOT auto-navigate when checkout is null', async () => {
    store.dispatch(setSearchFormParams({ ...completeParams, checkout: null }));
    renderWithoutQuery();
    await waitFor(() => {});
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('does NOT auto-navigate on cache hit (chat-hydrated results match Redux params)', async () => {
    // Simulate the chat → /hotels/search flow: cache is hydrated with results that
    // match the Redux searchFormParams. Mount-effect should render cached results
    // directly without touching the URL or firing resolveCity / triggerSearch.
    store.dispatch(setSearchFormParams(completeParams));
    store.dispatch(
      setCachedHotelResults({ data: mockSearchResponse, params: completeParams })
    );
    renderWithoutQuery();
    await waitFor(() => {});
    const autoSearchCalls = (mockNavigate.mock.calls as [string, unknown][]).filter(
      ([url]) => typeof url === 'string' && url.includes('/hotels/search?q='),
    );
    expect(autoSearchCalls).toHaveLength(0);
    expect(mockTriggerSearch).not.toHaveBeenCalled();
    expect(mockResolveCity).not.toHaveBeenCalled();
  });

  it('navigates exactly once for the same component instance (one-shot ref guard)', async () => {
    store.dispatch(setSearchFormParams(completeParams));
    const { rerender } = renderWithoutQuery();
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledOnce();
    });
    rerender(
      <ThemeProvider theme={lightTheme}>
        <MantineProvider theme={mantineTheme} env="test">
          <Provider store={store}>
            <MemoryRouter initialEntries={['/hotels/search']}>
              <Routes>
                <Route path="/hotels/search" element={<HotelSearchPage />} />
              </Routes>
            </MemoryRouter>
          </Provider>
        </MantineProvider>
      </ThemeProvider>,
    );
    // mount-only effect does not re-fire on re-render; ref prevents a second call
    expect(mockNavigate).toHaveBeenCalledOnce();
  });
});
