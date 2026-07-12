/**
 * Inline hotel card for the itinerary day plan (#1038).
 *
 * Visual treatment mirrors the activity cards in ``ItineraryDetailsComponent``
 * (white surface + subtle default border) so hotel entries read as siblings
 * of the activity entries on the same day, not as call-out banners. The teal
 * accent is reduced to a small icon tile — same role the activity card's
 * thumbnail image plays.
 *
 * The same hotel object is used for both check-in and check-out; the ``phase``
 * prop drives the label. The Book CTA only appears on check-in — there's
 * nothing to book on check-out, the user is already in the hotel by then.
 */
import { Box, Button, Group, Stack, Text } from '@mantine/core';
import { Building2 } from 'lucide-react';

import { formatPrice } from '@/features/chat/utils/formatters';
import type { ChatHotelInfo } from '@/types/api.helpers';

export interface InlineHotelCardProps {
  /** Hotel from the chat-response top-level ``hotels`` array. */
  hotel: ChatHotelInfo;
  /** Check-in (Day 1) or check-out (Day N). */
  phase: 'check-in' | 'check-out';
  /** Click handler — only used on check-in cards. */
  onBook?: (hotel: ChatHotelInfo) => void;
}

/**
 * Pick the price + label pair to render. ``per_night_price`` wins when
 * present (more informative for a multi-night stay); ``total_price`` falls
 * back with a "total" label so a partial payload never silently mislabels a
 * total as per-night.
 */
function resolvePriceDisplay(hotel: ChatHotelInfo): {
  amount: number;
  suffix: '/night' | 'total';
} | null {
  if (typeof hotel.per_night_price === 'number' && hotel.per_night_price > 0) {
    return { amount: hotel.per_night_price, suffix: '/night' };
  }
  if (typeof hotel.total_price === 'number' && hotel.total_price > 0) {
    return { amount: hotel.total_price, suffix: 'total' };
  }
  return null;
}

export function InlineHotelCard({ hotel, phase, onBook }: InlineHotelCardProps) {
  const name = hotel.hotel_name || hotel.name || '';
  const city = hotel.city || '';
  const address = hotel.address || '';
  const price = resolvePriceDisplay(hotel);
  const currency = hotel.currency || 'USD';
  const phaseLabel = phase === 'check-in' ? 'Hotel check-in' : 'Hotel check-out';

  return (
    <Group
      align="flex-start"
      gap="md"
      wrap="nowrap"
      style={{
        padding: 12,
        borderRadius: 12,
        backgroundColor: 'var(--mantine-color-body)',
        border: '1px solid var(--mantine-color-default-border)',
      }}
    >
      <Box
        style={{
          width: 56,
          height: 56,
          borderRadius: 10,
          backgroundColor: 'var(--mantine-color-teal-1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <Building2 size={24} color="var(--mantine-color-teal-7)" />
      </Box>

      <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
        <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 0.4 }}>
          {phaseLabel}
        </Text>
        <Text fw={700} size="sm" c="dark.8" lineClamp={1}>
          {name || 'Hotel'}
        </Text>
        {(address || city) && (
          <Text size="sm" c="dimmed" lineClamp={1}>
            {address || city}
          </Text>
        )}
      </Stack>

      <Stack gap={6} align="flex-end" style={{ flexShrink: 0 }}>
        {price !== null && phase === 'check-in' && (
          <Text fw={700} size="sm" c="dark.8">
            {formatPrice(price.amount, currency)}
            <Text component="span" size="xs" c="dimmed" ml={4}>
              {price.suffix}
            </Text>
          </Text>
        )}
        {phase === 'check-in' && (
          <Button
            size="xs"
            variant="subtle"
            color="teal"
            disabled={!onBook}
            onClick={onBook ? () => onBook(hotel) : undefined}
          >
            Book this
          </Button>
        )}
      </Stack>
    </Group>
  );
}
