import { Box, Group, Text, Badge, UnstyledButton, Divider, Anchor } from '@mantine/core';
import { useElementSize } from '@mantine/hooks';
import { ChevronLeft, Star, MapPin } from 'lucide-react';
import type { ItineraryStop } from './ItineraryDayCard';
import { AuthenticatedImage } from './AuthenticatedImage';
import { DAY_GRADIENTS } from '../constants/dayColors';

export interface ItineraryStopDetailProps {
  stop: ItineraryStop;
  dayNumber: number;
  dayDate: string;
  onClose?: () => void;
}

function StopBody({ stop, dayNumber, dayDate }: Omit<ItineraryStopDetailProps, 'onClose'>) {
  return (
    <Box px={14} pt={12} pb={14} style={{ flex: 1, overflowY: 'auto' }}>
      <Group gap={8} align="baseline" mb={3} wrap="nowrap">
        <Text fw={700} style={{ fontSize: '1rem', lineHeight: 1.2, flex: 1, minWidth: 0 }}>
          {stop.name}
        </Text>
        <Badge variant="light" color="brand" size="xs" radius="xl" style={{ flexShrink: 0 }}>
          Day {dayNumber}{dayDate ? ` · ${dayDate}` : ''}
        </Badge>
      </Group>

      <Group gap={5} wrap="wrap" mb={3}>
        <Text style={{ fontSize: '0.75rem' }} c="navy.5">{stop.duration}</Text>
        {stop.rating !== undefined && (
          <>
            <Text style={{ fontSize: '0.75rem' }} c="navy.3">·</Text>
            <Group gap={3} align="center">
              <Star size={10} fill="#f5a623" color="#f5a623" />
              <Text style={{ fontSize: '0.75rem' }} c="navy.5">{stop.rating}</Text>
            </Group>
          </>
        )}
      </Group>

      <Text size="xs" c="dark.4" lineClamp={2} style={{ lineHeight: 1.55 }} mb={12}>
        {stop.description}
      </Text>

      <Divider mb={10} style={{ borderColor: 'var(--mantine-color-gray-1)' }} />

      <Group gap={5}>
        <MapPin size={12} color="var(--mantine-color-navy-9)" />
        <Anchor
          href={
            stop.lat != null && stop.lng != null
              ? `https://maps.google.com/?q=${stop.lat},${stop.lng}`
              : `https://maps.google.com/?q=${encodeURIComponent(stop.name)}`
          }
          target="_blank"
          size="xs"
          fw={500}
          c="navy.9"
        >
          Open in Google Maps
        </Anchor>
      </Group>
    </Box>
  );
}

export function ItineraryStopDetail({ stop, dayNumber, dayDate, onClose }: ItineraryStopDetailProps) {
  const { ref, width } = useElementSize();
  const gradient = DAY_GRADIENTS[(dayNumber - 1) % DAY_GRADIENTS.length] ?? DAY_GRADIENTS[0]!;
  const isWide = width >= 520;

  return (
    <Box
      ref={ref}
      data-testid="itinerary-stop-detail"
      style={{
        width: '100%',
        borderRadius: 'var(--mantine-radius-md)',
        border: '1px solid var(--mantine-color-gray-2)',
        backgroundColor: 'white',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Back header */}
      <Box style={{ padding: '8px 14px 8px', borderBottom: '1px solid var(--mantine-color-gray-1)', flexShrink: 0 }}>
        <UnstyledButton
          onClick={onClose}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 13, fontWeight: 600, color: '#5C6494' }}
        >
          <ChevronLeft size={15} />
          Day {dayNumber}
        </UnstyledButton>
      </Box>

      {/* Photo + body */}
      <Box style={{ display: 'flex', flexDirection: isWide ? 'row' : 'column', flex: 1, overflow: 'hidden' }}>
        {/* Photo — left column (wide) or top banner (narrow) */}
        <Box
          style={{
            width: isWide ? 200 : '100%',
            height: isWide ? '100%' : 130,
            minHeight: isWide ? 200 : 130,
            background: gradient,
            position: 'relative',
            overflow: 'hidden',
            flexShrink: 0,
          }}
        >
          <AuthenticatedImage
            src={stop.imageUrl}
            alt={stop.name}
            sx={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        </Box>

        <StopBody
          stop={stop}
          dayNumber={dayNumber}
          dayDate={dayDate}
        />
      </Box>
    </Box>
  );
}
