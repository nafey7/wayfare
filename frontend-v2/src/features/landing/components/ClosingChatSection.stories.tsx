import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn, userEvent, within } from 'storybook/test';

import { ClosingChatSection } from './ClosingChatSection';

const meta: Meta<typeof ClosingChatSection> = {
  title: 'Marketing/ClosingChatSection',
  component: ClosingChatSection,
  parameters: {
    layout: 'fullscreen',
  },
  args: {
    onSearchSubmit: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof ClosingChatSection>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(
      canvas.getByRole('heading', { name: 'Ready when you are.' }),
    ).toBeInTheDocument();
    expect(canvas.getByText('Start planning')).toBeInTheDocument();
    expect(
      canvas.getByText(/Tell Voya AI where you want to go/i),
    ).toBeInTheDocument();
    expect(canvas.getByRole('textbox', { name: /chat with voya ai/i })).toBeInTheDocument();
    expect(canvas.getByRole('button', { name: /send to voya ai/i })).toBeInTheDocument();
  },
};

export const CustomCopy: Story = {
  args: {
    title: 'Plan your next escape',
    subtitle: 'Describe your perfect trip and Voya AI handles the rest.',
    eyebrow: 'Get started',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(
      canvas.getByRole('heading', { name: 'Plan your next escape' }),
    ).toBeInTheDocument();
    expect(canvas.getByText('Get started')).toBeInTheDocument();
    expect(
      canvas.getByText('Describe your perfect trip and Voya AI handles the rest.'),
    ).toBeInTheDocument();
  },
};

export const NoEyebrow: Story = {
  args: {
    eyebrow: '',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.queryByText('Start planning')).not.toBeInTheDocument();
    expect(
      canvas.getByRole('heading', { name: 'Ready when you are.' }),
    ).toBeInTheDocument();
  },
};

export const SubmitsTypedQuery: Story = {
  args: {
    onSearchSubmit: fn(),
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    const input = canvas.getByRole('textbox', { name: /chat with voya ai/i });
    await userEvent.type(input, '5 days in Lisbon');
    await userEvent.keyboard('{Enter}');
    expect(args.onSearchSubmit).toHaveBeenCalledWith('5 days in Lisbon');
  },
};
