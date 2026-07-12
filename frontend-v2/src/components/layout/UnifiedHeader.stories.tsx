import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within, waitFor } from 'storybook/test';
import { UnifiedHeader } from './UnifiedHeader';

const meta: Meta<typeof UnifiedHeader> = {
  title: 'Layout/UnifiedHeader',
  component: UnifiedHeader,
  parameters: {
    layout: 'fullscreen',
    initialEntries: ['/chat'],
  },
};

export default meta;
type Story = StoryObj<typeof UnifiedHeader>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Desktop: logo link and section nav are rendered
    expect(canvas.getByRole('link', { name: /voya home/i })).toBeInTheDocument();
    expect(canvas.getByRole('navigation', { name: /section navigation/i })).toBeInTheDocument();
    expect(canvas.getByText('Flights')).toBeInTheDocument();
    expect(canvas.getByText('Stays')).toBeInTheDocument();
    expect(canvas.getByText('Day plan')).toBeInTheDocument();
    // Unscrolled: subtabs are in expanded layout
    expect(canvas.getByTestId('subtabs-expanded')).toBeInTheDocument();
  },
};

export const FlightsRoute: Story = {
  parameters: {
    initialEntries: ['/flights/recommendations'],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByRole('link', { name: /voya home/i })).toBeInTheDocument();
    // Flights subtab is active (aria-current="page")
    const flightsBtn = canvas.getByRole('button', { name: /flights/i });
    expect(flightsBtn).toHaveAttribute('aria-current', 'page');
  },
};

export const HotelsRoute: Story = {
  parameters: {
    initialEntries: ['/hotels/search'],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByRole('link', { name: /voya home/i })).toBeInTheDocument();
    // Stays subtab is active
    const staysBtn = canvas.getByRole('button', { name: /stays/i });
    expect(staysBtn).toHaveAttribute('aria-current', 'page');
  },
};

export const Mobile: Story = {
  parameters: {
    viewport: { defaultViewport: 'mobile1' },
    initialEntries: ['/chat'],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // On mobile the logo link is hidden (display:none) and hamburger is gone;
    // the chat input and section nav are shown instead.
    expect(canvas.queryByRole('link', { name: /voya home/i })).toBeNull();
    expect(canvas.getByRole('navigation', { name: /section navigation/i })).toBeInTheDocument();
    expect(canvas.getByText('Flights')).toBeInTheDocument();
    expect(canvas.getByText('Stays')).toBeInTheDocument();
  },
};

/** Scrolled past 80px — subtabs collapse to inline icon+text (subtabsMinimal state). */
export const Scrolled: Story = {
  parameters: {
    initialEntries: ['/flights/recommendations'],
  },
  decorators: [
    (Story) => (
      <div
        id="main-scroll-root"
        style={{ height: 300, overflowY: 'auto', position: 'relative' }}
      >
        <div style={{ paddingBottom: 500 }}>
          <Story />
        </div>
      </div>
    ),
  ],
  play: async ({ canvasElement }) => {
    const scrollRoot = document.getElementById('main-scroll-root');
    if (scrollRoot) {
      scrollRoot.scrollTop = 100;
      scrollRoot.dispatchEvent(new Event('scroll', { bubbles: true }));
    }
    const canvas = within(canvasElement);
    await waitFor(() => {
      // Section nav still present in collapsed mode
      expect(canvas.getByRole('navigation', { name: /section navigation/i })).toBeInTheDocument();
      // Active tab still marked
      expect(canvas.getByRole('button', { name: /flights/i })).toHaveAttribute('aria-current', 'page');
      // Collapsed state: subtabs switch to minimal (row) layout
      expect(canvas.getByTestId('subtabs-minimal')).toBeInTheDocument();
    });
  },
};
