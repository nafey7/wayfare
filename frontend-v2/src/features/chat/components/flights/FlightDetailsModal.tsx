import { useState } from 'react';
import {
  ActionIcon,
  Box,
  Button,
  Divider,
  Group,
  Modal,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Plane, Clock, Calendar, MapPin, CircleDot, X, ArrowRight } from 'lucide-react';
import { formatTimeDifference, getStopsLabel, getSegmentFlightNumber } from '@/features/chat/utils/flightUtils';
import { formatPrice } from '@/features/chat/utils/formatters';
import { DEFAULT_PLATFORM_FEE_PERCENTAGE } from '@/features/chat/utils/constants';
import { airlineLogoFallbackUrl } from '@/utils/apiAssetUrl';
import type { MappedFlight, SegmentData, FlightSegment as FlightSegmentType } from '@/types/flight';
import { zIndex } from '@/theme';

interface AirlineLogoProps {
  airlineCode?: string;
  logoUrl?: string | null;
  size?: number;
}

function AirlineLogo({ airlineCode, logoUrl, size = 48 }: AirlineLogoProps) {
  const [hasError, setHasError] = useState(false);
  const src =
    logoUrl ?? airlineLogoFallbackUrl(airlineCode);

  if (!src || hasError) {
    return <Plane size={24} />;
  }

  return (
    <img
      src={src}
      alt={`${airlineCode ?? 'Airline'} logo`}
      onError={() => setHasError(true)}
      style={{
        width: size,
        height: size,
        objectFit: 'contain',
        borderRadius: 4,
      }}
    />
  );
}

interface FlightLegProps {
  leg: SegmentData;
  title: string;
  isReturn?: boolean;
  segments?: FlightSegmentType[];
  flightNumber?: string | null;
  airline?: string | null;
}

function FlightLeg({ leg, title, segments = [], flightNumber, airline }: FlightLegProps) {
  const hasStops = leg.stops > 0;
  const hasLayovers = hasStops && leg.layovers && leg.layovers.length > 0;

  const flightNumbers: string[] = [];
  if (segments && segments.length > 0) {
    segments.forEach((seg) => {
      const num = getSegmentFlightNumber(seg);
      if (num && !flightNumbers.includes(num)) flightNumbers.push(num);
    });
  }
  if (flightNumbers.length === 0 && flightNumber) flightNumbers.push(flightNumber);

  const stopChipBg = leg.stops === 0 ? '#e8f5e9' : '#fff3e0';
  const stopChipColor = leg.stops === 0 ? '#2e7d32' : '#e65100';

  return (
    <Box>
      <Group gap={8} mb={16} align="center">
        <Text size="xs" c="dimmed" fw={600} style={{ textTransform: 'uppercase', letterSpacing: 1 }}>
          {title}
        </Text>
        <ArrowRight size={16} style={{ color: '#9ca3af' }} />
        <Text size="sm" c="dimmed">
          {leg.origin_code} → {leg.destination_code}
        </Text>
      </Group>

      <Group justify="space-between" align="center" mb={24}>
        <Box style={{ textAlign: 'center' }}>
          <Title order={4} fw={700}>
            {leg.origin_code}
          </Title>
          <Text size="sm" c="dimmed">
            {leg.origin_city}
          </Text>
        </Box>

        <Box style={{ flex: 1, paddingInline: 16 }}>
          <Box style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Box
              style={{
                position: 'absolute',
                left: 0,
                right: 0,
                borderTop: '2px dashed var(--mantine-color-gray-3)',
              }}
            />
            <Box style={{ position: 'relative', backgroundColor: 'white', paddingInline: 12 }}>
              <Stack align="center" gap={4} style={{ color: 'var(--mantine-color-dimmed)' }}>
                {hasLayovers && leg.flight_duration ? (
                  <Stack align="center" gap={4}>
                    <Text size="xs" style={{ color: '#667eea', fontWeight: 600 }}>
                      Total time: {leg.duration}
                    </Text>
                    <Text size="sm" fw={500}>
                      Flight Duration: {leg.flight_duration}
                    </Text>
                  </Stack>
                ) : (
                  <Text size="sm" fw={500}>
                    {leg.duration}
                  </Text>
                )}
              </Stack>
            </Box>
          </Box>
          <Group justify="center" align="center" gap={8} mt={4}>
            {hasStops ? (
              <>
                <Plane size={20} style={{ color: '#f18433a8', transform: 'rotate(90deg)' }} />
                <Text size="xs" c="dimmed">
                  {getStopsLabel(leg.stops)}
                </Text>
              </>
            ) : (
              <Box
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  marginTop: 8,
                  height: 24,
                  paddingInline: 12,
                  borderRadius: 9999,
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  backgroundColor: stopChipBg,
                  color: stopChipColor,
                }}
              >
                {getStopsLabel(leg.stops)}
              </Box>
            )}
          </Group>
        </Box>

        <Box style={{ textAlign: 'center' }}>
          <Title order={4} fw={700}>
            {leg.destination_code}
          </Title>
          <Text size="sm" c="dimmed">
            {leg.destination_city}
          </Text>
        </Box>
      </Group>

      {flightNumbers.length > 0 && (
        <Group
          justify="center"
          align="center"
          gap={8}
          my={16}
          py={12}
          style={{
            borderTop: '1px solid var(--mantine-color-gray-3)',
            borderBottom: '1px solid var(--mantine-color-gray-3)',
          }}
        >
          <Plane size={18} style={{ color: '#667eea' }} />
          <Text size="sm" c="dimmed">
            <Text component="span" fw={600} c="dark">
              {airline || (leg as SegmentData & { airline?: string }).airline || 'Flight'}
            </Text>
            {flightNumbers.length > 0 && (
              <>
                <Text component="span" mx={8}>
                  •
                </Text>
                <Text component="span">{flightNumbers.join(', ')}</Text>
              </>
            )}
          </Text>
        </Group>
      )}

      <Box style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <Box>
          <Text size="xs" c="dimmed" fw={600} style={{ textTransform: 'uppercase', letterSpacing: 1 }}>
            Departure
          </Text>
          <Stack mt={8} gap={8}>
            <Group gap={8} align="center">
              <Clock size={16} style={{ color: '#9ca3af' }} />
              <Text size="lg">{leg.departure_time}</Text>
            </Group>
            <Group gap={8} align="center">
              <Calendar size={16} style={{ color: '#9ca3af' }} />
              <Text size="sm">{leg.departure_date}</Text>
            </Group>
            <Group gap={8} align="center">
              <MapPin size={16} style={{ color: '#9ca3af' }} />
              <Text size="sm" c="dimmed">
                {leg.origin_airport}
              </Text>
            </Group>
          </Stack>
        </Box>

        <Box>
          <Text size="xs" c="dimmed" fw={600} style={{ textTransform: 'uppercase', letterSpacing: 1 }}>
            Arrival
          </Text>
          <Stack mt={8} gap={8}>
            <Group gap={8} align="center">
              <Clock size={16} style={{ color: '#9ca3af' }} />
              <Text size="lg">{leg.arrival_time}</Text>
            </Group>
            <Group gap={8} align="center">
              <Calendar size={16} style={{ color: '#9ca3af' }} />
              <Text size="sm">{leg.arrival_date}</Text>
            </Group>
            <Group gap={8} align="center">
              <MapPin size={16} style={{ color: '#9ca3af' }} />
              <Text size="sm" c="dimmed">
                {leg.destination_airport}
              </Text>
            </Group>
          </Stack>
        </Box>
      </Box>

      {hasStops && leg.layovers && (
        <>
          <Divider my={8} />
          <Box>
            <Text
              size="xs"
              c="dimmed"
              fw={600}
              mb={16}
              style={{ display: 'block', textTransform: 'uppercase', letterSpacing: 1 }}
            >
              Layover{leg.stops > 1 ? 's' : ''}
            </Text>
            <Stack gap={16}>
              {leg.layovers.map((stop: FlightSegmentType, index: number) => (
                <Box key={index} style={{ position: 'relative', paddingLeft: 24 }}>
                  <Box
                    style={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      bottom: 0,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                    }}
                  >
                    <CircleDot size={16} style={{ color: '#f59e0b', flexShrink: 0 }} />
                    <Box style={{ width: 2, flex: 1, backgroundColor: 'var(--mantine-color-gray-3)', marginTop: 4 }} />
                  </Box>

                  <Paper
                    withBorder
                    p={16}
                    radius={8}
                    style={{
                      backgroundColor: '#fffbeb',
                      borderColor: '#fcd34d',
                    }}
                  >
                    <Group gap={16} align="flex-start">
                      <Box
                        style={{
                          width: 48,
                          height: 48,
                          backgroundColor: 'white',
                          borderRadius: 12,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          border: '1px solid #e5e7eb',
                          overflow: 'hidden',
                          flexShrink: 0,
                        }}
                      >
                        <AirlineLogo airlineCode={stop.airline_code} logoUrl={stop.logo_url} size={40} />
                      </Box>
                      <Box style={{ flex: 1, minWidth: 0 }}>
                        <Group justify="space-between" align="center" mb={4} wrap="wrap" gap={8}>
                          <Group gap={8} align="center">
                            <Text size="lg" fw={700}>
                              {stop.destination_code}
                            </Text>
                            <Text size="sm" c="dimmed">
                              {stop.destination_city}
                            </Text>
                          </Group>
                          <Box
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              paddingInline: 12,
                              paddingBlock: 4,
                              borderRadius: 9999,
                              fontSize: '0.75rem',
                              fontWeight: 500,
                              backgroundColor: '#fef3c7',
                              color: '#b45309',
                            }}
                          >
                            {`${
                              stop.layover_duration ||
                              formatTimeDifference(stop.arrival_time, stop.departure_time)
                            } layover`}
                          </Box>
                        </Group>
                        {(stop.airline ||
                          stop.airline_name ||
                          (stop as FlightSegmentType & { airline?: string }).airline) && (
                          <Text size="xs" c="dimmed" style={{ display: 'block', marginBottom: 4 }}>
                            {stop.airline ||
                              stop.airline_name ||
                              (stop as FlightSegmentType & { airline?: string }).airline}{' '}
                            · {stop.flight_number}
                          </Text>
                        )}
                        <Text size="xs" c="dimmed" style={{ display: 'block', marginBottom: 8 }}>
                          {stop.destination_airport}
                        </Text>
                        <Group gap={24}>
                          <Box>
                            <Text size="sm">
                              <Text component="span" c="dimmed">
                                Arrive:{' '}
                              </Text>
                              {stop.arrival_time}
                            </Text>
                            {stop.arrival_date &&
                              stop.departure_date &&
                              stop.arrival_date !== stop.departure_date && (
                                <Text size="xs" c="dimmed" style={{ display: 'block' }}>
                                  {stop.arrival_date}
                                </Text>
                              )}
                          </Box>
                          <Box>
                            <Text size="sm">
                              <Text component="span" c="dimmed">
                                Depart:{' '}
                              </Text>
                              {stop.departure_time}
                            </Text>
                            {stop.arrival_date &&
                              stop.departure_date &&
                              stop.arrival_date !== stop.departure_date && (
                                <Text size="xs" c="dimmed" style={{ display: 'block' }}>
                                  {stop.departure_date}
                                </Text>
                              )}
                          </Box>
                        </Group>
                      </Box>
                    </Group>
                  </Paper>
                </Box>
              ))}
            </Stack>
          </Box>
        </>
      )}
    </Box>
  );
}

interface FlightDetailsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  flight: MappedFlight;
}

/** Extract segments for a leg (outbound or return) for flight number display. */
function getSegmentsForLeg(
  flight: MappedFlight,
  leg: SegmentData,
  isReturnLeg: boolean
): FlightSegmentType[] {
  const allSegments =
    flight.segments ||
    (flight.outbound as SegmentData & { segments?: FlightSegmentType[] })?.segments ||
    (flight.return as SegmentData & { segments?: FlightSegmentType[] })?.segments ||
    [];
  if (!allSegments.length || !leg) return [];

  if (flight.is_round_trip && isReturnLeg) {
    const finalDestinationCode = flight.outbound?.destination_code || leg.origin_code;
    const turningPointIndex = allSegments.findIndex(
      (seg) => seg.destination_code === finalDestinationCode
    );
    if (turningPointIndex !== -1) return allSegments.slice(turningPointIndex + 1);
    return allSegments.filter(
      (seg) => (seg.origin_code || seg.departure_code) === leg.origin_code
    );
  }
  const finalDestinationCode = leg.destination_code;
  const turningPointIndex = allSegments.findIndex(
    (seg) => seg.destination_code === finalDestinationCode
  );
  if (turningPointIndex !== -1) return allSegments.slice(0, turningPointIndex + 1);
  return allSegments;
}

export function FlightDetailsModal({ open, onOpenChange, flight }: FlightDetailsModalProps) {
  const isRoundTrip =
    flight.is_round_trip || (flight.return && Object.keys(flight.return).length > 0);

  const isMobile = useMediaQuery('(max-width: 37.49em)');

  const airlineCode = flight.airline_code ?? flight.airline_codes?.[0];
  const airlineName = flight.airline ?? flight.airline_names?.[0];
  const flightNumber =
    flight.flight_number ??
    (flight.segments?.[0] ? getSegmentFlightNumber(flight.segments[0]) : undefined) ??
    flight.outbound?.layovers?.[0]?.flight_number;

  // Round-trip uses 1200px (~lg), one-way uses 900px (~md) — preserves MUI Dialog dual-leg vs single-leg layout.
  const modalSize = isRoundTrip ? 1200 : 900;

  return (
    <Modal
      opened={open}
      onClose={() => onOpenChange(false)}
      fullScreen={isMobile}
      size={modalSize}
      withCloseButton={false}
      padding={0}
      zIndex={zIndex.detailModal}
    >
      <Box
        style={{
          background: 'linear-gradient(to right, #6b72b1, #7e83a7)',
          color: 'white',
          padding: 24,
          position: 'relative',
          width: '100%',
        }}
      >
        <ActionIcon
          onClick={() => onOpenChange(false)}
          variant="transparent"
          style={{ position: 'absolute', top: 32, right: 8, color: 'white' }}
          aria-label="Close"
        >
          <X size={20} />
        </ActionIcon>
        <Group gap={16} align="center">
          <Box
            style={{
              width: 48,
              height: 48,
              backgroundColor: 'white',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
            }}
          >
            <AirlineLogo airlineCode={airlineCode ?? undefined} logoUrl={flight.logo_url} size={40} />
          </Box>
          <Box style={{ flex: 1 }}>
            <Title order={6} fw={600} c="white">
              {airlineName || 'Flight'}
            </Title>
            <Text size="sm" style={{ color: 'rgba(255,255,255,0.8)' }}>
              {flight.outbound?.origin_city} → {flight.outbound?.destination_city}
            </Text>
          </Box>
        </Group>
      </Box>

      <Box style={{ padding: 24 }}>
        {isRoundTrip && flight.return && flight.outbound ? (
          <>
            <FlightLeg
              leg={flight.outbound}
              title="Outbound Flight"
              segments={getSegmentsForLeg(flight, flight.outbound, false)}
              flightNumber={flightNumber ?? undefined}
              airline={airlineName ?? undefined}
            />

            <Divider my={32} />

            <FlightLeg
              leg={flight.return}
              title="Return Flight"
              isReturn
              segments={getSegmentsForLeg(flight, flight.return, true)}
              flightNumber={flightNumber ?? undefined}
              airline={airlineName ?? undefined}
            />
          </>
        ) : (
          <FlightLeg
            leg={flight.outbound || ({} as SegmentData)}
            title="Flight Details"
            segments={flight.outbound ? getSegmentsForLeg(flight, flight.outbound, false) : []}
            flightNumber={flightNumber ?? undefined}
            airline={airlineName ?? undefined}
          />
        )}

        <Divider my={24} />

        {(flight.original_total_fare ?? flight.original_ticket_amount) != null ? (
          <Box>
            <Stack gap={12} mb={16}>
              <Group justify="space-between" align="center">
                <Text size="sm" c="dimmed">
                  🎫 Tickets Amount
                </Text>
                <Text size="sm" fw={600}>
                  ${(flight.original_total_fare ?? flight.original_ticket_amount)!.toFixed(2)}
                </Text>
              </Group>
              <Group justify="space-between" align="center">
                <Text size="sm" c="dimmed">
                  💼 Platform Fee (
                  {flight.platform_fee_percentage ?? DEFAULT_PLATFORM_FEE_PERCENTAGE}
                  %)
                </Text>
                <Text size="sm" fw={600}>
                  ${(
                    (flight.price || 0) -
                    (flight.original_total_fare ?? flight.original_ticket_amount)!
                  ).toFixed(2)}
                </Text>
              </Group>
            </Stack>
            <Divider my={16} />
            <Group justify="space-between" align="center">
              <Text c="dimmed">Total Price</Text>
              <Text size="lg" fw={600}>
                ${(flight.price || 0).toFixed(2)}
              </Text>
            </Group>
          </Box>
        ) : (
          <Group justify="space-between" align="center">
            <Text c="dimmed">Price</Text>
            <Text size="lg" fw={600}>
              {formatPrice(flight.price, flight.currency, true)}
            </Text>
          </Group>
        )}
      </Box>

      <Box style={{ padding: 24, paddingTop: 0 }}>
        <Button fullWidth variant="outline" onClick={() => onOpenChange(false)} radius={8}>
          Close
        </Button>
      </Box>
    </Modal>
  );
}
