import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box, Button } from '@mantine/core';
import { expect, within } from 'storybook/test';
import { BookingDetailsRefCard } from './BookingDetailsRefCard';

const meta: Meta<typeof BookingDetailsRefCard> = {
  title: 'Flights/Booking/BookingDetailsRefCard',
  component: BookingDetailsRefCard,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <Box style={{ maxWidth: 720 }}>
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof BookingDetailsRefCard>;

/** Confirmed booking — all four status rows + ticketed status, no action button. */
export const Ticketed: Story = {
  args: {
    voyaBookingReference: 'VOYA-AB12CD',
    externalBookingReference: 'PNR-XYZ789',
    bookingStatus: 'Confirmed',
    ticketStatus: 'Ticketed',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('VOYA-AB12CD')).toBeInTheDocument();
    expect(canvas.getByText('PNR-XYZ789')).toBeInTheDocument();
    expect(canvas.getByText('Confirmed')).toBeInTheDocument();
    expect(canvas.getByText('Ticketed')).toBeInTheDocument();
  },
};

/** Pending booking — Pay Now action slot rendered. */
export const PendingPayment: Story = {
  args: {
    voyaBookingReference: 'VOYA-PD56EF',
    bookingStatus: 'Pending',
    actions: (
      <Button variant="contained" color="primary">
        Pay now
      </Button>
    ),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('VOYA-PD56EF')).toBeInTheDocument();
    expect(canvas.getByText('Pending')).toBeInTheDocument();
    expect(canvas.getByRole('button', { name: /pay now/i })).toBeInTheDocument();
  },
};

/** Minimal — only the VOYA reference row. */
export const Minimal: Story = {
  args: {
    voyaBookingReference: 'VOYA-MN34PQ',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('VOYA-MN34PQ')).toBeInTheDocument();
    expect(canvas.queryByText(/external reference/i)).not.toBeInTheDocument();
    expect(canvas.queryByText(/booking status/i)).not.toBeInTheDocument();
  },
};
