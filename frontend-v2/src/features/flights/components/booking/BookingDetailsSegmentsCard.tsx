import { Box, Card, Divider, Stack, Text, Title } from '@mantine/core';
import type { TripDetailsSegmentCamel } from '@/types/flightBackend';

export interface BookingDetailsSegmentsCardProps {
  segments: TripDetailsSegmentCamel[];
  /** Pre-computed bound labels — one per segment. null when itinerary isn't a recognizable round trip. */
  segmentBoundLabels?: ('OUTBOUND' | 'RETURN')[] | null;
}

function parseSegmentDatetime(dt: string | { value?: string } | undefined): string | null {
  if (!dt) return null;
  if (typeof dt === 'string') return dt;
  return dt?.value ?? null;
}

function boundColor(bound: 'OUTBOUND' | 'RETURN' | undefined): string {
  if (bound === 'RETURN') return 'var(--mantine-color-grape-6)';
  if (bound === 'OUTBOUND') return 'var(--mantine-color-navy-7)';
  return 'var(--mantine-color-gray-4)';
}

/**
 * Booking details segments card. Renders a flat segment list with OUTBOUND/RETURN
 * coloring when bound labels are provided. Used on `/flights/bookings/:ref` to show
 * the saved itinerary for a confirmed booking.
 */
export function BookingDetailsSegmentsCard({
  segments,
  segmentBoundLabels,
}: BookingDetailsSegmentsCardProps) {
  if (segments.length === 0) return null;

  return (
    <Card mb="md" radius="md" withBorder>
      <Box p="md">
        <Title order={5} fw={700}>
          Flight Details
        </Title>
        <Divider my="sm" />
        <Stack gap="sm">
          {segments.map((seg, idx) => {
            const bound = segmentBoundLabels?.[idx];
            const depIso = parseSegmentDatetime(seg.departureDatetime);
            const arrIso = parseSegmentDatetime(seg.arrivalDatetime);
            const depAirport = seg.departureAirport?.iataCode ?? '';
            const arrAirport = seg.arrivalAirport?.iataCode ?? '';
            const depCity =
              seg.departureAirport?.cityName ?? seg.departureAirport?.airportName ?? depAirport;
            const arrCity =
              seg.arrivalAirport?.cityName ?? seg.arrivalAirport?.airportName ?? arrAirport;
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
              seg.marketingAirline?.iataCode ?? seg.operatingAirline?.iataCode ?? '';
            const airline =
              seg.marketingAirline?.airlineName ??
              seg.operatingAirline?.airlineName ??
              (airlineCode || 'Unknown');
            const flightNumberDisplay =
              seg.marketingFlightNumber?.formattedNumber ??
              seg.marketingFlightNumber?.flightNumber ??
              '';

            return (
              <Box
                key={idx}
                p="sm"
                style={{
                  backgroundColor: 'var(--mantine-color-gray-0)',
                  borderRadius: 8,
                  borderLeft: `3px solid ${boundColor(bound)}`,
                }}
              >
                {segments.length > 1 && bound && (
                  <Text size="xs" fw={600} c={bound === 'RETURN' ? 'grape.7' : 'navy.7'} mb={4}>
                    {bound}
                  </Text>
                )}
                <Text size="md" fw={600}>
                  {depDate} · {depTime} {depCity} ({depAirport}) → {arrTime} {arrCity} ({arrAirport})
                </Text>
                <Text size="sm" c="dimmed" mt={2}>
                  {flightNumberDisplay ? `${airline} ${flightNumberDisplay}` : airline}
                </Text>
              </Box>
            );
          })}
        </Stack>
      </Box>
    </Card>
  );
}
