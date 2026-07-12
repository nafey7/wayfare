import { useMemo, useState, useCallback } from 'react';
import { Box, Group, Loader, Text } from '@mantine/core';
import { APIProvider, Map } from '@vis.gl/react-google-maps';
import { HotelMapMarker } from './HotelMapMarker';
import { hasValidCoords, getPosition, getHotelKey } from '@/features/hotels/utils/hotelMapCoords';
import type { Hotel, HotelItinerary } from '@/types/hotels';

const DEFAULT_CENTER = { lat: 51.5074, lng: -0.1278 };
const DEFAULT_ZOOM = 12;

export interface HotelMapViewProps {
  apiKey: string;
  hotels: (Hotel | HotelItinerary)[];
  nights: number;
  rooms: number;
  onSelectHotel: (hotel: Hotel | HotelItinerary) => void;
  selectingTokenId?: string | null;
  /** When true, map fills parent flex height (e.g. /hotels/search right column). */
  fillHeight?: boolean;
}

export function HotelMapView({
  apiKey,
  hotels,
  nights,
  rooms,
  onSelectHotel,
  selectingTokenId = null,
  fillHeight = false,
}: HotelMapViewProps) {
  const [selectedHotelId, setSelectedHotelId] = useState<string | null>(null);

  const handleMarkerToggle = useCallback((hotelId: string) => {
    setSelectedHotelId((prev) => (prev === hotelId ? null : hotelId));
  }, []);

  const handleMapClick = useCallback(() => {
    setSelectedHotelId(null);
  }, []);

  const hotelsWithCoords = useMemo(
    () => hotels.filter(hasValidCoords),
    [hotels]
  );

  const { defaultCenter, defaultZoom, defaultBounds } = useMemo(() => {
    if (hotelsWithCoords.length === 0) {
      return {
        defaultCenter: DEFAULT_CENTER,
        defaultZoom: DEFAULT_ZOOM,
        defaultBounds: null as { north: number; south: number; east: number; west: number } | null,
      };
    }
    if (hotelsWithCoords.length === 1) {
      const first = hotelsWithCoords[0]!;
      const pos = getPosition(first);
      return {
        defaultCenter: pos,
        defaultZoom: DEFAULT_ZOOM,
        defaultBounds: null as { north: number; south: number; east: number; west: number } | null,
      };
    }
    let minLat = 90;
    let maxLat = -90;
    let minLng = 180;
    let maxLng = -180;
    for (const h of hotelsWithCoords) {
      const { lat, lng } = getPosition(h);
      minLat = Math.min(minLat, lat);
      maxLat = Math.max(maxLat, lat);
      minLng = Math.min(minLng, lng);
      maxLng = Math.max(maxLng, lng);
    }
    const padding = 0.01;
    return {
      defaultCenter: DEFAULT_CENTER,
      defaultZoom: DEFAULT_ZOOM,
      defaultBounds: {
        north: maxLat + padding,
        south: minLat - padding,
        east: maxLng + padding,
        west: minLng - padding,
      },
    };
  }, [hotelsWithCoords]);

  if (hotelsWithCoords.length === 0) {
    return (
      <Box
        py="xl"
        ta="center"
        style={
          fillHeight
            ? { flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }
            : undefined
        }
      >
        <Text c="dimmed">No hotels with location data to show on the map.</Text>
      </Box>
    );
  }

  const mapProps = defaultBounds
    ? { defaultBounds }
    : { defaultCenter, defaultZoom };

  return (
    <APIProvider apiKey={apiKey}>
      <Box
        style={{
          width: '100%',
          ...(fillHeight
            ? { flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }
            : { height: 480 }),
          borderRadius: 8,
          overflow: 'hidden',
        }}
      >
        <Box
          style={{
            position: 'relative',
            ...(fillHeight ? { flex: 1, minHeight: 0 } : { height: '100%' }),
          }}
        >
          <Map
            {...mapProps}
            style={{ width: '100%', height: '100%' }}
            mapTypeControl
            streetViewControl
            fullscreenControl
            onClick={handleMapClick}
          >
            {hotelsWithCoords.map((hotel) => {
              const key = getHotelKey(hotel);
              return (
                <HotelMapMarker
                  key={key}
                  hotel={hotel}
                  position={getPosition(hotel)}
                  nights={nights}
                  rooms={rooms}
                  isOpen={selectedHotelId === key}
                  isSelecting={selectingTokenId != null && selectingTokenId === key}
                  onToggle={() => handleMarkerToggle(key)}
                  onSelect={() => onSelectHotel(hotel)}
                />
              );
            })}
          </Map>
        </Box>
      </Box>
    </APIProvider>
  );
}

export interface HotelMapViewWrapperProps {
  apiKey: string | null | undefined;
  apiLoading: boolean;
  hotels: (Hotel | HotelItinerary)[];
  nights: number;
  rooms: number;
  onSelectHotel: (hotel: Hotel | HotelItinerary) => void;
  selectingTokenId?: string | null;
  fillHeight?: boolean;
}

/**
 * Wrapper that shows loading state or "Map unavailable" when API key is missing,
 * and renders HotelMapView when key is available.
 */
export function HotelMapViewWrapper({
  apiKey,
  apiLoading,
  hotels,
  nights,
  rooms,
  onSelectHotel,
  selectingTokenId = null,
  fillHeight = false,
}: HotelMapViewWrapperProps) {
  if (apiLoading) {
    return (
      <Group
        justify="center"
        align="center"
        py={64}
        style={fillHeight ? { flex: 1, minHeight: 0 } : undefined}
      >
        <Loader />
        <Text size="sm" c="dimmed">
          Loading map…
        </Text>
      </Group>
    );
  }

  if (!apiKey || apiKey.trim() === '') {
    return (
      <Box
        py="xl"
        ta="center"
        style={
          fillHeight
            ? { flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }
            : undefined
        }
      >
        <Text c="dimmed">Map view is not available (Google Maps API key not configured).</Text>
      </Box>
    );
  }

  return (
    <HotelMapView
      apiKey={apiKey}
      hotels={hotels}
      nights={nights}
      rooms={rooms}
      onSelectHotel={onSelectHotel}
      selectingTokenId={selectingTokenId}
      fillHeight={fillHeight}
    />
  );
}
