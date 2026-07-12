import { useEffect, useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn } from 'storybook/test';
import { Box } from '@mantine/core';
import { ChatInput } from './ChatInput';

// Controlled wrapper so typing works in the story. useEffect syncs when the
// Storybook `value` arg changes (e.g. reset controls, switch story) so the
// field reflects the current arg instead of stale initial state.
function InteractiveChatInput(args: React.ComponentProps<typeof ChatInput>) {
  const [value, setValue] = useState(args.value);
  useEffect(() => {
    setValue(args.value);
  }, [args.value]);
  return (
    <ChatInput
      {...args}
      value={value}
      onChange={(v) => {
        setValue(v);
        args.onChange(v);
      }}
      onSend={(v) => {
        args.onSend(v);
        setValue('');
      }}
    />
  );
}

const meta: Meta<typeof ChatInput> = {
  title: 'Chat/ChatInput',
  component: ChatInput,
  render: (args) => <InteractiveChatInput {...args} />,
  args: {
    value: '',
    onChange: fn(),
    onSend: fn(),
    disabled: false,
    loading: false,
    placeholder: 'Type your message...',
  },
  decorators: [
    (Story) => (
      <Box w={440} style={{ backgroundColor: 'var(--mantine-color-gray-0)' }}>
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof ChatInput>;

export const Empty: Story = {};

export const WithText: Story = {
  args: {
    value: 'Find me flights to Barcelona',
  },
};

export const Loading: Story = {
  args: {
    value: 'Finding the best options…',
    loading: true,
  },
};

export const Disabled: Story = {
  args: {
    value: '',
    disabled: true,
  },
};

export const LongText: Story = {
  args: {
    value:
      'I want to fly from Amsterdam to Barcelona next month for a 5-day trip, ' +
      'preferably direct flights under 200 EUR, and a hotel close to the beach.',
  },
};
