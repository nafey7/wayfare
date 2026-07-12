import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import { HomeSignInCard } from './HomeSignInCard';

const meta: Meta<typeof HomeSignInCard> = {
  title: 'Marketing/HomeSignInCard',
  component: HomeSignInCard,
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof HomeSignInCard>;

/** Visible on all screen sizes so Storybook can render it regardless of viewport. */
export const Default: Story = {
  args: {
    showOnDesktop: true,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/log in or sign up/i)).toBeInTheDocument();
  },
};

export const MobileOnly: Story = {
  args: {
    showOnDesktop: false,
  },
  parameters: {
    viewport: { defaultViewport: 'mobile1' },
  },
};
