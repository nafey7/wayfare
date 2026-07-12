import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { within } from 'storybook/test';
import { fn } from 'storybook/test';
import type { RoomOccupancy } from '@/types/hotels';
import { expectRoomConfigPopulated, expectNoPlaceholderText } from '@/stories/helpers/playAssertions';
import { RoomConfigurator } from './RoomConfigurator';
import {
  singleRoom,
  multiRoom,
  maxGuestsRoom,
} from '../__fixtures__/mockHotelDetailData';

const meta: Meta<typeof RoomConfigurator> = {
  title: 'Hotels/RoomConfigurator',
  component: RoomConfigurator,
};

export default meta;
type Story = StoryObj<typeof RoomConfigurator>;

/**
 * Stateful wrapper — RoomConfigurator is a controlled component; the story
 * needs a useState wrapper so the selects respond to user interaction.
 */
function StatefulRoomConfigurator(props: { initialRooms: RoomOccupancy[]; showRoomCount?: boolean }) {
  const [rooms, setRooms] = useState<RoomOccupancy[]>(props.initialRooms);
  return (
    <RoomConfigurator rooms={rooms} onChange={setRooms} showRoomCount={props.showRoomCount ?? true} />
  );
}

export const Default: Story = {
  render: () => <StatefulRoomConfigurator initialRooms={singleRoom} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectRoomConfigPopulated(canvas, { totalAdults: 2, totalChildren: 0 });
    expectNoPlaceholderText(canvas);
  },
};

export const MultiRoom: Story = {
  name: 'Multi-room (2 rooms)',
  render: () => <StatefulRoomConfigurator initialRooms={multiRoom} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectRoomConfigPopulated(canvas, { totalAdults: 3, totalChildren: 1 });
    expectNoPlaceholderText(canvas);
  },
};

export const MaxGuests: Story = {
  name: 'Max guests (2 rooms, many occupants)',
  render: () => <StatefulRoomConfigurator initialRooms={maxGuestsRoom} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectRoomConfigPopulated(canvas, { totalAdults: 7, totalChildren: 5 });
    expectNoPlaceholderText(canvas);
  },
};

export const HiddenRoomCount: Story = {
  name: 'Hidden room count selector',
  render: () => <StatefulRoomConfigurator initialRooms={singleRoom} showRoomCount={false} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // "Rooms" dropdown should be absent
    expectNoPlaceholderText(canvas);
  },
};

// Keep a controlled (non-interactive) variant for testing onChange callback
export const Controlled: Story = {
  args: {
    rooms: singleRoom,
    onChange: fn(),
    showRoomCount: true,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectRoomConfigPopulated(canvas, { totalAdults: 2, totalChildren: 0 });
    expectNoPlaceholderText(canvas);
  },
};
