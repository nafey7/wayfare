import { Alert, Badge, Box, Card, Group, Loader, Stack, Text, UnstyledButton } from '@mantine/core';
import { CalendarDays, ChevronRight, CreditCard, PlaneTakeoff } from 'lucide-react';
import { tryClassicRoundTripLine } from '@/features/flights/utils/classicRoundTripRoute';
import type { LinkedBookingEventSummary } from '@/types/itineraries';
import {
  formatAirportPairLine,
  formatBookingDate,
  formatUsdAmount,
} from './linkedBookingFormat';

export interface FlightBookingRow {
  voyaReference: string;
  event?: LinkedBookingEventSummary | null;
}

export interface ItineraryFlightBookingsListProps {
  itineraryId: string;
  items: FlightBookingRow[];
  onSelectReference: (voyaReference: string) => void;
  isLoading?: boolean;
  error?: boolean;
}

const monoFont =
  'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';

/**
 * Linked flight bookings for one itinerary — card layout with booking_events fields.
 */
export function ItineraryFlightBookingsList({
  itineraryId,
  items,
  onSelectReference,
  isLoading,
  error,
}: ItineraryFlightBookingsListProps) {
  if (isLoading) {
    return (
      <Group justify="center" py="xl">
        <Loader aria-label="Loading flight bookings" />
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
        No flight bookings are linked to this itinerary.
      </Text>
    );
  }

  return (
    <Stack
      component="nav"
      gap="md"
      aria-label={`Flight bookings linked to itinerary ${itineraryId}`}
    >
      {items.map(({ voyaReference, event }) => {
        const bookedLabel =
          formatBookingDate(event?.dateBooked ?? undefined) ??
          formatBookingDate(event?.timestamp);
        const amountLabel = formatUsdAmount(event?.amount ?? undefined);
        const status = event?.ticketStatus?.trim();
        const pnr = event?.airlinePnrCode?.trim();
        const displayAirline = (
          event?.primaryMarketingAirlineName?.trim() ||
          event?.airlinePnrAirlineName?.trim() ||
          ''
        );
        const legs = event?.routeLegs;
        const tripType = event?.flightTripType;
        let classicRoundTripLine: string | null = null;
        let outboundRoute: string | null = null;
        let returnRoute: string | null = null;
        /** When more than two route legs, show every leg (multi-city / complex itineraries). */
        let multiLegLines: { label: string; line: string }[] | null = null;
        if (legs && legs.length > 0) {
          if (legs.length > 2) {
            multiLegLines = legs.map((leg, idx) => ({
              label: `Leg ${idx + 1}`,
              line:
                formatAirportPairLine(
                  leg.departureIata?.trim(),
                  leg.arrivalIata?.trim(),
                ) ?? '',
            }));
          } else {
            const a = legs[0];
            if (legs.length > 1) {
              const b = legs[1];
              classicRoundTripLine =
                a && b
                  ? tryClassicRoundTripLine(
                      a.departureIata,
                      a.arrivalIata,
                      b.departureIata,
                      b.arrivalIata,
                      tripType,
                    )
                  : null;
            }
            if (!classicRoundTripLine && a) {
              outboundRoute = formatAirportPairLine(
                a.departureIata?.trim(),
                a.arrivalIata?.trim(),
              );
            }
            if (!classicRoundTripLine && legs.length > 1) {
              const b = legs[1];
              if (b) {
                returnRoute = formatAirportPairLine(
                  b.departureIata?.trim(),
                  b.arrivalIata?.trim(),
                );
              }
            }
          }
        } else {
          const dep = event?.departureAirportIata?.trim();
          const legacyArr = event?.arrivalAirportIata?.trim();
          const retDep = event?.returnDepartureAirportIata?.trim();
          const retArr = event?.returnArrivalAirportIata?.trim();
          classicRoundTripLine = tryClassicRoundTripLine(
            dep,
            legacyArr,
            retDep,
            retArr,
            tripType,
          );
          if (!classicRoundTripLine) {
            outboundRoute = formatAirportPairLine(dep, legacyArr);
            returnRoute = formatAirportPairLine(retDep, retArr);
          }
        }

        return (
          <UnstyledButton
            key={voyaReference}
            onClick={() => onSelectReference(voyaReference)}
            aria-label={`Open flight booking ${voyaReference}`}
            style={{ display: 'block', width: '100%' }}
          >
            <Card
              withBorder
              radius="md"
              padding="lg"
              style={{
                backgroundColor: 'var(--mantine-color-brand-0)',
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
                    backgroundColor: 'var(--mantine-color-brand-1)',
                    color: 'var(--mantine-color-brand-6)',
                  }}
                >
                  <PlaneTakeoff size={26} aria-hidden />
                </Box>
                <Stack gap="xs" style={{ flex: 1, minWidth: 0 }}>
                  <Text
                    size="xs"
                    c="dimmed"
                    style={{ letterSpacing: 0.08, lineHeight: 1.2, textTransform: 'uppercase' }}
                  >
                    Flight booking
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
                      <Badge variant="outline" color="brand.6" size="sm" fw={600}>
                        {status}
                      </Badge>
                    </Box>
                  ) : null}
                  <Stack gap={4}>
                    {multiLegLines && multiLegLines.length > 0
                      ? multiLegLines.map(({ label, line }) => (
                          <Text key={`${voyaReference}-${label}`} size="sm" c="dimmed" fw={600}>
                            {label} · {line}
                          </Text>
                        ))
                      : null}
                    {!multiLegLines?.length && classicRoundTripLine ? (
                      <Text size="sm" c="dimmed" fw={600}>
                        {classicRoundTripLine}
                      </Text>
                    ) : null}
                    {!multiLegLines?.length && !classicRoundTripLine && outboundRoute ? (
                      <Text size="sm" c="dimmed" fw={600}>
                        {outboundRoute}
                      </Text>
                    ) : null}
                    {!multiLegLines?.length && !classicRoundTripLine && returnRoute ? (
                      <Text size="sm" c="dimmed">
                        Return · {returnRoute}
                      </Text>
                    ) : null}
                    {displayAirline ? (
                      <Box>
                        <Badge
                          variant="filled"
                          size="sm"
                          fw={600}
                          style={{
                            backgroundColor: 'var(--mantine-color-brand-2)',
                            color: 'var(--mantine-color-dark-8)',
                          }}
                        >
                          {displayAirline}
                        </Badge>
                      </Box>
                    ) : null}
                    {pnr ? (
                      <Text size="sm" c="dimmed">
                        PNR {pnr}
                      </Text>
                    ) : null}
                  </Stack>
                  <Group gap="md" wrap="wrap" pt={4}>
                    {bookedLabel ? (
                      <Group gap={6} align="center" wrap="nowrap">
                        <CalendarDays size={18} color="var(--mantine-color-dimmed)" aria-hidden />
                        <Text size="sm" c="dimmed">
                          {event?.dateBooked ? 'Booked' : 'Recorded'} · {bookedLabel}
                        </Text>
                      </Group>
                    ) : null}
                    {amountLabel ? (
                      <Group gap={6} align="center" wrap="nowrap">
                        <CreditCard size={18} color="var(--mantine-color-dimmed)" aria-hidden />
                        <Text size="sm" fw={600}>
                          {amountLabel}
                        </Text>
                      </Group>
                    ) : null}
                  </Group>
                </Stack>
                <ChevronRight
                  aria-hidden
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
