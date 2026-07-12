import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn } from 'storybook/test';
import { SuggestedReplies } from './SuggestedReplies';
import type { ChatSuggestion } from '@/types/chat';

const sampleSuggestions: ChatSuggestion[] = [
  { title: 'Search flights', command: 'Find me flights next month' },
  { title: 'Book a hotel', command: 'I need a hotel for my trip' },
  { title: 'Plan an itinerary', command: 'Plan a 5-day trip' },
];

const meta: Meta<typeof SuggestedReplies> = {
  title: 'Chat/SuggestedReplies',
  component: SuggestedReplies,
  args: {
    onSelect: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof SuggestedReplies>;

export const WithSuggestions: Story = {
  args: {
    suggestions: sampleSuggestions,
  },
};

export const Empty: Story = {
  args: {
    suggestions: [],
  },
};

export const SingleChip: Story = {
  args: {
    suggestions: [{ title: 'Continue', command: 'Tell me more' }],
  },
};

export const ManySuggestions: Story = {
  args: {
    suggestions: [
      ...sampleSuggestions,
      { title: 'Weekend getaway', command: 'Weekend trip ideas near me' },
      { title: 'Budget options', command: 'Show me budget-friendly travel options' },
    ],
  },
};
