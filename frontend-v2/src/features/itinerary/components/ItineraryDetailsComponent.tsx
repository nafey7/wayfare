import { Box, Group, Stack, Text, Title } from '@mantine/core';
import {
  ExternalLink,
  Bus,
  Car,
  Footprints,
  Plane,
  Lightbulb,
  UtensilsCrossed,
  Wallet,
} from 'lucide-react';
import React, { useState, useRef, useEffect } from 'react';
import { AuthenticatedImage } from './AuthenticatedImage';
import { InlineFlightCard } from './InlineFlightCard';
import { InlineHotelCard } from './InlineHotelCard';
import { Chip, PhotoBlock, TimelineRow, computeDayColors, dayCardContainerStyle } from './dayCardPrimitives';
import { ItineraryStopDetail } from './ItineraryStopDetail';
import { usePlacesImage } from '../hooks/usePlacesImage';
import type { ChatHotelInfo, FlightInfo } from '@/types/api.helpers';
import {
  C_NAVY, C_BORDER, C_NAVY_MID, C_NAVY_LIGHT, C_LABEL,
  C_PILL_BG, C_PILL_HOVER, C_DIVIDER, C_SHADOW_PILL,
} from '../constants/itineraryColors';

export interface ItineraryItem {
  day: number;
  /** Short date label, e.g. "THU 15 MAY" — mirrors ItineraryDay.date */
  date?: string;
  title: string;
  description: string;
  imageUrl: string;
  iconType?: string;
  /** Rich timeline content when expanded (hero, activities, travel bars, tip). API-shaped. */
  expandedContent?: ExpandedDayContent;
}

export interface LocalExperience {
  id: string;
  imageUrl: string;
  imageAlt?: string;
  title: string;
  description: string;
}

export interface BudgetSnapshotProps {
  title: string;
  description: string;
}

/**
 * Kind discriminator for itinerary day entries (#1038).
 *
 * - ``"activity"`` (the default — including when ``kind`` is absent for
 *   back-compat with pre-#1038 saved itineraries) — render a normal
 *   activity card from ``location/description/imageUrl``.
 * - ``"flight"`` — render an inline flight card from ``flight`` payload.
 *   ``leg`` tells the card whether to label as outbound or inbound.
 * - ``"hotel-checkin"`` / ``"hotel-checkout"`` — render inline hotel
 *   check-in / check-out cards from ``hotel`` payload.
 */
export type DayActivityKind =
  | 'activity'
  | 'flight'
  | 'hotel-checkin'
  | 'hotel-checkout';

export interface DayActivityItem {
  /** Optional stable id for list keys; use composite key when absent */
  id?: string;
  /**
   * Activity kind — defaults to ``"activity"`` when absent (back-compat with
   * pre-#1038 saved itineraries that have no kind field on activity entries).
   */
  kind?: DayActivityKind;
  /** Outbound vs inbound — only meaningful when ``kind === "flight"``. */
  leg?: 'outbound' | 'inbound';
  /** Flight payload — only set when ``kind === "flight"``. Shape mirrors a
   * single entry from the chat-response top-level ``flights`` array. */
  flight?: Record<string, unknown>;
  /** Hotel payload — set on both ``hotel-checkin`` and ``hotel-checkout``. */
  hotel?: Record<string, unknown>;
  // Legacy activity fields (LLM-produced day-plan entries). Optional now so
  // flight/hotel entries don't have to fake them.
  location?: string;
  description?: string;
  imageUrl?: string;
  duration?: string;
  rating?: number;
}

export interface DayTravelOption {
  icon: 'bus' | 'taxi' | 'car' | 'walk' | 'plane';
  label: string;
}

export interface TravelBarLatLng {
  lat: number;
  lng: number;
}

export interface TravelBarData {
  options: DayTravelOption[];
  /** Google encoded polyline for this segment (from Directions/Transit API) */
  polyline?: string | null;
  originLatLng?: TravelBarLatLng | null;
  destinationLatLng?: TravelBarLatLng | null;
}

export interface TravelBarRouteInfo {
  polyline?: string | null;
  originLatLng?: TravelBarLatLng | null;
  destinationLatLng?: TravelBarLatLng | null;
}

/** Rich expanded content for a day (hero, timeline, travel bars, tip). */
export interface ExpandedDayContent {
  mainImageUrl?: string;
  activities: DayActivityItem[];
  /** One entry per gap between activities (e.g. after Morning, after Afternoon). */
  travelBars: TravelBarData[];
  tip?: { text: string };
}

export interface ItineraryDetailsComponentProps {
  itineraryItems: ItineraryItem[];
  footerSectionTitle?: string;
  localExperiences?: LocalExperience[];
  budgetSnapshot?: BudgetSnapshotProps | null;
  onTravelBarHover?: (bar: TravelBarRouteInfo | null) => void;
  onTravelBarClick?: (bar: TravelBarRouteInfo) => void;
  selectedTravelBar?: TravelBarRouteInfo | null;
  /** Called whenever the expanded day changes (null = all collapsed). */
  onExpandedDayChange?: (dayId: number | null) => void;
  /** Optional controlled expanded day. When provided, the component reflects this value. */
  expandedDay?: number | null;
  /** Trip destination (e.g. "London") — used to bias local experience image searches. */
  destination?: string;
}

/** lucide-react ships no taxi icon, so we render the Car icon for both. */
const TRAVEL_ICON_MAP = {
  bus: Bus,
  taxi: Car,
  car: Car,
  walk: Footprints,
  plane: Plane,
} as const;

// ─── Connector pill (preserves TravelBar data for map integration) ────────────

function ConnectorPill({
  travelBar, onHover, onClick, isSelected,
}: {
  travelBar: TravelBarData;
  onHover?: (bar: TravelBarRouteInfo | null) => void;
  onClick?: (bar: TravelBarRouteInfo) => void;
  isSelected?: boolean;
}) {
  const [hovered, setHovered] = useState(false);
  const active = hovered || isSelected;
  const mapsUrl =
    travelBar.originLatLng && travelBar.destinationLatLng
      ? `https://www.google.com/maps/dir/?api=1&origin=${travelBar.originLatLng.lat},${travelBar.originLatLng.lng}&destination=${travelBar.destinationLatLng.lat},${travelBar.destinationLatLng.lng}`
      : null;

  return (
    <Box style={{ margin: '8px 0 8px 32px', display: 'flex', alignItems: 'center', gap: 6 }}>
      <button
        type="button"
        aria-label={travelBar.options.length > 1
          ? `Travel options: ${travelBar.options.map((o) => `${o.icon} ${o.label}`).join(', ')}`
          : travelBar.options.length === 1
            ? `Travel: ${travelBar.options[0]?.icon} ${travelBar.options[0]?.label}`
            : 'Travel segment'}
        onMouseEnter={() => { setHovered(true); onHover?.({ polyline: travelBar.polyline ?? null, originLatLng: travelBar.originLatLng, destinationLatLng: travelBar.destinationLatLng }); }}
        onMouseLeave={() => { setHovered(false); onHover?.(null); }}
        onClick={() => { if (onClick && (travelBar.polyline || travelBar.originLatLng || travelBar.destinationLatLng)) onClick({ polyline: travelBar.polyline, originLatLng: travelBar.originLatLng, destinationLatLng: travelBar.destinationLatLng }); }}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 7,
          padding: '6px 12px', borderRadius: 9999,
          background: active ? C_PILL_HOVER : C_PILL_BG,
          border: `1px solid ${active ? C_NAVY : C_BORDER}`,
          color: C_NAVY, fontSize: 12.5, fontWeight: 600, lineHeight: 1.3,
          width: 'fit-content', userSelect: 'none',
          cursor: (onClick && (travelBar.polyline || travelBar.originLatLng || travelBar.destinationLatLng)) ? 'pointer' : 'default',
          boxShadow: active ? `0 1px 6px ${C_SHADOW_PILL}` : 'none',
          transition: 'background .12s, border-color .12s, box-shadow .12s',
        }}
      >
        {travelBar.options.map((opt, i) => {
          const Icon = TRAVEL_ICON_MAP[opt.icon];
          return (
            <Box key={i} component="span" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              {i > 0 && <Box component="span" style={{ color: C_NAVY_LIGHT, margin: '0 2px' }}>·</Box>}
              <Icon size={13} color={active ? C_NAVY : C_LABEL} />
              <span>{opt.label}</span>
            </Box>
          );
        })}
      </button>
      {mapsUrl && (
        <a
          href={mapsUrl} target="_blank" rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          aria-label="Open route in Google Maps"
          style={{ display: 'inline-flex', alignItems: 'center', color: C_NAVY_MID, textDecoration: 'none', flexShrink: 0 }}
        >
          <ExternalLink size={12} />
        </a>
      )}
    </Box>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isSameBar(a: TravelBarRouteInfo | null | undefined, b: TravelBarData | undefined): boolean {
  if (!a || !b) return false;
  if (a.polyline && b.polyline) return a.polyline === b.polyline;
  return (
    a.originLatLng?.lat === b.originLatLng?.lat &&
    a.originLatLng?.lng === b.originLatLng?.lng &&
    a.destinationLatLng?.lat === b.destinationLatLng?.lat &&
    a.destinationLatLng?.lng === b.destinationLatLng?.lng
  );
}

// ─── Expanded day view (timeline layout matching Ross) ────────────────────────

function ExpandedDayView({
  richContent, day, gradient, accent, onTravelBarHover, onTravelBarClick, selectedTravelBar, onActivityClick,
}: {
  richContent: ExpandedDayContent;
  day: number;
  gradient: string;
  accent: string;
  onTravelBarHover?: (bar: TravelBarRouteInfo | null) => void;
  onTravelBarClick?: (bar: TravelBarRouteInfo) => void;
  selectedTravelBar?: TravelBarRouteInfo | null;
  onActivityClick?: (idx: number) => void;
}) {
  return (
    <Box>
      {/* Timeline */}
      {richContent.activities.length > 0 && (
        <Box style={{ position: 'relative', padding: '4px 16px 8px' }}>
          {/* Vertical line */}
          <Box style={{ position: 'absolute', left: 25, top: 22, bottom: 18, width: 1.5, background: C_DIVIDER }} />

          {richContent.activities.map((activity, idx) => {
            const rawBar = richContent.travelBars[idx];
            const travelBar: TravelBarData | undefined = Array.isArray(rawBar) ? { options: rawBar } : rawBar;
            const hasConnector = travelBar && travelBar.options.length > 0 && idx < richContent.activities.length - 1;

            // #1038: stitched flight + hotel entries render with dedicated
            // inline cards. Missing kind defaults to "activity" (back-compat
            // with pre-#1038 saved itineraries).
            const kind = activity.kind ?? 'activity';

            return (
              <Box key={activity.id ?? `day-${day}-activity-${idx}`}>
                {kind === 'flight' && activity.flight && (
                  <InlineFlightCard
                    flight={activity.flight as unknown as FlightInfo}
                    leg={activity.leg}
                  />
                )}
                {kind === 'hotel-checkin' && activity.hotel && (
                  <InlineHotelCard
                    hotel={activity.hotel as unknown as ChatHotelInfo}
                    phase="check-in"
                  />
                )}
                {kind === 'hotel-checkout' && activity.hotel && (
                  <InlineHotelCard
                    hotel={activity.hotel as unknown as ChatHotelInfo}
                    phase="check-out"
                  />
                )}
                {kind === 'activity' && (
                  <TimelineRow
                    item={{
                      title: activity.location ?? '',
                      description: activity.description ?? '',
                      imageUrl: activity.imageUrl,
                      duration: activity.duration,
                      rating: activity.rating ?? undefined,
                    }}
                    gradient={gradient}
                    accent={accent}
                    isSelected={false}
                    onClick={onActivityClick ? () => onActivityClick(idx) : undefined}
                  />
                )}
                {hasConnector && travelBar && (
                  <ConnectorPill
                    travelBar={travelBar}
                    onHover={onTravelBarHover}
                    onClick={onTravelBarClick}
                    isSelected={isSameBar(selectedTravelBar, travelBar)}
                  />
                )}
              </Box>
            );
          })}
        </Box>
      )}

      {/* Tip */}
      {richContent.tip?.text && (
        <Box
          style={{
            margin: '4px 16px 16px',
            display: 'flex', gap: 8, alignItems: 'flex-start',
            padding: 12, borderRadius: 12,
            backgroundColor: 'var(--mantine-color-yellow-1)',
            border: '1px solid var(--mantine-color-yellow-3)',
          }}
        >
          <Lightbulb size={18} color="var(--mantine-color-yellow-7)" style={{ flexShrink: 0, marginTop: 2 }} />
          <Text size="sm" c="dimmed" fs="italic">{richContent.tip.text}</Text>
        </Box>
      )}
    </Box>
  );
}

// ─── Day card ─────────────────────────────────────────────────────────────────

function DayCard({
  item, isExpanded, onToggle, cardRef, onTravelBarHover, onTravelBarClick, selectedTravelBar,
}: {
  item: ItineraryItem;
  isExpanded: boolean;
  onToggle: () => void;
  cardRef: (el: HTMLElement | null) => void;
  onTravelBarHover?: (bar: TravelBarRouteInfo | null) => void;
  onTravelBarClick?: (bar: TravelBarRouteInfo) => void;
  selectedTravelBar?: TravelBarRouteInfo | null;
}) {
  const [isHovered, setIsHovered] = useState(false);
  const [selectedActivityIdx, setSelectedActivityIdx] = useState<number | null>(null);
  const { gradient, accent } = computeDayColors(item.day);
  const richContent = item.expandedContent;
  const stopCount = richContent?.activities?.length ?? 0;

  useEffect(() => {
    if (!isExpanded) setSelectedActivityIdx(null);
  }, [isExpanded]);

  useEffect(() => {
    if (selectedActivityIdx !== null && selectedActivityIdx >= stopCount) setSelectedActivityIdx(null);
  }, [stopCount, selectedActivityIdx]);

  const selectedActivity = selectedActivityIdx !== null ? richContent?.activities[selectedActivityIdx] ?? null : null;

  return (
    <Box
      ref={cardRef}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={!isExpanded ? onToggle : undefined}
      style={{ ...dayCardContainerStyle(isExpanded, isHovered), cursor: isExpanded ? 'default' : 'pointer' }}
    >
      <PhotoBlock
        height={120}
        imageUrl={item.imageUrl}
        gradient={gradient}
        dayChipText={`Day ${item.day}${item.date ? ` · ${item.date}` : ''}`}
        accent={accent}
        isExpanded={isExpanded}
        onToggle={onToggle}
        alt={item.title}
        fallback={
          <Box style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Text size="xl" fw={700} c="white" style={{ opacity: 0.7 }}>{item.day}</Text>
          </Box>
        }
        unavailableLabel={`Day ${item.day}: ${item.title}`}
      />

      {/* Card header — acts as collapsed body OR expanded header */}
      <Box
        style={{
          padding: isExpanded ? '14px 16px 12px' : '10px 14px 12px',
          borderBottom: isExpanded ? `1px solid ${C_DIVIDER}` : 'none',
          display: 'flex', flexDirection: 'column', gap: 4,
        }}
      >
        <Box
          style={{
            fontSize: isExpanded ? 16 : 15,
            fontWeight: isExpanded ? 700 : 600,
            color: C_NAVY, lineHeight: 1.3,
            overflow: 'hidden', textOverflow: 'ellipsis',
            whiteSpace: isExpanded ? 'normal' : 'nowrap',
          }}
        >
          {item.title}
        </Box>
        <Box
          style={{
            fontSize: 13, color: C_NAVY_MID,
            lineHeight: isExpanded ? 1.45 : 1.3,
            marginBottom: isExpanded ? 6 : 0,
            overflow: 'hidden', textOverflow: isExpanded ? 'clip' : 'ellipsis',
            whiteSpace: isExpanded ? 'normal' : 'nowrap',
          }}
        >
          {item.description}
        </Box>
        {stopCount > 0 && (
          <Box style={{ display: 'flex', gap: 5 }}>
            <Chip>{stopCount} stop{stopCount === 1 ? '' : 's'}</Chip>
          </Box>
        )}
      </Box>

      {/* Expanded content area — swaps between stop detail and timeline */}
      {isExpanded && selectedActivity ? (
        <ItineraryStopDetail
          stop={{
            id: selectedActivity.id ?? `d${item.day}-s${selectedActivity.location ?? selectedActivityIdx}`,
            name: selectedActivity.location ?? '',
            description: selectedActivity.description ?? '',
            duration: selectedActivity.duration ?? '',
            rating: selectedActivity.rating,
            imageUrl: selectedActivity.imageUrl,
          }}
          dayNumber={item.day}
          dayDate={item.date ?? ''}
          onClose={() => setSelectedActivityIdx(null)}
        />
      ) : isExpanded && richContent ? (
        <ExpandedDayView
          richContent={richContent}
          day={item.day}
          gradient={gradient}
          accent={accent}
          onTravelBarHover={onTravelBarHover}
          onTravelBarClick={onTravelBarClick}
          selectedTravelBar={selectedTravelBar}
          onActivityClick={(idx) => setSelectedActivityIdx(idx)}
        />
      ) : isExpanded && !richContent ? (
        <Box style={{ padding: '14px 16px 16px' }}>
          <Text size="sm" c="dimmed">{item.description}</Text>
        </Box>
      ) : null}
    </Box>
  );
}

// ─── Local experience card ─────────────────────────────────────────────────────

function LocalExperienceCard({ exp, destination }: { exp: LocalExperience; destination?: string }) {
  const place = destination ? `${exp.title} ${destination}` : exp.title;
  const { ref, objectUrl } = usePlacesImage({
    place,
    disabled: !!exp.imageUrl,
  });

  return (
    <Box
      style={{
        minWidth: 280, maxWidth: 280, flexShrink: 0,
        borderRadius: 16, overflow: 'hidden',
        background: 'white', border: `1px solid ${C_DIVIDER}`,
        display: 'flex', flexDirection: 'column',
      }}
    >
      <Box
        ref={ref as React.RefObject<HTMLDivElement>}
        style={{ width: '100%', height: 140, overflow: 'hidden', backgroundColor: 'var(--mantine-color-gray-1)' }}
      >
        {exp.imageUrl && (
          <AuthenticatedImage
            src={exp.imageUrl}
            alt={exp.imageAlt ?? exp.title}
            sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
            unavailableLabel={exp.title}
            fallback={
              <Box style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--mantine-color-gray-2)' }}>
                <UtensilsCrossed size={40} color="var(--mantine-color-dimmed)" />
              </Box>
            }
          />
        )}
        {!exp.imageUrl && objectUrl && (
          <img
            src={objectUrl}
            alt={exp.imageAlt ?? exp.title}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        )}
        {!exp.imageUrl && !objectUrl && (
          <Box style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--mantine-color-gray-2)' }}>
            <UtensilsCrossed size={40} color="var(--mantine-color-dimmed)" />
          </Box>
        )}
      </Box>
      <Stack p="md" gap={4}>
        <Text fw={700} size="md" c="dark.8">{exp.title}</Text>
        <Text size="sm" c="dimmed">{exp.description}</Text>
      </Stack>
    </Box>
  );
}

// ─── Main component ────────────────────────────────────────────────────────────

export function ItineraryDetailsComponent({
  itineraryItems,
  footerSectionTitle = 'Must-Try Local Experiences',
  localExperiences = [],
  budgetSnapshot,
  onTravelBarHover,
  onTravelBarClick,
  selectedTravelBar,
  onExpandedDayChange,
  expandedDay: controlledExpandedDay,
  destination,
}: ItineraryDetailsComponentProps) {
  const [internalExpandedDay, setInternalExpandedDay] = useState<number | null>(null);
  const isControlled = controlledExpandedDay !== undefined;
  const expandedDay = isControlled ? controlledExpandedDay : internalExpandedDay;
  const cardRefs = useRef<Record<number, HTMLElement | null>>({});

  const toggleDay = (day: number) => {
    const next = expandedDay === day ? null : day;
    if (!isControlled) setInternalExpandedDay(next);
    onExpandedDayChange?.(next);
  };

  useEffect(() => {
    if (expandedDay !== null) {
      const el = cardRefs.current[expandedDay];
      if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' });
    }
  }, [expandedDay]);

  return (
    <Box style={{ height: '100%', minHeight: 0, overflow: 'auto', borderRadius: 8 }}>
      <Stack gap={12} p="lg">
        {itineraryItems.map((item) => (
          <DayCard
            key={item.day}
            item={item}
            isExpanded={expandedDay === item.day}
            onToggle={() => toggleDay(item.day)}
            cardRef={(el) => { cardRefs.current[item.day] = el; }}
            onTravelBarHover={onTravelBarHover}
            onTravelBarClick={onTravelBarClick}
            selectedTravelBar={selectedTravelBar}
          />
        ))}

        {(footerSectionTitle || localExperiences.length > 0) && (
          <Stack gap="md" mt="xl">
            <Group align="center" gap="xs">
              <UtensilsCrossed size={24} color="var(--mantine-color-dark-8)" />
              <Title order={3} fw={700} c="dark.8">{footerSectionTitle}</Title>
            </Group>
            {localExperiences.length > 0 && (
              <Group gap="md" wrap="nowrap" style={{ overflowX: 'auto', paddingTop: 4, paddingBottom: 4 }}>
                {localExperiences.map((exp) => (
                  <LocalExperienceCard key={exp.id} exp={exp} destination={destination} />
                ))}
              </Group>
            )}
          </Stack>
        )}

        {budgetSnapshot && (
          <Box style={{ backgroundColor: 'var(--mantine-color-gray-0)', borderRadius: 12, padding: 24, marginTop: 16 }}>
            <Group align="flex-start" gap="md" wrap="nowrap">
              <Box
                style={{
                  width: 48, height: 48, borderRadius: '50%',
                  backgroundColor: 'var(--mantine-color-gray-2)',
                  border: '1px solid var(--mantine-color-default-border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}
              >
                <Wallet size={24} color="var(--mantine-color-brand-6)" />
              </Box>
              <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
                <Title order={4} fw={700} c="dark.8">{budgetSnapshot.title}</Title>
                <Text size="sm" c="dimmed">{budgetSnapshot.description}</Text>
              </Stack>
            </Group>
          </Box>
        )}
      </Stack>
    </Box>
  );
}
