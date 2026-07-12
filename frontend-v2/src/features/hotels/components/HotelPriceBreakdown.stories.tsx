import type { Meta, StoryObj } from '@storybook/react-vite';
import { within } from 'storybook/test';
import {
  expectPriceBreakdownTotals,
  expectNoPlaceholderText,
} from '@/stories/helpers/playAssertions';
import { HotelPriceBreakdown } from './HotelPriceBreakdown';
import {
  mockPriceBreakdown,
  mockPriceBreakdownWithVoucher,
  mockPriceBreakdownLongStay,
} from '../__fixtures__/mockHotelDetailData';

const meta: Meta<typeof HotelPriceBreakdown> = {
  title: 'Hotels/HotelPriceBreakdown',
  component: HotelPriceBreakdown,
};

export default meta;
type Story = StoryObj<typeof HotelPriceBreakdown>;

export const Default: Story = {
  args: mockPriceBreakdown,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectPriceBreakdownTotals(canvas, { currency: '€', hasTotal: true });
    expectNoPlaceholderText(canvas);
  },
};

export const WithTaxesFees: Story = {
  name: 'With voucher discount',
  args: mockPriceBreakdownWithVoucher,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectPriceBreakdownTotals(canvas, { currency: '€', hasTotal: true, hasDiscount: true });
    expectNoPlaceholderText(canvas);
  },
};

export const LongStay: Story = {
  name: 'Long stay (USD, high total)',
  args: mockPriceBreakdownLongStay,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectPriceBreakdownTotals(canvas, { currency: '$', hasTotal: true });
    expectNoPlaceholderText(canvas);
  },
};
