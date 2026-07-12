import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { expect, within } from 'storybook/test';
import { FlightDetailsItineraryCard } from './FlightDetailsItineraryCard';
import type { ProcessedLeg } from '@/types/flightBackend';

const directLegOutbound: ProcessedLeg = {
  legLabel: 'Outbound · Wed Jul 15',
  departure: { city: 'Amsterdam', airport: 'AMS', time: '10:30', date: 'Jul 15, 2026' },
  arrival: { city: 'Barcelona', airport: 'BCN', time: '13:00', date: 'Jul 15, 2026' },
  duration: '2h 30m',
  totalTimeDisplay: '2h 30m',
  hasLayover: false,
  stops: 0,
  stopsText: 'Direct',
  segments: [
    {
      departureDatetime: '2026-07-15T10:30:00',
      arrivalDatetime: '2026-07-15T13:00:00',
      departureAirport: { iataCode: 'AMS', cityName: 'Amsterdam' },
      arrivalAirport: { iataCode: 'BCN', cityName: 'Barcelona' },
      marketingAirline: { iataCode: 'KL', airlineName: 'KLM' },
      marketingFlightNumber: { formattedNumber: 'KL1671' },
    },
  ],
  airlinesInfo: [{ name: 'KLM', code: 'KL', flights: ['KL1671'] }],
};

const directLegReturn: ProcessedLeg = {
  legLabel: 'Return · Wed Jul 22',
  departure: { city: 'Barcelona', airport: 'BCN', time: '18:00', date: 'Jul 22, 2026' },
  arrival: { city: 'Amsterdam', airport: 'AMS', time: '20:30', date: 'Jul 22, 2026' },
  duration: '2h 30m',
  totalTimeDisplay: '2h 30m',
  hasLayover: false,
  stops: 0,
  stopsText: 'Direct',
  segments: [],
  airlinesInfo: [{ name: 'KLM', code: 'KL', flights: ['KL1672'] }],
};

const oneStopLeg: ProcessedLeg = {
  legLabel: 'Outbound · Aug 1',
  departure: { city: 'Amsterdam', airport: 'AMS', time: '08:00', date: 'Aug 1, 2026' },
  arrival: { city: 'New York', airport: 'JFK', time: '14:30', date: 'Aug 1, 2026' },
  duration: '12h 30m',
  totalTimeDisplay: '12h 30m',
  hasLayover: true,
  stops: 1,
  stopsText: '1 stop · LHR',
  segments: [
    {
      departureDatetime: '2026-08-01T08:00:00',
      arrivalDatetime: '2026-08-01T08:55:00',
      departureAirport: { iataCode: 'AMS' },
      arrivalAirport: { iataCode: 'LHR' },
      marketingAirline: { iataCode: 'BA', airlineName: 'British Airways' },
      operatingAirline: { iataCode: 'BA', airlineName: 'British Airways' },
      marketingFlightNumber: { formattedNumber: 'BA431' },
    },
    {
      departureDatetime: '2026-08-01T11:30:00',
      arrivalDatetime: '2026-08-01T14:30:00',
      departureAirport: { iataCode: 'LHR' },
      arrivalAirport: { iataCode: 'JFK' },
      marketingAirline: { iataCode: 'BA', airlineName: 'British Airways' },
      operatingAirline: { iataCode: 'AA', airlineName: 'American Airlines' },
      marketingFlightNumber: { formattedNumber: 'BA117' },
    },
  ],
  airlinesInfo: [{ name: 'British Airways', code: 'BA', flights: ['BA431', 'BA117'] }],
};

const meta: Meta<typeof FlightDetailsItineraryCard> = {
  title: 'Flights/Booking/FlightDetailsItineraryCard',
  component: FlightDetailsItineraryCard,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <Box style={{ maxWidth: 900 }}>
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof FlightDetailsItineraryCard>;

/** Single direct leg (one-way). */
export const OneWay: Story = {
  args: { processedLegs: [directLegOutbound] },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('AMS')).toBeInTheDocument();
    expect(canvas.getByText('BCN')).toBeInTheDocument();
    expect(canvas.getAllByText(/2h 30m/).length).toBeGreaterThan(0);
    expect(canvas.getByText('Direct')).toBeInTheDocument();
  },
};

/** Round-trip: two direct legs with bound labels. */
export const RoundTrip: Story = {
  args: { processedLegs: [directLegOutbound, directLegReturn] },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/Outbound/)).toBeInTheDocument();
    expect(canvas.getByText(/Return/)).toBeInTheDocument();
    expect(canvas.getAllByText('AMS').length).toBe(2);
    expect(canvas.getAllByText('BCN').length).toBe(2);
  },
};

/** Connecting flight with codeshare segment + segment details rendered. */
export const WithConnection: Story = {
  args: { processedLegs: [oneStopLeg] },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/1 stop/)).toBeInTheDocument();
    expect(canvas.getByText(/Segment Details/)).toBeInTheDocument();
    expect(canvas.getByText(/operated by American Airlines/)).toBeInTheDocument();
  },
};
