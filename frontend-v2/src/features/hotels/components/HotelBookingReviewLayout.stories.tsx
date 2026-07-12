import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { fn } from 'storybook/test';
import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';
import { HotelDetailRoomCard } from './hotelDetail';
import { HotelBookingReviewLayout } from './HotelBookingReviewLayout';
import type { RoomRate } from '@/types/hotels';

const sampleRoom: RoomRate = {
  rateBasisId: 'rb-1',
  roomType: 'Deluxe King',
  mealPlan: 'Breakfast included',
  totalPrice: 420,
  currency: 'USD',
  pricePerNight: 140,
  images: [hotelFallback],
  maxOccupancy: { adults: 2, children: 0 },
};

const meta: Meta<typeof HotelBookingReviewLayout> = {
  title: 'Hotels/HotelBookingReviewLayout',
  component: HotelBookingReviewLayout,
  args: {
    subtitle: 'Great Northern Hotel',
    dateLine: 'Mon, Jun 9 – Thu, Jun 12 · 3 nights',
    hotelName: 'Great Northern Hotel',
    hotelImageUrl: hotelFallback,
    hotelLightboxImages: [hotelFallback, hotelFallback],
    hotelAddressLine: '123 Market St, San Francisco, CA',
    onShowOnMap: fn(),
    selectedRoomCard: (
      <HotelDetailRoomCard room={sampleRoom} stayNights={3} showReserveButton={false} matchHotelSummaryImage />
    ),
    hotelAmountLabel: 'Hotel price',
    hotelAmountDisplay: '$420.00',
    platformFeeLabel: 'Platform fee (10.5%)',
    platformFeeDisplay: '$44.10',
    totalAmountDisplay: '$464.10',
    totalSubtext: 'USD · includes taxes & fees',
    guestForms: (
      <Box style={{ padding: 16, backgroundColor: 'var(--mantine-color-gray-0)', borderRadius: 8 }}>
        Guest form area (use GuestForm story for detail)
      </Box>
    ),
    contactSection: (
      <Box style={{ padding: 16, backgroundColor: 'var(--mantine-color-gray-0)', borderRadius: 8 }}>
        Contact fields placeholder
      </Box>
    ),
    selectedSummaryTitle: 'Selected guests',
    selectedGuestBullets: ['Room 1: Adult 1 — Jamie Rivera', 'Room 1: Adult 2 — Manual'],
    footerPrimaryLabel: 'Continue to payment',
    onContinue: fn(),
    onFooterBack: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof HotelBookingReviewLayout>;

export const Default: Story = {};

export const ContinueLoading: Story = {
  args: {
    continueLoading: true,
  },
};

export const SingleHeroImage: Story = {
  args: {
    hotelLightboxImages: [hotelFallback],
  },
};
