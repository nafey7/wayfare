import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn, within } from 'storybook/test';
import { EditorialCard } from './EditorialCard';

const meta: Meta<typeof EditorialCard> = {
  title: 'Marketing/EditorialCard',
  component: EditorialCard,
  args: {
    onCtaClick: fn(),
  },
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof EditorialCard>;

export const Default: Story = {
  args: {
    title: 'A 7-day journey through Kyoto',
    body: 'Temples at dawn. Tea ceremony in Gion. Nishiki Market lunches. A sunset boat on the Hozugawa. We built the whole week — flights from London, ryokan stays, and a curated day plan — in 53 seconds.',
    meta: ['⚡ Built in 53s', '$3,290 total · 7 nights', '★ 4.9 Voya guests'],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('A 7-day journey through Kyoto')).toBeInTheDocument();
    expect(canvas.getByText('Voya picks · this week')).toBeInTheDocument();
    expect(canvas.getByText('See the trip')).toBeInTheDocument();
  },
};

export const WithImage: Story = {
  args: {
    eyebrow: 'Voya picks · spring edition',
    title: 'Cherry blossom season in Tokyo',
    body: 'Book now — peak season fills fast. We searched 40+ hotels and 200+ flights to build this itinerary overnight.',
    meta: ['⚡ Built in 47s', '$4,100 total · 10 nights', '★ 4.9 Voya guests'],
    ctaLabel: 'Plan this trip',
    imageUrl: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=1200&h=800&q=80',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Cherry blossom season in Tokyo')).toBeInTheDocument();
    expect(canvas.getByText('Voya picks · spring edition')).toBeInTheDocument();
    expect(canvas.getByText('Plan this trip')).toBeInTheDocument();
  },
};

export const MinimalNoMeta: Story = {
  args: {
    title: 'The perfect Amalfi coast road trip',
    body: 'Seven days, three coastal towns, one unforgettable drive. Flights from Rome included.',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('The perfect Amalfi coast road trip')).toBeInTheDocument();
  },
};
