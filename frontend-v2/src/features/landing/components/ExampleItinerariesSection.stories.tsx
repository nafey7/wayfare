import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn, within } from 'storybook/test';
import { ExampleItinerariesSection } from './ExampleItinerariesSection';

const meta: Meta<typeof ExampleItinerariesSection> = {
  title: 'Marketing/Sections/ExampleItineraries',
  component: ExampleItinerariesSection,
  args: {
    onPlanMyOwnTripClick: fn(),
    onCardPlanClick: fn(),
  },
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof ExampleItinerariesSection>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('See what Voya can plan for you')).toBeInTheDocument();
    expect(canvas.getByText('7 Days in Tokyo')).toBeInTheDocument();
    expect(canvas.getByText('Digital Nomad Month')).toBeInTheDocument();
    expect(canvas.getByText('Cherry blossom season')).toBeInTheDocument();
    expect(canvas.getByText('Work & explore')).toBeInTheDocument();
    expect(canvas.getByText('Plan my own trip')).toBeInTheDocument();
    expect(canvas.getAllByText('Plan a trip like this').length).toBeGreaterThanOrEqual(2);
  },
};
