import { useState, useCallback, useMemo, type RefObject } from 'react';
import { ActionIcon, Alert, Box, Drawer, Group, Text } from '@mantine/core';
import { X } from 'lucide-react';
import type { Hotel, HotelItinerary } from '@/types/hotels';
import { hasValidCoords, getHotelKey } from '@/features/hotels/utils/hotelMapCoords';
import { HotelsMobileMap } from './HotelsMobileMap';
import { HotelMobilePinCard } from './HotelMobilePinCard';

export interface HotelSearchMobileMapOverlayProps {
  hotels: (Hotel | HotelItinerary)[];
  nights: number;
  rooms: number;
  onSelectHotel: (hotel: Hotel | HotelItinerary) => void;
  selectingTokenId?: string | null;
  onClose: () => void;
  returnFocusRef: RefObject<HTMLButtonElement | null>;
}

/**
 * Full-screen map for /hotels/search on narrow viewports (opened from FAB).
 */
export function HotelSearchMobileMapOverlay({
  hotels,
  nights,
  rooms,
  onSelectHotel,
  selectingTokenId = null,
  onClose,
  returnFocusRef,
}: HotelSearchMobileMapOverlayProps) {
  const [selectedHotel, setSelectedHotel] = useState<Hotel | HotelItinerary | null>(null);

  const hotelsWithCoords = useMemo(() => hotels.filter(hasValidCoords), [hotels]);
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;
  const mapId = import.meta.env.VITE_GOOGLE_MAPS_MAP_ID;

  const handlePinClick = useCallback((hotel: Hotel | HotelItinerary) => {
    setSelectedHotel((prev) => {
      const key = getHotelKey(hotel);
      const prevKey = prev ? getHotelKey(prev) : null;
      return prevKey === key ? null : hotel;
    });
  }, []);

  const handleMapClick = useCallback(() => {
    setSelectedHotel(null);
  }, []);

  const handleDrawerClose = useCallback(() => {
    setSelectedHotel(null);
  }, []);

  const handleClose = useCallback(() => {
    setSelectedHotel(null);
    onClose();
    setTimeout(() => returnFocusRef.current?.focus(), 50);
  }, [onClose, returnFocusRef]);

  const selectedKey = selectedHotel ? getHotelKey(selectedHotel) : null;

  const renderBody = () => {
    if (!apiKey?.trim()) {
      return (
        <Group justify="center" align="center" p="md" style={{ flex: 1 }}>
          <Alert color="blue" style={{ maxWidth: 320 }}>
            Map view is not available (Google Maps API key not configured).
          </Alert>
        </Group>
      );
    }

    if (hotelsWithCoords.length === 0) {
      return (
        <Group justify="center" align="center" p="md" style={{ flex: 1 }}>
          <Alert color="blue" style={{ maxWidth: 320 }}>
            No hotels with location data to show on the map.
          </Alert>
        </Group>
      );
    }

    return (
      <Box style={{ flex: 1, position: 'relative', overflow: 'hidden', minHeight: 0 }}>
        <HotelsMobileMap
          mapId={mapId}
          hotels={hotelsWithCoords}
          nights={nights}
          selectedId={selectedKey}
          onPinClick={handlePinClick}
          onMapClick={handleMapClick}
        />
      </Box>
    );
  };

  return (
    <Box
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 'var(--mantine-z-index-modal)',
        backgroundColor: 'var(--mantine-color-body)',
        display: 'flex',
        flexDirection: 'column',
        paddingTop: 'env(safe-area-inset-top)',
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}
    >
      <Group
        align="center"
        justify="space-between"
        px="sm"
        py="xs"
        style={{
          borderBottom: '1px solid var(--mantine-color-default-border)',
          backgroundColor: 'var(--mantine-color-body)',
          flexShrink: 0,
        }}
      >
        <Text fw={600} size="sm">
          {hotelsWithCoords.length > 0
            ? `${hotelsWithCoords.length} hotel${hotelsWithCoords.length !== 1 ? 's' : ''} on map`
            : 'Map view'}
        </Text>
        <ActionIcon onClick={handleClose} variant="subtle" color="gray" size="sm" aria-label="Close map">
          <X size={18} />
        </ActionIcon>
      </Group>

      {renderBody()}

      <Drawer
        position="bottom"
        opened={selectedHotel !== null}
        onClose={handleDrawerClose}
        withCloseButton={false}
        size="auto"
        keepMounted
        zIndex="calc(var(--mantine-z-index-modal) + 1)"
        styles={{
          content: {
            borderTopLeftRadius: 12,
            borderTopRightRadius: 12,
            paddingBottom: 'env(safe-area-inset-bottom)',
          },
        }}
      >
        {selectedHotel && (
          <HotelMobilePinCard
            key={getHotelKey(selectedHotel)}
            hotel={selectedHotel}
            nights={nights}
            rooms={rooms}
            isSelecting={selectingTokenId === getHotelKey(selectedHotel)}
            onSelect={() => onSelectHotel(selectedHotel)}
          />
        )}
      </Drawer>
    </Box>
  );
}
