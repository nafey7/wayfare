import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn, within } from 'storybook/test';
import { HomeHero } from './HomeHero';

const meta: Meta<typeof HomeHero> = {
  title: 'Marketing/HomeHero',
  component: HomeHero,
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof HomeHero>;

export const Default: Story = {
  args: {
    onSearchSubmit: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Your next trip, planned in minutes.')).toBeInTheDocument();
    expect(canvas.getByText('DUB')).toBeInTheDocument();
    expect(canvas.getByText('LON')).toBeInTheDocument();
    expect(canvas.getByText('The Ritz London')).toBeInTheDocument();
    expect(canvas.getByRole('textbox', { name: /chat with voya ai/i })).toBeInTheDocument();
    expect(canvas.getByRole('button', { name: /send to voya ai/i })).toBeInTheDocument();
  },
};

export const CustomCopy: Story = {
  args: {
    calloutText: 'NEW: Hotel booking available',
    headline: 'Plan your dream vacation',
    subheadline: 'Search flights, hotels, and experiences with real-time prices.',
    flightOrigin: 'JFK',
    flightDestination: 'CDG',
    flightDetails: '8:30 AM • Direct',
    hotelName: 'Hôtel de Crillon',
    hotelDetails: 'Checked in • 2 Guests',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Plan your dream vacation')).toBeInTheDocument();
    expect(canvas.getByText('JFK')).toBeInTheDocument();
    expect(canvas.getByText('CDG')).toBeInTheDocument();
    expect(canvas.getByText('Hôtel de Crillon')).toBeInTheDocument();
  },
};

export const NoCallout: Story = {
  args: {
    calloutText: '',
    calloutTextMobile: '',
    headline: 'Travel smarter with AI',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Travel smarter with AI')).toBeInTheDocument();
  },
};

export const WithCta: Story = {
  args: {
    onCtaClick: fn(),
    ctaLabel: 'Plan My Trip',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const btn = canvas.getByRole('button', { name: 'Plan My Trip' });
    expect(btn).toBeInTheDocument();
    expect(btn).toBeVisible();
  },
};

export const WithoutCta: Story = {
  args: {
    onCtaClick: undefined,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.queryByRole('button', { name: /plan my trip/i })).not.toBeInTheDocument();
  },
};

export const CtaHiddenByEmptyLabel: Story = {
  args: {
    onCtaClick: fn(),
    ctaLabel: '',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.queryByRole('button')).not.toBeInTheDocument();
  },
};
