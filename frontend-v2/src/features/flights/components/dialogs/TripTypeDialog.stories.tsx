import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn, within } from 'storybook/test';
import { TripTypeDialog } from './TripTypeDialog';
import type { TripType } from '@/types/flights';

/**
 * Content-only Mantine radio list (M4-2b refactor — was a Popover with `anchorEl`).
 */
const meta: Meta<typeof TripTypeDialog> = {
  title: 'Flights/dialogs/TripTypeDialog',
  component: TripTypeDialog,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 400, padding: 8 }}>
        <Story />
      </div>
    ),
  ],
  args: {
    onUpdate: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof TripTypeDialog>;

export const Default: Story = {
  args: { value: 'round-trip' },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Round trip')).toBeInTheDocument();
    expect(canvas.getByText('One way')).toBeInTheDocument();
    expect(canvas.getByText('Multi-city')).toBeInTheDocument();
    const roundTrip = canvas.getByRole('button', { name: 'Round trip' });
    expect(roundTrip).toHaveAttribute('aria-pressed', 'true');
  },
};

export const OneWaySelected: Story = {
  args: { value: 'one-way' as TripType },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const oneWay = canvas.getByRole('button', { name: 'One way' });
    expect(oneWay).toHaveAttribute('aria-pressed', 'true');
  },
};

export const Interactive: Story = {
  render: function Render(args) {
    const [value, setValue] = useState<TripType>('round-trip');
    return (
      <TripTypeDialog
        value={value}
        onUpdate={(next) => {
          setValue(next);
          args.onUpdate?.(next);
        }}
      />
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Round trip')).toBeInTheDocument();
  },
};
