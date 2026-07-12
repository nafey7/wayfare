import { useState, useCallback } from 'react';
import { Box, Text, UnstyledButton } from '@mantine/core';
import { Map, AdvancedMarker } from '@vis.gl/react-google-maps';

// ─── Types ────────────────────────────────────────────────────────────────────

export type HotelPinState = 'default' | 'selected' | 'viewed';

export interface HotelMapPin {
  id: string;
  lat: number;
  lng: number;
  /** Formatted price string, e.g. "£142" */
  price: string;
  name: string;
}

export interface HotelMobileMapViewProps {
  hotels: HotelMapPin[];
  /** Externally controlled selected pin. Omit to let the component manage it internally. */
  selectedId?: string | null;
  /** Ids that the user has already opened — rendered in the "viewed" (lavender) style. */
  viewedIds?: string[];
  onPinTap?: (id: string | null) => void;
  /** Fires when the user pans the map — parent can show "Search this area" in response. */
  onPan?: () => void;
  /** When true, renders the "Search this area" pill at the top of the map. */
  showSearchPill?: boolean;
  onSearchThisArea?: () => void;
  height?: string;
}

// ─── Price pill (AdvancedMarker child) ────────────────────────────────────────

export function HotelPricePin({ price, state }: { price: string; state: HotelPinState }) {
  const selected = state === 'selected';
  const viewed = state === 'viewed';

  return (
    <div
      style={{
        padding: '5px 10px',
        borderRadius: 9999,
        background: selected ? '#2A2F5F' : viewed ? '#ECEEFF' : 'white',
        color: selected ? 'white' : viewed ? '#9aa2c5' : '#2A2F5F',
        border: '2px solid white',
        boxShadow: selected
          ? '0 3px 10px rgba(42,47,95,0.45), 0 1px 3px rgba(0,0,0,0.18)'
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

// ─── "Search this area" pill ──────────────────────────────────────────────────

function SearchAreaPill({ onTap }: { onTap: () => void }) {
  return (
    <Box style={{ position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 10 }}>
      <UnstyledButton
        onClick={onTap}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '7px 14px', background: 'white',
          borderRadius: 9999, border: '1px solid #E4E6F5',
          boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
          fontSize: 12, fontWeight: 600, color: '#2A2F5F', whiteSpace: 'nowrap',
        }}
      >
        <svg viewBox="0 0 24 24" width={12} height={12} fill="none" stroke="#2A2F5F" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 12a9 9 0 1 0 9-9" /><path d="M3 4v5h5" />
        </svg>
        Search this area
      </UnstyledButton>
    </Box>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function HotelMobileMapView({
  hotels,
  selectedId: externalSelectedId,
  viewedIds = [],
  onPinTap,
  onPan,
  showSearchPill = false,
  onSearchThisArea,
  height = '100%',
}: HotelMobileMapViewProps) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;
  const [localSelectedId, setLocalSelectedId] = useState<string | null>(null);

  const isControlled = externalSelectedId !== undefined;
  const selectedId = isControlled ? externalSelectedId : localSelectedId;

  const handlePinTap = useCallback((id: string) => {
    const next = selectedId === id ? null : id;
    if (!isControlled) setLocalSelectedId(next);
    onPinTap?.(next);
  }, [selectedId, isControlled, onPinTap]);

  const handleMapClick = useCallback(() => {
    if (!isControlled) setLocalSelectedId(null);
    onPinTap?.(null);
  }, [isControlled, onPinTap]);

  const defaultCenter = hotels.length > 0
    ? {
        lat: hotels.reduce((s, h) => s + h.lat, 0) / hotels.length,
        lng: hotels.reduce((s, h) => s + h.lng, 0) / hotels.length,
      }
    : { lat: 38.7169, lng: -9.1399 };

  if (!apiKey?.trim()) {
    return (
      <Box style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#F4F5FF', borderRadius: 'var(--mantine-radius-md)' }}>
        <Text size="sm" c="navy.5" ta="center">Map unavailable — set VITE_GOOGLE_MAPS_API_KEY.</Text>
      </Box>
    );
  }

  return (
    <Box style={{ height, position: 'relative', overflow: 'hidden' }}>
      <Map
        defaultCenter={defaultCenter}
        defaultZoom={14}
        mapId={import.meta.env.VITE_GOOGLE_MAPS_MAP_ID}
        style={{ width: '100%', height: '100%' }}
        gestureHandling="greedy"
        disableDefaultUI
        onClick={handleMapClick}
        onDragend={onPan}
      >
        {hotels.map((hotel) => {
          const state: HotelPinState =
            selectedId === hotel.id ? 'selected' :
            viewedIds.includes(hotel.id) ? 'viewed' :
            'default';

          return (
            <AdvancedMarker
              key={hotel.id}
              position={{ lat: hotel.lat, lng: hotel.lng }}
              title={hotel.name}
              zIndex={state === 'selected' ? 10 : 1}
              onClick={() => handlePinTap(hotel.id)}
            >
              <HotelPricePin price={hotel.price} state={state} />
            </AdvancedMarker>
          );
        })}
      </Map>

      {showSearchPill && <SearchAreaPill onTap={() => onSearchThisArea?.()} />}
    </Box>
  );
}
