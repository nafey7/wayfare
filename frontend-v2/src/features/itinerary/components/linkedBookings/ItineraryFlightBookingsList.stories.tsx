import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { fn, expect, within } from 'storybook/test';
import { ItineraryFlightBookingsList } from './ItineraryFlightBookingsList';

const meta: Meta<typeof ItineraryFlightBookingsList> = {
  title: 'Itinerary/linkedBookings/ItineraryFlightBookingsList',
  component: ItineraryFlightBookingsList,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <Box style={{ maxWidth: 640 }}>
        <Story />
      </Box>
    ),
  ],
  args: { itineraryId: 'it-1', onSelectReference: fn() },
};

export default meta;
type Story = StoryObj<typeof ItineraryFlightBookingsList>;

/** Round trip with airline + dates + amount. */
export const RoundTrip: Story = {
  args: {
    items: [
      {
        voyaReference: 'VOYA-AB12CD',
        event: {
          voyaBookingReference: 'VOYA-AB12CD',
          eventType: 'FLIGHT',
          timestamp: '2026-04-21T10:00:00.000Z',
          dateBooked: '2026-04-21',
          flightTripType: 'round_trip',
          ticketStatus: 'Issued',
          airlinePnrCode: 'PNR123',
          primaryMarketingAirlineName: 'British Airways',
          amount: 643.21,
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
        },
      },
    ],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('VOYA-AB12CD')).toBeInTheDocument();
    expect(canvas.getByText('British Airways')).toBeInTheDocument();
    expect(canvas.getByText('JFK ⇆ LHR')).toBeInTheDocument();
  },
};

/** Empty state. */
export const Empty: Story = {
  args: { items: [] },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/No flight bookings/i)).toBeInTheDocument();
  },
};

/** Loading state. */
export const Loading: Story = {
  args: { items: [], isLoading: true },
};
