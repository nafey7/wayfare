import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import { Alert, Box, Group, Loader, Stack, UnstyledButton } from '@mantine/core';
import { CONTENT_SPLIT } from '@/components/layout/layoutConstants';
import { useMediaQuery } from '@mantine/hooks';
import { motion, useMotionValue, animate, useDragControls } from 'framer-motion';
import type { PanInfo } from 'framer-motion';
import { ItineraryPlannerForm } from '../components/ItineraryPlannerForm';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  setActiveSavedItineraryIdForBooking,
  selectLastItineraryState,
} from '@/store/slices/uiSlice';
import { syncItineraryToSearchParams } from '@/store/thunks/syncItineraryToSearchParams';
import type { TripType } from '@/types/flights';
import {
  ItineraryDetailsComponent,
  LinkedBookingChips,
  ItineraryDayCard,
  ItineraryStopDetail,
  MultiDayRouteMap,
  type ConnectorDescriptor,
  type ItineraryDetailsComponentProps,
  type TravelBarRouteInfo,
  type ItineraryDay,
  type ItineraryStop,
  type RouteDay,
  type RouteStop,
} from '../components';
import { getItineraryMapCenterFromTripMeta } from '../utils/destinationLocation';
import { parseItineraryNavigationState } from '../utils/navigationState';
import { computeItineraryDayLabel } from '../utils/itineraryDayDates';
import { DAY_ACCENTS } from '../constants/dayColors';
import {
  C_BORDER, C_NAVY_MID, C_NAVY_BLUE,
  C_DRAG_PILL, C_SHADOW_SHEET, C_SHADOW_MAP_BTN,
} from '../constants/itineraryColors';
import { useGetItineraryQuery } from '@/api/itinerariesApi';
import { isPublicChatRoute, ROUTES } from '@/features/routing';

// ─── Mobile sheet primitives ──────────────────────────────────────────────────

// ChatSheet (44px resting) sits position:absolute in LayoutWithChat and overlaps the bottom
// 28px of mobileContainerRef (44px - 16px ContentPanel paddingBottom). Keep PEEK_H large
// enough that the full drag handle (~60px) clears that overlap with some buffer.
const PEEK_H = 100;
const HALF_H = 300;
const SNAP_SPRING = { type: 'spring', stiffness: 400, damping: 40 } as const;

function MapIcon() {
  return (
    <svg viewBox="0 0 24 24" width={15} height={15} fill="none" stroke="white" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18V6l6 4v12z"/><path d="M3 6v12l6-2"/><path d="M15 10l6-2v12l-6 2"/>
    </svg>
  );
}

type SheetState = 'peek' | 'half' | 'full';

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Read departure_date from tripMeta regardless of key casing.
 * Nav-state tripMeta uses snake_case; saved-itinerary API response is camelCased via toCamelCase.
 */
function getTripDepartureDate(meta: unknown): string | undefined {
  if (!meta || typeof meta !== 'object') return undefined;
  const m = meta as Record<string, unknown>;
  const val = m['departure_date'] ?? m['departureDate'];
  return typeof val === 'string' ? val : undefined;
}

/** Check if structured itinerary has valid itineraryItems. */
function hasValidItineraryItems(structured: Record<string, unknown> | undefined): boolean {
  if (!structured || typeof structured !== 'object') return false;
  const items = structured.itineraryItems as unknown[] | undefined;
  return Array.isArray(items) && items.length > 0;
}

/**
 * Extract RouteDay[] for MultiDayRouteMap from the structured itinerary.
 * Coordinates are derived from travelBars: bar[i].originLatLng = activity i,
 * bar[i].destinationLatLng = activity i+1.
 */
function extractRouteDays(structured: Record<string, unknown> | undefined): RouteDay[] {
  if (!structured) return [];

  const items = structured.itineraryItems as Array<{
    day: number;
    title: string;
    expandedContent?: {
      activities?: Array<{ location: string }>;
      travelBars?: Array<{
        originLatLng?: { lat: number; lng: number } | null;
        destinationLatLng?: { lat: number; lng: number } | null;
      }>;
    };
  }> | undefined;

  if (!Array.isArray(items)) return [];

  return items
    .map((item, idx) => {
      const color = DAY_ACCENTS[idx % DAY_ACCENTS.length] ?? DAY_ACCENTS[0]!;
      const activities = item.expandedContent?.activities ?? [];
      const travelBars = item.expandedContent?.travelBars ?? [];

      const stops: RouteStop[] = activities.flatMap((act, i) => {
        const coord =
          i === 0
            ? travelBars[0]?.originLatLng
            : travelBars[i - 1]?.destinationLatLng;
        if (!coord) return [];
        return [{ lat: coord.lat, lng: coord.lng, name: act.location }];
      });

      return { id: item.day, label: item.title, color, stops };
    })
    .filter((d) => d.stops.length > 0);
}

function travelBarIconToMode(icon: string): ConnectorDescriptor['mode'] {
  if (icon === 'walk') return 'walk';
  if (icon === 'bus') return 'bus';
  return 'transit';
}

/** Convert itineraryItems from the backend response to ItineraryDay[] for the mobile view. */
function toMobileItineraryDays(
  structured: Record<string, unknown> | undefined,
  departureDate?: string,
): ItineraryDay[] {
  if (!structured) return [];
  const items = structured.itineraryItems as Array<{
    day: number;
    title: string;
    description: string;
    imageUrl: string;
    expandedContent?: {
      activities?: Array<{ id?: string; location: string; description: string; imageUrl?: string; duration?: string; rating?: number }>;
      travelBars?: Array<{
        options?: Array<{ icon: string; label: string }>;
        originLatLng?: { lat: number; lng: number } | null;
        destinationLatLng?: { lat: number; lng: number } | null;
      }>;
    };
  }> | undefined;
  if (!Array.isArray(items)) return [];

  return items.map((item) => ({
    dayNumber: item.day,
    date: computeItineraryDayLabel(departureDate, item.day),
    title: item.title,
    description: item.description,
    imageUrl: item.imageUrl,
    stopCount: item.expandedContent?.activities?.length ?? 0,
    stops: item.expandedContent?.activities?.map((act, i) => {
      const travelBars = item.expandedContent?.travelBars ?? [];
      const coord = i === 0 ? travelBars[0]?.originLatLng : travelBars[i - 1]?.destinationLatLng;
      const barOptions = travelBars[i]?.options ?? [];
      const connector: ConnectorDescriptor[] = barOptions.map((opt) => ({
        mode: travelBarIconToMode(opt.icon),
        label: opt.label,
      }));
      return {
        stop: {
          id: act.id ?? `d${item.day}-s${i}`,
          name: act.location,
          description: act.description,
          duration: act.duration ?? '',
          rating: act.rating,
          imageUrl: act.imageUrl,
          lat: coord?.lat,
          lng: coord?.lng,
        } satisfies ItineraryStop,
        connector: connector.length > 0 ? connector : undefined,
      };
    }) ?? [],
  }));
}

// ─── Day navigation header (when a day is tapped) ────────────────────────────

function DayHeader({
  dayLabel,
  title,
  date,
  onBack,
}: {
  dayLabel: string;
  title: string;
  date: string;
  onBack: () => void;
}) {
  return (
    <Box style={{ padding: '8px 14px 10px', borderBottom: `1px solid ${C_BORDER}`, flexShrink: 0 }}>
      <UnstyledButton
        onClick={onBack}
        style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 13, color: C_NAVY_MID, fontWeight: 600, marginBottom: 4 }}
      >
        <svg viewBox="0 0 24 24" width={14} height={14} fill="none" stroke={C_NAVY_MID} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="m15 18-6-6 6-6"/>
        </svg>
        {dayLabel}
      </UnstyledButton>
      <div style={{ fontSize: 15, fontWeight: 700, color: C_NAVY_BLUE, lineHeight: 1.3 }}>{title}</div>
      {date && <div style={{ fontSize: 12, color: C_NAVY_MID, marginTop: 2 }}>{date}</div>}
    </Box>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

/**
 * Itinerary page.
 * - Desktop (md+): two-column layout (details | MultiDayRouteMap).
 * - Mobile (<md): MultiDayRouteMap background + draggable bottom sheet.
 */
export function ItineraryPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const lastItineraryFromStore = useAppSelector(selectLastItineraryState);

  const reduxState = parseItineraryNavigationState(lastItineraryFromStore);
  const reduxMatchesRoute = !id || reduxState?.savedItineraryId === id;
  const navState =
    (reduxMatchesRoute ? reduxState : undefined) ??
    parseItineraryNavigationState(location.state);

  const { data: savedItinerary, isLoading, error } = useGetItineraryQuery(id ?? '', {
    skip: !id,
  });

  useEffect(() => {
    if (!id || isLoading || error || !savedItinerary?.id) return;
    dispatch(setActiveSavedItineraryIdForBooking(id));
  }, [id, isLoading, error, savedItinerary?.id, dispatch]);

  const structuredItinerary =
    navState?.structuredItinerary ?? savedItinerary?.structuredItinerary;
  const tripMeta = navState?.tripMeta ?? savedItinerary?.tripMeta;
  const hasValidData = hasValidItineraryItems(structuredItinerary);

  // Populate the flight and hotel nav-bar search params from tripMeta whenever
  // an itinerary is viewed, so the unified search bars reflect the trip details.
  // Uses the thunk so existing cabinClass/nationality/childAge in Redux state are
  // preserved — only itinerary-known fields (origin, destination, dates, pax) are
  // overwritten.
  useEffect(() => {
    if (!tripMeta) return;
    const meta = tripMeta as Record<string, unknown>;

    const origin = (meta['origin'] as string | undefined) ?? '';
    const destination = (meta['destination'] as string | undefined) ?? '';
    if (!origin && !destination) return;

    // Handle snake_case (nav-state) and camelCase (API toCamelCase transformer)
    const departureDate =
      ((meta['departure_date'] ?? meta['departureDate']) as string | undefined) ?? null;
    const returnDate =
      ((meta['return_date'] ?? meta['returnDate']) as string | undefined) ?? null;
    const adults = (meta['adults'] as number | undefined) ?? 1;
    const children = (meta['children'] as number | undefined) ?? 0;
    const infants = (meta['infants'] as number | undefined) ?? 0;
    const cabinClass =
      ((meta['cabin_class'] ?? meta['cabinClass']) as string | undefined) ?? undefined;

    // Respect a multi-city trip_type from tripMeta; otherwise fall back to
    // round-trip vs one-way based on whether a return date is set.
    const storedTripType = (meta['trip_type'] ?? meta['tripType']) as string | undefined;
    const tripType: TripType =
      storedTripType === 'multi_city' || storedTripType === 'multi-city'
        ? 'multi-city'
        : returnDate
          ? 'round-trip'
          : 'one-way';

    dispatch(
      syncItineraryToSearchParams({
        origin,
        destination,
        departure_date: departureDate,
        return_date: returnDate,
        adults,
        children,
        infants,
        trip_type:
          tripType === 'round-trip'
            ? 'round_trip'
            : tripType === 'one-way'
              ? 'one_way'
              : tripType === 'multi-city'
                ? 'multi_city'
                : undefined,
        cabin_class: cabinClass,
      }),
    );
  }, [tripMeta, dispatch]);

  const mapCenter = getItineraryMapCenterFromTripMeta(tripMeta ?? undefined);

  // Route days for MultiDayRouteMap — memoised so the map doesn't re-mount on
  // every render of ItineraryPage.
  const routeDays = useMemo(
    () => extractRouteDays(structuredItinerary),
    [structuredItinerary],
  );

  // Stable identity per itinerary. Switching between itineraries (e.g. clicking
  // "View itinerary" on different chat conversations) keeps the same
  // ItineraryPage instance, so we use this key to remount the map and reset
  // view-only local state below. Without it, <Map> retains the first
  // itinerary's `defaultCenter` and stale highlight/focus state.
  const savedItineraryId = navState?.savedItineraryId;
  const itineraryKey = useMemo(() => {
    if (id) return `id:${id}`;
    if (savedItineraryId) return `id:${savedItineraryId}`;
    const firstStop = routeDays[0]?.stops[0];
    if (firstStop) {
      return `coords:${firstStop.lat},${firstStop.lng}:${routeDays.length}`;
    }
    return `center:${mapCenter.centerLatitude},${mapCenter.centerLongitude}`;
  }, [id, savedItineraryId, routeDays, mapCenter.centerLatitude, mapCenter.centerLongitude]);

  // Enrich itineraryItems with computed date labels derived from tripMeta departure date.
  // JS Date arithmetic handles 30/31-day month boundaries and leap years automatically.
  const enrichedStructuredItinerary = useMemo(() => {
    if (!structuredItinerary) return structuredItinerary;
    const departureDate = getTripDepartureDate(tripMeta);
    if (!departureDate) return structuredItinerary;
    const items = structuredItinerary.itineraryItems;
    if (!Array.isArray(items)) return structuredItinerary;
    return {
      ...structuredItinerary,
      itineraryItems: items.map((item) => ({
        ...(item as Record<string, unknown>),
        date:
          (item as { date?: string }).date ??
          computeItineraryDayLabel(departureDate, (item as { day: number }).day),
      })),
    };
  }, [structuredItinerary, tripMeta]);

  // ── Desktop travel-bar state (drives left-panel highlight only) ─────────
  const [selectedBar, setSelectedBar] = useState<TravelBarRouteInfo | null>(null);
  const [desktopExpandedDay, setDesktopExpandedDay] = useState<number | null>(null);
  const isMdUp = useMediaQuery('(min-width: 900px)') ?? false;

  const handleTravelBarClick = (bar: TravelBarRouteInfo) => {
    setSelectedBar((prev) => {
      if (prev?.polyline && bar.polyline && prev.polyline === bar.polyline) return null;
      if (!bar.polyline &&
        prev?.originLatLng?.lat === bar.originLatLng?.lat &&
        prev?.originLatLng?.lng === bar.originLatLng?.lng &&
        prev?.destinationLatLng?.lat === bar.destinationLatLng?.lat &&
        prev?.destinationLatLng?.lng === bar.destinationLatLng?.lng) return null;
      return bar;
    });
  };

  // ── Mobile sheet state ───────────────────────────────────────────────────
  const mobileContainerRef = useRef<HTMLDivElement>(null);
  const [containerH, setContainerH] = useState(() => window.innerHeight);
  useEffect(() => {
    const el = mobileContainerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setContainerH(entry.contentRect.height);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const snaps = useMemo(() => ({
    full: 0,
    half: Math.max(0, containerH - HALF_H),
    peek: Math.max(0, containerH - PEEK_H),
  }), [containerH]);

  const y = useMotionValue(snaps.half);

  // Re-sync y to the current snap point when the container resizes.
  // `snaps` is the only dep because its identity only changes when `containerH` changes (it is
  // memoised above), so this effect fires exclusively on resize — exactly what we want.
  // `y` is a stable MotionValue reference and never changes identity.
  // `sheetState` is intentionally omitted: including it would re-trigger on every snap transition,
  // fighting the spring animation that already moved y to the correct position.

  useEffect(() => {
    const target = sheetState === 'full' ? snaps.full : sheetState === 'half' ? snaps.half : snaps.peek;
    y.set(target);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snaps]);

  const dragControls = useDragControls();
  const [sheetState, setSheetState] = useState<SheetState>('half');
  const [expandedDayId, setExpandedDayId] = useState<number | null>(null);
  const [selectedStopId, setSelectedStopId] = useState<string | null>(null);

  // Reset view-only state whenever the itinerary identity changes — otherwise a
  // day expanded for itinerary A would keep MultiDayRouteMap's FitBounds
  // constrained to that day when viewing itinerary B.
  useEffect(() => {
    setSelectedBar(null);
    setDesktopExpandedDay(null);
    setExpandedDayId(null);
    setSelectedStopId(null);
  }, [itineraryKey]);

  const snapTo = useCallback((targetY: number, state: SheetState) => {
    animate(y, targetY, SNAP_SPRING);
    setSheetState(state);
  }, [y]);

  const handleDragEnd = useCallback((_: unknown, info: PanInfo) => {
    if (Math.abs(info.offset.y) < 8) return;
    const current = y.get();
    const vel = info.velocity.y;
    let targetY: number;
    let state: SheetState;
    if (vel > 500) {
      if (current < snaps.half) { targetY = snaps.half; state = 'half'; }
      else { targetY = snaps.peek; state = 'peek'; }
    } else if (vel < -500) {
      if (current > snaps.half) { targetY = snaps.half; state = 'half'; }
      else { targetY = snaps.full; state = 'full'; }
    } else {
      const points: [number, SheetState][] = [[snaps.full, 'full'], [snaps.half, 'half'], [snaps.peek, 'peek']];
      [targetY, state] = points.reduce((a, b) => Math.abs(b[0] - current) < Math.abs(a[0] - current) ? b : a);
    }
    snapTo(targetY, state);
  }, [y, snaps, snapTo]);

  const handleHandleClick = useCallback(() => {
    if (sheetState === 'peek') snapTo(snaps.half, 'half');
    else if (sheetState === 'half') snapTo(snaps.full, 'full');
    else snapTo(snaps.half, 'half');
  }, [sheetState, snaps, snapTo]);

  const mobileItineraryDays = useMemo(
    () => toMobileItineraryDays(structuredItinerary, getTripDepartureDate(tripMeta)),
    [structuredItinerary, tripMeta],
  );

  const selectedStop = useMemo(() => {
    if (!selectedStopId) return null;
    for (const day of mobileItineraryDays) {
      const entry = day.stops?.find((e) => e.stop.id === selectedStopId);
      if (entry) return { stop: entry.stop, dayNumber: day.dayNumber, dayDate: day.date };
    }
    return null;
  }, [selectedStopId, mobileItineraryDays]);

  const expandedDay = useMemo(
    () => mobileItineraryDays.find((d) => d.dayNumber === expandedDayId) ?? null,
    [mobileItineraryDays, expandedDayId],
  );

  /** Booking chips are for the saved-itinerary list/detail route only. */
  const showLinkedBookingChips =
    Boolean(id) && location.pathname.startsWith(`${ROUTES.ITINERARIES}/`);

  // ── Loading / error / empty states ──────────────────────────────────────
  if (id && isLoading) {
    return (
      <Group justify="center" align="center" style={{ flex: 1 }}>
        <Loader />
      </Group>
    );
  }

  if (id && error) {
    return (
      <Alert color="red" m="md">
        Failed to load itinerary. It may have been deleted.
      </Alert>
    );
  }

  if (!hasValidData) {
    const isPublic = isPublicChatRoute(location.pathname);
    return (
      <Box style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        {!isPublic && (
          <Box
            style={{
              display: 'flex',
              justifyContent: 'center',
              padding: '32px 24px 40px',
            }}
          >
            <ItineraryPlannerForm />
          </Box>
        )}
      </Box>
    );
  }

  // ── Mobile layout ────────────────────────────────────────────────────────
  if (!isMdUp) {
    return (
      <Box ref={mobileContainerRef} style={{ position: 'relative', flex: 1, overflow: 'hidden' }}>
        {/* MultiDayRouteMap background — shows day-coloured markers with legend */}
        <Box style={{ position: 'absolute', inset: 0 }}>
          <MultiDayRouteMap
            key={itineraryKey}
            days={routeDays}
            center={{ lat: mapCenter.centerLatitude, lng: mapCenter.centerLongitude }}
            height="100%"
            focusDayId={expandedDayId}
            onFocusDayChange={setExpandedDayId}
          />
        </Box>

        {/* Bottom sheet */}
        <motion.div
          drag="y"
          dragControls={dragControls}
          dragListener={false}
          dragConstraints={{ top: snaps.full, bottom: snaps.peek }}
          dragElastic={{ top: 0.05, bottom: 0 }}
          onDragEnd={handleDragEnd}
          style={{
            y,
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 20,
            background: 'white',
            borderRadius: '18px 18px 0 0',
            boxShadow: `0 -4px 20px ${C_SHADOW_SHEET}`,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Drag-handle zone */}
          <Box
            role="button"
            aria-label="Adjust sheet height"
            style={{ touchAction: 'none', userSelect: 'none', flexShrink: 0, cursor: 'grab' }}
            onPointerDown={(e) => dragControls.start(e)}
            onClick={handleHandleClick}
          >
            {/* Pill */}
            <Box style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 6px' }}>
              <Box style={{ width: 36, height: 4, background: C_DRAG_PILL, borderRadius: 2 }} />
            </Box>

            {/* Header row */}
            <Box style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '2px 14px 10px', borderBottom: sheetState !== 'peek' ? `1px solid ${C_BORDER}` : 'none' }}>
              <Box>
                <div style={{ fontSize: 15, fontWeight: 700, color: C_NAVY_BLUE }}>
                  {expandedDay ? `Day ${expandedDay.dayNumber}` : 'Itinerary'}
                </div>
                {sheetState === 'peek' && (
                  <div style={{ fontSize: 12, color: C_NAVY_MID, marginTop: 1 }}>Swipe up to show list</div>
                )}
                {sheetState === 'half' && (
                  <div style={{ fontSize: 12, color: C_NAVY_MID, marginTop: 1 }}>Swipe up for full list · down to hide</div>
                )}
              </Box>
            </Box>
          </Box>

          {/* Stop detail overlay */}
          {selectedStop ? (
            <Box style={{ flex: 1, overflowY: 'auto', overscrollBehavior: 'contain' }}>
              <ItineraryStopDetail
                stop={selectedStop.stop}
                dayNumber={selectedStop.dayNumber}
                dayDate={selectedStop.dayDate}
                onClose={() => setSelectedStopId(null)}
              />
            </Box>
          ) : expandedDay ? (
            /* Day tapped — show day's stop list */
            <>
              <DayHeader
                dayLabel={`Day ${expandedDay.dayNumber}`}
                title={expandedDay.title}
                date={expandedDay.date}
                onBack={() => setExpandedDayId(null)}
              />
              <Box style={{ flex: 1, overflowY: 'auto', overscrollBehavior: 'contain', paddingBottom: 16 }}>
                <ItineraryDayCard
                  day={expandedDay}
                  isExpanded
                  hideBanner
                  isMobile={!isMdUp}
                  selectedStopId={selectedStopId}
                  onStopSelect={(sid) => {
                    setSelectedStopId(sid);
                  }}
                />
              </Box>
            </>
          ) : (
            /* Default — list of all days; always rendered so drag works in peek state */
            <Box style={{ flex: 1, overflowY: 'auto', overscrollBehavior: 'contain', position: 'relative' }}>
              <Stack gap={8} p={12}>
                {mobileItineraryDays.map((day) => (
                  <ItineraryDayCard
                    key={day.dayNumber}
                    day={day}
                    isMobile={!isMdUp}
                    onToggle={() => {
                      setExpandedDayId(day.dayNumber);
                    }}
                  />
                ))}
              </Stack>

              {/* Floating Map pill when sheet is full */}
              {sheetState === 'full' && (
                <Box style={{ position: 'sticky', bottom: 54, display: 'flex', justifyContent: 'center', pointerEvents: 'none' }}>
                  <UnstyledButton
                    onPointerDown={(e) => e.stopPropagation()}
                    style={{ pointerEvents: 'auto', display: 'inline-flex', alignItems: 'center', gap: 7, padding: '10px 20px', background: C_NAVY_BLUE, color: 'white', borderRadius: 9999, fontSize: 14, fontWeight: 600, boxShadow: `0 4px 14px ${C_SHADOW_MAP_BTN}` }}
                    onClick={() => snapTo(snaps.half, 'half')}
                  >
                    <MapIcon />
                    Map
                  </UnstyledButton>
                </Box>
              )}
            </Box>
          )}
        </motion.div>
      </Box>
    );
  }

  // ── Desktop layout ───────────────────────────────────────────────────────
  return (
    <Group
      gap="lg"
      align="stretch"
      wrap="nowrap"
      style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}
    >
      <Box
        style={{
          flex: CONTENT_SPLIT.LIST,
          minWidth: 0,
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        {showLinkedBookingChips && id ? (
          <LinkedBookingChips
            itineraryId={id}
            linkedBookings={savedItinerary?.linkedBookings}
          />
        ) : null}
        <ItineraryDetailsComponent
          {...(enrichedStructuredItinerary as Omit<ItineraryDetailsComponentProps, 'onTravelBarHover'>)}
          onTravelBarClick={handleTravelBarClick}
          selectedTravelBar={selectedBar}
          expandedDay={desktopExpandedDay}
          onExpandedDayChange={setDesktopExpandedDay}
          destination={tripMeta?.destination}
        />
      </Box>

      <Box
        style={{
          flex: CONTENT_SPLIT.MAP,
          minWidth: 0,
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        <MultiDayRouteMap
          key={itineraryKey}
          days={routeDays}
          center={{ lat: mapCenter.centerLatitude, lng: mapCenter.centerLongitude }}
          height="100%"
          focusDayId={desktopExpandedDay}
          onFocusDayChange={setDesktopExpandedDay}
        />
      </Box>
    </Group>
  );
}
