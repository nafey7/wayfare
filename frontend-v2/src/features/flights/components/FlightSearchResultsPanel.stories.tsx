import type { Meta, StoryObj } from '@storybook/react-vite';
import { within } from 'storybook/test';
import { FlightSearchResultsPanel } from './FlightSearchResultsPanel';
import {
  mockExtractedFlightSearchData,
  mockExtractedDateRangeData,
} from '../__fixtures__/mockFlightData';
import type { ExtractedFlightSearchData } from '@/types/api.helpers';
import { ChatContext } from '@/features/chat/context/ChatContext';
import { getStubChatContextValue } from '@/stories/helpers/stubChatContextValue';
import { expectFlightCardPopulated } from '@/stories/helpers/playAssertions';

/** Build a single-date ExtractedFlightSearchData from the first available date in the date-range fixture. */
function dateRangeToSingleDate(): ExtractedFlightSearchData {
  const dateEntry = mockExtractedDateRangeData.dates[0]!;
  return {
    session_id: dateEntry.session_id ?? 'sess-dr-0',
    flights: [
      ...(dateEntry.categories?.cheapest?.flights ?? []),
      ...(dateEntry.categories?.fastest?.flights ?? []),
      ...(dateEntry.categories?.best_value?.flights ?? []),
    ],
    data: {
      search_params: {
        ...mockExtractedFlightSearchData.data.search_params,
        departure_date: dateEntry.date,
      },
      summary: dateEntry.summary ?? mockExtractedFlightSearchData.data.summary,
      categories: dateEntry.categories ?? mockExtractedFlightSearchData.data.categories,
    },
  };
}

const meta: Meta<typeof FlightSearchResultsPanel> = {
  title: 'Flights/FlightSearchResultsPanel',
  component: FlightSearchResultsPanel,
  parameters: {
    layout: 'padded',
    initialEntries: ['/flights/search'],
  },
  decorators: [
    (Story) => (
      <ChatContext.Provider value={getStubChatContextValue()}>
        <div style={{ maxWidth: 800 }}>
          <Story />
        </div>
      </ChatContext.Provider>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof FlightSearchResultsPanel>;

/** Recommendations layout: sticky bottom bar + "Show All Flights" CTA */
export const Default: Story = {
  args: {
    data: mockExtractedFlightSearchData,
    source: 'recommendations',
    stickyBottomBar: true,
  },
  // AMS↔BCN round-trip; both legs must populate (PR #852 regressed inbound).
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
      inbound: { origin: 'BCN', destination: 'AMS' },
    });
  },
};

/** Chat layout: inline CTA, summary text visible */
export const ChatVariant: Story = {
  args: {
    data: mockExtractedFlightSearchData,
    source: 'chat',
    showSummary: true,
    stickyBottomBar: false,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
      inbound: { origin: 'BCN', destination: 'AMS' },
    });
  },
};

/** Date-range first date entry rendered as a standard panel */
export const WithDateRangeEntry: Story = {
  args: {
    data: dateRangeToSingleDate(),
    source: 'recommendations',
    stickyBottomBar: true,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
      inbound: { origin: 'BCN', destination: 'AMS' },
    });
  },
};
