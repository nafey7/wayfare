import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';

import { ItineraryFlightBookingsList } from './ItineraryFlightBookingsList';

function renderWithProviders(ui: React.ReactElement) {
  return render(<MantineProvider env="test">{ui}</MantineProvider>);
}

describe('ItineraryFlightBookingsList', () => {
  it('calls onSelectReference with the clicked ref', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    renderWithProviders(
      <ItineraryFlightBookingsList
        itineraryId="it-1"
        items={[
          { voyaReference: 'REF-A' },
          { voyaReference: 'REF-B', event: { voyaBookingReference: 'REF-B', eventType: 'FLIGHT', timestamp: '2026-01-01T00:00:00.000Z' } },
        ]}
        onSelectReference={onSelect}
      />,
    );

    await user.click(screen.getByRole('button', { name: /open flight booking REF-B/i }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith('REF-B');
  });

  it('shows loading state', () => {
    renderWithProviders(
      <ItineraryFlightBookingsList
        itineraryId="it-1"
        items={[]}
        onSelectReference={vi.fn()}
        isLoading
      />,
    );

    expect(screen.getByLabelText('Loading flight bookings')).toBeInTheDocument();
  });

  it('shows outbound route, return route, and airline without PNR (routeLegs)', () => {
    renderWithProviders(
      <ItineraryFlightBookingsList
        itineraryId="it-1"
        items={[
          {
            voyaReference: 'VOYA-X',
            event: {
              voyaBookingReference: 'VOYA-X',
              eventType: 'FLIGHT',
              timestamp: '2026-01-01T00:00:00.000Z',
              flightTripType: 'round_trip',
              routeLegs: [
                {
                  legIndex: 0,
                  departureIata: 'JFK',
                  arrivalIata: 'LHR',
                  segmentCount: 1,
                  segments: [{ departureIata: 'JFK', arrivalIata: 'LHR' }],
                },
                {
                  legIndex: 1,
                  departureIata: 'LHR',
                  arrivalIata: 'JFK',
                  segmentCount: 1,
                  segments: [{ departureIata: 'LHR', arrivalIata: 'JFK' }],
                },
              ],
              primaryMarketingAirlineName: 'British Airways',
            },
          },
        ]}
        onSelectReference={vi.fn()}
      />,
    );

    expect(screen.getByText('JFK ⇆ LHR')).toBeInTheDocument();
    expect(screen.queryByText(/Return ·/)).not.toBeInTheDocument();
    expect(screen.getByText('British Airways')).toBeInTheDocument();
  });

  it('falls back to legacy flat IATAs when routeLegs absent', () => {
    renderWithProviders(
      <ItineraryFlightBookingsList
        itineraryId="it-1"
        items={[
          {
            voyaReference: 'VOYA-LEG',
            event: {
              voyaBookingReference: 'VOYA-LEG',
              eventType: 'FLIGHT',
              timestamp: '2026-01-01T00:00:00.000Z',
              departureAirportIata: 'JFK',
              arrivalAirportIata: 'LHR',
              returnDepartureAirportIata: 'LHR',
              returnArrivalAirportIata: 'JFK',
              flightTripType: 'round_trip',
              primaryMarketingAirlineName: 'British Airways',
            },
          },
        ]}
        onSelectReference={vi.fn()}
      />,
    );

    expect(screen.getByText('JFK ⇆ LHR')).toBeInTheDocument();
    expect(screen.queryByText(/Return ·/)).not.toBeInTheDocument();
  });

  it('renders every route leg when more than two legs (multi-city)', () => {
    renderWithProviders(
      <ItineraryFlightBookingsList
        itineraryId="it-1"
        items={[
          {
            voyaReference: 'VOYA-MC',
            event: {
              voyaBookingReference: 'VOYA-MC',
              eventType: 'FLIGHT',
              timestamp: '2026-01-01T00:00:00.000Z',
              flightTripType: 'multi_city',
              routeLegs: [
                {
                  legIndex: 0,
                  departureIata: 'JFK',
                  arrivalIata: 'LHR',
                  segmentCount: 1,
                  segments: [{ departureIata: 'JFK', arrivalIata: 'LHR' }],
                },
                {
                  legIndex: 1,
                  departureIata: 'LHR',
                  arrivalIata: 'CDG',
                  segmentCount: 1,
                  segments: [{ departureIata: 'LHR', arrivalIata: 'CDG' }],
                },
                {
                  legIndex: 2,
                  departureIata: 'CDG',
                  arrivalIata: 'JFK',
                  segmentCount: 1,
                  segments: [{ departureIata: 'CDG', arrivalIata: 'JFK' }],
                },
              ],
            },
          },
        ]}
        onSelectReference={vi.fn()}
      />,
    );

    expect(screen.getByText(/Leg 1 · JFK → LHR/)).toBeInTheDocument();
    expect(screen.getByText(/Leg 2 · LHR → CDG/)).toBeInTheDocument();
    expect(screen.getByText(/Leg 3 · CDG → JFK/)).toBeInTheDocument();
  });
});
