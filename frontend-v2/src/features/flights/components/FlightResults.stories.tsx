import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn, within } from 'storybook/test';
import { FlightResults } from './FlightResults';
import {
  mockFlightCardOneWay,
  mockFlightCardRoundTrip,
  mockFlightCardMultiStop,
} from '../__fixtures__/mockFlightSearchData';
import {
  expectFlightCardPopulated,
} from '@/stories/helpers/playAssertions';

const meta: Meta<typeof FlightResults> = {
  title: 'Flights/FlightResults',
  component: FlightResults,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 700 }}>
        <Story />
      </div>
    ),
  ],
  args: {
    onFlightSelect: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof FlightResults>;

/** Three flight cards — one-way, round-trip, multi-stop. */
export const Default: Story = {
  args: {
    flights: [mockFlightCardOneWay, mockFlightCardRoundTrip, mockFlightCardMultiStop],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // All three cards render — at least two AMS codes visible (outbound + return legs)
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
    });
  },
};

/** No flights matching current search criteria. */
export const Empty: Story = {
  args: {
    flights: [],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(
      canvas.getByText('No flights found. Try adjusting your search criteria.')
    ).toBeInTheDocument();
  },
};

/** One flight in the process of being booked (card shows wait cursor, aria-busy). */
export const Selecting: Story = {
  args: {
    flights: [mockFlightCardOneWay],
    selectingFlightId: mockFlightCardOneWay.id,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
    });
    // Card is marked busy (aria-busy) while a booking request is in-flight
    const card = canvasElement.querySelector('[aria-busy="true"]');
    expect(card).toBeTruthy();
  },
};
