import type { Meta, StoryObj } from '@storybook/react-vite';
import { waitFor, within } from 'storybook/test';
import { Box } from '@mantine/core';
import { FlightResultMessage } from './FlightResultMessage';
import { mockFlightResultsMessage } from '../__fixtures__/mockChatData';
import { PHONE_VIEWPORT } from '@/stories/helpers/viewports';
import { expectAirportPair } from '@/stories/helpers/playAssertions';
import { ChatContext } from '@/features/chat/context/ChatContext';
import { getStubChatContextValue } from '@/stories/helpers/stubChatContextValue';

const meta: Meta<typeof FlightResultMessage> = {
  title: 'Chat/FlightResultMessage',
  component: FlightResultMessage,
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
type Story = StoryObj<typeof FlightResultMessage>;

export const Default: Story = {
  args: { message: mockFlightResultsMessage },
};

/** Oneway trip — same card shape, different search params. */
export const OneWay: Story = {
  args: {
    message: {
      ...mockFlightResultsMessage,
      _id: 'msg-flights-oneway',
      content: {
        messages: [{ text: 'I found flights from London (LHR) to New York (JFK).' }],
      },
      extraData: {
        ...(mockFlightResultsMessage.extraData ?? {}),
        data: {
          ...((mockFlightResultsMessage.extraData?.data as Record<string, unknown>) ?? {}),
          search_params: {
            origin: 'LHR',
            destination: 'JFK',
            departure_date: '2026-06-01',
            journey_type: 'OneWay',
            passengers: { adults: 1, children: 0, infants: 0 },
          },
        },
      },
    },
  },
};

/** Falls back to error UI when extraData is missing. */
export const ErrorFallback: Story = {
  args: {
    message: {
      ...mockFlightResultsMessage,
      extraData: undefined,
    },
  },
};

/**
 * Mobile (375 px) — `useIsMdUp() === false` makes `FlightResultMessage` render
 * the full `FlightSearchResultsPanel` inline (Cheapest / Best / Fastest tabs +
 * cards) instead of a "View flights" CTA bubble. This story compares that
 * mobile layout before/after the MUI → Mantine migration.
 *
 * The play function asserts IATA codes that appear in both render paths:
 * inline panel at 375 px (Storybook UI) and summary text at 1280 px (vitest).
 */
export const Mobile: Story = {
  parameters: { viewport: PHONE_VIEWPORT },
  args: { message: mockFlightResultsMessage },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // At mobile width `useIsMdUp() === false` mounts the inline
    // FlightSearchResultsPanel with real flight cards (driven by `segments[]`
    // in the fixture). AMS/BCN appear on each card.
    await waitFor(() => expectAirportPair(canvas, 'AMS', 'BCN'));
  },
};
