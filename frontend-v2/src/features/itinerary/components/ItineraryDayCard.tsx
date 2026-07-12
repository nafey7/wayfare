import { useState } from 'react';
import { Box, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Chip, PhotoBlock, TimelineRow, computeDayColors, dayCardContainerStyle } from './dayCardPrimitives';
import {
  C_NAVY, C_BORDER, C_NAVY_MID, C_LABEL,
  C_NAVY_LIGHT, C_PILL_BG, C_PILL_HOVER, C_DIVIDER, C_BTN_HOVER,
  C_SHADOW_PILL,
} from '../constants/itineraryColors';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ItineraryStop {
  id: string;
  name: string;
  description: string;
  duration: string;
  startTime?: string;
  endTime?: string;
  cost?: string;
  rating?: number;
  reviewCount?: number;
  imageUrl?: string;
  location?: string;
  category?: string;
  tip?: string;
  address?: string;
  phone?: string;
  website?: string;
  lat?: number;
  lng?: number;
}

export interface ConnectorDescriptor {
  mode: 'walk' | 'transit' | 'bus';
  label: string;
}

export interface ItineraryStopEntry {
  stop: ItineraryStop;
  connector?: ConnectorDescriptor[];
}

export interface ItineraryDay {
  dayNumber: number;
  /** Short date label, e.g. "THU 15 MAY" */
  date: string;
  title: string;
  description: string;
  stopCount: number;
  /** Thumbnail used in collapsed row. Falls back to per-day gradient. */
  imageUrl?: string;
  /** Higher-res cover used as full-width banner when expanded. Falls back to imageUrl then gradient. */
  bannerImageUrl?: string;
  stops?: ItineraryStopEntry[];
}

export interface ItineraryDayCardProps {
  day: ItineraryDay;
  isExpanded?: boolean;
  isSkipped?: boolean;
  /** Hide the full-width banner when expanded (e.g. when used as a stops-only list). */
  hideBanner?: boolean;
  selectedStopId?: string | null;
  onStopSelect?: (stopId: string | null) => void;
  onToggle?: () => void;
  onSkipDay?: () => void;
  onUnskipDay?: () => void;
  /** Pass `!isMdUp` from the parent so only one matchMedia subscription exists per page. Falls back to an internal query when omitted. */
  isMobile?: boolean;
}

// ─── Icons (local — not shared with ItineraryDetailsComponent) ────────────────

function CalendarXIcon({ size = 12 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zM9 13l6 6M15 13l-6 6" />
    </svg>
  );
}

function UndoIcon({ size = 12 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7v6h6M3.51 15a9 9 0 1 0 .49-3.96" />
    </svg>
  );
}

// ─── Transport icons + connector ─────────────────────────────────────────────

function WalkIcon({ size = 13, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="4" r="2" />
      <path d="M9 20l1.5-6 2.5 2 2.5-4.5L17 20" />
      <path d="M9.5 14L7 18" />
    </svg>
  );
}

function TransitIcon({ size = 13, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      <rect x="4" y="3" width="16" height="13" rx="2" /><path d="M4 10h16" /><path d="M8 19l-2 2" /><path d="M16 19l2 2" /><path d="M8 16v3" /><path d="M16 16v3" />
    </svg>
  );
}

function BusIcon({ size = 13, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      <path d="M8 6v6M15 6v6M2 12h19.6" /><path d="M18 18h3s.5-1.7.8-4.4c.3-2.4.2-6.6 0-8.6c-.4-3.6-2.8-4-6.8-4H9c-4 0-6.4.4-6.8 4c-.2 2-.3 6.2 0 8.6C2.5 16.3 3 18 3 18h3" /><circle cx="7" cy="18" r="2" /><circle cx="17" cy="18" r="2" />
    </svg>
  );
}

const CONNECTOR_ICON_MAP = {
  walk: WalkIcon,
  transit: TransitIcon,
  bus: BusIcon,
} as const;

function StopConnector({ options }: { options: ConnectorDescriptor[] }) {
  const [hovered, setHovered] = useState(false);
  if (options.length === 0) return null;
  return (
    <Box style={{ margin: '8px 0 8px 32px' }}>
      <Box
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 7,
          padding: '6px 12px', borderRadius: 9999,
          background: hovered ? C_PILL_HOVER : C_PILL_BG,
          border: `1px solid ${hovered ? C_NAVY : C_BORDER}`,
          color: C_NAVY, fontSize: 12.5, fontWeight: 600, lineHeight: 1.3,
          width: 'fit-content', userSelect: 'none',
          boxShadow: hovered ? `0 1px 6px ${C_SHADOW_PILL}` : 'none',
          transition: 'background .12s, border-color .12s, box-shadow .12s',
        }}
      >
        {options.map((opt, i) => {
          const Icon = CONNECTOR_ICON_MAP[opt.mode];
          return (
            <Box key={i} component="span" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              {i > 0 && <Box component="span" style={{ color: C_NAVY_LIGHT, margin: '0 2px' }}>·</Box>}
              <Icon size={13} color={hovered ? C_NAVY : C_LABEL} />
              <span>{opt.label}</span>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function ItineraryDayCard({
  day,
  isExpanded = false,
  isSkipped = false,
  hideBanner = false,
  selectedStopId = null,
  onStopSelect,
  onToggle,
  onSkipDay,
  onUnskipDay,
  isMobile: isMobileProp,
}: ItineraryDayCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const isMobileQuery = useMediaQuery('(max-width: 900px)') ?? false;
  const isMobile = isMobileProp ?? isMobileQuery;

  const { gradient, accent } = computeDayColors(day.dayNumber);
  const banner      = day.bannerImageUrl ?? day.imageUrl;
  const dayChipText = `Day ${day.dayNumber}${day.date ? ` · ${day.date}` : ''}`;

  const cardStyle: React.CSSProperties = {
    ...dayCardContainerStyle(isExpanded, isHovered, isSkipped),
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0,
  };

  // ── Collapsed ──────────────────────────────────────────────────────────────
  if (!isExpanded) {
    return (
      <Box
        onClick={onToggle}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        style={{ ...cardStyle, cursor: onToggle ? 'pointer' : 'default' }}
      >
        <PhotoBlock
          height={120}
          imageUrl={day.imageUrl}
          gradient={gradient}
          dayChipText={dayChipText}
          accent={accent}
          isExpanded={false}
          onToggle={onToggle}
          isMobile={isMobile}
          alt={day.title}
          fallback={
            <Box style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Text size="xl" fw={700} c="white" style={{ opacity: 0.7 }}>{day.dayNumber}</Text>
            </Box>
          }
          unavailableLabel={`Day ${day.dayNumber}: ${day.title}`}
        />

        <Box style={{ padding: '10px 14px 12px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <Box
            style={{
              fontSize: 15, fontWeight: 600, color: C_NAVY, lineHeight: 1.3,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}
          >
            {day.title}
          </Box>
          <Box
            style={{
              fontSize: 13, color: C_NAVY_MID, lineHeight: 1.3,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}
          >
            {day.description}
          </Box>
          <Box style={{ display: 'flex', gap: 5, marginTop: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <Chip>{day.stopCount} stops</Chip>
            {isSkipped && <Chip solid>Skipped</Chip>}
          </Box>
        </Box>
      </Box>
    );
  }

  // ── Expanded ───────────────────────────────────────────────────────────────
  return (
    <Box
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={cardStyle}
    >
      {!hideBanner && (
        <PhotoBlock
          height={160}
          imageUrl={banner}
          gradient={gradient}
          dayChipText={dayChipText}
          accent={accent}
          isExpanded
          onToggle={onToggle}
          isMobile={isMobile}
          alt={day.title}
          fallback={
            <Box style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Text size="xl" fw={700} c="white" style={{ opacity: 0.7 }}>{day.dayNumber}</Text>
            </Box>
          }
          unavailableLabel={`Day ${day.dayNumber}: ${day.title}`}
        />
      )}

      {/* Day header */}
      <Box style={{ padding: '14px 16px 12px', borderBottom: `1px solid ${C_DIVIDER}` }}>
        <Box style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <Box style={{ flex: 1, minWidth: 0, fontSize: 16, fontWeight: 700, color: C_NAVY, lineHeight: 1.3 }}>
            {day.title}
          </Box>
          {(onSkipDay || onUnskipDay) && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); (isSkipped ? onUnskipDay : onSkipDay)?.(); }}
              aria-label={isSkipped ? 'Restore day' : 'Skip this day'}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 5,
                padding: '5px 10px', borderRadius: 9999,
                background: 'transparent', border: '1px solid transparent',
                color: C_LABEL, fontSize: 12, fontWeight: 500,
                cursor: 'pointer', flexShrink: 0,
                transition: 'background 120ms, border-color 120ms, color 120ms',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = C_BTN_HOVER; e.currentTarget.style.borderColor = C_DIVIDER; e.currentTarget.style.color = C_NAVY; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent'; e.currentTarget.style.color = C_LABEL; }}
            >
              {isSkipped ? <UndoIcon /> : <CalendarXIcon />}
              {isSkipped ? 'Restore' : 'Skip day'}
            </button>
          )}
        </Box>
        <Box style={{ fontSize: 13, color: C_NAVY_MID, lineHeight: 1.45, marginBottom: 10 }}>
          {day.description}
        </Box>
        <Box style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
          <Chip>{day.stopCount} stops</Chip>
        </Box>
      </Box>

      {/* Timeline */}
      {day.stops && day.stops.length > 0 && (
        <Box style={{ position: 'relative', padding: '12px 16px 6px' }}>
          {/* Vertical line */}
          <Box style={{ position: 'absolute', left: 25, top: 24, bottom: 18, width: 1.5, background: C_DIVIDER }} />

          {day.stops.map((entry, idx) => (
            <Box key={entry.stop.id}>
              <TimelineRow
                item={{
                  title: entry.stop.name,
                  description: entry.stop.description,
                  imageUrl: entry.stop.imageUrl,
                  timeLabel: [entry.stop.startTime, entry.stop.endTime].filter(Boolean).join(' – ') || undefined,
                  duration: entry.stop.duration,
                  cost: entry.stop.cost,
                  rating: entry.stop.rating,
                  reviewCount: entry.stop.reviewCount,
                }}
                gradient={gradient}
                accent={accent}
                isSelected={selectedStopId === entry.stop.id}
                onClick={() => onStopSelect?.(selectedStopId === entry.stop.id ? null : entry.stop.id)}
              />
              {entry.connector && entry.connector.length > 0 && idx < (day.stops?.length ?? 0) - 1 && (
                <StopConnector options={entry.connector} />
              )}
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
