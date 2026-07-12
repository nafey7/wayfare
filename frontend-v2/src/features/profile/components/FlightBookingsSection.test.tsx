import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { FlightBookingsSection } from './FlightBookingsSection';

const hoisted = vi.hoisted(() => ({
  data: undefined as unknown[] | undefined,
  isLoading: false,
  isError: false,
}));

vi.mock('@/api/flightsApi', () => ({
  useGetMyBookingsQuery: () => ({
    data: hoisted.data,
    isLoading: hoisted.isLoading,
    isError: hoisted.isError,
    refetch: vi.fn(),
  }),
}));

function renderWithStore(ui: ReactElement) {
  const store = configureStore({
    reducer: { _noop: () => null },
  });
  return render(
    <MantineProvider env="test">
      <Provider store={store}>
        <MemoryRouter>{ui}</MemoryRouter>
      </Provider>
    </MantineProvider>
  );
}

describe('FlightBookingsSection', () => {
  it('shows empty state when there are no bookings', () => {
    hoisted.data = [];
    hoisted.isLoading = false;
    hoisted.isError = false;
    renderWithStore(<FlightBookingsSection />);
    expect(screen.getByText(/No flight bookings yet/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open chat/i })).toHaveAttribute('href', '/chat');
  });

  it('exposes Get receipt link to flight booking details on the card', () => {
    hoisted.data = [
      {
        voyaBookingReference: 'VOYA-TEST99',
        action: 'BOOKED',
        timestamp: '2026-05-01T10:00:00.000Z',
        dateBooked: null,
        amount: 100,
        departureAirportIata: 'LHR',
        ticketStatus: null,
      },
    ];
    hoisted.isLoading = false;
    hoisted.isError = false;
    renderWithStore(<FlightBookingsSection />);
    const link = screen.getByRole('link', { name: /Get receipt/i });
    expect(link.getAttribute('href')).toContain('/flights/bookings/');
    expect(link.getAttribute('href')).toContain('VOYA-TEST99');
  });

  it('shows travel dates from flightLegSummaries when present', () => {
    hoisted.data = [
      {
        voyaBookingReference: 'VOYA-DATES',
        action: 'BOOKED',
        timestamp: '2026-05-01T10:00:00.000Z',
        dateBooked: '2026-05-01T10:00:00.000Z',
        amount: 50,
        departureAirportIata: 'LHR',
        ticketStatus: null,
        flightLegSummaries: [
          { departureDate: '2026-07-20', originIata: 'CDG', destinationIata: 'BCN' },
        ],
      },
    ];
    hoisted.isLoading = false;
    hoisted.isError = false;
    renderWithStore(<FlightBookingsSection />);
    expect(screen.getByText(/Jul 20, 2026/)).toBeInTheDocument();
  });
});
