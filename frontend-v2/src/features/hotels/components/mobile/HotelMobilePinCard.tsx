import { Badge, Box, Button, Group, Loader, Stack, Text } from '@mantine/core';
import type { Hotel, HotelItinerary } from '@/types/hotels';
import { getHotelTotal, getHotelCurrency, hotelCurrencySymbol } from '@/features/hotels/utils/hotelFilters';
import { getHotelThumbnailUrl } from '@/features/hotels/utils/imageUtils';
import { HotelImageWithFallback } from '../HotelImageWithFallback';
import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';

export interface HotelMobilePinCardProps {
  hotel: Hotel | HotelItinerary;
  nights: number;
  rooms: number;
  isSelecting: boolean;
  onSelect: () => void;
}

export function HotelMobilePinCard({
  hotel,
  nights,
  rooms,
  isSelecting,
  onSelect,
}: HotelMobilePinCardProps) {
  const name = hotel.name ?? (hotel as { hotelName?: string }).hotelName ?? 'Hotel';
  const currency = hotelCurrencySymbol(getHotelCurrency(hotel));
  const total = getHotelTotal(hotel);
  const perNight = nights > 0 ? total / nights : total;
  const city = hotel.city ?? '';
  const address = hotel.address ?? '';
  const starRating = hotel.starRating ?? 0;
  const thumbRaw = getHotelThumbnailUrl(hotel);

  return (
    <Box p="md">
      <Group align="flex-start" gap="md" wrap="nowrap">
        <Box style={{ width: 80, height: 80, borderRadius: 8, overflow: 'hidden', flexShrink: 0 }}>
          <HotelImageWithFallback
            primaryUrl={thumbRaw || null}
            hotelName={name}
            city={city || null}
            address={address || null}
            fallbackSrc={hotelFallback as string}
            alt={name}
            sx={{ width: 80, height: 80, objectFit: 'cover' }}
          />
        </Box>
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Text fw={700} size="sm" truncate>
            {name}
          </Text>
          {city && (
            <Text size="xs" c="dimmed" truncate>
              {city}
            </Text>
          )}
          {Math.round(starRating) > 0 && (
            <Badge
              size="xs"
              variant="default"
              radius="sm"
              mt={2}
              styles={{ root: { height: 18, fontSize: 10, paddingLeft: 4, paddingRight: 4 } }}
            >
              {'★'.repeat(Math.min(5, Math.round(starRating)))}
            </Badge>
          )}
          <Group align="baseline" gap={4} mt={2}>
            <Text fw={700} size="sm">
              {currency}{Math.round(perNight)}
            </Text>
            <Text size="xs" c="dimmed">
              /night
            </Text>
          </Group>
          <Text size="xs" c="dimmed">
            {currency}{total.toFixed(2)} · {rooms} room{rooms !== 1 ? 's' : ''}, {nights}{' '}
            night{nights !== 1 ? 's' : ''}
          </Text>
        </Box>
      </Group>

      <Button
        fullWidth
        onClick={onSelect}
        disabled={isSelecting}
        mt="md"
        aria-label={`Select ${name}`}
      >
        {isSelecting ? (
          <Stack gap={4} style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Loader size="xs" color="white" />
            <span>Loading…</span>
          </Stack>
        ) : (
          'Select Hotel →'
        )}
      </Button>
    </Box>
  );
}
