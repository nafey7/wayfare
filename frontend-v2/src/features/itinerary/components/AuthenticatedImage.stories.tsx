import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box, Text } from '@mantine/core';
import { Provider } from 'react-redux';
import { expect, within } from 'storybook/test';
import { AuthenticatedImage } from './AuthenticatedImage';
import { createAuthenticatedStoryStore } from '@/stories/helpers/createStoryStore';

// 1×1 transparent PNG as a data: URI — no auth-proxy fetch needed.
const DATA_URI_PNG =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

const meta: Meta<typeof AuthenticatedImage> = {
  title: 'Itinerary/AuthenticatedImage',
  component: AuthenticatedImage,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <Box style={{ width: 240, height: 160, border: '1px solid var(--mantine-color-default-border)', borderRadius: 4, overflow: 'hidden' }}>
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof AuthenticatedImage>;

/**
 * Default: authenticated session with a data: URI image.
 * Uses a mock JWT token in the Redux store so the component takes the JWT branch.
 * The data: URI is fetched directly (no backend needed).
 */
export const Default: Story = {
  decorators: [
    (Story) => (
      <Provider store={createAuthenticatedStoryStore()}>
        <Story />
      </Provider>
    ),
  ],
  args: {
    src: DATA_URI_PNG,
    alt: 'Sample itinerary image',
    sx: { width: '100%', height: '100%', objectFit: 'cover' },
    fallback: (
      <Box style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--mantine-color-gray-1)' }}>
        <Text size="xs" c="dimmed">Fallback</Text>
      </Box>
    ),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // The component renders either the image or the fallback; confirm no crash.
    const container = canvas.queryAllByRole('img').length > 0
      || canvas.queryAllByText(/fallback/i).length > 0;
    expect(container, 'expected AuthenticatedImage to render (image or fallback)').toBe(true);
  },
};

/**
 * LoadFailure: no src supplied — renders the fallback immediately.
 * In production this happens when the itinerary day has no image URL.
 */
export const LoadFailure: Story = {
  args: {
    src: undefined,
    alt: 'Missing image',
    fallback: (
      <Box style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--mantine-color-gray-1)' }}>
        <Text size="xs" c="dimmed">No image available</Text>
      </Box>
    ),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('No image available')).toBeInTheDocument();
  },
};

/**
 * WithUnavailableLabel: when `src` is omitted the component returns the
 * fallback. The `unavailableLabel` overlay only renders when the
 * Places-session JWT is forbidden (a runtime state that can't be triggered
 * from props alone), so this story shows the fallback path. The label
 * value is preserved as a prop so the story exercises that branch of the
 * type system without asserting the overlay copy.
 */
export const WithUnavailableLabel: Story = {
  args: {
    src: undefined,
    alt: 'Day 1: Gothic Quarter',
    unavailableLabel: 'Day 1: Gothic Quarter',
    fallback: (
      <Box style={{ width: '100%', height: '100%', backgroundColor: 'var(--mantine-color-gray-1)' }} />
    ),
  },
};
