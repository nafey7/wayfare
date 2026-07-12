import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { MantineProvider } from '@mantine/core';
import { store } from '@/store';

const mockUseGetItinerariesQuery = vi.fn();

vi.mock('@/api/itinerariesApi', () => ({
  useGetItinerariesQuery: () => mockUseGetItinerariesQuery(),
  useDeleteItineraryMutation: () => [vi.fn(), { isLoading: false }],
}));

vi.mock('@/utils/toast', () => ({
  showSuccessToast: vi.fn(),
  showErrorToast: vi.fn(),
}));

import { ItinerariesListPage } from './ItinerariesListPage';

const baseItinerary = {
  id: '507f1f77bcf86cd799439022', // pragma: allowlist secret
  structuredItinerary: { itineraryItems: [{ day: 1, title: 'Day 1' }] },
  tripMeta: { destination: 'Paris', origin: 'LHR' },
  createdAt: '2026-01-01T00:00:00.000Z',
};

describe('ItinerariesListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders itinerary summary without booking chips', () => {
    mockUseGetItinerariesQuery.mockReturnValue({
      data: [
        {
          ...baseItinerary,
          linkedBookings: {
            flightVoyaReferences: ['VOYA-F1'],
            hotelVoyaReferences: [],
          },
        },
      ],
      isLoading: false,
      error: undefined,
    });

    render(
      <MantineProvider env="test">
        <Provider store={store}>
          <MemoryRouter>
            <ItinerariesListPage />
          </MemoryRouter>
        </Provider>
      </MantineProvider>,
    );

    expect(screen.getByText('Paris')).toBeInTheDocument();
    expect(
      screen.queryByRole('group', { name: 'Bookings linked to this itinerary' }),
    ).not.toBeInTheDocument();
  });
});
