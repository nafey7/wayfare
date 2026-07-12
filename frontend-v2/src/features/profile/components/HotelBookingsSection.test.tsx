import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { baseApi } from '@/api/baseApi';
import authReducer from '@/store/slices/authSlice';
import { HotelBookingsSection } from './HotelBookingsSection';

const hoisted = vi.hoisted(() => ({
  data: undefined as unknown[] | undefined,
  isLoading: false,
  isError: false,
}));

vi.mock('@/api/hotelsApi', () => ({
  useGetMyHotelBookingsQuery: () => ({
    data: hoisted.data,
    isLoading: hoisted.isLoading,
    isError: hoisted.isError,
    refetch: vi.fn(),
  }),
}));

function renderWithStore(ui: ReactElement) {
  const store = configureStore({
    reducer: {
      [baseApi.reducerPath]: baseApi.reducer,
      auth: authReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(baseApi.middleware),
  });
  return render(
    <MantineProvider env="test">
      <Provider store={store}>
        <MemoryRouter>{ui}</MemoryRouter>
      </Provider>
    </MantineProvider>
  );
}

describe('HotelBookingsSection', () => {
  it('shows empty state when there are no bookings', () => {
    hoisted.data = [];
    hoisted.isLoading = false;
    hoisted.isError = false;
    renderWithStore(<HotelBookingsSection />);
    expect(screen.getByText(/No hotel bookings yet/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open chat/i })).toHaveAttribute('href', '/chat');
  });

  it('exposes Get receipt link to hotel booking details on the card', () => {
    hoisted.data = [
      {
        voyaBookingReference: 'VOYA-HOTEL1',
        action: 'BOOKED',
        timestamp: '2026-05-01T10:00:00.000Z',
        dateBooked: null,
        amount: 250,
        hotelImageUrl: null,
        hotelName: 'Seaside Inn',
        hotelCity: 'Barcelona',
      },
    ];
    hoisted.isLoading = false;
    hoisted.isError = false;
    renderWithStore(<HotelBookingsSection />);
    expect(screen.getByText('Seaside Inn')).toBeInTheDocument();
    const link = screen.getByRole('link', { name: /Get receipt/i });
    expect(link.getAttribute('href')).toContain('/hotels/bookings/');
    expect(link.getAttribute('href')).toContain('VOYA-HOTEL1');
  });
});
