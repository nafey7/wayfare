/**
 * Inline flight card for the itinerary day plan (#1038).
 *
 * Visual treatment mirrors the activity cards in ``ItineraryDetailsComponent``
 * (white surface + subtle default border) so flight entries read as siblings
 * of the activity entries on the same day, not as call-out banners. The
 * violet accent is reduced to a small icon tile — same role the activity
 * card's thumbnail image plays.
 *
 * Book CTA wiring is intentionally minimal here — the parent component is
 * responsible for hooking the click into the existing flight-booking flow
 * via ``onBook``. Falls back to a disabled state when no handler is provided.
 */
import { Box, Button, Group, Stack, Text } from '@mantine/core';
import { Plane } from 'lucide-react';

import { formatPrice } from '@/features/chat/utils/formatters';
import type { FlightInfo } from '@/types/api.helpers';

export interface InlineFlightCardProps {
  /** Flight from the chat-response top-level ``flights`` array. */
  flight: FlightInfo;
  /**
   * Which leg this card represents. Drives the "Outbound" / "Return"
   * label so the user can tell them apart on Day 1 vs Day N.
   */
  leg?: 'outbound' | 'inbound';
  /**
   * Click handler. Receives the full flight so the caller can route to the
   * existing flight-booking flow (#1038 Q8: alternative tap may swap inline
   * card AND open booking).
   */
  onBook?: (flight: FlightInfo) => void;
}

export function InlineFlightCard({ flight, leg, onBook }: InlineFlightCardProps) {
  const origin = flight.origin_code;
  const destination = flight.destination_code;
  const departure = flight.departure_time;
  const arrival = flight.arrival_time;
  const airline = flight.airline;
  const flightNumber = flight.flight_number;
  const duration = flight.duration;
  const stops = flight.stops;
  const price = flight.price;
  const currency = flight.currency || 'USD';
  const legLabel = leg === 'inbound' ? 'Return flight' : 'Outbound flight';

  const stopsLabel =
    typeof stops === 'number'
      ? stops === 0
        ? 'Direct'
        : `${stops} stop${stops > 1 ? 's' : ''}`
      : null;

  const subtitleParts = [
    airline && (flightNumber ? `${airline} ${flightNumber}` : airline),
    duration,
    stopsLabel,
  ].filter(Boolean) as string[];

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
          backgroundColor: 'var(--mantine-color-violet-1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <Plane size={24} color="var(--mantine-color-violet-7)" />
      </Box>

      <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
        <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 0.4 }}>
          {legLabel}
        </Text>
        <Text fw={700} size="sm" c="dark.8">
          {origin || '?'} {departure ? `${departure} ` : ''}→ {destination || '?'}
          {arrival ? ` ${arrival}` : ''}
        </Text>
        {subtitleParts.length > 0 && (
          <Text size="sm" c="dimmed" style={{ wordBreak: 'break-word' }}>
            {subtitleParts.join(' · ')}
          </Text>
        )}
      </Stack>

      <Stack gap={6} align="flex-end" style={{ flexShrink: 0 }}>
        {typeof price === 'number' && (
          <Text fw={700} size="sm" c="dark.8">
            {formatPrice(price, currency)}
          </Text>
        )}
        <Button
          size="xs"
          variant="subtle"
          color="violet"
          disabled={!onBook}
          onClick={onBook ? () => onBook(flight) : undefined}
        >
          Book this
        </Button>
      </Stack>
    </Group>
  );
}
