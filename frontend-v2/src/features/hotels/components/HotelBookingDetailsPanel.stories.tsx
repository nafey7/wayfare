import type { Meta, StoryObj } from '@storybook/react-vite';

import { HotelBookingDetailsPanel } from './HotelBookingDetailsPanel';

const meta: Meta<typeof HotelBookingDetailsPanel> = {
  title: 'Hotels/HotelBookingDetailsPanel',
  component: HotelBookingDetailsPanel,
};

export default meta;
type Story = StoryObj<typeof HotelBookingDetailsPanel>;

const baseArgs = {
  headlineCity: 'Barcelona',
  destinationTitle: 'Barcelona',
  stayDateLine: 'Jun 1–5, 2026 • 4 nights',
  hotelImageUrls: [],
  hotelName: 'Example Boutique Hotel',
  addressLine: 'Carrer de la Marina 123',
  nightsAdultsLine: '4 nights・2 adults',
  roomTypeName: 'Deluxe double',
  roomAmenityChip: 'Breakfast included',
  reservationCode: 'VOYA-DEMO-001',
  guests: [
    { roleLabel: 'Adult 1', fullName: 'Jane Doe' },
    { roleLabel: 'Adult 2', fullName: 'John Doe' },
  ],
  paymentMethodLabel: 'Visa ···· 4242',
  paymentTimestamp: 'Apr 17, 2026 · 14:32',
  paymentAmountFormatted: 'EUR 612.00',
  paymentApproved: true,
  nextStepsItems: [
    { id: '1', text: 'Check your email for the supplier confirmation.' },
    { id: '2', text: 'Add this stay to your calendar.', tone: 'muted' as const },
  ],
  hotelWebsiteUrl: 'https://example.com',
};

export const Default: Story = {
  args: {
    ...baseArgs,
    confirmationEmail: 'jane@example.com',
  },
};

export const WithPrimaryActions: Story = {
  args: {
    ...baseArgs,
    confirmationEmail: 'jane@example.com',
    showPrimaryBookingActions: true,
    viewItineraryTo: '/itinerary',
  },
};
