import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, expect, fn } from 'storybook/test';
import type { HotelItinerary } from '@/types/hotels';
import { HotelMobilePinCard } from './HotelMobilePinCard';
import { mockHotelBestValue, MOCK_NIGHTS } from '../../__fixtures__/mockHotelData';
import { expectPricePresent } from '@/stories/helpers/playAssertions';

const mockHotelUSD: HotelItinerary = {
  ...mockHotelBestValue,
  id: 'hotel-nyc-001',
  tokenId: 'tok-nyc-001',
  productId: 'prod-nyc-001',
  name: 'The Lexington Hotel New York',
  city: 'New York',
  address: '511 Lexington Avenue',
  country: 'United States',
  startingPrice: { currency: 'USD', amount: 700.0, perNight: 100.0 },
  total: 700.0,
};

const meta: Meta<typeof HotelMobilePinCard> = {
  title: 'Hotels/Mobile/HotelMobilePinCard',
  component: HotelMobilePinCard,
  parameters: { layout: 'padded' },
  args: {
    nights: MOCK_NIGHTS,
    rooms: 1,
    isSelecting: false,
    onSelect: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof HotelMobilePinCard>;

/** EUR pricing: symbol € must appear; the currency code "EUR" must not. */
export const EUR: Story = {
  args: { hotel: mockHotelBestValue },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectPricePresent(canvas, '€');
    const codeMatches = canvas.queryAllByText(/\bEUR\b/);
    expect(codeMatches.length, 'EUR currency code must not appear in rendered output').toBe(0);
  },
};

/** USD pricing: symbol $ must appear; exact total $700 must be visible; the currency code "USD" must not. */
export const USD: Story = {
  args: { hotel: mockHotelUSD },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectPricePresent(canvas, '$');
    const totalMatches = canvas.queryAllByText(/\$700/);
    expect(totalMatches.length, 'expected $700 total to be pinned in rendered output').toBeGreaterThan(0);
    const codeMatches = canvas.queryAllByText(/\bUSD\b/);
    expect(codeMatches.length, 'USD currency code must not appear in rendered output').toBe(0);
  },
};

/** Selecting state: button shows loading text and is disabled. */
export const Selecting: Story = {
  args: { hotel: mockHotelBestValue, isSelecting: true },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const loadingText = canvas.queryAllByText(/Loading/i);
    expect(loadingText.length, 'expected "Loading…" text in selecting state').toBeGreaterThan(0);
    const btn = canvas.getByRole('button', { name: /Select/i });
    expect(btn).toBeDisabled();
  },
};
