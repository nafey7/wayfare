import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, expect, fn } from 'storybook/test';
import { HotelCard } from './HotelCard';
import {
  mockHotelBestValue,
  mockHotelCheapest,
  mockHotelHighestRated,
  MOCK_NIGHTS,
} from '../__fixtures__/mockHotelData';
import { expectHotelCardPopulated } from '@/stories/helpers/playAssertions';

const meta: Meta<typeof HotelCard> = {
  title: 'Hotels/HotelCard',
  component: HotelCard,
  parameters: { layout: 'padded' },
};

export default meta;
type Story = StoryObj<typeof HotelCard>;

/** Best Value: 5-star hotel, Room Only, EUR pricing, with TripAdvisor rating. */
export const Default: Story = {
  args: {
    hotel: mockHotelBestValue,
    nights: MOCK_NIGHTS,
    onSelect: fn(),
    tripAdvisorRating: 4.7,
    tripAdvisorReviews: 2341,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelCardPopulated(canvas, {
      name: 'Hotel Arts Barcelona',
      stars: 5,
      currency: '€',
    });
  },
};

/** Best Value badge: curated "Best Value" pick with badge in footer. */
export const BestValue: Story = {
  args: {
    hotel: mockHotelBestValue,
    nights: MOCK_NIGHTS,
    onSelect: fn(),
    valueBadge: 'Best Value',
    tripAdvisorRating: 4.7,
    tripAdvisorReviews: 2341,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelCardPopulated(canvas, {
      name: 'Hotel Arts Barcelona',
      stars: 5,
      currency: '€',
    });
    const badge = canvas.queryAllByText(/Best Value/i);
    expect(badge.length, 'Best Value badge should be visible').toBeGreaterThan(0);
  },
};

/** Cheapest: 4-star budget pick with "Cheapest" badge. */
export const Cheapest: Story = {
  args: {
    hotel: mockHotelCheapest,
    nights: MOCK_NIGHTS,
    onSelect: fn(),
    valueBadge: 'Cheapest',
    tripAdvisorRating: 3.9,
    tripAdvisorReviews: 812,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelCardPopulated(canvas, {
      name: 'Barceló Raval',
      stars: 4,
      currency: '€',
    });
  },
};

/** Highest Rated: 5-star with "Highest Rated" badge and Breakfast chip (fareType contains breakfast). */
export const HighestRated: Story = {
  args: {
    hotel: mockHotelHighestRated,
    nights: MOCK_NIGHTS,
    onSelect: fn(),
    valueBadge: 'Highest Rated',
    tripAdvisorRating: 4.9,
    tripAdvisorReviews: 5420,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelCardPopulated(canvas, {
      name: 'Mandarin Oriental Barcelona',
      stars: 5,
      currency: '€',
    });
    const breakfastChip = canvas.queryAllByText(/Breakfast/i);
    expect(breakfastChip.length, 'Breakfast badge should be visible').toBeGreaterThan(0);
  },
};

/** Selected state: highlighted with navy border. */
export const Selected: Story = {
  args: {
    hotel: mockHotelBestValue,
    nights: MOCK_NIGHTS,
    onSelect: fn(),
    isSelected: true,
    tripAdvisorRating: 4.7,
    tripAdvisorReviews: 2341,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelCardPopulated(canvas, { name: 'Hotel Arts Barcelona', currency: '€' });
  },
};

/** Selecting state: card is dimmed while room rates load. */
export const Selecting: Story = {
  args: {
    hotel: mockHotelBestValue,
    nights: MOCK_NIGHTS,
    onSelect: fn(),
    isSelecting: true,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelCardPopulated(canvas, { name: 'Hotel Arts Barcelona', currency: '€' });
  },
};

/** No rating: TripAdvisor row is hidden when rating is omitted. */
export const NoRating: Story = {
  args: {
    hotel: mockHotelBestValue,
    nights: MOCK_NIGHTS,
    onSelect: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelCardPopulated(canvas, { name: 'Hotel Arts Barcelona', currency: '€' });
    const stars = canvas.queryAllByText(/★/);
    expect(stars.length, 'rating row should be hidden when no rating provided').toBe(0);
  },
};

/** No image: gradient placeholder shown. */
export const NoImage: Story = {
  args: {
    hotel: { ...mockHotelBestValue, imageUrl: undefined, images: [] },
    nights: MOCK_NIGHTS,
    onSelect: fn(),
    tripAdvisorRating: 4.2,
    tripAdvisorReviews: 310,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelCardPopulated(canvas, { name: 'Hotel Arts Barcelona', currency: '€' });
  },
};
