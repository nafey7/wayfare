import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn, expect, within } from 'storybook/test';
import { BudgetDialog } from './BudgetDialog';

const meta: Meta<typeof BudgetDialog> = {
  title: 'Itinerary/dialogs/BudgetDialog',
  component: BudgetDialog,
  parameters: { layout: 'fullscreen' },
  args: {
    open: true,
    onClose: fn(),
    onUpdate: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof BudgetDialog>;

export const Default: Story = {
  args: { initialBudget: 'any' },
  play: async () => {
    const canvas = within(document.body as HTMLElement);
    expect(canvas.getByText('Budget')).toBeInTheDocument();
    expect(canvas.getByText('Any budget')).toBeInTheDocument();
    expect(canvas.getByText('Luxury')).toBeInTheDocument();
  },
};

export const Luxury: Story = {
  args: { initialBudget: 'luxury' },
};
