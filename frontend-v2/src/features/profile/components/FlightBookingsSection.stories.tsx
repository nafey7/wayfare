import type { Meta, StoryObj } from '@storybook/react-vite';
import { Provider } from 'react-redux';
import { expect, waitFor, within } from 'storybook/test';
import { FlightBookingsSection } from './FlightBookingsSection';
import { createStoryStore } from '@/stories/helpers/createStoryStore';
import { flightsApi } from '@/api/flightsApi';
import type { FlightBookingListItem } from '@/types/flights';
import { expectAirportPair } from '@/stories/helpers/playAssertions';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockFlightBooking: FlightBookingListItem = {
  id: 'be-001',
  userId: 'u-001',
  voyaBookingReference: 'VOYA-FLT-001',
  externalBookingReference: 'PNR-XYZ',
  action: 'BOOKED',
  timestamp: '2026-04-01T10:00:00Z',
  eventType: 'FLIGHT',
  airlinePnrCode: 'ABC123',
  airlinePnrAirlineName: 'KLM',
  primaryMarketingAirlineName: 'KLM',
  departureAirportIata: 'AMS',
  flightTripType: 'round_trip',
  routeLegs: [
    {
      legIndex: 0,
      departureIata: 'AMS',
      arrivalIata: 'BCN',
      segmentCount: 1,
      segments: [{ departureIata: 'AMS', arrivalIata: 'BCN' }],
    },
    {
      legIndex: 1,
      departureIata: 'BCN',
      arrivalIata: 'AMS',
      segmentCount: 1,
      segments: [{ departureIata: 'BCN', arrivalIata: 'AMS' }],
    },
  ],
  amount: 450,
  dateBooked: '2026-03-15T14:00:00Z',
};

const pendingBooking: FlightBookingListItem = {
  ...mockFlightBooking,
  id: 'be-002',
  voyaBookingReference: 'VOYA-FLT-002',
  action: 'PENDING',
  airlinePnrAirlineName: 'Ryanair',
  primaryMarketingAirlineName: 'Ryanair',
  departureAirportIata: 'LHR',
  flightTripType: 'one_way',
  routeLegs: [
    {
      legIndex: 0,
      departureIata: 'LHR',
      arrivalIata: 'JFK',
      segmentCount: 1,
      segments: [{ departureIata: 'LHR', arrivalIata: 'JFK' }],
    },
  ],
  amount: 280,
};

const cancelledBooking: FlightBookingListItem = {
  ...mockFlightBooking,
  id: 'be-003',
  voyaBookingReference: 'VOYA-FLT-003',
  action: 'CANCELLED',
  departureAirportIata: 'CDG',
  flightTripType: 'one_way',
  routeLegs: [
    {
      legIndex: 0,
      departureIata: 'CDG',
      arrivalIata: 'DXB',
      segmentCount: 1,
      segments: [{ departureIata: 'CDG', arrivalIata: 'DXB' }],
    },
  ],
  amount: 620,
};

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function storeWithBookings(bookings: FlightBookingListItem[]) {
  const store = createStoryStore();
  store.dispatch(flightsApi.util.upsertQueryData('getMyBookings', { limit: 20 }, bookings));
  return store;
}

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const meta: Meta<typeof FlightBookingsSection> = {
  title: 'Profile/FlightBookingsSection',
  component: FlightBookingsSection,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
        <Story />
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof FlightBookingsSection>;

// ---------------------------------------------------------------------------
// Stories
// ---------------------------------------------------------------------------

/** Default: one confirmed round-trip booking (AMS ↔ BCN). */
export const Default: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithBookings([mockFlightBooking])}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expectAirportPair(canvas, 'AMS', 'BCN'));
  },
};

/** Empty: no bookings — shows the "No flight bookings yet" prompt. */
export const Empty: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithBookings([])}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() =>
      expect(canvas.getByText('No flight bookings yet. Plan a trip in chat.')).toBeInTheDocument()
    );
  },
};

/** Many: multiple bookings in different statuses. */
export const Many: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithBookings([mockFlightBooking, pendingBooking, cancelledBooking])}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expectAirportPair(canvas, 'AMS', 'BCN'));
    await waitFor(() => expect(canvas.getByText(/flight bookings \(3\)/i)).toBeInTheDocument());
  },
};
