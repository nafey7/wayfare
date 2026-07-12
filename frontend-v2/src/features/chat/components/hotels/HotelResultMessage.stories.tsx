import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, waitFor, within } from 'storybook/test';
import { Box } from '@mantine/core';
import { HotelResultMessage } from './HotelResultMessage';
import { mockHotelResultsMessage } from '../__fixtures__/mockChatData';
import { PHONE_VIEWPORT } from '@/stories/helpers/viewports';
import { ChatContext } from '@/features/chat/context/ChatContext';
import { getStubChatContextValue } from '@/stories/helpers/stubChatContextValue';

const meta: Meta<typeof HotelResultMessage> = {
  title: 'Chat/HotelResultMessage',
  component: HotelResultMessage,
  parameters: {
    layout: 'padded',
  },
  decorators: [
    (Story) => (
      <ChatContext.Provider value={getStubChatContextValue()}>
        <Box style={{ width: 480, backgroundColor: '#fafafa', padding: 16, borderRadius: 4 }}>
          <Story />
        </Box>
      </ChatContext.Provider>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof HotelResultMessage>;

export const Default: Story = {
  args: { message: mockHotelResultsMessage },
};

/** Multi-room booking: 2 rooms, 4 guests. */
export const MultiRoom: Story = {
  args: {
    message: {
      ...mockHotelResultsMessage,
      _id: 'msg-hotels-multiroom',
      extraData: {
        ...(mockHotelResultsMessage.extraData ?? {}),
        data: {
          ...((mockHotelResultsMessage.extraData?.data as Record<string, unknown>) ?? {}),
          search_params: {
            destination: 'Lisbon',
            destination_city: 'Lisbon',
            check_in_date: '2026-07-10',
            check_out_date: '2026-07-15',
            rooms: 2,
            adults: 4,
            children: 1,
          },
        },
      },
    },
  },
};

/**
 * Mobile (375 px) — `useIsMdUp() === false` makes `HotelResultMessage` render
 * the full `HotelSearchResultsPanel` inline (Cheapest / Best / Top Rated tabs +
 * cards) instead of a "View hotels" CTA bubble. This story compares that
 * mobile layout before/after the MUI → Mantine migration.
 */
export const Mobile: Story = {
  parameters: { viewport: PHONE_VIEWPORT },
  args: { message: mockHotelResultsMessage },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      const matches = canvas.queryAllByText(/barcelona/i);
      expect(
        matches.length,
        'destination "Barcelona" must be visible in inline hotel panel'
      ).toBeGreaterThan(0);
    });
  },
};
