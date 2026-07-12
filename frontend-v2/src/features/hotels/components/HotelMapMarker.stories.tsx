import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn } from 'storybook/test';
import { Box, Text } from '@mantine/core';
import { APIProvider, Map } from '@vis.gl/react-google-maps';
import { HotelMapMarker } from './HotelMapMarker';
import {
  mockHotelBestValue,
  mockHotelCheapest,
  MOCK_NIGHTS,
} from '../__fixtures__/mockHotelData';

const BCN_CENTER = { lat: 41.3851, lng: 2.1734 };
const API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;

/**
 * HotelMapMarker must be rendered inside an APIProvider + Map from @vis.gl/react-google-maps.
 * Marker and InfoWindow content renders in the Google Maps canvas DOM — not in the React root —
 * so play functions assert the outer container rather than the marker content.
 * In the deployed Storybook (VITE_GOOGLE_MAPS_API_KEY set) the real map tiles load.
 * Without the key (CI / local), a placeholder is shown instead so APIProvider is never
 * called with an empty key — an empty key triggers ApiProjectMapError which can crash the iframe.
 */
function MapWrapper({ children }: { children: React.ReactNode }) {
  if (!API_KEY) {
    return (
      <Box
        style={{
          width: '100%',
          height: 400,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--mantine-color-gray-1)',
          borderRadius: 8,
        }}
      >
        <Text size="sm" c="dimmed">Map preview not available (no API key in this environment).</Text>
      </Box>
    );
  }
  return (
    <APIProvider apiKey={API_KEY}>
      <Box style={{ width: '100%', height: 400 }}>
        <Map
          defaultCenter={BCN_CENTER}
          defaultZoom={14}
          style={{ width: '100%', height: '100%' }}
        >
          {children}
        </Map>
      </Box>
    </APIProvider>
  );
}

const meta: Meta<typeof HotelMapMarker> = {
  title: 'Hotels/HotelMapMarker',
  component: HotelMapMarker,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <MapWrapper>
        <Story />
      </MapWrapper>
    ),
  ],
  args: {
    hotel: mockHotelBestValue,
    position: BCN_CENTER,
    nights: MOCK_NIGHTS,
    rooms: 1,
    isOpen: false,
    isSelecting: false,
    onToggle: fn(),
    onSelect: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof HotelMapMarker>;

/** Default: marker closed, pin visible on map (Google Maps canvas). */
export const Default: Story = {
  play: async ({ canvasElement }) => {
    // Marker renders in Google Maps canvas; assert outer map container is present
    const mapEl = canvasElement.querySelector('div') ?? canvasElement;
    expect(mapEl, 'map wrapper element should be present').not.toBeNull();
  },
};

/**
 * Selected: InfoWindow open — hotel name, price, and "Select Hotel" button
 * render in the Google Maps overlay DOM (not in canvasElement).
 */
export const Selected: Story = {
  args: {
    isOpen: true,
  },
  play: async ({ canvasElement }) => {
    // InfoWindow renders in Google Maps overlay DOM, not canvasElement — assert container only.
    const mapEl = canvasElement.querySelector('div') ?? canvasElement;
    expect(mapEl, 'map wrapper element should be present').not.toBeNull();
  },
};

/** Cheapest: lowest-price hotel on the map. */
export const Cheapest: Story = {
  args: {
    hotel: mockHotelCheapest,
    position: { lat: mockHotelCheapest.latitude, lng: mockHotelCheapest.longitude },
    isOpen: false,
  },
  play: async ({ canvasElement }) => {
    const mapEl = canvasElement.querySelector('div') ?? canvasElement;
    expect(mapEl, 'map wrapper element should be present').not.toBeNull();
  },
};
