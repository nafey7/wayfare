import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import { LinkedBookingChips } from './LinkedBookingChips';
import type { LinkedBookings } from '@/types/itineraries';
import { expectLinkedBookingChips } from '@/stories/helpers/playAssertions';

const bothLinked: LinkedBookings = {
  flightVoyaReferences: ['VOYA-FLT-001'],
  hotelVoyaReferences: ['VOYA-HTL-001'],
};

const flightOnly: LinkedBookings = {
  flightVoyaReferences: ['VOYA-FLT-001'],
  hotelVoyaReferences: [],
};

const hotelOnly: LinkedBookings = {
  flightVoyaReferences: [],
  hotelVoyaReferences: ['VOYA-HTL-001'],
};

const multipleRefs: LinkedBookings = {
  flightVoyaReferences: ['VOYA-FLT-001', 'VOYA-FLT-002'],
  hotelVoyaReferences: ['VOYA-HTL-001', 'VOYA-HTL-002'],
};

const meta: Meta<typeof LinkedBookingChips> = {
  title: 'Itinerary/LinkedBookingChips',
  component: LinkedBookingChips,
  // Router supplied by global StorybookProviders; route via parameters.
  parameters: { layout: 'padded', initialEntries: ['/itineraries/itin-01'] },
};

export default meta;
type Story = StoryObj<typeof LinkedBookingChips>;

/** Both flight and hotel booking linked (single refs → navigate to detail). */
export const Default: Story = {
  args: {
    itineraryId: 'itin-01',
    linkedBookings: bothLinked,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectLinkedBookingChips(canvas);
  },
};

/** Only a flight booking linked; hotel chip is disabled. */
export const FlightOnly: Story = {
  args: {
    itineraryId: 'itin-01',
    linkedBookings: flightOnly,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectLinkedBookingChips(canvas);
  },
};

/** Only a hotel booking linked; flight chip is disabled. */
export const HotelOnly: Story = {
  args: {
    itineraryId: 'itin-01',
    linkedBookings: hotelOnly,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectLinkedBookingChips(canvas);
  },
};

/** Multiple refs on both sides → chips navigate to the list view. */
export const MultipleRefs: Story = {
  args: {
    itineraryId: 'itin-01',
    linkedBookings: multipleRefs,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectLinkedBookingChips(canvas);
    // Multiple refs show count in label
    const flightChip = canvas.queryAllByText(/flight booking \(2\)/i);
    expect(flightChip.length).toBeGreaterThan(0);
  },
};

/** No bookings linked — both chips disabled. */
export const NoneLinked: Story = {
  args: {
    itineraryId: 'itin-01',
    linkedBookings: { flightVoyaReferences: [], hotelVoyaReferences: [] },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectLinkedBookingChips(canvas);
  },
};
