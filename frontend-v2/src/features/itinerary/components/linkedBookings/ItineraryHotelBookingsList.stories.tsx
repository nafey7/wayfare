import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { fn, expect, within } from 'storybook/test';
import { ItineraryHotelBookingsList } from './ItineraryHotelBookingsList';

const meta: Meta<typeof ItineraryHotelBookingsList> = {
  title: 'Itinerary/linkedBookings/ItineraryHotelBookingsList',
  component: ItineraryHotelBookingsList,
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
type Story = StoryObj<typeof ItineraryHotelBookingsList>;

/** Confirmed hotel booking with confirmation number, dates, amount. */
export const Default: Story = {
  args: {
    items: [
      {
        voyaReference: 'VOYA-HOT-9XK1',
        event: {
          voyaBookingReference: 'VOYA-HOT-9XK1',
          eventType: 'HOTEL',
          timestamp: '2026-04-21T12:34:56.000Z',
          dateBooked: '2026-04-21',
          ticketStatus: 'Confirmed',
          hotelReferenceNumber: 'HX-998877',
          amount: 412.5,
        },
      },
    ],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('VOYA-HOT-9XK1')).toBeInTheDocument();
    expect(canvas.getByText('Confirmed')).toBeInTheDocument();
    expect(canvas.getByText(/Confirmation · HX-998877/)).toBeInTheDocument();
  },
};

/** Empty state. */
export const Empty: Story = {
  args: { items: [] },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/No hotel bookings/i)).toBeInTheDocument();
  },
};

/** Loading state. */
export const Loading: Story = {
  args: { items: [], isLoading: true },
};
