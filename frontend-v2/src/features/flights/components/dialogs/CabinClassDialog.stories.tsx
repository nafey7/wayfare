import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn, within } from 'storybook/test';
import { CabinClassDialog } from './CabinClassDialog';
import type { CabinClassUI } from '@/types/flights';

/**
 * Content-only Mantine radio list (M4-2b refactor — was a Popover with `anchorEl`).
 * Stories render the component directly, no portal, no anchor.
 */
const meta: Meta<typeof CabinClassDialog> = {
  title: 'Flights/dialogs/CabinClassDialog',
  component: CabinClassDialog,
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
type Story = StoryObj<typeof CabinClassDialog>;

export const Default: Story = {
  args: { value: 'Economy' },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Economy')).toBeInTheDocument();
    expect(canvas.getByText('Premium Economy')).toBeInTheDocument();
    expect(canvas.getByText('Business')).toBeInTheDocument();
    expect(canvas.getByText('First')).toBeInTheDocument();
    const economy = canvas.getByRole('button', { name: 'Economy' });
    expect(economy).toHaveAttribute('aria-pressed', 'true');
  },
};

export const BusinessSelected: Story = {
  args: { value: 'Business' as CabinClassUI },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const business = canvas.getByRole('button', { name: 'Business' });
    expect(business).toHaveAttribute('aria-pressed', 'true');
  },
};

/** Demonstrates the controlled state — useful as a manual test in Storybook UI. */
export const Interactive: Story = {
  render: function Render(args) {
    const [value, setValue] = useState<CabinClassUI>('Economy');
    return (
      <CabinClassDialog
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
    expect(canvas.getByText('Economy')).toBeInTheDocument();
  },
};
