import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { expect, within } from 'storybook/test';
import { BookingFlightLegsCard } from './BookingFlightLegsCard';
import type { FlightLegCamel } from '@/types/flightBackend';

const outboundLeg: FlightLegCamel = {
  flightSegments: [
    {
      departureDatetime: '2026-07-15T10:30:00',
      arrivalDatetime: '2026-07-15T13:00:00',
      departureAirport: { iataCode: 'AMS', cityName: 'Amsterdam' },
      arrivalAirport: { iataCode: 'BCN', cityName: 'Barcelona' },
      marketingAirline: { iataCode: 'KL', airlineName: 'KLM' },
      marketingFlightNumber: { formattedNumber: 'KL1671' },
    },
  ],
};

const returnLeg: FlightLegCamel = {
  flightSegments: [
    {
      departureDatetime: '2026-07-22T18:00:00',
      arrivalDatetime: '2026-07-22T20:30:00',
      departureAirport: { iataCode: 'BCN', cityName: 'Barcelona' },
      arrivalAirport: { iataCode: 'AMS', cityName: 'Amsterdam' },
      marketingAirline: { iataCode: 'KL', airlineName: 'KLM' },
      marketingFlightNumber: { formattedNumber: 'KL1672' },
    },
  ],
};

const meta: Meta<typeof BookingFlightLegsCard> = {
  title: 'Flights/Booking/BookingFlightLegsCard',
  component: BookingFlightLegsCard,
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
type Story = StoryObj<typeof BookingFlightLegsCard>;

/** One-way: single leg, no OUTBOUND/RETURN labels. */
export const OneWay: Story = {
  args: {
    flightLegs: [outboundLeg],
    isRoundTripLayout: false,
    rtLegBounds: [null],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/AMS/)).toBeInTheDocument();
    expect(canvas.getByText(/BCN/)).toBeInTheDocument();
    expect(canvas.getByText('KLM')).toBeInTheDocument();
    expect(canvas.queryByText('OUTBOUND')).not.toBeInTheDocument();
    expect(canvas.queryByText('RETURN')).not.toBeInTheDocument();
  },
};

/** Round-trip: two legs with OUTBOUND/RETURN markers. */
export const RoundTrip: Story = {
  args: {
    flightLegs: [outboundLeg, returnLeg],
    isRoundTripLayout: true,
    rtLegBounds: [null, null],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('OUTBOUND')).toBeInTheDocument();
    expect(canvas.getByText('RETURN')).toBeInTheDocument();
    expect(canvas.getAllByText('KLM').length).toBe(2);
  },
};

/** Multi-leg (e.g. multicity), no round-trip semantics. */
export const Multicity: Story = {
  args: {
    flightLegs: [
      outboundLeg,
      {
        flightSegments: [
          {
            departureDatetime: '2026-07-22T08:00:00',
            arrivalDatetime: '2026-07-22T11:30:00',
            departureAirport: { iataCode: 'BCN', cityName: 'Barcelona' },
            arrivalAirport: { iataCode: 'CDG', cityName: 'Paris' },
            marketingAirline: { iataCode: 'AF', airlineName: 'Air France' },
            marketingFlightNumber: { formattedNumber: 'AF1149' },
          },
        ],
      },
      returnLeg,
    ],
    isRoundTripLayout: false,
    rtLegBounds: [null, null, null],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getAllByText('KLM').length).toBe(2);
    expect(canvas.getByText('Air France')).toBeInTheDocument();
    expect(canvas.queryByText('OUTBOUND')).not.toBeInTheDocument();
  },
};
