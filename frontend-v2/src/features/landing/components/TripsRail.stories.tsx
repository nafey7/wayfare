import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn, within } from 'storybook/test';
import { TripsRail } from './TripsRail';
import type { InspirationTripData } from './InspirationTripCard';
import { INTEREST_CHIPS } from '../data/inspirationTrips';

const SAMPLE_TRIPS: InspirationTripData[] = [
  {
    id: 'we-lis',
    title: 'Weekend in Lisbon',
    builtInSeconds: 41,
    flightRoute: 'MAD → LIS',
    hotelName: 'Memmo Alfama',
    stops: 8,
    priceAmount: 390,
    duration: '2 nights',
    theme: 'lisbon',
    tag: 'Quick getaway',
    rating: 4.8,
  },
  {
    id: 'we-cph',
    title: 'Weekend in Copenhagen',
    builtInSeconds: 38,
    flightRoute: 'AMS → CPH',
    hotelName: 'Hotel Sanders',
    stops: 7,
    priceAmount: 440,
    duration: '2 nights',
    theme: 'tokyo',
    tag: 'Design',
    rating: 4.9,
  },
  {
    id: 'we-bcn',
    title: 'Weekend in Barcelona',
    builtInSeconds: 36,
    flightRoute: 'CDG → BCN',
    hotelName: 'Hotel Brummell',
    stops: 9,
    priceAmount: 360,
    duration: '2 nights',
    theme: 'bali',
    tag: 'Foodie',
    rating: 4.7,
  },
  {
    id: 'we-mar',
    title: 'Weekend in Marrakech',
    builtInSeconds: 44,
    flightRoute: 'SVQ → RAK',
    hotelName: 'El Fenn',
    stops: 10,
    priceAmount: 330,
    duration: '3 nights',
    theme: 'bangkok',
    tag: 'Culture',
    rating: 4.7,
  },
];

const meta: Meta<typeof TripsRail> = {
  title: 'Marketing/TripsRail',
  component: TripsRail,
  args: {
    onTripClick: fn(),
    onToggleSave: fn(),
    onChipSelect: fn(),
  },
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof TripsRail>;

export const Default: Story = {
  args: {
    title: 'Trips for this weekend',
    subtitle: 'Quick escapes — leave Friday, back Sunday',
    trips: SAMPLE_TRIPS,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Trips for this weekend')).toBeInTheDocument();
    expect(canvas.getByText('Weekend in Lisbon')).toBeInTheDocument();
    expect(canvas.getByText('Weekend in Copenhagen')).toBeInTheDocument();
  },
};

export const MistBackground: Story = {
  args: {
    title: 'From London',
    subtitle: 'Trips starting where you are',
    trips: SAMPLE_TRIPS,
    background: 'mist',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('From London')).toBeInTheDocument();
  },
};

export const WithInterestChips: Story = {
  args: {
    title: 'By your interests',
    subtitle: 'Pick what you love',
    trips: SAMPLE_TRIPS,
    background: 'mist',
    chips: INTEREST_CHIPS,
    activeChip: 'adventure',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('By your interests')).toBeInTheDocument();
    expect(canvas.getByText('Adventure')).toBeInTheDocument();
    expect(canvas.getByText('Beach')).toBeInTheDocument();
  },
};
