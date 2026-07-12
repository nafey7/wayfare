import type { ReactElement } from 'react';
import { Box, Card, Divider, Group, Stack, Text, UnstyledButton } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { CalendarDays, Bed, Map as MapIcon, Users, Eye, Trash2 } from 'lucide-react';

import { AuthenticatedImage } from './AuthenticatedImage';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import { ListItemRow } from '@/features/profile/components/shared';
import type { SavedItineraryCardSummary } from '@/features/itinerary/utils/savedItineraryCardSummary';

export interface SavedItineraryTripCardProps {
  trip: SavedItineraryCardSummary;
  onView: () => void;
  /** `carousel` matches profile horizontal strip; `grid` fills a grid cell. */
  layout?: 'carousel' | 'grid';
  onDelete?: () => void;
  deleteDisabled?: boolean;
}

function TripHeroPlaceholder() {
  return (
    <Box
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--mantine-color-gray-1)',
      }}
    >
      <MapIcon size={64} color="var(--mantine-color-dimmed)" />
    </Box>
  );
}

function CardActionChip({
  icon,
  label,
  onClick,
  disabled,
  tone = 'default',
}: {
  icon: ReactElement;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  /** `danger` — red border and text for destructive actions. */
  tone?: 'default' | 'danger';
}) {
  const danger = tone === 'danger';
  return (
    <UnstyledButton
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        height: 32,
        paddingLeft: 8,
        paddingRight: 12,
        paddingTop: 6,
        paddingBottom: 6,
        borderRadius: 4,
        border: `1px solid ${danger ? 'var(--mantine-color-red-4)' : 'var(--mantine-color-default-border)'}`,
        color: danger ? LANDING_TOKENS.crossRed : LANDING_TOKENS.textHighlight,
        fontFamily: LANDING_TOKENS.fontFamily.display,
        fontWeight: 600,
        fontSize: 14,
        lineHeight: '20px',
        letterSpacing: 0.1,
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        backgroundColor: 'transparent',
      }}
    >
      <Box style={{ display: 'inline-flex', alignItems: 'center' }}>{icon}</Box>
      {label}
    </UnstyledButton>
  );
}

/**
 * Saved itinerary card — same visual design as profile "Upcoming trips" (hero, rows, View chip).
 */
export function SavedItineraryTripCard({
  trip,
  onView,
  layout = 'carousel',
  onDelete,
  deleteDisabled,
}: SavedItineraryTripCardProps) {
  const isSm = useMediaQuery('(min-width: 600px)') ?? false;
  const isMd = useMediaQuery('(min-width: 900px)') ?? false;

  const carouselWidth = isMd
    ? 'min(460px, calc((100vw - 64px) / 3 - 11px))'
    : isSm
      ? 'min(460px, calc(50vw - 24px))'
      : 'min(460px, calc(100vw - 32px))';
  const carouselMinWidth = isSm ? 280 : 260;

  const widthStyle: React.CSSProperties =
    layout === 'grid'
      ? { width: '100%', maxWidth: 460, justifySelf: 'center' }
      : {
          flex: '0 0 auto',
          scrollSnapAlign: 'start',
          width: carouselWidth,
          maxWidth: 460,
          minWidth: carouselMinWidth,
        };

  const statusChip = trip.hasLinkedBookings
    ? { label: 'Confirmed', bgcolor: LANDING_TOKENS.confirmColor, color: LANDING_TOKENS.textLight }
    : { label: 'Pending', bgcolor: LANDING_TOKENS.pendingColor, color: LANDING_TOKENS.pendingChipTextColor };

  return (
    <Card
      withBorder
      padding={0}
      radius="md"
      style={{
        ...widthStyle,
        borderColor: LANDING_TOKENS.baseLighter,
        overflow: 'hidden',
      }}
    >
      <Box
        style={{
          height: 240,
          position: 'relative',
          overflow: 'hidden',
          backgroundColor: 'var(--mantine-color-gray-1)',
        }}
      >
        <AuthenticatedImage
          src={trip.heroImageUrl ?? undefined}
          alt=""
          sx={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
          fallback={<TripHeroPlaceholder />}
        />
        <Box
          style={{
            position: 'absolute',
            top: 11,
            right: 11,
            zIndex: 1,
            pointerEvents: 'none',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: statusChip.bgcolor,
            color: statusChip.color,
            fontFamily: LANDING_TOKENS.fontFamily.display,
            fontWeight: 600,
            fontSize: 13,
            lineHeight: '18px',
            height: 28,
            paddingLeft: 10,
            paddingRight: 10,
            borderRadius: 999,
            boxShadow: '0 1px 4px rgba(0,0,0,0.35)',
          }}
        >
          {statusChip.label}
        </Box>
        <Stack
          gap={4}
          style={{
            position: 'absolute',
            left: 11,
            bottom: 11,
            zIndex: 1,
            pointerEvents: 'none',
          }}
        >
          <Text
            component="span"
            style={{
              fontFamily: LANDING_TOKENS.fontFamily.display,
              fontWeight: 700,
              fontSize: 22,
              lineHeight: '28px',
              color: LANDING_TOKENS.textLight,
              margin: 0,
              display: 'block',
              textShadow: '0 1px 4px rgba(0,0,0,0.65)',
            }}
          >
            {trip.destinationLabel}
          </Text>
        </Stack>
      </Box>

      <Box style={{ padding: '11px 30px 11px 16px' }}>
        <Stack gap={11}>
          <Stack gap={0}>
            <ListItemRow icon={<CalendarDays size={24} />} text={trip.dateRangeLabel} />
            <ListItemRow icon={<Bed size={24} />} text={trip.nightsLabel} />
            <ListItemRow icon={<Users size={24} />} text={trip.passengersLabel} />
          </Stack>
          <Divider color={LANDING_TOKENS.borderDivider} />
          <Group justify="center" align="center" gap={32} wrap="wrap">
            <CardActionChip icon={<Eye size={18} />} label="View" onClick={onView} />
            {onDelete && (
              <CardActionChip
                icon={<Trash2 size={18} />}
                label="Delete"
                onClick={onDelete}
                disabled={deleteDisabled}
                tone="danger"
              />
            )}
          </Group>
        </Stack>
      </Box>
    </Card>
  );
}
