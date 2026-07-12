import type { Meta, StoryObj } from '@storybook/react-vite';
import { within } from 'storybook/test';
import { expectHotelBannerPopulated, expectNoPlaceholderText } from '@/stories/helpers/playAssertions';
import { HotelInfoBanner } from './HotelInfoBanner';
import {
  mockHotelItinerary,
  mockHotelItineraryNoImage,
  CHECKIN_DATE,
  CHECKOUT_DATE,
  STAY_NIGHTS,
} from '../__fixtures__/mockHotelDetailData';

const meta: Meta<typeof HotelInfoBanner> = {
  title: 'Hotels/HotelInfoBanner',
  component: HotelInfoBanner,
  args: {
    hotel: mockHotelItinerary,
    checkin: CHECKIN_DATE,
    checkout: CHECKOUT_DATE,
    nights: STAY_NIGHTS,
  },
};

export default meta;
type Story = StoryObj<typeof HotelInfoBanner>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelBannerPopulated(canvas, {
      hotelName: 'Gran Hotel Barcelona',
      nights: STAY_NIGHTS,
    });
    expectNoPlaceholderText(canvas);
  },
};

export const NoImage: Story = {
  name: 'No primary image (fallback)',
  args: {
    hotel: mockHotelItineraryNoImage,
    checkin: CHECKIN_DATE,
    checkout: CHECKOUT_DATE,
    nights: 7,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelBannerPopulated(canvas, {
      hotelName: 'Amsterdam Canal View',
      nights: 7,
    });
    expectNoPlaceholderText(canvas);
  },
};
