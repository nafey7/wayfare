/**
 * Inline result cards rendered inside the chat panel when Voya finds results.
 * Four variants: flights, hotels, itinerary, whole-trip summary.
 */
import { Box, Stack, Text, UnstyledButton } from '@mantine/core';
import { ChevronRight, Plane, Building2, Map as MapIcon, Globe } from 'lucide-react';
import { surfaces } from '@/theme/tokens';

// ── Brand tokens ──────────────────────────────────────────────────────────────

const C = {
  navy:    'var(--mantine-color-navy-7)',
  slate:   'var(--mantine-color-navy-5)',
  indigo:  'var(--mantine-color-brand-6)',
  muted:   'var(--mantine-color-navy-5)',
  dim:     'var(--mantine-color-navy-3)',
  border:  surfaces.borderDefault,
  rowDiv:  'var(--mantine-color-gray-1)',
  bg:      'white',
};

// ── Shared primitives ─────────────────────────────────────────────────────────

function CardRoot({ children }: { children: React.ReactNode }) {
  return (
    <Box style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, overflow: 'hidden', width: '100%' }}>
      {children}
    </Box>
  );
}

function CardHeader({ iconBg, iconColor, icon, title, count }: {
  iconBg: string; iconColor: string; icon: React.ReactNode;
  title: string; count?: string;
}) {
  return (
    <Box style={{ padding: '8px 12px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 8 }}>
      <Box style={{ width: 24, height: 24, borderRadius: 6, background: iconBg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: iconColor }}>
        {icon}
      </Box>
      <Text size="xs" fw={700} c="navy.9" style={{ flex: 1 }}>{title}</Text>
      {count && <Text size="xs" c="dimmed">{count}</Text>}
    </Box>
  );
}

function FilledCta({ label, onClick }: { label: string; onClick?: () => void }) {
  return (
    <Box style={{ padding: '8px 12px', borderTop: `1px solid ${C.border}` }}>
      <UnstyledButton
        onClick={onClick}
        style={{ display: 'block', width: '100%', padding: '8px', background: C.navy, color: 'white', borderRadius: 8, fontSize: 12, fontWeight: 600, textAlign: 'center', cursor: 'pointer' }}
      >
        {label}
      </UnstyledButton>
    </Box>
  );
}

function TextCta({ label, onClick }: { label: string; onClick?: () => void }) {
  return (
    <Box style={{ padding: '8px 12px', borderTop: `1px solid ${C.border}` }}>
      <UnstyledButton
        onClick={onClick}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, width: '100%', fontSize: 12, fontWeight: 600, color: C.slate, cursor: 'pointer' }}
      >
        {label}
        <ChevronRight size={13} />
      </UnstyledButton>
    </Box>
  );
}

// ── Tag colours ───────────────────────────────────────────────────────────────

const TAG_STYLES: Record<string, { bg: string; color: string }> = {
  Best:     { bg: '#EDEEF5', color: C.slate },
  Cheapest: { bg: '#EEF5F0', color: '#2a9d8f' },
  Fastest:  { bg: '#F4F0FF', color: '#7b4f8e' },
};

// ── Day dot colours ───────────────────────────────────────────────────────────

const DAY_COLORS = ['#4d5a8a', '#2a9d8f', '#a0681e', '#7b4f8e', '#636e9d'];

// ─────────────────────────────────────────────────────────────────────────────
//  1. FlightResultCard
// ─────────────────────────────────────────────────────────────────────────────

export interface FlightPick {
  label: string;
  airline: string;
  departure: string;
  arrival: string;
  duration: string;
  stops: string;
  price: string;
  tag: string;
}

export interface FlightResultCardProps {
  route: string;
  totalCount: number;
  picks: FlightPick[];
  onViewAll?: () => void;
  onPickSelect?: (index: number) => void;
}

export function FlightResultCard({ route, totalCount, picks, onViewAll, onPickSelect }: FlightResultCardProps) {
  return (
    <CardRoot>
      <CardHeader
        iconBg="#EEF0FF" iconColor={C.slate}
        icon={<Plane size={13} />}
        title={`Flights · ${route}`}
        count={`${totalCount} found`}
      />

      {picks.map((pick, i) => {
        const tag = TAG_STYLES[pick.tag] ?? TAG_STYLES['Best']!;
        return (
          <UnstyledButton
            key={pick.tag}
            onClick={() => onPickSelect?.(i)}
            style={{
              display: 'flex', alignItems: 'center', width: '100%',
              padding: '9px 12px', gap: 8,
              borderBottom: i < picks.length - 1 ? `1px solid ${C.rowDiv}` : 'none',
              cursor: 'pointer',
            }}
          >
            <Box style={{ flex: 1, minWidth: 0 }}>
              <Text size="xs" fw={700} c="dimmed" style={{ textTransform: 'uppercase', letterSpacing: '0.04em', fontSize: 10 }}>
                {pick.label}
              </Text>
              <Text size="sm" fw={600} c="navy.9" style={{ lineHeight: 1.2, marginTop: 1 }}>{pick.airline}</Text>
              <Text size="xs" c="dimmed">{pick.departure}–{pick.arrival} · {pick.stops} · {pick.duration}</Text>
            </Box>
            <Stack gap={3} align="flex-end" style={{ flexShrink: 0 }}>
              <Text size="sm" fw={700} c="navy.9">{pick.price}</Text>
              <Box style={{ background: tag.bg, color: tag.color, borderRadius: 4, padding: '2px 6px', fontSize: 10, fontWeight: 600 }}>
                {pick.tag}
              </Box>
            </Stack>
            <ChevronRight size={14} color={C.border} />
          </UnstyledButton>
        );
      })}

      <FilledCta label={`View all ${totalCount} flights →`} onClick={onViewAll} />
    </CardRoot>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  2. HotelResultCard
// ─────────────────────────────────────────────────────────────────────────────

export interface HotelPick {
  name: string;
  stars: number;
  area: string;
  rating: number;
  price: string;
  priceUnit?: string;
  imageUrl?: string;
  badge?: string;
}

export interface HotelResultCardProps {
  destination: string;
  totalCount: number;
  fromPrice: string;
  picks: HotelPick[];
  onViewAll?: () => void;
  onPickSelect?: (index: number) => void;
}

export function HotelResultCard({ destination, totalCount, fromPrice, picks, onViewAll, onPickSelect }: HotelResultCardProps) {
  return (
    <CardRoot>
      <CardHeader
        iconBg="#EEF5F0" iconColor="#2a9d8f"
        icon={<Building2 size={13} />}
        title={`${totalCount} hotels · from ${fromPrice}/night`}
      />

      {picks.map((pick, i) => (
        <UnstyledButton
          key={pick.name}
          onClick={() => onPickSelect?.(i)}
          style={{
            display: 'flex', alignItems: 'center', width: '100%',
            padding: '9px 12px', gap: 10,
            borderBottom: i < picks.length - 1 ? `1px solid ${C.rowDiv}` : 'none',
            cursor: 'pointer',
          }}
        >
          {/* Thumbnail */}
          <Box
            style={{
              width: 44, height: 44, borderRadius: 8, flexShrink: 0, overflow: 'hidden',
              background: `linear-gradient(135deg, ${DAY_COLORS[i % DAY_COLORS.length]}88, ${DAY_COLORS[i % DAY_COLORS.length]})`,
            }}
          >
            {pick.imageUrl && (
              <img src={pick.imageUrl} alt={pick.name} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
            )}
          </Box>

          {/* Details */}
          <Box style={{ flex: 1, minWidth: 0 }}>
            <Text size="sm" fw={600} c="navy.9" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {pick.name}
            </Text>
            <Text size="xs" c="dimmed">{'★'.repeat(pick.stars)} · {pick.area} · {pick.rating}</Text>
          </Box>

          {/* Price + badge */}
          <Stack gap={3} align="flex-end" style={{ flexShrink: 0 }}>
            <Text size="sm" fw={700} c="navy.9">{pick.price}</Text>
            {pick.badge && (
              <Box style={{ background: '#EDEEF5', color: C.slate, borderRadius: 4, padding: '2px 6px', fontSize: 10, fontWeight: 600 }}>
                {pick.badge}
              </Box>
            )}
          </Stack>
        </UnstyledButton>
      ))}

      <TextCta label={`View all ${destination} hotels`} onClick={onViewAll} />
    </CardRoot>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  3. ItineraryResultCard
// ─────────────────────────────────────────────────────────────────────────────

export interface ItineraryDay {
  dayNumber: number;
  date: string;
  title: string;
  stopCount: number;
}

export interface ItineraryResultCardProps {
  destination: string;
  dateRange: string;
  days: ItineraryDay[];
  onViewAll?: () => void;
  onDaySelect?: (dayNumber: number) => void;
}

export function ItineraryResultCard({ destination, dateRange, days, onViewAll, onDaySelect }: ItineraryResultCardProps) {
  return (
    <CardRoot>
      <CardHeader
        iconBg="#F4F0FF" iconColor="#7b4f8e"
        icon={<MapIcon size={13} />}
        title={`${days.length}-day ${destination} · ${dateRange}`}
      />

      {days.map((day, i) => (
        <UnstyledButton
          key={day.dayNumber}
          onClick={() => onDaySelect?.(day.dayNumber)}
          style={{
            display: 'flex', alignItems: 'center', width: '100%',
            padding: '9px 12px', gap: 10,
            borderBottom: i < days.length - 1 ? `1px solid ${C.rowDiv}` : 'none',
            cursor: 'pointer',
          }}
        >
          <Box style={{ width: 8, height: 8, borderRadius: '50%', background: DAY_COLORS[i % DAY_COLORS.length], flexShrink: 0 }} />
          <Box style={{ flex: 1, minWidth: 0 }}>
            <Text size="sm" c="navy.9" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {day.title}
            </Text>
            <Text size="xs" c="dimmed">{day.date} · {day.stopCount} stops</Text>
          </Box>
          <ChevronRight size={14} color={C.border} />
        </UnstyledButton>
      ))}

      <TextCta label="View full itinerary" onClick={onViewAll} />
    </CardRoot>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  4. TripResultCard
// ─────────────────────────────────────────────────────────────────────────────

export interface TripSection {
  emoji: string;
  title: string;
  sub: string;
  price?: string;
}

export interface TripResultCardProps {
  tripSummary: string;
  sections: TripSection[];
  totalEstimate?: string;
  onViewTrip?: () => void;
}

export function TripResultCard({ tripSummary, sections, totalEstimate, onViewTrip }: TripResultCardProps) {
  return (
    <CardRoot>
      <CardHeader
        iconBg="#EEF0FF" iconColor={C.slate}
        icon={<Globe size={13} />}
        title={tripSummary}
      />

      {sections.map((s) => (
        <Box
          key={s.title}
          style={{
            display: 'flex', alignItems: 'center', padding: '9px 12px', gap: 10,
            borderBottom: `1px solid ${C.rowDiv}`,
          }}
        >
          <Box style={{ width: 28, height: 28, borderRadius: 7, background: '#F4F5FF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, flexShrink: 0 }}>
            {s.emoji}
          </Box>
          <Box style={{ flex: 1, minWidth: 0 }}>
            <Text size="sm" fw={600} c="navy.9">{s.title}</Text>
            <Text size="xs" c="dimmed">{s.sub}</Text>
          </Box>
          {s.price && <Text size="sm" fw={700} c="navy.9" style={{ flexShrink: 0 }}>{s.price}</Text>}
        </Box>
      ))}

      {totalEstimate && (
        <Box style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', background: '#F8F9FF', borderBottom: `1px solid ${C.border}` }}>
          <Text size="xs" fw={600} c="dimmed">Total estimate</Text>
          <Text size="sm" fw={700} c="navy.9">{totalEstimate}</Text>
        </Box>
      )}

      <FilledCta label="View full trip →" onClick={onViewTrip} />
    </CardRoot>
  );
}
