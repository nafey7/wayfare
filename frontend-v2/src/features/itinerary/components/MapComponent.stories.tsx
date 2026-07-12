import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { expect, within } from 'storybook/test';
import { MapComponent } from './MapComponent';

const meta: Meta<typeof MapComponent> = {
  title: 'Itinerary/MapComponent',
  component: MapComponent,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <Box style={{ height: 500, width: '100%' }}>
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof MapComponent>;

/**
 * Default: Amsterdam → Barcelona route with two markers.
 * When VITE_GOOGLE_MAPS_API_KEY is set (deployed Storybook preview), the real
 * Google Maps tile renders. Without the key (CI smoke test), the fallback
 * message "Map view is not available" is shown. Both render paths pass.
 */
export const Default: Story = {
  args: {
    centerLatitude: 48.5,
    centerLongitude: 5.0,
    zoomLevel: 5,
    markers: [
      { latitude: 52.3676, longitude: 4.9041, label: 'Amsterdam (AMS)' },
      { latitude: 41.3851, longitude: 2.1734, label: 'Barcelona (BCN)' },
    ],
    routePath: [
      { latitude: 52.3676, longitude: 4.9041 },
      { latitude: 41.3851, longitude: 2.1734 },
    ],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Either the real map container or the no-key fallback is visible.
    const fallback = canvas.queryAllByText(/map view is not available/i);
    const hasMap = canvas.queryAllByRole('application').length > 0;
    expect(
      fallback.length > 0 || hasMap,
      'expected either the Google Map or the no-key fallback to be visible'
    ).toBe(true);
  },
};

/** Single marker with no route — just a pin on Amsterdam. */
export const SingleMarker: Story = {
  args: {
    centerLatitude: 52.3676,
    centerLongitude: 4.9041,
    zoomLevel: 12,
    markers: [{ latitude: 52.3676, longitude: 4.9041, label: 'Amsterdam (AMS)' }],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const fallback = canvas.queryAllByText(/map view is not available/i);
    const hasMap = canvas.queryAllByRole('application').length > 0;
    expect(fallback.length > 0 || hasMap).toBe(true);
  },
};
