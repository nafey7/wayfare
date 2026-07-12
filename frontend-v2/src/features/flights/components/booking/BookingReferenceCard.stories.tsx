import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { expect, within } from 'storybook/test';
import { BookingReferenceCard } from './BookingReferenceCard';

const meta: Meta<typeof BookingReferenceCard> = {
  title: 'Flights/Booking/BookingReferenceCard',
  component: BookingReferenceCard,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <Box style={{ maxWidth: 720 }}>
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof BookingReferenceCard>;

/** Single-flight booking with carrier reference and successful payment. */
export const Default: Story = {
  args: {
    voyaBookingReference: 'VOYA-AB12CD',
    externalBookingReference: 'PNR-XYZ789',
    paymentStatus: 'succeeded',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('VOYA-AB12CD')).toBeInTheDocument();
    expect(canvas.getByText('PNR-XYZ789')).toBeInTheDocument();
    expect(canvas.getByText(/payment status: succeeded/i)).toBeInTheDocument();
  },
};

/** Single-flight booking with no external reference and no payment status (email-link flow). */
export const Minimal: Story = {
  args: {
    voyaBookingReference: 'VOYA-MN34PQ',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('VOYA-MN34PQ')).toBeInTheDocument();
    expect(canvas.queryByText(/external reference/i)).not.toBeInTheDocument();
    expect(canvas.queryByText(/payment status/i)).not.toBeInTheDocument();
  },
};

/** Multi-city booking with group reference and per-leg references. */
export const Multicity: Story = {
  args: {
    voyaBookingReference: 'VOYA-MC-GROUP',
    multicityGroupReference: 'VOYA-MC-GROUP',
    multicityLegs: [
      { legIndex: 0, voyaBookingReference: 'VOYA-LEG-001' },
      { legIndex: 1, voyaBookingReference: 'VOYA-LEG-002' },
      { legIndex: 2, voyaBookingReference: 'VOYA-LEG-003' },
    ],
    paymentStatus: 'succeeded',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Multi-city group')).toBeInTheDocument();
    expect(canvas.getByText('VOYA-LEG-001')).toBeInTheDocument();
    expect(canvas.getByText('VOYA-LEG-002')).toBeInTheDocument();
    expect(canvas.getByText('VOYA-LEG-003')).toBeInTheDocument();
    expect(canvas.getByText(/leg 1/i)).toBeInTheDocument();
    expect(canvas.getByText(/leg 3/i)).toBeInTheDocument();
  },
};

/** Pending payment chip styling (non-success status). */
export const PendingPayment: Story = {
  args: {
    voyaBookingReference: 'VOYA-PD56EF',
    externalBookingReference: 'PNR-PEND01',
    paymentStatus: 'pending',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/payment status: pending/i)).toBeInTheDocument();
  },
};
