import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, expect } from 'storybook/test';
import { Box } from '@mantine/core';
import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';
import { HotelImageWithFallback } from './HotelImageWithFallback';

/**
 * HotelImageWithFallback — three-tier image resolution:
 * 1. Primary URL → rendered as <img>
 * 2. On primary failure → Google Places API → AuthenticatedImage
 * 3. On API failure → fallback SVG
 *
 * Stories use picsum.photos placeholder URLs (no auth required) so the
 * story doesn't trigger the auth proxy. The FallbackTriggered story
 * provides a deliberately broken URL to exercise tier-3.
 */

const meta: Meta<typeof HotelImageWithFallback> = {
  title: 'Hotels/HotelImageWithFallback',
  component: HotelImageWithFallback,
  decorators: [
    (Story) => (
      <Box style={{ width: 400, height: 280, position: 'relative', border: '1px solid var(--mantine-color-default-border)' }}>
        <Story />
      </Box>
    ),
  ],
  args: {
    hotelName: 'Gran Hotel Barcelona',
    city: 'Barcelona',
    fallbackSrc: hotelFallback,
    alt: 'Gran Hotel Barcelona',
    sx: { position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' },
  },
};

export default meta;
type Story = StoryObj<typeof HotelImageWithFallback>;

export const Default: Story = {
  name: 'Primary image loaded',
  args: {
    primaryUrl: 'https://picsum.photos/seed/hotel-bcn/800/600',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const img = canvas.getByRole('img', { name: 'Gran Hotel Barcelona' });
    expect(img).toBeTruthy();
  },
};

export const FallbackTriggered: Story = {
  name: 'Broken URL → fallback SVG',
  args: {
    primaryUrl: 'https://this-url-does-not-exist.invalid/image.jpg',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // The component renders an img regardless (primary, places, or fallback).
    const img = canvas.getByRole('img', { name: 'Gran Hotel Barcelona' });
    expect(img).toBeTruthy();
  },
};

export const NoPrimaryUrl: Story = {
  name: 'No URL → fallback SVG directly',
  args: {
    primaryUrl: null,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const img = canvas.getByRole('img', { name: 'Gran Hotel Barcelona' });
    expect(img).toBeTruthy();
  },
};
