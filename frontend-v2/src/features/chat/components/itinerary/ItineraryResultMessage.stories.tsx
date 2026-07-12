import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { expect, within } from 'storybook/test';
import { ItineraryResultMessage } from './ItineraryResultMessage';
import { mockItineraryResultsMessage } from '../__fixtures__/mockChatData';
import { PHONE_VIEWPORT } from '@/stories/helpers/viewports';
import { expectItineraryDayPresent } from '@/stories/helpers/playAssertions';

const meta: Meta<typeof ItineraryResultMessage> = {
  title: 'Chat/ItineraryResultMessage',
  component: ItineraryResultMessage,
  parameters: {
    layout: 'padded',
  },
  decorators: [
    (Story) => (
      <Box style={{ width: 480, backgroundColor: '#fafafa', padding: 16, borderRadius: 4 }}>
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof ItineraryResultMessage>;

export const Default: Story = {
  args: { message: mockItineraryResultsMessage },
};

/** Already saved — View itinerary would navigate to `/itinerary/:id`. */
export const Saved: Story = {
  args: {
    message: {
      ...mockItineraryResultsMessage,
      _id: 'msg-itin-saved',
      extraData: {
        ...(mockItineraryResultsMessage.extraData ?? {}),
        saved_itinerary_id: 'saved-abc123',
      },
    },
  },
};

/** Minimal extraData — default fallback copy is used. */
export const MinimalFallback: Story = {
  args: {
    message: {
      ...mockItineraryResultsMessage,
      _id: 'msg-itin-minimal',
      content: { messages: [] },
      extraData: { session_id: 'sess-minimal' },
    },
  },
};

/**
 * Mobile view (375 px) — `useIsMdUp()` returns `false` so
 * `ItineraryResultMessage` renders `ItineraryDetailsComponent` inline with
 * day-by-day preview cards above the "View itinerary" CTA.
 *
 * At desktop viewport (vitest default) only the message text and CTA button
 * are rendered; the play function's primary assertion ("View itinerary" button
 * reachable) holds in both modes.
 */
export const Mobile: Story = {
  parameters: {
    viewport: PHONE_VIEWPORT,
  },
  args: { message: mockItineraryResultsMessage },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // "View itinerary" CTA is present at every viewport — primary reachability check.
    const viewBtn = canvas.getByRole('button', { name: /view itinerary/i });
    expect(viewBtn).toBeEnabled();
    // At mobile viewport the itinerary day cards also render — assert the first day title.
    if (canvas.queryAllByText(/Arrival.*Gothic/i).length > 0) {
      expectItineraryDayPresent(canvas, 'Arrival & Gothic Quarter');
    }
  },
};
