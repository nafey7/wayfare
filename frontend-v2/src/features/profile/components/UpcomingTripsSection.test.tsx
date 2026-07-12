import '@testing-library/jest-dom/vitest';

import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { MantineProvider } from '@mantine/core';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import type { SavedItineraryCardSummary } from '@/features/itinerary/utils/savedItineraryCardSummary';
import type { LinkedBookings } from '@/types/itineraries';

import { UpcomingTripsSection } from './_wip/UpcomingTripsSection';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('@/features/itinerary/components/AuthenticatedImage', () => ({
  AuthenticatedImage: ({
    src,
    fallback,
  }: {
    src?: string;
    fallback?: ReactNode;
  }) => (src ? <div data-testid="authenticated-image">{src}</div> : <>{fallback}</>),
}));

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <MantineProvider env="test">
      <MemoryRouter>{ui}</MemoryRouter>
    </MantineProvider>,
  );
}

const baseTrip: SavedItineraryCardSummary = {
  id: '507f1f77bcf86cd799439011', // pragma: allowlist secret
  destinationLabel: 'Paris',
  origin: 'NYC',
  heroImageUrl: null,
  dateRangeLabel: 'Jan 1, 2026 – Jan 5, 2026',
  nightsLabel: '4 nights',
  passengersLabel: '2 adults',
  dayCount: 5,
  preview: 'Arrival',
  hasLinkedBookings: false,
  linkedBookings: null,
};

const flightLinkedBookings: LinkedBookings = {
  flightVoyaReferences: ['VOYA-FL01'],
  hotelVoyaReferences: [],
  flightEvents: [
    {
      voyaBookingReference: 'VOYA-FL01',
      eventType: 'FLIGHT',
      timestamp: '2026-01-01T00:00:00Z',
      flightTripType: 'one_way',
      routeLegs: [{ legIndex: 0, departureIata: 'JFK', arrivalIata: 'LHR', segmentCount: 0, segments: [] }],
    },
  ],
};

const hotelLinkedBookings: LinkedBookings = {
  flightVoyaReferences: [],
  hotelVoyaReferences: ['VOYA-HT01'],
  hotelEvents: [
    {
      voyaBookingReference: 'VOYA-HT01',
      eventType: 'HOTEL',
      timestamp: '2026-01-02T00:00:00Z',
      hotelReferenceNumber: 'HILTON-99',
    },
  ],
};

const multipleLinkedBookings: LinkedBookings = {
  flightVoyaReferences: ['VOYA-FL01', 'VOYA-FL02'],
  hotelVoyaReferences: ['VOYA-HT01'],
  flightEvents: [
    {
      voyaBookingReference: 'VOYA-FL01',
      eventType: 'FLIGHT',
      timestamp: '2026-01-01T00:00:00Z',
      flightTripType: 'round_trip',
      routeLegs: [
        { legIndex: 0, departureIata: 'JFK', arrivalIata: 'LHR', segmentCount: 0, segments: [] },
        { legIndex: 1, departureIata: 'LHR', arrivalIata: 'JFK', segmentCount: 0, segments: [] },
      ],
    },
    {
      voyaBookingReference: 'VOYA-FL02',
      eventType: 'FLIGHT',
      timestamp: '2026-01-03T00:00:00Z',
      flightTripType: 'one_way',
      routeLegs: [{ legIndex: 0, departureIata: 'LHR', arrivalIata: 'CDG', segmentCount: 0, segments: [] }],
    },
  ],
};

describe('UpcomingTripsSection', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('renders the section heading and trip card when trips exist', () => {
    renderWithProviders(<UpcomingTripsSection trips={[baseTrip]} />);

    expect(screen.getByText('Trips')).toBeInTheDocument();
    expect(screen.getByText('Paris')).toBeInTheDocument();
    expect(screen.getByText('Jan 1, 2026 – Jan 5, 2026')).toBeInTheDocument();
  });

  it('passes hero URL to AuthenticatedImage when present', () => {
    const trip: SavedItineraryCardSummary = {
      ...baseTrip,
      heroImageUrl: '/api/places/photos/x/media',
    };
    renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

    expect(screen.getByTestId('authenticated-image')).toHaveTextContent('/api/places/photos/x/media');
  });

  it('shows Planned status when trip has no linked bookings', () => {
    renderWithProviders(<UpcomingTripsSection trips={[{ ...baseTrip, hasLinkedBookings: false }]} />);

    expect(screen.getByText('Planned')).toBeInTheDocument();
    expect(screen.queryByText('Confirmed')).not.toBeInTheDocument();
  });

  it('shows Confirmed status when trip has linked bookings', () => {
    renderWithProviders(<UpcomingTripsSection trips={[{ ...baseTrip, hasLinkedBookings: true }]} />);

    expect(screen.getByText('Confirmed')).toBeInTheDocument();
    expect(screen.queryByText('Planned')).not.toBeInTheDocument();
  });

  describe('bookings toggle', () => {
    it('does not render a bookings toggle when hasLinkedBookings is false', () => {
      renderWithProviders(<UpcomingTripsSection trips={[baseTrip]} />);

      expect(screen.queryByText(/booking/i)).not.toBeInTheDocument();
    });

    it('renders "1 booking" toggle when trip has exactly one linked booking', () => {
      const trip: SavedItineraryCardSummary = {
        ...baseTrip,
        hasLinkedBookings: true,
        linkedBookings: flightLinkedBookings,
      };
      renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

      expect(screen.getByText('1 booking')).toBeInTheDocument();
    });

    it('renders "N bookings" toggle for multiple linked bookings', () => {
      const trip: SavedItineraryCardSummary = {
        ...baseTrip,
        hasLinkedBookings: true,
        linkedBookings: multipleLinkedBookings,
      };
      renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

      expect(screen.getByText('3 bookings')).toBeInTheDocument();
    });

    it('toggle starts with aria-expanded=false (panel collapsed)', () => {
      const trip: SavedItineraryCardSummary = {
        ...baseTrip,
        hasLinkedBookings: true,
        linkedBookings: flightLinkedBookings,
      };
      renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

      const toggle = screen.getByText('1 booking').closest('button');
      expect(toggle).toHaveAttribute('aria-expanded', 'false');
    });

    it('expands the panel and shows flight rows when toggle is clicked', async () => {
      const user = userEvent.setup();
      const trip: SavedItineraryCardSummary = {
        ...baseTrip,
        hasLinkedBookings: true,
        linkedBookings: flightLinkedBookings,
      };
      renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

      const toggle = screen.getByText('1 booking');
      await user.click(toggle);

      expect(screen.getByText('JFK → LHR')).toBeInTheDocument();
      expect(screen.getByText('VOYA-FL01')).toBeInTheDocument();
    });

    it('toggle has aria-expanded=true after click and aria-controls wired to panel id', async () => {
      const user = userEvent.setup();
      const trip: SavedItineraryCardSummary = {
        ...baseTrip,
        hasLinkedBookings: true,
        linkedBookings: flightLinkedBookings,
      };
      renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

      const toggle = screen.getByText('1 booking').closest('button')!;
      await user.click(toggle);

      expect(toggle).toHaveAttribute('aria-expanded', 'true');
      const panelId = toggle.getAttribute('aria-controls');
      expect(panelId).toBeTruthy();
      expect(document.getElementById(panelId!)).toBeInTheDocument();
      expect(screen.getByRole('region', { name: /linked bookings for paris/i })).toBeInTheDocument();
    });

    it('collapses the panel on second click', async () => {
      const user = userEvent.setup();
      const trip: SavedItineraryCardSummary = {
        ...baseTrip,
        hasLinkedBookings: true,
        linkedBookings: flightLinkedBookings,
      };
      renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

      const toggle = screen.getByText('1 booking');
      await user.click(toggle);
      await user.click(toggle);

      const toggleBtn = screen.getByText('1 booking').closest('button');
      expect(toggleBtn).toHaveAttribute('aria-expanded', 'false');
    });
  });

  describe('flight booking row navigation', () => {
    it('navigates to flightBookingDetail when a flight row is clicked', async () => {
      const user = userEvent.setup();
      const trip: SavedItineraryCardSummary = {
        ...baseTrip,
        hasLinkedBookings: true,
        linkedBookings: flightLinkedBookings,
      };
      renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

      await user.click(screen.getByText('1 booking'));
      await user.click(screen.getByLabelText('Open flight booking VOYA-FL01'));

      expect(mockNavigate).toHaveBeenCalledWith('/flights/bookings/VOYA-FL01');
    });

    it('shows round-trip route label (↔) for round-trip flights', async () => {
      const user = userEvent.setup();
      const trip: SavedItineraryCardSummary = {
        ...baseTrip,
        hasLinkedBookings: true,
        linkedBookings: multipleLinkedBookings,
      };
      renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

      await user.click(screen.getByText('3 bookings'));

      expect(screen.getByText('JFK ↔ LHR')).toBeInTheDocument();
      expect(screen.getByText('LHR → CDG')).toBeInTheDocument();
    });
  });

  describe('hotel booking row navigation', () => {
    it('navigates to hotelBookingDetail when a hotel row is clicked', async () => {
      const user = userEvent.setup();
      const trip: SavedItineraryCardSummary = {
        ...baseTrip,
        hasLinkedBookings: true,
        linkedBookings: hotelLinkedBookings,
      };
      renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

      await user.click(screen.getByText('1 booking'));
      await user.click(screen.getByLabelText('Open hotel booking VOYA-HT01'));

      expect(mockNavigate).toHaveBeenCalledWith('/hotels/bookings/VOYA-HT01');
    });

    it('shows hotel reference number in label when hotelReferenceNumber is present', async () => {
      const user = userEvent.setup();
      const trip: SavedItineraryCardSummary = {
        ...baseTrip,
        hasLinkedBookings: true,
        linkedBookings: hotelLinkedBookings,
      };
      renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

      await user.click(screen.getByText('1 booking'));

      expect(screen.getByText('Hotel · HILTON-99')).toBeInTheDocument();
    });

    it('shows fallback "Hotel Booking" label when hotelReferenceNumber is absent', async () => {
      const user = userEvent.setup();
      const bookings: LinkedBookings = {
        flightVoyaReferences: [],
        hotelVoyaReferences: ['VOYA-HT02'],
        hotelEvents: [
          {
            voyaBookingReference: 'VOYA-HT02',
            eventType: 'HOTEL',
            timestamp: '2026-01-02T00:00:00Z',
          },
        ],
      };
      const trip: SavedItineraryCardSummary = {
        ...baseTrip,
        hasLinkedBookings: true,
        linkedBookings: bookings,
      };
      renderWithProviders(<UpcomingTripsSection trips={[trip]} />);

      await user.click(screen.getByText('1 booking'));

      expect(screen.getByText('Hotel Booking')).toBeInTheDocument();
    });
  });
});
