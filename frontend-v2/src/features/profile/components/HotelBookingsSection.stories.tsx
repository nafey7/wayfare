import type { Meta, StoryObj } from '@storybook/react-vite';
import { Provider } from 'react-redux';
import { expect, waitFor, within } from 'storybook/test';
import { HotelBookingsSection } from './HotelBookingsSection';
import { createStoryStore } from '@/stories/helpers/createStoryStore';
import { hotelsApi } from '@/api/hotelsApi';
import type { HotelMyBookingListItem } from '@/types/hotels';
import { expectBookingCardPopulated } from '@/stories/helpers/playAssertions';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockHotelBooking: HotelMyBookingListItem = {
  voyaBookingReference: 'VOYA-HTL-001',
  action: 'BOOKED',
  timestamp: '2026-04-01T10:00:00Z',
  dateBooked: '2026-03-15T14:00:00Z',
  amount: 1200,
  hotelImageUrl: null,
  hotelName: 'Hotel Arts Barcelona',
  hotelCity: 'Barcelona',
  hotelCheckInDate: '2026-05-10',
  hotelCheckOutDate: '2026-05-17',
  hotelNights: 7,
};

const pendingHotelBooking: HotelMyBookingListItem = {
  voyaBookingReference: 'VOYA-HTL-002',
  action: 'PENDING',
  timestamp: '2026-04-10T09:00:00Z',
  dateBooked: '2026-04-10T09:00:00Z',
  amount: 800,
  hotelImageUrl: null,
  hotelName: 'The Grand Tokyo',
  hotelCity: 'Tokyo',
  hotelCheckInDate: '2026-06-01',
  hotelCheckOutDate: '2026-06-06',
  hotelNights: 5,
};

const cancelledHotelBooking: HotelMyBookingListItem = {
  voyaBookingReference: 'VOYA-HTL-003',
  action: 'CANCELLED',
  timestamp: '2026-03-01T12:00:00Z',
  dateBooked: '2026-02-28T10:00:00Z',
  amount: 450,
  hotelImageUrl: null,
  hotelName: 'Marriott Paris',
  hotelCity: 'Paris',
  hotelCheckInDate: '2026-04-05',
  hotelCheckOutDate: '2026-04-08',
  hotelNights: 3,
};

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function storeWithBookings(bookings: HotelMyBookingListItem[]) {
  const store = createStoryStore();
  store.dispatch(hotelsApi.util.upsertQueryData('getMyHotelBookings', { limit: 20 }, bookings));
  return store;
}

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const meta: Meta<typeof HotelBookingsSection> = {
  title: 'Profile/HotelBookingsSection',
  component: HotelBookingsSection,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
        <Story />
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof HotelBookingsSection>;

// ---------------------------------------------------------------------------
// Stories
// ---------------------------------------------------------------------------

/** Default: one confirmed hotel booking (Hotel Arts Barcelona). */
export const Default: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithBookings([mockHotelBooking])}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expectBookingCardPopulated(canvas, 'Hotel Arts Barcelona'));
  },
};

/** Empty: no bookings — shows the "No hotel bookings yet" prompt. */
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
      expect(canvas.getByText('No hotel bookings yet. Plan a trip in chat.')).toBeInTheDocument()
    );
  },
};

/** Many: three bookings in different statuses. */
export const Many: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithBookings([mockHotelBooking, pendingHotelBooking, cancelledHotelBooking])}>
        <Story />
      </Provider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expectBookingCardPopulated(canvas, 'Hotel Arts Barcelona'));
    await waitFor(() => expect(canvas.getByText(/hotel bookings \(3\)/i)).toBeInTheDocument());
  },
};
