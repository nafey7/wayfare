import { Box, Card, Divider, Group, Stack, Text, Title } from '@mantine/core';
import type { ProcessedLeg, FlightSegmentCamel } from '@/types/flightBackend';
import { extractTimeFromISO } from '../../utils/flightUtils';

export interface FlightDetailsItineraryCardProps {
  /** Pre-processed legs from `processLeg(...)`. */
  processedLegs: ProcessedLeg[];
}

/**
 * Detailed itinerary card on `/flights/details`. Renders each processed leg as a
 * dep→arr summary with a flight-path visual, airline summary block, and per-segment
 * codeshare details for multi-segment legs. The card is purely presentational —
 * all derivations happen upstream via `processLeg`.
 */
export function FlightDetailsItineraryCard({ processedLegs }: FlightDetailsItineraryCardProps) {
  return (
    <Card mb="md" radius="md" withBorder>
      <Box p="md">
        <Title order={3} fw={700}>
          Flight Details
        </Title>
        <Divider my="sm" />

        {processedLegs.map((leg, legIndex) => {
          const isFirst = legIndex === 0;
          const accentVar = isFirst
            ? 'var(--mantine-color-navy-7)'
            : 'var(--mantine-color-grape-6)';
          const accentDarkVar = isFirst
            ? 'var(--mantine-color-navy-7)'
            : 'var(--mantine-color-grape-7)';
          return (
            <Box
              key={legIndex}
              mb={legIndex < processedLegs.length - 1 ? 'lg' : 0}
              style={
                legIndex > 0
                  ? {
                      borderTop: '1px solid var(--mantine-color-gray-3)',
                      paddingTop: 24,
                      marginTop: 24,
                    }
                  : undefined
              }
            >
              {leg.legLabel && (
                <Text size="sm" fw={600} c={isFirst ? 'navy.7' : 'grape.6'} mb="sm">
                  ✈️ {leg.legLabel}
                </Text>
              )}

              <Group justify="space-between" align="center" wrap="nowrap">
                <Box style={{ flex: 1, textAlign: 'center' }}>
                  <Title order={4} fw={700}>
                    {leg.departure.time}
                  </Title>
                  <Text size="sm" c="dimmed">
                    {leg.departure.airport}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {leg.departure.city}
                  </Text>
                  <Text size="xs" c="dimmed" display="block" mt={2}>
                    {leg.departure.date}
                  </Text>
                </Box>

                <Box
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    padding: '0 16px',
                  }}
                >
                  <div
                    style={{
                      width: '100%',
                      height: 2,
                      backgroundColor: 'var(--mantine-color-gray-3)',
                      position: 'relative',
                      marginBottom: 4,
                    }}
                  >
                    <div
                      style={{
                        position: 'absolute',
                        left: '50%',
                        top: '50%',
                        transform: 'translate(-50%, -50%)',
                        width: 20,
                        height: 20,
                        backgroundColor: accentVar,
                        borderRadius: '50%',
                        border: '2px solid white',
                      }}
                    />
                  </div>
                  <Text size="sm" c="dimmed" mb={2}>
                    {leg.duration}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {leg.stopsText}
                  </Text>
                  {leg.totalTimeDisplay && (
                    <Text size="xs" fw={600} mt={2} style={{ color: accentDarkVar }}>
                      Total: {leg.totalTimeDisplay}
                    </Text>
                  )}
                </Box>

                <Box style={{ flex: 1, textAlign: 'center' }}>
                  <Title order={4} fw={700}>
                    {leg.arrival.time}
                  </Title>
                  <Text size="sm" c="dimmed">
                    {leg.arrival.airport}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {leg.arrival.city}
                  </Text>
                  <Text size="xs" c="dimmed" display="block" mt={2}>
                    {leg.arrival.date}
                  </Text>
                </Box>
              </Group>

              {leg.airlinesInfo && leg.airlinesInfo.length > 0 && (
                <Box
                  mt="sm"
                  p="sm"
                  style={{
                    backgroundColor: 'var(--mantine-color-gray-0)',
                    borderRadius: 8,
                    borderLeft: `3px solid ${accentVar}`,
                  }}
                >
                  <Text size="sm" fw={600} c={isFirst ? 'navy.7' : 'grape.6'} mb={4}>
                    ✈️ Flight Details
                  </Text>
                  <Stack gap={4}>
                    {leg.airlinesInfo.map((airlineInfo, infoIndex) => (
                      <Text key={infoIndex} size="sm">
                        <span style={{ fontWeight: 600, color: accentVar }}>
                          {airlineInfo.name}
                        </span>
                        {airlineInfo.flights.length > 0 && (
                          <>
                            <span style={{ margin: '0 8px', color: 'var(--mantine-color-dimmed)' }}>
                              •
                            </span>
                            <span>{airlineInfo.flights.join(', ')}</span>
                          </>
                        )}
                      </Text>
                    ))}
                  </Stack>
                </Box>
              )}

              {leg.segments && leg.segments.length > 1 && (
                <Box
                  mt="sm"
                  pl="sm"
                  style={{ borderLeft: '2px solid var(--mantine-color-gray-3)' }}
                >
                  <Text size="xs" fw={600} c="dimmed" mb={4} display="block">
                    Segment Details:
                  </Text>
                  <Stack gap={6}>
                    {(leg.segments as FlightSegmentCamel[]).map((segment, segIndex) => {
                      const airlineCode =
                        segment.marketingAirline?.iataCode ??
                        segment.operatingAirline?.iataCode ??
                        '';
                      const airline =
                        segment.marketingAirline?.airlineName ??
                        segment.operatingAirline?.airlineName ??
                        (airlineCode || 'Unknown');
                      const flightNumber = segment.marketingFlightNumber?.formattedNumber ?? '';
                      const isCodeshare =
                        segment.marketingAirline?.iataCode &&
                        segment.operatingAirline?.iataCode &&
                        segment.marketingAirline.iataCode !== segment.operatingAirline.iataCode;
                      const operatingAirline = isCodeshare
                        ? segment.operatingAirline?.airlineName ??
                          segment.operatingAirline?.iataCode ??
                          null
                        : null;

                      const depTime = segment.departureDatetime
                        ? extractTimeFromISO(segment.departureDatetime)
                        : '';
                      const arrTime = segment.arrivalDatetime
                        ? extractTimeFromISO(segment.arrivalDatetime)
                        : '';
                      const depAirport = segment.departureAirport?.iataCode ?? '';
                      const arrAirport = segment.arrivalAirport?.iataCode ?? '';

                      return (
                        <Text key={segIndex} size="xs" c="dimmed">
                          {segIndex > 0 && '→ '}
                          <span style={{ fontWeight: 600, color: accentVar }}>{airline}</span>
                          {flightNumber && (
                            <>
                              <span style={{ margin: '0 4px' }}>•</span>
                              <span>{flightNumber}</span>
                            </>
                          )}
                          {operatingAirline && (
                            <span style={{ marginLeft: 4, fontStyle: 'italic' }}>
                              (operated by {operatingAirline})
                            </span>
                          )}
                          {depTime && arrTime && depAirport && arrAirport && (
                            <span style={{ marginLeft: 8 }}>
                              • {depTime} {depAirport} → {arrTime} {arrAirport}
                            </span>
                          )}
                        </Text>
                      );
                    })}
                  </Stack>
                </Box>
              )}
            </Box>
          );
        })}
      </Box>
    </Card>
  );
}
