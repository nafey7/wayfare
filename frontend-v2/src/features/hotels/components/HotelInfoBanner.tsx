import { Box, Group, Text, Title } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Star } from 'lucide-react';
import type { Hotel, HotelItinerary } from '@/types/hotels';
import { resolveHotelImageUrl } from '../utils';
import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';
import { HotelImageWithFallback } from './HotelImageWithFallback';

export interface HotelInfoBannerProps {
  /** Selected hotel from Redux */
  hotel: Hotel | HotelItinerary;
  /** Check-in date (ISO string) */
  checkin: string;
  /** Check-out date (ISO string) */
  checkout: string;
  /** Number of nights (calculated) */
  nights: number;
}

function getDisplayName(hotel: Hotel | HotelItinerary): string {
  return hotel.name ?? (hotel as { hotelName?: string }).hotelName ?? 'Hotel';
}

function getThumbnailUrl(hotel: Hotel | HotelItinerary): string | undefined {
  const it = hotel as HotelItinerary;
  return it.thumbnailUrl ?? hotel.imageUrl ?? hotel.images?.[0];
}

function formatDate(isoDate: string): string {
  try {
    const d = new Date(isoDate);
    return d.toLocaleDateString(undefined, {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return isoDate;
  }
}

/**
 * Hotel info banner for the room selection page (gradient header with image, name, dates).
 */
export function HotelInfoBanner({ hotel, checkin, checkout, nights }: HotelInfoBannerProps) {
  const name = getDisplayName(hotel);
  const thumbnail = resolveHotelImageUrl(getThumbnailUrl(hotel)) ?? undefined;
  const rating = hotel.starRating ?? 0;
  const it = hotel as HotelItinerary;
  const propertyType = it.propertyType ?? '';
  const isMd = useMediaQuery('(min-width: 768px)') ?? false;

  return (
    <Box
      mb="md"
      style={{
        borderRadius: 12,
        overflow: 'hidden',
        background: 'linear-gradient(135deg, #1a237e 0%, #3949ab 50%, #5c6bc0 100%)',
        color: 'white',
        boxShadow: 'var(--mantine-shadow-md)',
      }}
    >
      <Group align="stretch" gap={0} wrap="wrap">
        <Box
          style={{
            position: 'relative',
            width: isMd ? 280 : '100%',
            minHeight: isMd ? 180 : 200,
            overflow: 'hidden',
            flexShrink: 0,
            backgroundColor: 'rgba(0,0,0,0.2)',
          }}
        >
          <HotelImageWithFallback
            primaryUrl={thumbnail}
            hotelName={name}
            city={hotel.city}
            address={hotel.address}
            fallbackSrc={hotelFallback}
            alt={name}
            sx={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        </Box>
        <Box
          p="md"
          style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}
        >
          <Title order={4} fw={700} c="white" mb={4}>
            {name}
          </Title>
          {rating > 0 && (
            <Group align="center" gap={2} mb={2}>
              {Array.from({ length: Math.min(5, Math.max(0, rating)) }, (_, i) => (
                <Star key={i} size={20} color="var(--mantine-color-yellow-6)" fill="var(--mantine-color-yellow-6)" />
              ))}
              <Text size="sm" style={{ opacity: 0.95 }}>
                {rating} star{rating !== 1 ? 's' : ''}
              </Text>
            </Group>
          )}
          {(hotel.address || hotel.city) && (
            <Text size="sm" mb={2} style={{ opacity: 0.9 }}>
              {[hotel.address, hotel.city].filter(Boolean).join(', ')}
            </Text>
          )}
          {propertyType && (
            <Text size="xs" mb={4} style={{ opacity: 0.85 }}>
              {propertyType}
            </Text>
          )}
          <Group gap="md" wrap="wrap" mt={4}>
            <Text size="sm" style={{ opacity: 0.95 }}>
              <strong>Check-in:</strong> {formatDate(checkin)}
            </Text>
            <Text size="sm" style={{ opacity: 0.95 }}>
              <strong>Check-out:</strong> {formatDate(checkout)}
            </Text>
            <Text size="sm" style={{ opacity: 0.95 }}>
              <strong>{nights} night{nights !== 1 ? 's' : ''}</strong>
            </Text>
          </Group>
        </Box>
      </Group>
    </Box>
  );
}
