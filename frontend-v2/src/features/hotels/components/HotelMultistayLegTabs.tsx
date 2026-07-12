import { Box, Text, UnstyledButton } from '@mantine/core';
import { CheckCircle } from 'lucide-react';
import type { HotelMultistayLegState, HotelMultistaySegment } from '@/types/hotels';

const PILL = 999;
const INNER = 10;

interface HotelMultistayLegTabsProps {
  segments: HotelMultistaySegment[];
  legs: HotelMultistayLegState[];
  activeLegIndex: number;
  onLegChange: (index: number) => void;
}

function formatDateRange(checkin: string | null, checkout: string | null): string {
  if (!checkin || !checkout) return '';
  const fmt = (d: string) => {
    const dt = new Date(d);
    return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };
  return `${fmt(checkin)} – ${fmt(checkout)}`;
}

export function HotelMultistayLegTabs({
  segments,
  legs,
  activeLegIndex,
  onLegChange,
}: HotelMultistayLegTabsProps) {
  const n = segments.length;

  return (
    <Box
      role="tablist"
      aria-label="Multi-stay hotel legs"
      mb="sm"
      style={{
        display: 'flex',
        flexDirection: 'row',
        flexWrap: 'nowrap',
        gap: 2,
        width: '100%',
        overflowX: 'auto',
        paddingBottom: 2,
        scrollbarWidth: 'thin',
      }}
    >
      {segments.map((seg, i) => {
        const leg = legs[i];
        const isSelected = Boolean(leg?.selectedHotel && leg.selectedRoom && leg.rateRulesResponse);
        const isActive = activeLegIndex === i;
        const label = seg.destination || `Stay ${i + 1}`;
        const dateRange = formatDateRange(seg.checkin, seg.checkout);

        return (
          <UnstyledButton
            key={i}
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onLegChange(i)}
            style={{
              flex: '1 1 0',
              minWidth: 148,
              padding: '10px 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              backgroundColor: isActive
                ? 'var(--mantine-color-navy-7)'
                : 'var(--mantine-color-gray-2)',
              color: isActive ? 'white' : 'var(--mantine-color-black)',
              borderTopLeftRadius: i === 0 ? PILL : INNER,
              borderBottomLeftRadius: i === 0 ? PILL : INNER,
              borderTopRightRadius: i === n - 1 ? PILL : INNER,
              borderBottomRightRadius: i === n - 1 ? PILL : INNER,
              transition: 'background-color 150ms, color 150ms',
            }}
          >
            {isSelected && (
              <CheckCircle
                size={16}
                color={isActive ? 'white' : 'var(--mantine-color-green-6)'}
                style={{ flexShrink: 0 }}
              />
            )}
            <Text
              component="span"
              fw={700}
              size="sm"
              style={{
                color: 'inherit',
                textAlign: 'center',
                lineHeight: 1.35,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexWrap: 'wrap',
                columnGap: 10,
                rowGap: 2,
              }}
            >
              <span>{label}</span>
              {dateRange ? <span>{dateRange}</span> : null}
            </Text>
          </UnstyledButton>
        );
      })}
    </Box>
  );
}
