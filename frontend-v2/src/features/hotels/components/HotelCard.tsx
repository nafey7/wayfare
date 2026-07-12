import { useState } from 'react';
import { Box, Text } from '@mantine/core';
import type { Hotel, HotelItinerary } from '@/types/hotels';
import { getHotelCurrency, getHotelTotal, hotelCurrencySymbol } from '../utils';
import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';
import { HotelImageWithFallback } from './HotelImageWithFallback';

export interface HotelCardProps {
  hotel: Hotel | HotelItinerary;
  nights: number;
  onSelect?: () => void;
  isSelecting?: boolean;
  isSelected?: boolean;
  /** Value signal badge shown overlaid on photo e.g. "Best Value", "Cheapest", "Highest Rated" */
  valueBadge?: string;
  tripAdvisorRating?: number | null;
  tripAdvisorReviews?: number | string | null;
}

function formatReviewCount(count: number | string | null | undefined): string {
  const n = Number(count);
  if (!count || isNaN(n)) return '';
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

// Case-insensitive allowlist of meaningful amenity strings from the FlightLogic API.
// Anything not in this list (e.g. "hotel", "American Express", "Visa") is suppressed.
const ALLOWED_AMENITIES = new Set([
  'wi-fi',
  'wifi',
  'free wi-fi',
  'free wifi',
  'air conditioning',
  '24-hour reception',
  'breakfast buffet',
  'continental breakfast',
  'car park',
  'parking',
  'free parking',
  'restaurant',
  'room service',
  'laundry service',
  'laundry',
  'airport shuttle',
  'swimming pool',
  'pool',
  'gym',
  'fitness center',
  'fitness centre',
  'spa',
  'bar',
  'pet-friendly',
  'pets allowed',
  'concierge',
  'business center',
  'business centre',
  'meeting rooms',
  'terrace',
  'garden',
  'jacuzzi',
  'sauna',
  'hot tub',
  'beach access',
  'ocean view',
  'sea view',
  'city view',
  'balcony',
  'kitchen',
  'kitchenette',
  'mini bar',
  'minibar',
  'safe',
  'iron',
  'hair dryer',
  'bathtub',
]);

function filterAmenities(raw: string[]): string[] {
  return raw
    .filter((a) => ALLOWED_AMENITIES.has(a.toLowerCase().trim()))
    .slice(0, 2);
}

export function HotelCard({
  hotel,
  nights,
  onSelect,
  isSelecting = false,
  isSelected = false,
  valueBadge,
  tripAdvisorRating,
  tripAdvisorReviews,
}: HotelCardProps) {
  const [hovered, setHovered] = useState(false);

  const hotelAny = hotel as Hotel & HotelItinerary & { thumbnailUrl?: string };
  const primaryImageUrl =
    hotelAny.thumbnailUrl ?? hotel.imageUrl ?? hotel.images?.[0] ?? null;
  const total = getHotelTotal(hotel);
  const currencySymbol = hotelCurrencySymbol(getHotelCurrency(hotel));
  const perNight =
    hotel.startingPrice?.perNight ?? (nights > 0 ? Math.round(total / nights) : total);

  const amenities = filterAmenities(
    hotel.amenities ?? (hotel as { facilities?: string[] }).facilities ?? []
  );
  const address = [hotel.address, hotel.city].filter(Boolean).join(', ');

  const fareType = hotelAny.fareType ?? '';
  const breakfastLikely =
    /\b(breakfast\s+(?:included|inclusive)|includes?\s+breakfast)\b/i.test(fareType);

  const isHoverActive = hovered && !isSelected;
  const borderColor = isSelected
    ? 'var(--mantine-color-navy-7)'
    : isHoverActive
      ? 'var(--mantine-color-navy-3)'
      : 'var(--mantine-color-gray-2)';
  const borderWidth = isSelected ? 2 : 1;
  const boxShadow = isHoverActive
    ? '0 16px 36px rgba(23,27,99,0.20)'
    : isSelected
      ? '0 2px 8px rgba(23,27,99,0.10)'
      : '0 1px 3px rgba(23,27,99,0.04)';

  return (
    <Box
      role={onSelect ? 'button' : undefined}
      tabIndex={onSelect ? 0 : undefined}
      onClick={isSelecting ? undefined : onSelect}
      onKeyDown={(e) => {
        if (onSelect && !isSelecting && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onSelect();
        }
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 16,
        overflow: 'hidden',
        background: 'white',
        border: `${borderWidth}px solid ${borderColor}`,
        boxShadow,
        cursor: isSelecting ? 'progress' : onSelect ? 'pointer' : 'default',
        opacity: isSelecting ? 0.6 : 1,
        transition: 'box-shadow 180ms ease, border-color 180ms ease, transform 180ms ease',
        transform: isHoverActive ? 'translateY(-4px) scale(1.01)' : 'translateY(0) scale(1)',
        flexShrink: 0,
      }}
    >
      {/* Photo */}
      <Box style={{ position: 'relative', flexShrink: 0, width: '100%', height: 180 }}>
        <HotelImageWithFallback
          primaryUrl={primaryImageUrl}
          hotelName={hotel.name}
          city={hotel.city}
          address={hotel.address}
          fallbackSrc={hotelFallback}
          alt={hotel.name}
          sx={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        />

        {/* Value badge overlay */}
        {valueBadge && (
          <Box
            style={{
              position: 'absolute',
              top: 12,
              left: 12,
              zIndex: 3,
              background: 'rgba(23,27,99,0.92)',
              color: 'white',
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: '-0.01em',
              padding: '5px 10px',
              borderRadius: 9999,
              backdropFilter: 'blur(6px)',
            }}
          >
            {valueBadge}
          </Box>
        )}
      </Box>

      {/* Info */}
      <Box style={{ padding: '12px 14px 14px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* Row 1: Name (left) + total price (right) */}
        <Box
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            gap: 8,
          }}
        >
          <Text
            fw={600}
            style={{
              fontSize: 15,
              color: 'var(--mantine-color-navy-7)',
              lineHeight: 1.3,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flex: 1,
              minWidth: 0,
            }}
          >
            {hotel.name}
          </Text>
          <Text
            fw={700}
            style={{
              fontSize: 14,
              color: 'var(--mantine-color-navy-7)',
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            {currencySymbol}{total.toLocaleString()}
          </Text>
        </Box>

        {/* Row 2: Address + rating (left) + per-night (right) */}
        <Box
          style={{
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'space-between',
            gap: 8,
          }}
        >
          <Text
            style={{
              fontSize: 13,
              color: 'var(--mantine-color-navy-5)',
              lineHeight: 1.3,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flex: 1,
              minWidth: 0,
            }}
          >
            {address}
            {tripAdvisorRating != null && (
              <Text
                component="span"
                style={{ marginLeft: 6, fontSize: 12, color: 'var(--mantine-color-navy-3)' }}
              >
                {' · '}★ {tripAdvisorRating.toFixed(1)}
                {tripAdvisorReviews != null && (
                  <Text component="span" style={{ fontSize: 11 }}>
                    {' '}({formatReviewCount(tripAdvisorReviews)})
                  </Text>
                )}
              </Text>
            )}
          </Text>
          <Text
            style={{
              fontSize: 11,
              color: 'var(--mantine-color-navy-3)',
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            {currencySymbol}{perNight.toLocaleString()} / night
          </Text>
        </Box>

        {/* Row 3: Chips */}
        <Box
          style={{
            display: 'flex',
            gap: 5,
            flexWrap: 'nowrap',
            overflow: 'hidden',
            marginTop: 5,
          }}
        >
          {hotel.starRating > 0 && (
            <Box
              style={{
                fontSize: 11,
                color: '#525874',
                padding: '2px 8px',
                border: '1px solid #e4e6f5',
                borderRadius: 9999,
                flexShrink: 0,
                whiteSpace: 'nowrap',
              }}
            >
              {hotel.starRating}-star
            </Box>
          )}
          {breakfastLikely ? (
            <Box
              style={{
                fontSize: 11,
                color: '#525874',
                padding: '2px 8px',
                border: '1px solid #e4e6f5',
                borderRadius: 9999,
                flexShrink: 0,
                whiteSpace: 'nowrap',
              }}
            >
              Breakfast
            </Box>
          ) : (
            amenities.map((amenity) => (
              <Box
                key={amenity}
                style={{
                  fontSize: 11,
                  color: '#525874',
                  padding: '2px 8px',
                  border: '1px solid #e4e6f5',
                  borderRadius: 9999,
                  flexShrink: 0,
                  whiteSpace: 'nowrap',
                }}
              >
                {amenity}
              </Box>
            ))
          )}
        </Box>
      </Box>
    </Box>
  );
}
