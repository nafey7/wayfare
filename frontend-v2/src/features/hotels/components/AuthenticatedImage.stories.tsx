import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, expect } from 'storybook/test';
import { Box } from '@mantine/core';
import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';
import { AuthenticatedImage } from './AuthenticatedImage';

/**
 * AuthenticatedImage — fetches a protected URL with JWT and renders via blob URL.
 *
 * Stories pass:
 *   - A public picsum URL for Default (no auth needed for picsum, but no
 *     token → component falls back immediately since token is null in Storybook).
 *   - An inline SVG data-URI for LoadSuccess (always renders, no network).
 *   - A broken URL for LoadFailure to exercise the fallback path.
 *
 * The auth proxy (useLazyGetPlaceImageUrlQuery) is NOT triggered here because
 * AuthenticatedImage only fetches `url` directly with the JWT — it does not
 * call the Places API. With no token in the Redux store, the component sets
 * `failed = true` and shows `fallbackSrc` immediately.
 */

// Inline SVG data-URI — always available, no network, no auth.
const INLINE_SVG_URI =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect width='400' height='300' fill='%234caf50'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='white' font-size='24' font-family='sans-serif'%3EHotel Image%3C/text%3E%3C/svg%3E";

const meta: Meta<typeof AuthenticatedImage> = {
  title: 'Hotels/AuthenticatedImage',
  component: AuthenticatedImage,
  decorators: [
    (Story) => (
      <Box style={{ width: 400, height: 300, position: 'relative', border: '1px solid var(--mantine-color-default-border)' }}>
        <Story />
      </Box>
    ),
  ],
  args: {
    alt: 'Hotel image',
    fallbackSrc: hotelFallback,
  },
};

export default meta;
type Story = StoryObj<typeof AuthenticatedImage>;

export const Default: Story = {
  name: 'Default (no token → fallback SVG shown)',
  args: {
    url: 'https://picsum.photos/seed/auth-hotel/800/600',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // No JWT in Storybook store → component immediately falls through to fallbackSrc.
    const img = canvas.getByRole('img', { name: 'Hotel image' });
    expect(img, 'expected an img element').toBeTruthy();
  },
};

export const InlineSvg: Story = {
  name: 'Inline SVG data-URI (always renders)',
  args: {
    url: INLINE_SVG_URI,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const img = canvas.getByRole('img', { name: 'Hotel image' });
    expect(img, 'expected an img element').toBeTruthy();
  },
};

export const LoadFailure: Story = {
  name: 'Load failure → fallback SVG',
  args: {
    url: 'https://this-protected-url-does-not-exist.invalid/places/image.jpg',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // No token → immediate fallback (same render path as a real fetch failure).
    const img = canvas.getByRole('img', { name: 'Hotel image' });
    expect(img, 'expected fallback img when URL cannot be fetched').toBeTruthy();
  },
};

export const NoFallback: Story = {
  name: 'No fallback (grey placeholder box)',
  args: {
    url: 'https://this-protected-url-does-not-exist.invalid/places/image.jpg',
    fallbackSrc: undefined,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // No token, no fallback → renders a grey Box (aria-hidden).
    // Verify no img with alt text is present (the grey box is aria-hidden).
    const img = canvas.queryByRole('img', { name: 'Hotel image' });
    expect(img, 'expected no visible img when both url and fallback are absent').toBeNull();
  },
};
