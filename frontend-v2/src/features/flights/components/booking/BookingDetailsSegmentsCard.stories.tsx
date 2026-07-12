import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { expect, within } from 'storybook/test';
import { BookingDetailsSegmentsCard } from './BookingDetailsSegmentsCard';
import type { TripDetailsSegmentCamel } from '@/types/flightBackend';

const outboundSegment: TripDetailsSegmentCamel = {
  segmentId: 1,
  departureDatetime: '2026-07-15T10:30:00',
  arrivalDatetime: '2026-07-15T13:00:00',
  departureAirport: { iataCode: 'AMS', cityName: 'Amsterdam' },
  arrivalAirport: { iataCode: 'BCN', cityName: 'Barcelona' },
  marketingAirline: { iataCode: 'KL', airlineName: 'KLM' },
  marketingFlightNumber: { formattedNumber: 'KL1671' },
};

const returnSegment: TripDetailsSegmentCamel = {
  segmentId: 2,
  departureDatetime: '2026-07-22T18:00:00',
  arrivalDatetime: '2026-07-22T20:30:00',
  departureAirport: { iataCode: 'BCN', cityName: 'Barcelona' },
  arrivalAirport: { iataCode: 'AMS', cityName: 'Amsterdam' },
  marketingAirline: { iataCode: 'KL', airlineName: 'KLM' },
  marketingFlightNumber: { formattedNumber: 'KL1672' },
};

const meta: Meta<typeof BookingDetailsSegmentsCard> = {
  title: 'Flights/Booking/BookingDetailsSegmentsCard',
  component: BookingDetailsSegmentsCard,
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
type Story = StoryObj<typeof BookingDetailsSegmentsCard>;

/** One-way single segment, no bound labels. */
export const OneWay: Story = {
  args: {
    segments: [outboundSegment],
    segmentBoundLabels: null,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/AMS/)).toBeInTheDocument();
    expect(canvas.getByText(/BCN/)).toBeInTheDocument();
    expect(canvas.getByText(/KLM KL1671/)).toBeInTheDocument();
    expect(canvas.queryByText('OUTBOUND')).not.toBeInTheDocument();
  },
};

/** Round-trip with two segments + OUTBOUND/RETURN labels. */
export const RoundTrip: Story = {
  args: {
    segments: [outboundSegment, returnSegment],
    segmentBoundLabels: ['OUTBOUND', 'RETURN'],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('OUTBOUND')).toBeInTheDocument();
    expect(canvas.getByText('RETURN')).toBeInTheDocument();
    expect(canvas.getByText(/KL1671/)).toBeInTheDocument();
    expect(canvas.getByText(/KL1672/)).toBeInTheDocument();
  },
};

/** Three-segment connection (e.g. AMS-LHR-JFK) — no bound labels. */
export const Connection: Story = {
  args: {
    segments: [
      {
        segmentId: 1,
        departureDatetime: '2026-08-01T08:00:00',
        arrivalDatetime: '2026-08-01T08:55:00',
        departureAirport: { iataCode: 'AMS', cityName: 'Amsterdam' },
        arrivalAirport: { iataCode: 'LHR', cityName: 'London' },
        marketingAirline: { iataCode: 'BA', airlineName: 'British Airways' },
        marketingFlightNumber: { formattedNumber: 'BA431' },
      },
      {
        segmentId: 2,
        departureDatetime: '2026-08-01T11:30:00',
        arrivalDatetime: '2026-08-01T14:30:00',
        departureAirport: { iataCode: 'LHR', cityName: 'London' },
        arrivalAirport: { iataCode: 'JFK', cityName: 'New York' },
        marketingAirline: { iataCode: 'BA', airlineName: 'British Airways' },
        marketingFlightNumber: { formattedNumber: 'BA117' },
      },
    ],
    segmentBoundLabels: null,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getAllByText(/British Airways/).length).toBe(2);
    expect(canvas.getByText(/BA431/)).toBeInTheDocument();
    expect(canvas.getByText(/BA117/)).toBeInTheDocument();
  },
};
