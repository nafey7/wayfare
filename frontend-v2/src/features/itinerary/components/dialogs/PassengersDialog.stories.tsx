import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn, expect, within } from 'storybook/test';
import { PassengersDialog } from './PassengersDialog';

const meta: Meta<typeof PassengersDialog> = {
  title: 'Itinerary/dialogs/PassengersDialog',
  component: PassengersDialog,
  parameters: { layout: 'fullscreen' },
  args: {
    open: true,
    onClose: fn(),
    onUpdate: fn(),
    onServiceAnimalClick: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof PassengersDialog>;

export const Default: Story = {
  args: {
    initialCounts: { adults: 2, children: 1, infants: 0, pets: 0 },
  },
  play: async () => {
    const canvas = within(document.body as HTMLElement);
    expect(canvas.getByText('Who')).toBeInTheDocument();
    expect(canvas.getByText('Adults')).toBeInTheDocument();
    expect(canvas.getByText('Bringing a service animal?')).toBeInTheDocument();
  },
};

export const Family: Story = {
  args: {
    initialCounts: { adults: 2, children: 3, infants: 1, pets: 1 },
  },
};
