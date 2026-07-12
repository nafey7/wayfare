import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn } from 'storybook/test';
import { within, waitFor, expect } from 'storybook/test';
import { ItineraryDayCard } from './ItineraryDayCard';
import type { ItineraryDay, ItineraryStopEntry } from './ItineraryDayCard';

// ── Fixtures ─────────────────────────────────────────────────────────────────

const day1: ItineraryDay = {
  dayNumber: 1,
  date: 'FRI 15 MAY',
  title: 'Arrival & Gothic Quarter',
  description: 'Land at El Prat, check in, then explore the winding streets of the Barri Gòtic.',
  stopCount: 4,
};

const day1WithImage: ItineraryDay = {
  ...day1,
  imageUrl: 'https://images.unsplash.com/photo-1583422409516-2895a77efded?w=400',
  bannerImageUrl: 'https://images.unsplash.com/photo-1583422409516-2895a77efded?w=800',
};

const day2: ItineraryDay = {
  dayNumber: 2,
  date: 'SAT 16 MAY',
  title: 'Gaudí & Modernisme',
  description: 'Sagrada Família at dawn, Park Güell, Casa Batlló.',
  stopCount: 3,
};

const stops: ItineraryStopEntry[] = [
  {
    stop: {
      id: 's1',
      name: 'Sagrada Família',
      description: "Gaudí's iconic basilica — book tickets in advance.",
      duration: '2h',
      cost: '€26',
      rating: 4.8,
      reviewCount: 95000,
      startTime: '09:00',
      endTime: '11:00',
    },
    connector: [{ mode: 'walk', label: '12 min · 900m' }],
  },
  {
    stop: {
      id: 's2',
      name: 'Park Güell',
      description: 'Mosaic terraces and panoramic views over the city.',
      duration: '1h 30m',
      cost: '€10',
      rating: 4.6,
      reviewCount: 72000,
      startTime: '11:30',
      endTime: '13:00',
    },
    connector: [{ mode: 'bus', label: '20 min · Bus 24' }],
  },
  {
    stop: {
      id: 's3',
      name: 'Casa Batlló',
      description: "Dragon-spine roof and Gaudí's vivid tilework.",
      duration: '1h',
      cost: '€35',
      rating: 4.7,
      reviewCount: 53000,
      startTime: '15:00',
      endTime: '16:00',
    },
  },
];

const day2WithStops: ItineraryDay = {
  ...day2,
  stops,
  imageUrl: 'https://images.unsplash.com/photo-1523531294919-4bcd7c65e216?w=400',
  bannerImageUrl: 'https://images.unsplash.com/photo-1523531294919-4bcd7c65e216?w=800',
};

// ── Meta ─────────────────────────────────────────────────────────────────────

const meta: Meta<typeof ItineraryDayCard> = {
  title: 'Itinerary/ItineraryDayCard',
  component: ItineraryDayCard,
  parameters: { layout: 'padded' },
  args: {
    onToggle: fn(),
    onSkipDay: fn(),
    onUnskipDay: fn(),
    onStopSelect: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof ItineraryDayCard>;

// ── Stories ───────────────────────────────────────────────────────────────────

/** Default collapsed card — no image, gradient background. */
export const Collapsed: Story = {
  args: { day: day1 },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByText('Day 1 · FRI 15 MAY')).toBeInTheDocument();
      expect(canvas.getByText('Arrival & Gothic Quarter')).toBeInTheDocument();
      expect(canvas.getByText(/4 stops/i)).toBeInTheDocument();
      // Regression (2d334bc): must be type="button" to avoid form submission
      expect(canvas.getByRole('button', { name: 'Expand day' })).toHaveAttribute('type', 'button');
    });
  },
};

/** Collapsed card with a photo banner. */
export const CollapsedWithPhoto: Story = {
  args: { day: day1WithImage },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByText('Day 1 · FRI 15 MAY')).toBeInTheDocument();
      expect(canvas.getByText('Arrival & Gothic Quarter')).toBeInTheDocument();
    });
  },
};

/** Expanded card — full banner, day header, and stop timeline. */
export const Expanded: Story = {
  args: { day: day2WithStops, isExpanded: true },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByText('Day 2 · SAT 16 MAY')).toBeInTheDocument();
      expect(canvas.getByText('Gaudí & Modernisme')).toBeInTheDocument();
      expect(canvas.getByText('Sagrada Família')).toBeInTheDocument();
      expect(canvas.getByText('Park Güell')).toBeInTheDocument();
      expect(canvas.getByText('Casa Batlló')).toBeInTheDocument();
      // Regression (2d334bc): collapse + skip buttons must not submit forms
      expect(canvas.getByRole('button', { name: 'Collapse day' })).toHaveAttribute('type', 'button');
      expect(canvas.getByRole('button', { name: 'Skip this day' })).toHaveAttribute('type', 'button');
    });
  },
};

/** Expanded without a banner image — shows gradient fallback. */
export const ExpandedNoBanner: Story = {
  args: { day: day2WithStops, isExpanded: true, hideBanner: true },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByText('Gaudí & Modernisme')).toBeInTheDocument();
      expect(canvas.getByText('Sagrada Família')).toBeInTheDocument();
    });
  },
};

/** Skipped day — reduced opacity, "Skipped" chip visible, "Restore" button on expand. */
export const Skipped: Story = {
  args: { day: day1, isSkipped: true },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByText(/Skipped/i)).toBeInTheDocument();
    });
  },
};

/** Skipped day in expanded state — shows "Restore" button. */
export const SkippedExpanded: Story = {
  args: { day: day2WithStops, isExpanded: true, isSkipped: true },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      const restoreBtn = canvas.getByRole('button', { name: /restore day/i });
      expect(restoreBtn).toBeInTheDocument();
      // Regression (2d334bc): restore button must not submit forms
      expect(restoreBtn).toHaveAttribute('type', 'button');
    });
  },
};

/** Card without onToggle — static display, no expand button. */
export const Static: Story = {
  args: { day: day1WithImage, onToggle: undefined },
};

/** Second day — verifies per-day gradient/accent rotation. */
export const Day2: Story = {
  args: { day: day2 },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByText('Day 2 · SAT 16 MAY')).toBeInTheDocument();
      expect(canvas.getByText('Gaudí & Modernisme')).toBeInTheDocument();
    });
  },
};
