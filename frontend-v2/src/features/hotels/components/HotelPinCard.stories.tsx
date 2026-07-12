import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, expect, fn } from 'storybook/test';
import { Box } from '@mantine/core';
import { expectHotelName, expectPricePresent } from '@/stories/helpers/playAssertions';
import { HotelPinCard } from './HotelPinCard';
import type { HotelPinCardData } from './HotelPinCard';

const mockPinCard: HotelPinCardData = {
  id: 'hotel-bcn-001',
  name: 'Hotel Arts Barcelona',
  area: 'Poblenou, Barcelona',
  stars: 5,
  reviewScore: 8.9,
  reviewCount: 2341,
  reviewLabel: 'Excellent',
  pricePerNight: '€220',
  totalPrice: '€1,540',
};

const meta: Meta<typeof HotelPinCard> = {
  title: 'Hotels/Mobile/HotelPinCard',
  component: HotelPinCard,
  // Card is position:absolute — wrap in a relative container that simulates the map background.
  decorators: [
    (Story) => (
      <Box
        style={{
          position: 'relative',
          height: 380,
          background: 'linear-gradient(160deg, #c8d8e8 0%, #a0b8d0 100%)',
          borderRadius: 8,
          overflow: 'hidden',
        }}
      >
        <Story />
      </Box>
    ),
  ],
  args: {
    hotel: mockPinCard,
    onClose: fn(),
    onViewDetails: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof HotelPinCard>;

/** Default: no chrome offset — card floats 16 px from the container bottom. */
export const Default: Story = {
  args: { bottomInset: 0 },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelName(canvas, 'Hotel Arts Barcelona');
    expectPricePresent(canvas, '€');
  },
};

/**
 * WithFixedChrome: bottomInset=92 (FIXED_BOTTOM_CHROME in HotelsMobileSheetView:
 * BottomNav 48 px + ChatSheet resting 44 px).
 * Card floats 108 px from the bottom so it clears the fixed chrome.
 */
export const WithFixedChrome: Story = {
  args: { bottomInset: 92 },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectHotelName(canvas, 'Hotel Arts Barcelona');
    expectPricePresent(canvas, '€');
  },
};

/** USD pricing: dollar symbol renders correctly in the pin card format. */
export const USDPricing: Story = {
  args: {
    bottomInset: 0,
    hotel: {
      ...mockPinCard,
      id: 'hotel-nyc-001',
      name: 'The Lexington Hotel New York',
      area: 'Midtown, New York',
      pricePerNight: '$100',
      totalPrice: '$700',
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectPricePresent(canvas, '$');
    const codeMatches = canvas.queryAllByText(/\bUSD\b/);
    expect(codeMatches.length, 'USD currency code must not appear in rendered output').toBe(0);
  },
};
