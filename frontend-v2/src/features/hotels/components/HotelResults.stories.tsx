import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, expect, fn } from 'storybook/test';
import { HotelResults } from './HotelResults';
import {
  mockHotelList,
  mockFilterableHotels,
  mockHotelBestValue,
  mockHotelCheapest,
  mockHotelHighestRated,
  MOCK_NIGHTS,
} from '../__fixtures__/mockHotelData';
import { expectHotelCardPopulated } from '@/stories/helpers/playAssertions';

const meta: Meta<typeof HotelResults> = {
  title: 'Hotels/HotelResults',
  component: HotelResults,
  parameters: { layout: 'padded' },
  args: {
    hotels: mockFilterableHotels,
    hotelObjects: mockHotelList,
    nights: MOCK_NIGHTS,
    onHotelSelect: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof HotelResults>;

/** Default: curated section (best value, cheapest, highest rated) + hotel list. */
export const Default: Story = {
  args: {
    curatedHotels: {
      bestValue: mockHotelBestValue,
      cheapest: mockHotelCheapest,
      highestRated: mockHotelHighestRated,
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Top picks')).toBeInTheDocument();
    expectHotelCardPopulated(canvas, {
      name: 'Hotel Arts Barcelona',
      stars: 5,
      currency: '€',
    });
  },
};

/** Empty: no hotels match the current filters. */
export const Empty: Story = {
  args: {
    hotels: [],
    hotelObjects: [],
    curatedHotels: undefined,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(
      canvas.getByText(/No hotels match your filters/i)
    ).toBeInTheDocument();
  },
};

/** Loading more: load more button visible (cursor-token present, isLoadingMore active). */
export const LoadingMore: Story = {
  args: {
    hotels: mockFilterableHotels,
    hotelObjects: mockHotelList,
    nextToken: 'next-page-token',
    isLoadingMore: true,
    onLoadMore: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelCardPopulated(canvas, { name: 'Hotel Arts Barcelona', currency: '€' });
    const btn = canvas.getByRole('button', { name: /Loading/i });
    expect(btn).toBeDisabled();
  },
};
