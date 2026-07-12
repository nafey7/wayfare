import { Box, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { PlaneLanding, PlaneTakeoff } from 'lucide-react';
import { getStopsLabel } from '@/features/chat/utils/flightUtils';
import type { SegmentData } from '@/types/flight';

interface FlightSegmentProps {
  flight: SegmentData;
}

export function FlightSegment({ flight }: FlightSegmentProps) {
  const showDate = flight.departure_date !== flight.arrival_date;
  // Resolve responsive shapes at runtime; Mantine's static `style` prop can't
  // accept the `{ xs, sm, md }` shape MUI's sx supported.
  const isSmUp = useMediaQuery('(min-width: 37.5em)');
  const isMdUp = useMediaQuery('(min-width: 48em)');

  const timeFontSize = isMdUp ? '1.5rem' : isSmUp ? '1.35rem' : '1.125rem';
  const codeFontSize = isSmUp ? undefined : '0.8rem';
  const captionFontSize = isSmUp ? '0.75rem' : '0.65rem';
  const stopsHeight = isSmUp ? 24 : 22;
  const stopsPaddingInline = isSmUp ? 12 : 6;
  const planeIconSize = isSmUp ? 16 : 14;
  const lineMarginInline = isSmUp ? 8 : 4;
  const columnGap = isMdUp ? 16 : isSmUp ? 8 : 4;
  const sidePadding = isSmUp ? 2 : 0;
  const gridTemplateColumns = isMdUp
    ? 'minmax(0, 1fr) 180px minmax(0, 1fr)'
    : 'minmax(0, 1fr) minmax(4.75rem, 6.5rem) minmax(0, 1fr)';

  const stopsChipBg = flight.stops === 0 ? 'var(--mantine-color-green-1)' : 'var(--mantine-color-yellow-1)';
  const stopsChipColor = flight.stops === 0 ? 'var(--mantine-color-green-9)' : 'var(--mantine-color-yellow-9)';

  const timeStyle = {
    fontWeight: 700,
    marginBottom: 2,
    fontSize: timeFontSize,
    lineHeight: 1.2,
  } as const;

  return (
    <Box
      style={{
        display: 'grid',
        gridTemplateColumns,
        alignItems: 'center',
        columnGap,
        marginBottom: 16,
        width: '100%',
        minWidth: 0,
      }}
    >
      <Box style={{ textAlign: 'center', minWidth: 0, paddingInline: sidePadding }}>
        <Text style={timeStyle}>{flight.departure_time || 'N/A'}</Text>
        {showDate && (
          <Text
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: 'var(--mantine-color-dimmed)',
              display: 'block',
            }}
          >
            {flight.departure_date || 'N/A'}
          </Text>
        )}
        <Text
          style={{
            fontWeight: 600,
            fontSize: codeFontSize,
          }}
        >
          {flight.origin_code || 'N/A'}
        </Text>
        {!showDate && (
          <Text
            style={{
              fontSize: 12,
              color: 'var(--mantine-color-dimmed)',
              display: 'block',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: isMdUp ? 'normal' : 'nowrap',
            }}
            title={flight.origin_city || undefined}
          >
            {flight.origin_city || 'N/A'}
          </Text>
        )}
      </Box>

      <Box
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          width: '100%',
          minWidth: 0,
          maxWidth: isMdUp ? 180 : undefined,
          marginInline: 'auto',
        }}
      >
        <Text
          style={{
            color: 'var(--mantine-color-dimmed)',
            marginBottom: 4,
            fontWeight: 500,
            fontSize: captionFontSize,
            textAlign: 'center',
          }}
        >
          {flight.duration}
        </Text>
        <Box
          style={{
            display: 'flex',
            alignItems: 'center',
            width: '100%',
            position: 'relative',
          }}
        >
          <PlaneTakeoff
            size={planeIconSize}
            color="var(--mantine-color-blue-6)"
            style={{ zIndex: 1, flexShrink: 0 }}
          />
          <Box
            style={{
              flex: 1,
              minWidth: 0,
              height: 2,
              backgroundColor: 'var(--mantine-color-gray-3)',
              marginInline: lineMarginInline,
              position: 'relative',
            }}
          >
            {flight.stops > 0 && (
              <Box
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  backgroundColor: 'var(--mantine-color-yellow-6)',
                  border: '2px solid var(--mantine-color-body)',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
                }}
              />
            )}
          </Box>
          <PlaneLanding
            size={planeIconSize}
            color="var(--mantine-color-blue-6)"
            style={{ zIndex: 1, flexShrink: 0 }}
          />
        </Box>
        <Box
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginTop: 6,
            height: stopsHeight,
            paddingInline: stopsPaddingInline,
            borderRadius: 9999,
            fontSize: captionFontSize,
            fontWeight: 500,
            backgroundColor: stopsChipBg,
            color: stopsChipColor,
            maxWidth: '100%',
          }}
        >
          {getStopsLabel(flight.stops)}
        </Box>
      </Box>

      <Box style={{ textAlign: 'center', minWidth: 0, paddingInline: sidePadding }}>
        <Text style={timeStyle}>{flight.arrival_time || 'N/A'}</Text>
        {showDate && (
          <Text
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: 'var(--mantine-color-dimmed)',
              display: 'block',
            }}
          >
            {flight.arrival_date || 'N/A'}
          </Text>
        )}
        <Text
          style={{
            fontWeight: 600,
            fontSize: codeFontSize,
          }}
        >
          {flight.destination_code || 'N/A'}
        </Text>
        {!showDate && (
          <Text
            style={{
              fontSize: 12,
              color: 'var(--mantine-color-dimmed)',
              display: 'block',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: isMdUp ? 'normal' : 'nowrap',
            }}
            title={flight.destination_city || undefined}
          >
            {flight.destination_city || 'N/A'}
          </Text>
        )}
      </Box>
    </Box>
  );
}
