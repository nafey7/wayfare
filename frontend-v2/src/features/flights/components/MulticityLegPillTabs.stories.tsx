import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn } from 'storybook/test';
import { MulticityLegPillTabs } from './MulticityLegPillTabs';
import { mockLegTabRows, mockLegTabRowsMany } from '../__fixtures__/mockFlightData';

const meta: Meta<typeof MulticityLegPillTabs> = {
  title: 'Flights/MulticityLegPillTabs',
  component: MulticityLegPillTabs,
  parameters: {
    layout: 'padded',
  },
  args: {
    onChange: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof MulticityLegPillTabs>;

export const Default: Story = {
  args: {
    legs: mockLegTabRows,
    value: 0,
  },
};

export const SecondTabActive: Story = {
  args: {
    legs: mockLegTabRows,
    value: 1,
  },
};

export const ManyLegs: Story = {
  args: {
    legs: mockLegTabRowsMany,
    value: 2,
  },
};
