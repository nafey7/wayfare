import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn } from 'storybook/test';
import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';
import type { RoomRate } from '@/types/hotels';
import { HotelDetailRoomCard } from './HotelDetailRoomCard';

const baseRoom: RoomRate = {
  rateBasisId: 'rb-story',
  roomType: 'Superior Double',
  mealPlan: 'Room only',
  totalPrice: 580,
  originalTotalPrice: 640,
  currency: 'USD',
  pricePerNight: 290,
  images: [hotelFallback, hotelFallback],
  maxOccupancy: { adults: 2, children: 1 },
  roomsAvailable: 2,
};

const meta: Meta<typeof HotelDetailRoomCard> = {
  title: 'Hotels/HotelDetailRoomCard',
  component: HotelDetailRoomCard,
  args: {
    room: baseRoom,
    stayNights: 2,
    onReserve: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof HotelDetailRoomCard>;

export const SelectRoom: Story = {
  args: {
    showReserveButton: true,
    isSelecting: false,
  },
};

export const Selecting: Story = {
  args: {
    showReserveButton: true,
    isSelecting: true,
  },
};

export const ReviewBookingCompact: Story = {
  args: {
    showReserveButton: false,
    matchHotelSummaryImage: true,
  },
};
