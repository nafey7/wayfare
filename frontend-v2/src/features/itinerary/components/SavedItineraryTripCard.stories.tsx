import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { expect, fn, within } from 'storybook/test';
import { SavedItineraryTripCard } from './SavedItineraryTripCard';
import type { SavedItineraryCardSummary } from '@/features/itinerary/utils/savedItineraryCardSummary';

const baseTrip: SavedItineraryCardSummary = {
  id: 'trip-001',
  destinationLabel: 'Barcelona',
  origin: 'Amsterdam',
  heroImageUrl: null,
  dateRangeLabel: 'May 10, 2026 – May 17, 2026',
  nightsLabel: '7 nights',
  passengersLabel: '2 adults',
  dayCount: 7,
  preview: 'Arrival in Barcelona, Sagrada Família visit',
  hasLinkedBookings: false,
  linkedBookings: null,
};

const meta: Meta<typeof SavedItineraryTripCard> = {
  title: 'Itinerary/SavedItineraryTripCard',
  component: SavedItineraryTripCard,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <Box style={{ maxWidth: 480 }}>
        <Story />
      </Box>
    ),
  ],
  args: {
    onView: fn(),
    onDelete: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof SavedItineraryTripCard>;

/** Confirmed trip — has linked bookings, Confirmed status chip. */
export const Default: Story = {
  args: {
    trip: { ...baseTrip, hasLinkedBookings: true },
    layout: 'grid',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Barcelona')).toBeInTheDocument();
    expect(canvas.getByText('7 nights')).toBeInTheDocument();
    expect(canvas.getByText('Confirmed')).toBeInTheDocument();
  },
};

/** Pending trip — no linked bookings, Pending status chip. */
export const Pending: Story = {
  args: {
    trip: { ...baseTrip, hasLinkedBookings: false },
    layout: 'grid',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Barcelona')).toBeInTheDocument();
    expect(canvas.getByText('Pending')).toBeInTheDocument();
  },
};

/** Past trip with different date range and destination. */
export const Past: Story = {
  args: {
    trip: {
      ...baseTrip,
      id: 'trip-002',
      destinationLabel: 'Tokyo',
      origin: 'London',
      dateRangeLabel: 'Jan 5, 2026 – Jan 15, 2026',
      nightsLabel: '10 nights',
      passengersLabel: '1 adult',
      hasLinkedBookings: true,
    },
    layout: 'grid',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Tokyo')).toBeInTheDocument();
    expect(canvas.getByText('10 nights')).toBeInTheDocument();
  },
};

/** Carousel layout as used in the profile upcoming-trips strip. */
export const CarouselLayout: Story = {
  args: {
    trip: { ...baseTrip, hasLinkedBookings: false },
    layout: 'carousel',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Barcelona')).toBeInTheDocument();
  },
};
