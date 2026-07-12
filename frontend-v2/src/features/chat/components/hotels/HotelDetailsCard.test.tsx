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
import type { AuthCredentials } from '@/types/auth';
import type { MappedHotel } from '@/features/chat/utils/hotelUtils';
import { HotelDetailsCard } from './HotelDetailsCard';

const selectHotelTrigger = vi.fn();
const getRoomRatesTrigger = vi.fn();

vi.mock('@/api/hotelsApi', () => ({
  useSelectHotelMutation: () => [
    (...args: unknown[]) => {
      selectHotelTrigger(...args);
      return { unwrap: () => Promise.resolve({}) };
    },
    { isLoading: false },
  ],
  useGetRoomRatesMutation: () => [
    (...args: unknown[]) => {
      getRoomRatesTrigger(...args);
      return { unwrap: () => Promise.resolve({}) };
    },
    { isLoading: false },
  ],
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

function makeHotel(): MappedHotel {
  return {
    hotel_id: 'h1',
    token_id: 'tok1',
    product_id: 'prod1',
    hotel_name: 'Test Hotel',
    city: 'Paris',
    country: 'FR',
    address: '1 Rue',
    locality: 'Paris',
    hotel_rating: 4,
    trip_advisor_rating: null,
    trip_advisor_reviews: null,
    total_price: 200,
    per_night_price: 100,
    currency: 'EUR',
    fare_type: 'std',
    original_total_fare: null,
    platform_fee_percentage: null,
    facilities: [],
    property_type: 'hotel',
    thumbnail_url: null,
    distance_value: null,
    distance_unit: null,
  };
}

function TestWrapper({ children }: { children: ReactNode }) {
  return (
    <Provider store={store}>
      <MemoryRouter>
        <MantineProvider theme={mantineTheme}>{children}</MantineProvider>
      </MemoryRouter>
    </Provider>
  );
}

describe('HotelDetailsCard conversion gate', () => {
  beforeEach(() => {
    selectHotelTrigger.mockClear();
    getRoomRatesTrigger.mockClear();
    mockNavigate.mockClear();
    localStorage.removeItem('hotelSessionId');
    store.dispatch(clearAuth());
    store.dispatch(closeAuthModal());
  });

  it('does not call hotel booking APIs when guest clicks Book Now', async () => {
    localStorage.setItem('hotelSessionId', 'sess-h');
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <HotelDetailsCard hotel={makeHotel()} />
      </TestWrapper>
    );
    await user.click(screen.getByRole('button'));
    expect(store.getState().ui.authModalOpen).toBe(true);
    expect(selectHotelTrigger).not.toHaveBeenCalled();
    expect(getRoomRatesTrigger).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('calls select hotel and navigates when authenticated user clicks Book Now', async () => {
    localStorage.setItem('hotelSessionId', 'sess-h');
    store.dispatch(setCredentials(makeTestCredentials()));
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <HotelDetailsCard hotel={makeHotel()} />
      </TestWrapper>
    );
    await user.click(screen.getByRole('button'));
    expect(selectHotelTrigger).toHaveBeenCalled();
    expect(getRoomRatesTrigger).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/hotels/rooms/tok1');
  });
});
