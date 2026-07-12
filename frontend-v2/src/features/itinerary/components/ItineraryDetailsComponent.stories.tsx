import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { fn, within, waitFor, expect, userEvent } from 'storybook/test';
import {
  ItineraryDetailsComponent,
  type ItineraryItem,
  type LocalExperience,
} from './ItineraryDetailsComponent';
import { expectItineraryDayCard } from '@/stories/helpers/playAssertions';

// ---------------------------------------------------------------------------
// Fixtures — inline per issue file-plan convention
// ---------------------------------------------------------------------------

const day1: ItineraryItem = {
  day: 1,
  title: 'Arrival & Gothic Quarter',
  description:
    'Land at El Prat airport, check in to your hotel, then explore the winding streets of the Barri Gòtic.',
  imageUrl: '',
};

const day2: ItineraryItem = {
  day: 2,
  title: 'Gaudí & Modernisme',
  description:
    'Start with Sagrada Família at dawn, continue to Park Güell, finish at Casa Batlló.',
  imageUrl: '',
  expandedContent: {
    mainImageUrl: '',
    activities: [
      {
        id: 'a1',
        location: 'Sagrada Família',
        description: "Gaudi's iconic basilica - book tickets in advance.",
        duration: '2h',
        rating: 4.9,
      },
      {
        id: 'a2',
        location: 'Park Güell',
        description: 'Hilltop park with mosaic terraces and panoramic views.',
        duration: '1h 30m',
        rating: 4.7,
      },
    ],
    travelBars: [
      { options: [{ icon: 'bus', label: '25 min' }] },
    ],
    tip: { text: 'Buy a T-Casual card for unlimited metro + bus within 75 minutes.' },
  },
};

const day3: ItineraryItem = {
  day: 3,
  title: 'Barceloneta & Seafront',
  description:
    'Morning beach walk along Barceloneta, paella lunch at La Mar Salada, afternoon at MACBA.',
  imageUrl: '',
};

const threeItemItinerary: ItineraryItem[] = [day1, day2, day3];

const singleItemItinerary: ItineraryItem[] = [day1];

const sevenItemItinerary: ItineraryItem[] = [
  day1,
  day2,
  day3,
  { day: 4, title: 'Day Trip to Montserrat', description: 'Rack railway to the monastery and mountain views.', imageUrl: '' },
  { day: 5, title: 'El Born & Picasso Museum', description: 'Medieval district, Picasso Museum, and Santa Maria del Mar.', imageUrl: '' },
  { day: 6, title: 'Tibidabo & Collserola', description: 'Amusement park on the hill, forest walks.', imageUrl: '' },
  { day: 7, title: 'Departure', description: 'Morning brunch at Mercat de Santa Caterina, then head to El Prat.', imageUrl: '' },
];

const localExperiences: LocalExperience[] = [
  {
    id: 'le1',
    imageUrl: '',
    imageAlt: 'Pintxos spread',
    title: 'Pintxos Crawl in El Born',
    description: 'Hop between tapas bars sampling patatas bravas, pan con tomate, and seafood montaditos.',
  },
  {
    id: 'le2',
    imageUrl: '',
    imageAlt: 'Flamenco dancer',
    title: 'Flamenco Show at Tablao',
    description: 'Authentic flamenco in an intimate venue — book dinner for the full experience.',
  },
];

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const meta: Meta<typeof ItineraryDetailsComponent> = {
  title: 'Itinerary/ItineraryDetailsComponent',
  component: ItineraryDetailsComponent,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <Box style={{ height: 700, maxWidth: 600, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Story />
      </Box>
    ),
  ],
  args: {
    onTravelBarHover: fn(),
    onTravelBarClick: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof ItineraryDetailsComponent>;

// ---------------------------------------------------------------------------
// Stories
// ---------------------------------------------------------------------------

/** 3-day itinerary in collapsed state with local experiences and budget snapshot. */
export const Default: Story = {
  args: {
    itineraryItems: threeItemItinerary,
    localExperiences,
    budgetSnapshot: {
      title: 'Estimated Budget: €850 – €1,200 per person',
      description: 'Flights from Amsterdam, mid-range hotels, meals, and activities.',
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectItineraryDayCard(canvas, 1, 'Arrival');
    expectItineraryDayCard(canvas, 2, 'Gaudí');
    expectItineraryDayCard(canvas, 3, 'Barceloneta');
  },
};

/** Single-day itinerary — edge case for short trips or day-trip itineraries. */
export const SingleDay: Story = {
  args: {
    itineraryItems: singleItemItinerary,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectItineraryDayCard(canvas, 1, 'Arrival');
  },
};

/** 7-day itinerary — tests vertical scrolling of the card list. */
export const ManyDays: Story = {
  args: {
    itineraryItems: sevenItemItinerary,
    localExperiences,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectItineraryDayCard(canvas, 1, 'Arrival');
    expectItineraryDayCard(canvas, 7, 'Departure');
  },
};

/**
 * Regression (2d334bc): ConnectorPill must have type="button" and a descriptive
 * aria-label ("Travel: bus 25 min") rather than raw data ("25 min").
 */
export const ExpandedWithConnectors: Story = {
  args: {
    itineraryItems: [day2],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole('button', { name: 'Expand day' }));
    await waitFor(() => {
      const connectorBtn = canvas.getByRole('button', { name: 'Travel: bus 25 min' });
      expect(connectorBtn).toHaveAttribute('type', 'button');
    });
  },
};
