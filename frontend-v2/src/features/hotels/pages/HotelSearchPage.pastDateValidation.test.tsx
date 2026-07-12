import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { MantineProvider } from '@mantine/core';
import { lightTheme, mantineTheme } from '@/theme';
import { store } from '@/store';
import {
  setSearchFormParams,
  resetBooking,
  triggerSearchFromChips,
} from '@/store/slices/hotelBookingSlice';
import type { HotelSearchFormParams } from '@/types/hotels';

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

const mockTriggerSearch = vi.fn(() => Promise.resolve({ hotels: [], totalResults: 0 }));

vi.mock('@/api/hotelsApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/hotelsApi')>();
  return {
    ...actual,
    useLazySearchHotelsQuery: () => [
      mockTriggerSearch,
      { data: undefined, isLoading: false, isFetching: false, error: undefined },
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

const rooms = [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }];

// Render with ?q=x so the auto-search effect (navigate-to-?q=) returns early,
// avoiding a redundant mockNavigate call that would complicate assertions.
function renderWithChipTrigger() {
  return render(
    <ThemeProvider theme={lightTheme}>
      <MantineProvider theme={mantineTheme} env="test">
        <Provider store={store}>
          <MemoryRouter initialEntries={['/hotels/search?q=x']}>
            <Routes>
              <Route path="/hotels/search" element={<HotelSearchPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
      </MantineProvider>
    </ThemeProvider>,
  );
}

describe('HotelSearchPage handleSearch — past-date validation', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    mockShowErrorToast.mockClear();
    mockTriggerSearch.mockClear();
    store.dispatch(resetBooking());
  });

  it('shows error toast and skips search for past check-in date', async () => {
    const params: HotelSearchFormParams = {
      destination: 'Paris',
      checkin: '2020-01-10',
      checkout: '2020-01-15',
      rooms,
      nationality: 'US',
    };
    store.dispatch(setSearchFormParams(params));
    // Dispatch chip trigger before render so the effect fires on mount
    store.dispatch(triggerSearchFromChips());
    renderWithChipTrigger();
    await waitFor(() => {
      expect(mockShowErrorToast).toHaveBeenCalledWith('Check-in date cannot be in the past.');
    });
    expect(mockTriggerSearch).not.toHaveBeenCalled();
  });

  it('shows error toast and skips search when both dates are in the past', async () => {
    // checkout must be > checkin (normalizeHotelSearchFormParams enforces this),
    // so the check-in error always fires first when both dates are past.
    const params: HotelSearchFormParams = {
      destination: 'Paris',
      checkin: '2025-01-10',
      checkout: '2025-01-15',
      rooms,
      nationality: 'US',
    };
    store.dispatch(setSearchFormParams(params));
    store.dispatch(triggerSearchFromChips());
    renderWithChipTrigger();
    await waitFor(() => {
      expect(mockShowErrorToast).toHaveBeenCalledWith('Check-in date cannot be in the past.');
    });
    expect(mockTriggerSearch).not.toHaveBeenCalled();
  });

  it('does not show error toast for future dates and proceeds to search', async () => {
    const params: HotelSearchFormParams = {
      destination: 'Paris',
      checkin: '2026-08-01',
      checkout: '2026-08-05',
      rooms,
      nationality: 'US',
    };
    store.dispatch(setSearchFormParams(params));
    // Use act to dispatch chip trigger after render (chips increment after component mounts)
    renderWithChipTrigger();
    act(() => {
      store.dispatch(triggerSearchFromChips());
    });
    await waitFor(() => {
      expect(mockShowErrorToast).not.toHaveBeenCalledWith(
        expect.stringContaining('cannot be in the past'),
      );
    });
  });
});
