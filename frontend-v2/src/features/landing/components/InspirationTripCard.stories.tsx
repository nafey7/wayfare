import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn, within } from 'storybook/test';
import { InspirationTripCard } from './InspirationTripCard';
import type { InspirationTripData } from './InspirationTripCard';

const BASE_TRIP: InspirationTripData = {
  id: 'lon-jpn',
  title: '7 days in Kyoto + Tokyo',
  builtInSeconds: 58,
  flightRoute: 'LHR → KIX, HND → LHR',
  hotelName: 'The Hiramatsu · Park Hyatt',
  stops: 17,
  priceAmount: 2310,
  duration: '7 nights',
  theme: 'tokyo',
  tag: 'Culture',
  rating: 4.9,
};

const meta: Meta<typeof InspirationTripCard> = {
  title: 'Marketing/InspirationTripCard',
  component: InspirationTripCard,
  args: {
    onClick: fn(),
    onToggleSave: fn(),
  },
  parameters: {
    layout: 'centered',
  },
  decorators: [
    (Story) => (
      <div style={{ width: 280 }}>
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof InspirationTripCard>;

export const Default: Story = {
  args: {
    data: BASE_TRIP,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('7 days in Kyoto + Tokyo')).toBeInTheDocument();
    expect(canvas.getByText('Culture')).toBeInTheDocument();
    expect(canvas.getByRole('button', { name: /save trip/i })).toBeInTheDocument();
  },
};

export const Saved: Story = {
  args: {
    data: { ...BASE_TRIP, saved: true, savedLabel: 'Saved' },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Saved')).toBeInTheDocument();
    expect(canvas.getByRole('button', { name: /unsave trip/i })).toBeInTheDocument();
  },
};

export const BeachTheme: Story = {
  args: {
    data: {
      id: 'bch-mle',
      title: 'Maldives overwater 5 nights',
      builtInSeconds: 56,
      flightRoute: 'DXB → MLE',
      hotelName: 'Soneva Fushi',
      stops: 6,
      priceAmount: 9800,
      duration: '5 nights',
      theme: 'bali',
      tag: 'Beach',
      rating: 4.9,
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Maldives overwater 5 nights')).toBeInTheDocument();
    expect(canvas.getByText('Beach')).toBeInTheDocument();
  },
};

export const NoRatingNoTag: Story = {
  args: {
    data: {
      ...BASE_TRIP,
      id: 'plain',
      title: 'A quiet weekend in Lisbon',
      theme: 'lisbon',
      tag: undefined,
      rating: undefined,
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('A quiet weekend in Lisbon')).toBeInTheDocument();
  },
};
