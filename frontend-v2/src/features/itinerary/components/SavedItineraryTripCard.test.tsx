import '@testing-library/jest-dom/vitest';

import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MantineProvider } from '@mantine/core';

import type { SavedItineraryCardSummary } from '@/features/itinerary/utils/savedItineraryCardSummary';

import { SavedItineraryTripCard } from './SavedItineraryTripCard';

vi.mock('./AuthenticatedImage', () => ({
  AuthenticatedImage: ({
    src,
    fallback,
  }: {
    src?: string;
    fallback?: ReactNode;
  }) => (src ? <div data-testid="authenticated-image">{src}</div> : <>{fallback}</>),
}));

function renderWithProviders(ui: React.ReactElement) {
  return render(<MantineProvider env="test">{ui}</MantineProvider>);
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

describe('SavedItineraryTripCard', () => {
  it('renders Pending on the hero when hasLinkedBookings is false', () => {
    renderWithProviders(<SavedItineraryTripCard trip={baseTrip} onView={vi.fn()} />);

    expect(screen.getByText('Pending')).toBeInTheDocument();
    expect(screen.queryByText('Confirmed')).not.toBeInTheDocument();
  });

  it('renders Confirmed on the hero when hasLinkedBookings is true', () => {
    renderWithProviders(
      <SavedItineraryTripCard trip={{ ...baseTrip, hasLinkedBookings: true }} onView={vi.fn()} />,
    );

    expect(screen.getByText('Confirmed')).toBeInTheDocument();
    expect(screen.queryByText('Pending')).not.toBeInTheDocument();
  });
});
