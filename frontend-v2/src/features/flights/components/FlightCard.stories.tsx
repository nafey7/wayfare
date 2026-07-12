import type { Meta, StoryObj } from '@storybook/react-vite';
import { Stack } from '@mantine/core';
import { expect, fn, within } from 'storybook/test';
import { FlightCard } from './FlightCard';
import {
  mockFlightCardOneWay,
  mockFlightCardRoundTrip,
  mockFlightCardMultiStop,
  mockFlightCardBestValue,
} from '../__fixtures__/mockFlightSearchData';
import {
  expectFlightCardPopulated,
  expectNoPlaceholderText,
} from '@/stories/helpers/playAssertions';

const meta: Meta<typeof FlightCard> = {
  title: 'Flights/FlightCard',
  component: FlightCard,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 560 }}>
        <Story />
      </div>
    ),
  ],
  args: {
    onSelect: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof FlightCard>;

/** One-way, non-stop AMS → BCN. */
export const Default: Story = {
  args: {
    flight: mockFlightCardOneWay,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
    });
  },
};

/** Round-trip AMS ↔ BCN — both legs must populate. */
export const RoundTrip: Story = {
  args: {
    flight: mockFlightCardRoundTrip,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
      inbound: { origin: 'BCN', destination: 'AMS' },
    });
  },
};

/** One-way with 1 stop via MAD. */
export const MultiStop: Story = {
  args: {
    flight: mockFlightCardMultiStop,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
    });
    expect(canvas.getByText('1 stop via MAD')).toBeInTheDocument();
  },
};

/** Round-trip with "Best Value" tag badge. */
export const BestValue: Story = {
  args: {
    flight: mockFlightCardBestValue,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
      inbound: { origin: 'BCN', destination: 'AMS' },
    });
    expect(canvas.getByText('Best Value')).toBeInTheDocument();
  },
};

/** Selected state — brand border shown when chosen for a multicity leg. */
export const Selected: Story = {
  args: {
    flight: mockFlightCardOneWay,
    isSelected: true,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
    });
    expectNoPlaceholderText(canvas);
  },
};

/** Info button — verifies the details button is present on the card. */
export const InfoButton: Story = {
  args: {
    flight: mockFlightCardOneWay,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
    });
    expect(canvas.getByRole('button', { name: 'Flight details' })).toBeInTheDocument();
  },
};

/** Stack of all variants — visual smoke test for the full range. */
export const AllVariants: Story = {
  render: () => (
    <Stack gap={0} style={{ maxWidth: 560 }}>
      {[mockFlightCardOneWay, mockFlightCardRoundTrip, mockFlightCardMultiStop, mockFlightCardBestValue].map(
        (f) => (
          <FlightCard key={f.id} flight={f} />
        )
      )}
    </Stack>
  ),
};
