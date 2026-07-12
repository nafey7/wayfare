import { useCallback } from 'react';
import { Marker, InfoWindow, useMarkerRef } from '@vis.gl/react-google-maps';
import type { Hotel, HotelItinerary } from '@/types/hotels';
import { getHotelTotal, getHotelCurrency, hotelCurrencySymbol } from '../utils/hotelFilters';
import { resolveHotelImageUrl, getHotelThumbnailUrl } from '../utils/imageUtils';
import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';

export interface HotelMapMarkerProps {
  hotel: Hotel | HotelItinerary;
  position: { lat: number; lng: number };
  nights: number;
  rooms: number;
  isOpen: boolean;
  /** True while room-rates request is in flight for this marker (matches list view `HotelCard`). */
  isSelecting?: boolean;
  onToggle: () => void;
  onSelect: () => void;
}

export function HotelMapMarker({
  hotel,
  position,
  nights,
  rooms,
  isOpen,
  isSelecting = false,
  onToggle,
  onSelect,
}: HotelMapMarkerProps) {
  const [markerRef, marker] = useMarkerRef();

  const handleMarkerClick = useCallback(() => onToggle(), [onToggle]);
  const handleClose = useCallback(() => onToggle(), [onToggle]);

  const name = hotel.name ?? (hotel as { hotelName?: string }).hotelName ?? 'Hotel';
  const total = getHotelTotal(hotel);
  const currency = hotelCurrencySymbol(getHotelCurrency(hotel));
  const thumbRaw = getHotelThumbnailUrl(hotel);
  const thumbSrc = resolveHotelImageUrl(thumbRaw) ?? hotelFallback;
  const address = hotel.address ?? '';
  const city = hotel.city ?? '';

  return (
    <>
      <Marker
        ref={markerRef}
        position={position}
        title={name}
        onClick={handleMarkerClick}
      />
      {isOpen && marker && (
        <InfoWindow
          anchor={marker}
          onClose={handleClose}
          maxWidth={320}
          style={{ width: '100%', boxSizing: 'border-box' }}
        >
          <div style={{ width: '100%', boxSizing: 'border-box' }}>
            <img
              src={thumbSrc}
              alt={name}
              style={{
                width: '100%',
                height: 140,
                objectFit: 'cover',
                borderRadius: 6,
                marginBottom: 6,
              }}
            />
            <h3 style={{ margin: '0 0 4px', fontSize: 15 }}>{name}</h3>
            {(city || address) && (
              <div
                style={{
                  fontSize: 12,
                  color: '#666',
                  marginBottom: 6,
                  overflow: 'hidden',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                }}
              >
                {city && <>📍 {city}</>}
                {city && address && ' · '}
                {address}
              </div>
            )}
            <div style={{ fontWeight: 600, marginBottom: 8 }}>
              {currency}{total.toFixed(2)}
              <span style={{ fontSize: 11, fontWeight: 400, color: '#666', marginLeft: 6 }}>
                ({rooms} room{rooms !== 1 ? 's' : ''}, {nights} night{nights !== 1 ? 's' : ''})
              </span>
            </div>
            <button
              type="button"
              disabled={isSelecting}
              onClick={() => {
                onToggle();
                onSelect();
              }}
              style={{
                width: '100%',
                padding: '8px 12px',
                background: isSelecting ? '#9e9e9e' : '#1976d2',
                color: 'white',
                border: 'none',
                borderRadius: 6,
                cursor: isSelecting ? 'not-allowed' : 'pointer',
                fontWeight: 600,
              }}
            >
              {isSelecting ? 'Loading…' : 'Select Hotel →'}
            </button>
          </div>
        </InfoWindow>
      )}
    </>
  );
}
