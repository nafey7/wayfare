import { Box, Stack, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { ArrowRight } from 'lucide-react';
import { InspirationTripCard, type InspirationTripData } from './InspirationTripCard';
import { NAVY, SLATE, LINE } from '../landingColors';

export interface RailChip {
  id: string;
  label: string;
  icon?: string;
}

export interface TripsRailDomIds {
  section?: string;
  heading?: string;
  chip?: (index: number) => string;
  tripCard?: (index: number) => string;
}

export interface TripsRailProps {
  title: string;
  subtitle?: string;
  trips: InspirationTripData[];
  background?: 'white' | 'mist';
  chips?: RailChip[];
  activeChip?: string;
  onChipSelect?: (id: string) => void;
  onTripClick?: (data: InspirationTripData) => void;
  onToggleSave?: (data: InspirationTripData) => void;
  /** Stable marketing ids (only wired on `/`). */
  domIds?: TripsRailDomIds;
}

export function TripsRail({
  title,
  subtitle,
  trips,
  background = 'white',
  chips,
  activeChip,
  onChipSelect,
  onTripClick,
  onToggleSave,
  domIds,
}: TripsRailProps) {
  const isMdUp = useMediaQuery('(min-width: 48em)');

  return (
    <Box
      id={domIds?.section}
      component="section"
      style={{
        backgroundColor: background === 'white' ? 'white' : '#F3F5FE',
        paddingBlock: isMdUp ? 56 : 32,
        paddingInline: isMdUp ? 32 : 16,
      }}
    >
      <Box style={{ maxWidth: 1200, marginInline: 'auto' }}>
        {/* Header row */}
        <Box style={{
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          marginBottom: isMdUp ? 22 : 14,
        }}>
          <Stack gap={4} style={{ minWidth: 0, flex: 1 }}>
            <Box style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
              <Text
                id={domIds?.heading}
                component="h2"
                style={{
                  fontSize: isMdUp ? 26 : 20,
                  fontWeight: 900,
                  color: NAVY,
                  letterSpacing: '-.015em',
                  lineHeight: 1.15,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  margin: 0,
                }}
              >
                {title}
              </Text>
              <ArrowRight size={isMdUp ? 22 : 18} color={SLATE} style={{ flexShrink: 0 }} />
            </Box>
            {subtitle && (
              <Text style={{ fontSize: isMdUp ? 13 : 12, color: SLATE }}>
                {subtitle}
              </Text>
            )}
          </Stack>

        </Box>

        {/* Interest chip filter row */}
        {chips && chips.length > 0 && (
          <Box style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 20 }}>
            {chips.map((chip, chipIndex) => {
              const isActive = chip.id === activeChip;
              return (
                <Box
                  key={chip.id}
                  id={domIds?.chip?.(chipIndex)}
                  onClick={() => onChipSelect?.(chip.id)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    paddingInline: 16,
                    paddingBlock: 8,
                    borderRadius: 999,
                    border: `1px solid ${isActive ? NAVY : LINE}`,
                    backgroundColor: isActive ? NAVY : 'white',
                    color: isActive ? 'white' : SLATE,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all .15s ease',
                  }}
                >
                  {chip.icon && <span style={{ fontSize: 14 }}>{chip.icon}</span>}
                  <span>{chip.label}</span>
                </Box>
              );
            })}
          </Box>
        )}

        {/* Cards grid */}
        <Box
          style={{
            display: 'grid',
            gridTemplateColumns: isMdUp ? 'repeat(4, 1fr)' : '1fr',
            gap: 18,
            alignItems: 'start',
          }}
        >
          {trips.map((trip, tripIndex) => (
            <InspirationTripCard
              key={trip.id}
              id={domIds?.tripCard?.(tripIndex)}
              data={trip}
              onClick={onTripClick}
              onToggleSave={onToggleSave}
            />
          ))}
        </Box>
      </Box>
    </Box>
  );
}
