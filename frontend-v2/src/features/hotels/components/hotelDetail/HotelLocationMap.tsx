import { Box, Stack, Text, Title } from '@mantine/core';
import { APIProvider, Map, Marker } from '@vis.gl/react-google-maps';

import { isValidHotelMapCoordinates } from './hotelMapCoordinates';

const MAP_BASE_HEIGHT_PX = 400;

const DEFAULT_ZOOM = 14;

export interface HotelLocationMapProps {
  title?: string;
  latitude?: number;
  longitude?: number;
  zoom?: number;
  markerTitle?: string;
}

const placeholderBoxStyle: React.CSSProperties = {
  width: '100%',
  minHeight: MAP_BASE_HEIGHT_PX,
  borderRadius: 4,
  backgroundColor: 'var(--mantine-color-gray-2)',
  border: '1px solid var(--mantine-color-default-border)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  paddingLeft: 16,
  paddingRight: 16,
};

/**
 * Location section with Google Maps (@vis.gl/react-google-maps).
 * Set `VITE_GOOGLE_MAPS_API_KEY` in `.env` for the map to render.
 */
export function HotelLocationMap({
  title = 'Location',
  latitude,
  longitude,
  zoom = DEFAULT_ZOOM,
  markerTitle = 'Hotel',
}: HotelLocationMapProps) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;
  const coordsOk = isValidHotelMapCoordinates(latitude, longitude);

  const heading = (
    <Title order={2} m={0} fw={700} style={{ fontSize: 28, lineHeight: '36px' }}>
      {title}
    </Title>
  );

  if (!apiKey?.trim()) {
    return (
      <Stack gap="md" align="flex-start" style={{ width: '100%' }}>
        {heading}
        <Box style={placeholderBoxStyle}>
          <Text size="sm" c="dimmed" ta="center">
            Map view is not available (Google Maps API key not configured).
          </Text>
        </Box>
      </Stack>
    );
  }

  if (!coordsOk) {
    return (
      <Stack gap="md" align="flex-start" style={{ width: '100%' }}>
        {heading}
        <Box style={placeholderBoxStyle}>
          <Text size="sm" c="dimmed" ta="center">
            Map view is not available (location coordinates are missing or invalid).
          </Text>
        </Box>
      </Stack>
    );
  }

  const lat = latitude as number;
  const lng = longitude as number;
  const mapKey = `${lat.toFixed(6)},${lng.toFixed(6)}`;

  return (
    <Stack gap="md" align="flex-start" style={{ width: '100%' }}>
      {heading}
      <APIProvider apiKey={apiKey}>
        <Box
          style={{
            width: '100%',
            height: MAP_BASE_HEIGHT_PX,
            borderRadius: 4,
            overflow: 'hidden',
            border: '1px solid var(--mantine-color-default-border)',
          }}
        >
          <Map
            key={mapKey}
            defaultCenter={{ lat, lng }}
            defaultZoom={zoom}
            style={{ width: '100%', height: '100%' }}
            mapTypeControl
            streetViewControl
            fullscreenControl
          >
            <Marker position={{ lat, lng }} title={markerTitle} />
          </Map>
        </Box>
      </APIProvider>
    </Stack>
  );
}
