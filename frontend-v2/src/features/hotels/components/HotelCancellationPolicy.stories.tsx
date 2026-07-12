import type { Meta, StoryObj } from '@storybook/react-vite';
import { within } from 'storybook/test';
import {
  expectCancellationCopy,
  expectNoPlaceholderText,
} from '@/stories/helpers/playAssertions';
import { HotelCancellationPolicy } from './HotelCancellationPolicy';
import {
  mockFreeCancellationPolicy,
  mockNonRefundablePolicy,
  mockStringCancellationPolicy,
} from '../__fixtures__/mockHotelDetailData';

const meta: Meta<typeof HotelCancellationPolicy> = {
  title: 'Hotels/HotelCancellationPolicy',
  component: HotelCancellationPolicy,
};

export default meta;
type Story = StoryObj<typeof HotelCancellationPolicy>;

export const Default: Story = {
  args: {
    cancellationPolicy: mockFreeCancellationPolicy,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectCancellationCopy(canvas, { refundable: true });
    expectNoPlaceholderText(canvas);
  },
};

export const FreeCancellation: Story = {
  args: {
    cancellationPolicy: mockFreeCancellationPolicy,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectCancellationCopy(canvas, { refundable: true, hasDeadline: true });
    expectNoPlaceholderText(canvas);
  },
};

export const NonRefundable: Story = {
  args: {
    cancellationPolicy: mockNonRefundablePolicy,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectCancellationCopy(canvas, { refundable: false });
    expectNoPlaceholderText(canvas);
  },
};

export const StringPolicy: Story = {
  name: 'String policy (rate-rules format)',
  args: {
    cancellationPolicy: mockStringCancellationPolicy,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectCancellationCopy(canvas, { containsText: 'Non-refundable' });
    expectNoPlaceholderText(canvas);
  },
};
