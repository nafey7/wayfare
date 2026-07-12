import { Alert, Badge, Box, Card, Group, Loader, Stack, Text, UnstyledButton } from '@mantine/core';
import { CalendarDays, ChevronRight, CreditCard, Hotel as HotelIcon } from 'lucide-react';
import type { LinkedBookingEventSummary } from '@/types/itineraries';
import { formatBookingDate, formatUsdAmount } from './linkedBookingFormat';

export interface HotelBookingRow {
  voyaReference: string;
  event?: LinkedBookingEventSummary | null;
}

export interface ItineraryHotelBookingsListProps {
  itineraryId: string;
  items: HotelBookingRow[];
  onSelectReference: (voyaReference: string) => void;
  isLoading?: boolean;
  error?: boolean;
}

const monoFont =
  'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';

/**
 * Linked hotel bookings for one itinerary — card layout with booking_events fields.
 */
export function ItineraryHotelBookingsList({
  itineraryId,
  items,
  onSelectReference,
  isLoading,
  error,
}: ItineraryHotelBookingsListProps) {
  if (isLoading) {
    return (
      <Group justify="center" py="xl">
        <Loader aria-label="Loading hotel bookings" />
      </Group>
    );
  }

  if (error) {
    return (
      <Alert color="red" mt="sm">
        Failed to load itinerary. Please try again.
      </Alert>
    );
  }

  if (items.length === 0) {
    return (
      <Text size="sm" c="dimmed" mt="sm">
        No hotel bookings are linked to this itinerary.
      </Text>
    );
  }

  return (
    <Stack
      component="nav"
      gap="md"
      aria-label={`Hotel bookings linked to itinerary ${itineraryId}`}
    >
      {items.map(({ voyaReference, event }) => {
        const bookedLabel =
          formatBookingDate(event?.dateBooked ?? undefined) ??
          formatBookingDate(event?.timestamp);
        const amountLabel = formatUsdAmount(event?.amount ?? undefined);
        const status = event?.ticketStatus?.trim();
        const hotelRef = event?.hotelReferenceNumber?.trim();

        return (
          <UnstyledButton
            key={voyaReference}
            onClick={() => onSelectReference(voyaReference)}
            aria-label={`Open hotel booking ${voyaReference}`}
            style={{ display: 'block', width: '100%' }}
          >
            <Card
              withBorder
              radius="md"
              padding="lg"
              style={{
                backgroundColor: 'var(--mantine-color-grape-0)',
                transition: 'box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease',
              }}
            >
              <Group align="flex-start" gap="md" wrap="nowrap">
                <Box
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: 8,
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: 'var(--mantine-color-grape-1)',
                    color: 'var(--mantine-color-grape-6)',
                  }}
                >
                  <HotelIcon size={26} />
                </Box>
                <Stack gap="xs" style={{ flex: 1, minWidth: 0 }}>
                  <Text
                    size="xs"
                    c="dimmed"
                    style={{ letterSpacing: 0.08, lineHeight: 1.2, textTransform: 'uppercase' }}
                  >
                    Hotel booking
                  </Text>
                  <Text
                    fw={700}
                    size="lg"
                    style={{
                      fontFamily: monoFont,
                      wordBreak: 'break-word',
                    }}
                  >
                    {voyaReference}
                  </Text>
                  {status ? (
                    <Box>
                      <Badge variant="outline" color="grape.6" size="sm" fw={600}>
                        {status}
                      </Badge>
                    </Box>
                  ) : null}
                  {hotelRef ? (
                    <Text size="sm" c="dimmed">
                      Confirmation · {hotelRef}
                    </Text>
                  ) : null}
                  <Group gap="md" wrap="wrap" pt={4}>
                    {bookedLabel ? (
                      <Group gap={6} align="center" wrap="nowrap">
                        <CalendarDays size={18} color="var(--mantine-color-dimmed)" />
                        <Text size="sm" c="dimmed">
                          {event?.dateBooked ? 'Booked' : 'Recorded'} · {bookedLabel}
                        </Text>
                      </Group>
                    ) : null}
                    {amountLabel ? (
                      <Group gap={6} align="center" wrap="nowrap">
                        <CreditCard size={18} color="var(--mantine-color-dimmed)" />
                        <Text size="sm" fw={600}>
                          {amountLabel}
                        </Text>
                      </Group>
                    ) : null}
                  </Group>
                </Stack>
                <ChevronRight
                  size={20}
                  color="var(--mantine-color-dimmed)"
                  style={{ alignSelf: 'center', flexShrink: 0 }}
                />
              </Group>
            </Card>
          </UnstyledButton>
        );
      })}
    </Stack>
  );
}
