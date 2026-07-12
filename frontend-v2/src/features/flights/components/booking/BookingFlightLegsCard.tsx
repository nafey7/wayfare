import { Box, Card, Divider, Stack, Text, Title } from '@mantine/core';
import type { FlightLegCamel } from '@/types/flightBackend';

export interface BookingFlightLegsCardProps {
  /** Flight legs from the validated fare itinerary on the booking confirmation. */
  flightLegs: FlightLegCamel[];
  /** When true, applies OUTBOUND/RETURN coloring + label to two-leg layouts. */
  isRoundTripLayout: boolean;
  /** Per-vendor-leg bound labels (OUTBOUND/RETURN/null) — falls back to round-trip default. */
  rtLegBounds: (string | null | undefined)[];
}

function boundColor(bound: string | null): string {
  if (bound === 'RETURN') return 'var(--mantine-color-grape-6)';
  if (bound === 'OUTBOUND') return 'var(--mantine-color-navy-7)';
  return 'var(--mantine-color-gray-4)';
}

/**
 * Confirmation/details flight legs card. Renders each leg as a colored summary box
 * (date + dep→arr cities/IATA + airline) with OUTBOUND/RETURN bound markers when
 * the booking is a two-leg round trip.
 */
export function BookingFlightLegsCard({
  flightLegs,
  isRoundTripLayout,
  rtLegBounds,
}: BookingFlightLegsCardProps) {
  return (
    <Card mb="md" radius="md" withBorder>
      <Box p="md">
        <Title order={5} fw={700}>
          Flight Details
        </Title>
        <Divider my="sm" />
        <Stack gap="sm">
          {flightLegs.map((leg, legIndex) => {
            const segments = leg?.flightSegments ?? [];
            if (segments.length === 0) return null;

            const rawBound = rtLegBounds[legIndex];
            const bound =
              rawBound ??
              (isRoundTripLayout && flightLegs.length === 2
                ? legIndex === 0
                  ? 'OUTBOUND'
                  : 'RETURN'
                : null);
            const firstSegment = segments[0];
            const lastSegment = segments[segments.length - 1];
            if (!firstSegment || !lastSegment) return null;

            const depIso =
              typeof firstSegment.departureDatetime === 'string'
                ? firstSegment.departureDatetime
                : firstSegment.departureDatetime?.value ?? null;
            const arrIso =
              typeof lastSegment.arrivalDatetime === 'string'
                ? lastSegment.arrivalDatetime
                : lastSegment.arrivalDatetime?.value ?? null;

            const depAirport = firstSegment.departureAirport?.iataCode ?? '';
            const arrAirport = lastSegment.arrivalAirport?.iataCode ?? '';
            const depCity = firstSegment.departureAirport?.cityName ?? depAirport;
            const arrCity = lastSegment.arrivalAirport?.cityName ?? arrAirport;
            const depTime = depIso
              ? new Date(depIso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
              : '';
            const arrTime = arrIso
              ? new Date(arrIso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
              : '';
            const depDate = depIso
              ? new Date(depIso).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })
              : '';
            const airlineCode =
              firstSegment.marketingAirline?.iataCode ??
              firstSegment.operatingAirline?.iataCode ??
              '';
            const airline =
              firstSegment.marketingAirline?.airlineName ??
              firstSegment.operatingAirline?.airlineName ??
              (airlineCode || 'Unknown');

            return (
              <Box
                key={legIndex}
                p="sm"
                style={{
                  backgroundColor: 'var(--mantine-color-gray-0)',
                  borderRadius: 8,
                  borderLeft: `3px solid ${boundColor(bound)}`,
                }}
              >
                {isRoundTripLayout && bound && (
                  <Text size="xs" fw={600} c={bound === 'RETURN' ? 'grape.7' : 'navy.7'} mb={4}>
                    {bound}
                  </Text>
                )}
                <Text size="md" fw={600}>
                  {depDate} · {depTime} {depCity} ({depAirport}) → {arrTime} {arrCity} ({arrAirport})
                </Text>
                <Text size="sm" c="dimmed" mt={2}>
                  {airline}
                </Text>
              </Box>
            );
          })}
        </Stack>
      </Box>
    </Card>
  );
}
