import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn } from 'storybook/test';
import { Box } from '@mantine/core';
import { ChatHeader } from './ChatHeader';

const meta: Meta<typeof ChatHeader> = {
  title: 'Chat/ChatHeader',
  component: ChatHeader,
  parameters: {
    layout: 'centered',
  },
  args: {
    onClose: fn(),
    onClearChat: fn(),
    onToggleSound: fn(),
    onToggleAutoScroll: fn(),
    onToggleFullScreen: fn(),
    soundEnabled: true,
    autoScroll: true,
    isFullScreen: false,
    showCloseButton: true,
    showFullScreenButton: true,
  },
  decorators: [
    (Story) => (
      <Box w={440} style={{ border: '1px solid var(--mantine-color-gray-3)', borderRadius: 8, overflow: 'hidden' }}>
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof ChatHeader>;

export const Default: Story = {};

export const Fullscreen: Story = {
  args: {
    isFullScreen: true,
  },
};

export const SoundOff: Story = {
  args: {
    soundEnabled: false,
  },
};

export const AutoScrollOff: Story = {
  args: {
    autoScroll: false,
  },
};

/** Standalone chat view: no close button, no fullscreen toggle. */
export const Standalone: Story = {
  args: {
    showCloseButton: false,
    showFullScreenButton: false,
  },
};
