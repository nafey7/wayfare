import type { Meta, StoryObj } from '@storybook/react-vite';
import { Provider } from 'react-redux';
import { expect, waitFor, within, userEvent } from 'storybook/test';
import { ProfilePage } from './ProfilePage';
import { createStoryStore } from '@/stories/helpers/createStoryStore';
import { usersApi } from '@/api/usersApi';
import { flightsApi } from '@/api/flightsApi';
import { hotelsApi } from '@/api/hotelsApi';
import { itinerariesApi } from '@/api/itinerariesApi';
import type { ProfileAggregate } from '@/types/profile';
import type { FlightBookingListItem } from '@/types/flights';
import type { HotelMyBookingListItem } from '@/types/hotels';
import type { SavedItinerary } from '@/types/itineraries';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockProfile: ProfileAggregate = {
  user: {
    id: 'u-001',
    email: 'jane.doe@example.com',
    firstName: 'Jane',
    lastName: 'Doe',
    profileImage: null,
    mobile: '+31 6 1234 5678',
  },
  preferences: {
    documentExists: true,
    preferenceChips: ['Window seat', 'Boutique hotels'],
    travelStyle: {
      travelPace: 'moderate',
      budgetMindset: 'mid_range',
      accommodation: 'hotel',
      activityDensity: 'balanced',
      primaryGoals: ['culture', 'food'],
      gettingAround: ['public_transport', 'walking'],
    },
    flights: {
      seatPreference: 'window',
      maxStops: '1',
      preferredAirlines: ['KLM'],
      departureWindow: ['06:00', '22:00'],
    },
    hotels: {
      bedType: 'king',
      roomType: 'standard',
      amenities: ['wifi', 'gym'],
      hotelStyle: ['boutique'],
      locationPreference: ['city_center'],
      cancellation: ['free_cancellation'],
    },
  },
  passengers: [],
};

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

const mockHotelBooking: HotelMyBookingListItem = {
  voyaBookingReference: 'VOYA-HOTEL-001',
  action: 'BOOKED',
  timestamp: '2026-03-20T10:00:00Z',
  dateBooked: '2026-03-20T10:00:00Z',
  amount: 320,
  hotelImageUrl: null,
  hotelName: 'Hotel Arts Barcelona',
  hotelCity: 'Barcelona',
  hotelCheckInDate: '2026-07-10',
  hotelCheckOutDate: '2026-07-15',
  hotelNights: 5,
};

const mockItinerary: SavedItinerary = {
  id: 'itin-01',
  structuredItinerary: {
    itineraryItems: [
      {
        day: 1,
        title: 'Arrival in Paris',
        description: 'Check in and explore.',
        imageUrl: '',
      },
    ],
  },
  tripMeta: {
    destination: 'Paris, France',
    origin: 'Amsterdam',
    departureDate: '2026-09-01',
    returnDate: '2026-09-07',
    adults: 2,
  },
  createdAt: '2026-04-01T10:00:00Z',
  updatedAt: '2026-04-01T10:00:00Z',
};

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function storeWithData({
  profile = mockProfile,
  flightBookings = [mockFlightBooking],
  hotelBookings = [mockHotelBooking],
  itineraries = [mockItinerary],
}: {
  profile?: ProfileAggregate | null;
  flightBookings?: FlightBookingListItem[];
  hotelBookings?: HotelMyBookingListItem[];
  itineraries?: SavedItinerary[];
} = {}) {
  const store = createStoryStore();
  if (profile) {
    store.dispatch(usersApi.util.upsertQueryData('getProfile', undefined, profile));
  }
  store.dispatch(flightsApi.util.upsertQueryData('getMyBookings', { limit: 20 }, flightBookings));
  store.dispatch(hotelsApi.util.upsertQueryData('getMyHotelBookings', { limit: 20 }, hotelBookings));
  store.dispatch(itinerariesApi.util.upsertQueryData('getItineraries', undefined, itineraries));
  return store;
}

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const meta: Meta<typeof ProfilePage> = {
  title: 'Profile/ProfilePage',
  component: ProfilePage,
  parameters: { layout: 'fullscreen' },
};

export default meta;
type Story = StoryObj<typeof ProfilePage>;

// ---------------------------------------------------------------------------
// Stories
// ---------------------------------------------------------------------------

/** Default: About Me section — shows avatar, stats, and preferences list. */
export const Default: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithData()}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expect(canvas.getByText('Jane')).toBeInTheDocument());
    await waitFor(() => expect(canvas.getByText('Your preferences')).toBeInTheDocument());
  },
};

/** Flight bookings section — navigates to Bookings > Flights. */
export const FlightBookings: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithData()}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expect(canvas.getByText('Jane')).toBeInTheDocument());
    await userEvent.click(canvas.getByText('Bookings'));
    await userEvent.click(canvas.getByText('Flights'));
    await waitFor(() =>
      expect(canvas.getByText(/flight bookings/i)).toBeInTheDocument()
    );
  },
};

/** Hotel bookings section — navigates to Bookings > Hotels. */
export const HotelBookings: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithData()}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expect(canvas.getByText('Jane')).toBeInTheDocument());
    await userEvent.click(canvas.getByText('Bookings'));
    await userEvent.click(canvas.getByText('Hotels'));
    await waitFor(() =>
      expect(canvas.getByText(/hotel bookings/i)).toBeInTheDocument()
    );
  },
};

/** Trips section — shows saved itinerary card. */
export const Trips: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithData()}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expect(canvas.getByText('Jane')).toBeInTheDocument());
    // "Trips" also appears in the stats row of the hero card, so scope to the nav
    const nav = canvas.getByRole('navigation');
    await userEvent.click(within(nav).getByText('Trips'));
    await waitFor(() =>
      expect(canvas.getByText('Paris')).toBeInTheDocument()
    );
  },
};

/** Security section — shows change-password button. */
export const Security: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithData()}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expect(canvas.getByText('Jane')).toBeInTheDocument());
    await userEvent.click(canvas.getByText('Login & security'));
    await waitFor(() =>
      expect(canvas.getByText('Change password')).toBeInTheDocument()
    );
  },
};

/** Loading state — profile query not yet resolved, shows spinner. */
export const Loading: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithData({ profile: null })}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Profile data is pending — preferences list must not be visible yet
    await waitFor(() =>
      expect(canvas.queryByText('Your preferences')).not.toBeInTheDocument()
    );
  },
};

/** No bookings — empty state for both flight and hotel sections. */
export const NoBookings: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithData({ flightBookings: [], hotelBookings: [] })}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expect(canvas.getByText('Jane')).toBeInTheDocument());
    await userEvent.click(canvas.getByText('Bookings'));
    await userEvent.click(canvas.getByText('Flights'));
    await waitFor(() =>
      expect(canvas.getByText(/No flight bookings yet/i)).toBeInTheDocument()
    );
  },
};
