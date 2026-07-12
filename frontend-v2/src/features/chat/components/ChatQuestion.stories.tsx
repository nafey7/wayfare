import type { Meta, StoryObj } from '@storybook/react-vite';
import { Stack, Box } from '@mantine/core';
import { expect, fn, within } from 'storybook/test';
import { ChatQuestion, type ChatSuggestionItem } from './ChatQuestion';

const meta: Meta<typeof ChatQuestion> = {
  title: 'Chat/ChatQuestion',
  component: ChatQuestion,
  args: {
    onSelect: fn(),
  },
  parameters: {
    backgrounds: { default: 'white' },
    viewport: { defaultViewport: 'mobile1' },
  },
  decorators: [
    (Story) => (
      <Box p="md" bg="white">
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof ChatQuestion>;

const GUEST_OPENING: ChatSuggestionItem[] = [
  { id: 'tokyo', label: 'Tokyo next spring' },
  { id: 'lisbon', label: 'Lisbon weekend' },
  { id: 'warm', label: 'Somewhere warm' },
  { id: 'signin', label: 'Sign in to save trips', variant: 'signIn' },
];

const SIGNED_IN_OPENING: ChatSuggestionItem[] = [
  { id: 'tokyo', label: 'Tokyo next spring' },
  { id: 'lisbon', label: 'Lisbon weekend' },
  { id: 'warm', label: 'Somewhere warm' },
  { id: 'surprise', label: 'Surprise me' },
];

const SIGNED_IN_WITH_HISTORY: ChatSuggestionItem[] = [
  { id: 'paris', label: 'Paris again?' },
  { id: 'tokyo', label: 'Tokyo next spring' },
  { id: 'warm', label: 'Somewhere warm' },
  { id: 'surprise', label: 'Surprise me' },
];

export const GuestOpening: Story = {
  name: 'Guest · opening',
  args: {
    message: 'Where would you like to go today?',
    suggestions: GUEST_OPENING,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Where would you like to go today?')).toBeTruthy();
    expect(canvas.getByText('Tokyo next spring')).toBeTruthy();
    expect(canvas.getByText('Sign in to save trips')).toBeTruthy();
  },
};

export const SignedInNoHistory: Story = {
  name: 'Signed in · no history',
  args: {
    message: 'Where would you like to go today?',
    suggestions: SIGNED_IN_OPENING,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Where would you like to go today?')).toBeTruthy();
    expect(canvas.getByText('Tokyo next spring')).toBeTruthy();
    expect(canvas.getByText('Surprise me')).toBeTruthy();
  },
};

export const SignedInWithHistory: Story = {
  name: 'Signed in · with history',
  args: {
    message: 'Where would you like to go today?',
    suggestions: SIGNED_IN_WITH_HISTORY,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Where would you like to go today?')).toBeTruthy();
    expect(canvas.getByText('Paris again?')).toBeTruthy();
  },
};

export const AnsweredMidTransition: Story = {
  name: 'Answered · mid-transition (typing next question)',
  render: () => (
    <Stack gap="md">
      <ChatQuestion
        message="Where would you like to go today?"
        suggestions={SIGNED_IN_OPENING}
        answeredWith="tokyo"
      />
      <ChatQuestion message="" typing />
    </Stack>
  ),
};

export const AnsweredNextTurn: Story = {
  name: 'Answered · next turn',
  render: () => (
    <Stack gap="md">
      <ChatQuestion
        message="Where would you like to go today?"
        suggestions={SIGNED_IN_OPENING}
        answeredWith="tokyo"
      />
      <ChatQuestion
        message="Nice — when are you thinking?"
        suggestions={[
          { id: 'march', label: 'Late March' },
          { id: 'april', label: 'April' },
          { id: 'flexible', label: 'Flexible' },
        ]}
      />
    </Stack>
  ),
};

export const MultiTurn: Story = {
  name: 'Multi-turn conversation',
  render: () => (
    <Stack gap="md">
      <ChatQuestion
        message="Where would you like to go today?"
        suggestions={SIGNED_IN_OPENING}
        answeredWith="tokyo"
      />
      <ChatQuestion
        message="Nice — when are you thinking?"
        suggestions={[
          { id: 'march', label: 'Late March' },
          { id: 'april', label: 'April' },
          { id: 'flexible', label: 'Flexible' },
        ]}
        answeredWith="march"
      />
      <ChatQuestion
        message="How many travelling?"
        suggestions={[
          { id: 'solo', label: 'Just me' },
          { id: 'two', label: '2 adults' },
          { id: 'family', label: 'Family' },
        ]}
      />
    </Stack>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Where would you like to go today?')).toBeTruthy();
    expect(canvas.getByText('Nice — when are you thinking?')).toBeTruthy();
    expect(canvas.getByText('How many travelling?')).toBeTruthy();
    // Only the final unanswered turn should show active chips
    expect(canvas.getByText('Just me')).toBeTruthy();
    expect(canvas.getByText('2 adults')).toBeTruthy();
  },
};
