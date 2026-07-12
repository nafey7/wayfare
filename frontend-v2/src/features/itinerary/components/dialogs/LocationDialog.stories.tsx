import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn, expect, within } from 'storybook/test';
import { LocationDialog } from './LocationDialog';

const meta: Meta<typeof LocationDialog> = {
  title: 'Itinerary/dialogs/LocationDialog',
  component: LocationDialog,
  parameters: { layout: 'fullscreen' },
  args: {
    open: true,
    onClose: fn(),
    onUpdate: fn(),
    onAddPlace: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof LocationDialog>;

export const Default: Story = {
  args: { initialLocation: 'Barcelona, Spain' },
  play: async () => {
    const canvas = within(document.body as HTMLElement);
    expect(canvas.getByText('Where')).toBeInTheDocument();
    expect(canvas.getByText('Add place')).toBeInTheDocument();
  },
};

export const Empty: Story = {
  args: { initialLocation: '' },
};
