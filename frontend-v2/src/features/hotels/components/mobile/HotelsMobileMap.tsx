import { useMemo, useCallback } from 'react';
import { Box } from '@mantine/core';
import { Map, AdvancedMarker, Marker } from '@vis.gl/react-google-maps';
import type { Hotel, HotelItinerary } from '@/types/hotels';
import { getHotelTotal, getHotelCurrency, hotelCurrencySymbol } from '@/features/hotels/utils/hotelFilters';
import { getPosition, getHotelKey } from '@/features/hotels/utils/hotelMapCoords';

function HotelPricePin({ price, selected }: { price: string; selected: boolean }) {
  return (
    <div
      style={{
        padding: '5px 10px',
        borderRadius: 9999,
        background: selected ? 'var(--mantine-color-navy-7)' : 'white',
        color: selected ? 'white' : 'var(--mantine-color-navy-7)',
        border: '2px solid white',
        boxShadow: selected
          ? '0 3px 10px rgba(23,27,99,0.45), 0 1px 3px rgba(0,0,0,0.18)'
          : '0 2px 6px rgba(0,0,0,0.22), 0 0 0 1px rgba(0,0,0,0.04)',
        fontSize: 12,
        fontWeight: 700,
        fontFamily: 'Inter, -apple-system, sans-serif',
        whiteSpace: 'nowrap' as const,
        letterSpacing: '-0.01em',
        transform: selected ? 'scale(1.1)' : 'scale(1)',
        transition: 'transform 150ms ease, box-shadow 150ms ease',
        cursor: 'pointer',
        userSelect: 'none' as const,
      }}
    >
      {price}
    </div>
  );
}

export interface HotelsMobileMapProps {
  mapId?: string;
  /** Only hotels with valid lat/lng (e.g. pre-filtered with hasValidCoords). */
  hotels: (Hotel | HotelItinerary)[];
  nights: number;
  selectedId: string | null;
  onPinClick: (hotel: Hotel | HotelItinerary) => void;
  onMapClick: () => void;
}

export function HotelsMobileMap({
  mapId,
  hotels,
  nights,
  selectedId,
  onPinClick,
  onMapClick,
}: HotelsMobileMapProps) {
  const mapBoundsProps = useMemo(() => {
    if (hotels.length === 0) {
      return { defaultCenter: { lat: 51.5074, lng: -0.1278 }, defaultZoom: 12 };
    }
    if (hotels.length === 1) {
      return { defaultCenter: getPosition(hotels[0]!), defaultZoom: 14 };
    }
    let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;
    for (const h of hotels) {
      const { lat, lng } = getPosition(h);
      minLat = Math.min(minLat, lat);
      maxLat = Math.max(maxLat, lat);
      minLng = Math.min(minLng, lng);
      maxLng = Math.max(maxLng, lng);
    }
    const pad = 0.01;
    return {
      defaultBounds: {
        north: maxLat + pad,
        south: minLat - pad,
        east: maxLng + pad,
        west: minLng - pad,
      },
    };
  }, [hotels]);

  const formatPrice = useCallback(
    (h: Hotel | HotelItinerary) => {
      const symbol = hotelCurrencySymbol(getHotelCurrency(h));
      const total = getHotelTotal(h);
      const perNight = nights > 0 ? total / nights : total;
      return `${symbol}${Math.round(perNight)}`;
    },
    [nights]
  );

  return (
    <Box style={{ width: '100%', height: '100%', position: 'relative' }}>
      <Map
        {...mapBoundsProps}
        style={{ width: '100%', height: '100%' }}
        mapId={mapId ?? undefined}
        gestureHandling="greedy"
        disableDefaultUI
        onClick={onMapClick}
      >
        {hotels.map((hotel) => {
          const key = getHotelKey(hotel);
          const position = getPosition(hotel);
          const price = formatPrice(hotel);
          const isSelected = selectedId === key;

          if (mapId) {
            return (
              <AdvancedMarker
                key={key}
                position={position}
                title={hotel.name ?? 'Hotel'}
                zIndex={isSelected ? 10 : 1}
                onClick={() => onPinClick(hotel)}
              >
                <HotelPricePin price={price} selected={isSelected} />
              </AdvancedMarker>
            );
          }

          // Fallback: classic Marker when no Map ID (AdvancedMarker requires mapId)
          return (
            <Marker
              key={key}
              position={position}
              title={`${hotel.name ?? 'Hotel'} — ${price}`}
              label={{ text: price, fontSize: '10px', fontWeight: '700' }}
              onClick={() => onPinClick(hotel)}
            />
          );
        })}
      </Map>
    </Box>
  );
}
