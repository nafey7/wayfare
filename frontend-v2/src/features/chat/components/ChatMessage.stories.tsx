import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { ChatMessage } from './ChatMessage';
import {
  mockBotTextMessage,
  mockBotMarkdownMessage,
  mockFlightResultsMessage,
  mockHotelResultsMessage,
  mockItineraryResultsMessage,
  mockTypingMessage,
  mockUserMessage,
} from './__fixtures__/mockChatData';

const meta: Meta<typeof ChatMessage> = {
  title: 'Chat/ChatMessage',
  component: ChatMessage,
  parameters: {
    layout: 'padded',
  },
  decorators: [
    (Story) => (
      <Box w={480} style={{ backgroundColor: 'var(--mantine-color-gray-0)', padding: 16, borderRadius: 8 }}>
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof ChatMessage>;

export const UserMessage: Story = {
  args: { message: mockUserMessage },
};

export const BotText: Story = {
  args: { message: mockBotTextMessage },
};

export const BotMarkdown: Story = {
  args: { message: mockBotMarkdownMessage },
};

export const TypingIndicator: Story = {
  args: { message: mockTypingMessage },
};

export const FlightSearchResults: Story = {
  args: { message: mockFlightResultsMessage },
};

export const HotelSearchResults: Story = {
  args: { message: mockHotelResultsMessage },
};

export const ItineraryResults: Story = {
  args: { message: mockItineraryResultsMessage },
};
