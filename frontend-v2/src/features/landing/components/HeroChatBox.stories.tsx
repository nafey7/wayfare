import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn, userEvent, within } from 'storybook/test';
import { Box } from '@mantine/core';

import { HeroChatBox } from './HeroChatBox';

const meta: Meta<typeof HeroChatBox> = {
  title: 'Marketing/HeroChatBox',
  component: HeroChatBox,
  parameters: {
    layout: 'centered',
  },
  decorators: [
    (Story) => (
      <Box style={{ width: 'min(640px, 90vw)' }}>
        <Story />
      </Box>
    ),
  ],
  args: {
    onSubmit: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof HeroChatBox>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const input = canvas.getByRole('textbox', { name: /chat with voya ai/i });
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('placeholder', 'Where do you want to go?');
    expect(
      canvas.getByText(/Voya AI plans flights, hotels, and a day-by-day itinerary/i),
    ).toBeInTheDocument();
    expect(canvas.getByRole('button', { name: /send to voya ai/i })).toBeInTheDocument();
  },
};

export const Compact: Story = {
  args: {
    variant: 'compact',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByRole('textbox', { name: /chat with voya ai/i })).toBeInTheDocument();
    expect(canvas.getByRole('button', { name: /send to voya ai/i })).toBeInTheDocument();
  },
};

export const CustomCopy: Story = {
  args: {
    placeholder: 'Try: 5 days in Lisbon next month',
    helperText: 'Press Enter to send — Voya AI takes it from there.',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(
      canvas.getByPlaceholderText('Try: 5 days in Lisbon next month'),
    ).toBeInTheDocument();
    expect(
      canvas.getByText('Press Enter to send — Voya AI takes it from there.'),
    ).toBeInTheDocument();
  },
};

export const NoHelperText: Story = {
  args: {
    helperText: '',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(
      canvas.queryByText(/Voya AI plans flights, hotels, and a day-by-day itinerary/i),
    ).not.toBeInTheDocument();
  },
};

export const SubmitsOnEnter: Story = {
  args: {
    onSubmit: fn(),
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    const input = canvas.getByRole('textbox', { name: /chat with voya ai/i });
    await userEvent.type(input, '  Trip to Tokyo  ');
    await userEvent.keyboard('{Enter}');
    expect(args.onSubmit).toHaveBeenCalledWith('Trip to Tokyo');
  },
};

export const IgnoresEmptySubmit: Story = {
  args: {
    onSubmit: fn(),
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    const button = canvas.getByRole('button', { name: /send to voya ai/i });
    await userEvent.click(button);
    expect(args.onSubmit).not.toHaveBeenCalled();
  },
};
