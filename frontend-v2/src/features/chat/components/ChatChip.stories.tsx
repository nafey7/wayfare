import type { Meta, StoryObj } from '@storybook/react-vite';
import { Group } from '@mantine/core';
import { expect, fn, within } from 'storybook/test';
import { ChatChip } from './ChatChip';

const meta: Meta<typeof ChatChip> = {
  title: 'Chat/ChatChip',
  component: ChatChip,
  args: {
    onClick: fn(),
  },
  parameters: {
    viewport: { defaultViewport: 'mobile1' },
  },
};

export default meta;
type Story = StoryObj<typeof ChatChip>;

export const Active: Story = {
  args: { label: 'Tokyo next spring', variant: 'active' },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Tokyo next spring')).toBeTruthy();
  },
};

export const Selected: Story = {
  args: { label: 'Tokyo next spring', variant: 'selected' },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Tokyo next spring')).toBeTruthy();
  },
};

export const SignIn: Story = {
  args: { label: 'Sign in to save trips', variant: 'signIn' },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Sign in to save trips')).toBeTruthy();
  },
};

export const AllVariants: Story = {
  render: (args) => (
    <Group gap="xs" wrap="wrap">
      <ChatChip label="Tokyo next spring" variant="active" onClick={args.onClick} />
      <ChatChip label="Late March" variant="selected" />
      <ChatChip label="Sign in to save trips" variant="signIn" onClick={args.onClick} />
    </Group>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Tokyo next spring')).toBeTruthy();
    expect(canvas.getByText('Late March')).toBeTruthy();
    expect(canvas.getByText('Sign in to save trips')).toBeTruthy();
  },
};
