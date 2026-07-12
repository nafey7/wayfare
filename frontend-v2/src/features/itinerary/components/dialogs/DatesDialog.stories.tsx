import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn, expect, within } from 'storybook/test';
import { DatesDialog } from './DatesDialog';

const meta: Meta<typeof DatesDialog> = {
  title: 'Itinerary/dialogs/DatesDialog',
  component: DatesDialog,
  parameters: { layout: 'fullscreen' },
  args: {
    open: true,
    onClose: fn(),
    onUpdate: fn(),
    initialStartDate: new Date(2026, 5, 10),
    initialEndDate: new Date(2026, 5, 17),
  },
};

export default meta;
type Story = StoryObj<typeof DatesDialog>;

/** Two-month layout (md+ viewport). */
export const Default: Story = {
  args: { mdUp: true },
  play: async () => {
    // Modal portals to document.body, so query body rather than canvasElement.
    const canvas = within(document.body as HTMLElement);
    expect(canvas.getAllByTestId('dates-dialog-calendar')).toHaveLength(2);
  },
};

/** Single-month layout (mobile / sub-md viewport). */
export const Mobile: Story = {
  args: { mdUp: false },
  play: async () => {
    const canvas = within(document.body as HTMLElement);
    expect(canvas.getAllByTestId('dates-dialog-calendar')).toHaveLength(1);
  },
};

/** Hotel variant — different heading copy. */
export const HotelStay: Story = {
  args: { mdUp: true, dialogTitle: 'When are you staying?' },
};
