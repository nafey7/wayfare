import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, expect, waitFor } from 'storybook/test';
import { Box } from '@mantine/core';
import { HotelSearchResultsPanel } from './HotelSearchResultsPanel';
import { mockExtractedHotelSearchData } from '../__fixtures__/mockHotelData';
import { ChatContext } from '@/features/chat/context/ChatContext';
import { getStubChatContextValue } from '@/stories/helpers/stubChatContextValue';
import type { ExtractedHotelSearchData } from '@/types/api.helpers';

const emptyData: ExtractedHotelSearchData = {
  session_id: 'sess-empty',
  hotels: [],
  data: {
    search_params: {
      destination_city: 'Barcelona',
      country: 'Spain',
      check_in_date: '2026-07-10',
      check_out_date: '2026-07-17',
      rooms: 1,
      adults: 2,
    },
    summary: { total_found: 0, nights: 7 },
    categories: {
      cheapest: { hotels: [] },
      best_value: { hotels: [] },
      highest_rated: { hotels: [] },
    },
  },
};

const meta: Meta<typeof HotelSearchResultsPanel> = {
  title: 'Hotels/HotelSearchResultsPanel',
  component: HotelSearchResultsPanel,
  // Router is supplied by the global StorybookProviders decorator; pass initial route via parameters.
  parameters: { layout: 'padded', initialEntries: ['/hotels/search'] },
  decorators: [
    (Story) => (
      <ChatContext.Provider value={getStubChatContextValue()}>
        <Box style={{ maxWidth: 800 }}>
          <Story />
        </Box>
      </ChatContext.Provider>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof HotelSearchResultsPanel>;

/**
 * Default: recommendations layout. Post-#1034 the panel renders a flat
 * best-value-sorted list inline — no Cheapest/Best/Top Rated tabs and no
 * "Show All Hotels" CTA. Asserts the summary copy and that at least one
 * hotel card from the fixture is on screen.
 */
export const Default: Story = {
  args: {
    data: mockExtractedHotelSearchData,
    source: 'recommendations',
    showSummary: true,
    stickyBottomBar: true,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Tabs and CTA are gone (#1034).
    expect(canvas.queryByRole('tablist')).not.toBeInTheDocument();
    expect(
      canvas.queryByRole('button', { name: /Show All Hotels/i })
    ).not.toBeInTheDocument();
    // Summary text: 7 nights in Barcelona (may appear in multiple elements).
    expect(
      canvas.queryAllByText(/Barcelona/i).length,
      'Barcelona should appear in summary'
    ).toBeGreaterThan(0);
    // At least one hotel card from the fixture is rendered.
    await waitFor(() => {
      expect(canvas.getByText('Barceló Raval')).toBeInTheDocument();
    });
  },
};

/** Chat layout: same flat list, just rendered without the recommendations chrome. */
export const ChatVariant: Story = {
  args: {
    data: mockExtractedHotelSearchData,
    source: 'chat',
    showSummary: true,
    stickyBottomBar: false,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.queryByRole('tablist')).not.toBeInTheDocument();
    expect(
      canvas.queryAllByText(/Barcelona/i).length,
      'Barcelona in summary'
    ).toBeGreaterThan(0);
    await waitFor(() => {
      expect(canvas.getByText('Barceló Raval')).toBeInTheDocument();
    });
  },
};

/**
 * Empty: all category buckets are empty → component returns null.
 * Play function just asserts no crash (canvasElement renders without error).
 */
export const Empty: Story = {
  args: {
    data: emptyData,
    source: 'recommendations',
  },
  play: async ({ canvasElement }) => {
    // Component returns null when all categories empty; container exists but is empty
    expect(canvasElement).toBeInTheDocument();
  },
};
