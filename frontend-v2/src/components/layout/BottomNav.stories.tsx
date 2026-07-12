import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import { BottomNav } from './BottomNav';

const meta: Meta<typeof BottomNav> = {
  title: 'Layout/BottomNav',
  component: BottomNav,
  parameters: {
    layout: 'fullscreen',
    // BottomNav is mobile-only; render at mobile viewport so useMediaQuery returns true
    viewport: { defaultViewport: 'mobile1' },
    initialEntries: ['/chat'],
  },
};

export default meta;
type Story = StoryObj<typeof BottomNav>;

// On /home the Chat tab is visible (ChatSheet isn't available there so BottomNav hosts it).
// On /chat the ChatSheet handles the chat surface; BottomNav shows Explore/Trips/Sign in only.
export const GuestChat: Story = {
  parameters: {
    initialEntries: ['/home'],
    viewport: { defaultViewport: 'mobile1' },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const nav = canvas.getByRole('navigation', { name: /primary navigation/i });
    expect(nav).toBeInTheDocument();
    // On /home, guest sees Chat tab alongside Explore and Trips
    expect(within(nav).getByText('Explore')).toBeInTheDocument();
    expect(within(nav).getByText('Trips')).toBeInTheDocument();
    expect(within(nav).getByText('Chat')).toBeInTheDocument();
    // Explore tab is active on /home
    expect(within(nav).getByRole('button', { name: /explore/i })).toHaveAttribute('aria-current', 'page');
  },
};

export const GuestExplore: Story = {
  parameters: {
    initialEntries: ['/'],
    viewport: { defaultViewport: 'mobile1' },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const nav = canvas.getByRole('navigation', { name: /primary navigation/i });
    // Explore tab is active on /
    expect(within(nav).getByRole('button', { name: /explore/i })).toHaveAttribute('aria-current', 'page');
  },
};

/** BottomNav slid fully off-screen (e.g. user scrolled down). Stays mounted but is translated away. */
export const Hidden: Story = {
  args: { hidden: true },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Nav remains in the DOM so assistive tech can still find it; visibility is CSS-only
    expect(canvas.getByRole('navigation', { name: /primary navigation/i })).toBeInTheDocument();
  },
};
