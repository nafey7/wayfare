import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { expect, within } from 'storybook/test';
import { FlightDetailsPriceBreakdownCard } from './FlightDetailsPriceBreakdownCard';

const meta: Meta<typeof FlightDetailsPriceBreakdownCard> = {
  title: 'Flights/Booking/FlightDetailsPriceBreakdownCard',
  component: FlightDetailsPriceBreakdownCard,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <Box style={{ maxWidth: 600 }}>
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof FlightDetailsPriceBreakdownCard>;

/** Standard fare with 5% platform fee applied. */
export const Default: Story = {
  args: {
    baseFare: 180,
    totalTax: 30,
    ticketsAmount: 210,
    platformFee: 10.5,
    platformFeePercentage: 5,
    totalFare: 220.5,
    currency: 'EUR',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Price Breakdown')).toBeInTheDocument();
    expect(canvas.getByText('Base Fare')).toBeInTheDocument();
    expect(canvas.getByText('Taxes & Fees')).toBeInTheDocument();
    expect(canvas.getByText(/Platform Fee \(5%\)/)).toBeInTheDocument();
    expect(canvas.getByText('Total Amount')).toBeInTheDocument();
  },
};

/** USD currency with higher amounts. */
export const HighFareUSD: Story = {
  args: {
    baseFare: 1850,
    totalTax: 320,
    ticketsAmount: 2170,
    platformFee: 108.5,
    platformFeePercentage: 5,
    totalFare: 2278.5,
    currency: 'USD',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/Platform Fee \(5%\)/)).toBeInTheDocument();
    expect(canvas.getByText('Total Amount')).toBeInTheDocument();
  },
};
