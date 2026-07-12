import { useEffect, useMemo, useRef, useState } from 'react';
import { Box, Text, Group, Stack } from '@mantine/core';
import { APIProvider, Map, AdvancedMarker, useMap } from '@vis.gl/react-google-maps';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface RouteStop {
  lat: number;
  lng: number;
  name: string;
}

export interface RouteDay {
  id: number;
  label: string;
  color: string;
  stops: RouteStop[];
}

export interface MultiDayRouteMapProps {
  days: RouteDay[];
  center?: { lat: number; lng: number };
  zoom?: number;
  height?: string;
  /** Highlight a single day — others are hidden. Pass null to show all. */
  focusDayId?: number | null;
  /** Highlight a specific stop within the visible day. */
  highlightedStop?: { dayId: number; stopIndex: number } | null;
  /** Called when a stop marker is clicked on the map. */
  onStopClick?: (dayId: number, stopIndex: number) => void;
  /** Hide the day legend panel (useful on small viewports). */
  hideLegend?: boolean;
  /** Called when the legend focus changes. When provided, the legend is fully interactive even when `focusDayId` is controlled externally. */
  onFocusDayChange?: (id: number | null) => void;
}

// ─── PinDot marker ───────────────────────────────────────────────────────────

function PinDot({
  color,
  label,
  highlighted = false,
  dimmed = false,
}: {
  color: string;
  label: number;
  highlighted?: boolean;
  dimmed?: boolean;
}) {
  return (
    <div
      style={{
        width: highlighted ? 40 : 32,
        height: highlighted ? 40 : 32,
        borderRadius: '50%',
        background: color,
        border: `${highlighted ? 4 : 3}px solid white`,
        boxShadow: highlighted
          ? `0 3px 12px rgba(0,0,0,0.4), 0 0 0 4px ${color}55`
          : '0 2px 6px rgba(0,0,0,0.32), 0 0 0 1px rgba(0,0,0,0.06)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontSize: highlighted ? 14 : 11,
        fontWeight: 700,
        fontFamily: 'Inter, -apple-system, sans-serif',
        opacity: dimmed ? 0.55 : 1,
        transition: 'all 180ms ease',
        cursor: 'pointer',
        userSelect: 'none',
        letterSpacing: '-0.01em',
      }}
    >
      {label}
    </div>
  );
}

// ─── Per-day polyline (imperative) ────────────────────────────────────────────

function DayPolyline({ day, visible }: { day: RouteDay; visible: boolean }) {
  const map = useMap();
  const lineRef = useRef<google.maps.Polyline | null>(null);

  useEffect(() => {
    if (!map || day.stops.length < 2) return;

    lineRef.current = new google.maps.Polyline({
      path: day.stops.map((s) => ({ lat: s.lat, lng: s.lng })),
      geodesic: true,
      strokeOpacity: 0,
      strokeWeight: 0,
      icons: [
        {
          icon: {
            path: 'M 0,-1 0,1',
            strokeOpacity: 0.8,
            strokeColor: day.color,
            scale: 3,
          },
          offset: '0',
          repeat: '12px',
        },
      ],
      map: visible ? map : null,
    });

    return () => {
      lineRef.current?.setMap(null);
      lineRef.current = null;
    };
  }, [map, day]);

  useEffect(() => {
    if (!lineRef.current) return;
    lineRef.current.setMap(visible ? map : null);
  }, [visible, map]);

  return null;
}

// ─── Fit map bounds to visible stops ─────────────────────────────────────────

function FitBounds({
  days,
  visibleIds,
  focusDayId,
  skip,
}: {
  days: RouteDay[];
  visibleIds: Set<number>;
  focusDayId: number | null;
  skip: boolean;
}) {
  const map = useMap();

  useEffect(() => {
    if (!map || skip) return;
    const activeDays =
      focusDayId != null
        ? days.filter((d) => d.id === focusDayId && visibleIds.has(d.id))
        : days.filter((d) => visibleIds.has(d.id));
    const stops = activeDays.flatMap((d) => d.stops);
    if (stops.length < 2) return;
    const bounds = stops.reduce(
      (acc, s) => acc.extend({ lat: s.lat, lng: s.lng }),
      new google.maps.LatLngBounds(),
    );
    map.fitBounds(bounds, { top: 48, right: 48, bottom: 48, left: 48 });
  }, [map, days, visibleIds, focusDayId, skip]);

  return null;
}

// ─── Pan map to a specific stop ───────────────────────────────────────────────

function PanToStop({ lat, lng }: { lat: number | null; lng: number | null }) {
  const map = useMap();
  useEffect(() => {
    if (!map || lat == null || lng == null) return;
    map.panTo({ lat, lng });
  }, [map, lat, lng]);
  return null;
}

// ─── Move map type control to bottom-left at runtime ─────────────────────────

function MapTypeControlPosition() {
  const map = useMap();
  useEffect(() => {
    const g = (window as unknown as { google?: { maps?: { ControlPosition?: Record<string, number> } } }).google;
    if (!map || !g?.maps?.ControlPosition) return;
    map.setOptions({ mapTypeControlOptions: { position: g.maps.ControlPosition.BOTTOM_LEFT } });
  }, [map]);
  return null;
}

// ─── Legend panel ─────────────────────────────────────────────────────────────

function LegendPanel({
  days,
  focusDayId,
  onFocus,
  readOnly = false,
}: {
  days: RouteDay[];
  focusDayId: number | null;
  onFocus: (id: number | null) => void;
  readOnly?: boolean;
}) {
  const focused = focusDayId != null ? days.find((d) => d.id === focusDayId) : null;
  const [collapsed, setCollapsed] = useState(false);

  const handleSelect = (id: number | null) => {
    onFocus(id);
    setCollapsed(true);
  };

  return (
    <Box
      style={{
        position: 'absolute',
        top: 12,
        left: 12,
        zIndex: 10,
        background: 'rgba(255,255,255,0.97)',
        borderRadius: 10,
        padding: '10px 12px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
        border: '1px solid var(--mantine-color-gray-2)',
        minWidth: 168,
      }}
    >
      <Group
        justify="space-between"
        align="center"
        mb={collapsed ? 0 : 7}
        gap={8}
        role="button"
        tabIndex={0}
        aria-expanded={!collapsed}
        aria-label={
          focused
            ? `Toggle legend, currently showing Day ${focused.id} ${focused.label}`
            : 'Toggle legend, currently showing all days'
        }
        onClick={() => setCollapsed((c) => !c)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setCollapsed((c) => !c);
          }
        }}
        style={{ cursor: 'pointer', userSelect: 'none' }}
      >
        <Text
          style={{
            fontSize: '0.6rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}
          c="navy.4"
        >
          {focused ? `Day ${focused.id} · ${focused.label}` : 'Showing all days'}
        </Text>
        <Box
          aria-hidden
          style={{
            display: 'flex',
            alignItems: 'center',
            color: 'var(--mantine-color-navy-4)',
            flexShrink: 0,
            pointerEvents: 'none',
          }}
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            style={{
              transition: 'transform 200ms ease',
              transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
            }}
          >
            <path
              d="M2 4.5L6 8L10 4.5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </Box>
      </Group>

      {!collapsed && (
        <Stack gap={2}>
          {(() => {
            const allActive = focusDayId == null;
            return (
              <Group
                key="all-days"
                gap={8}
                align="center"
                onClick={!readOnly && !allActive ? () => handleSelect(null) : undefined}
                style={{
                  cursor: readOnly || allActive ? 'default' : 'pointer',
                  padding: '5px 6px',
                  margin: '0 -6px',
                  borderRadius: 5,
                  background: allActive ? '#ECEEFF' : 'transparent',
                  transition: 'background 150ms ease',
                }}
              >
                <Box
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background:
                      days.length === 0
                        ? 'var(--mantine-color-gray-3)'
                        : 'conic-gradient(' +
                          days.map((d, i) => `${d.color} ${(i / days.length) * 360}deg ${((i + 1) / days.length) * 360}deg`).join(', ') +
                          ')',
                    flexShrink: 0,
                  }}
                />
                <Text
                  style={{ fontSize: '0.6875rem' }}
                  fw={allActive ? 600 : 500}
                  c={allActive ? 'navy.8' : 'navy.6'}
                >
                  All days
                </Text>
              </Group>
            );
          })()}
          {days.map((day) => {
            const isFocused = focusDayId === day.id;
            const isFaded = focusDayId != null && !isFocused;
            return (
              <Group
                key={day.id}
                gap={8}
                align="center"
                onClick={!readOnly ? () => handleSelect(isFocused ? null : day.id) : undefined}
                style={{
                  cursor: readOnly ? 'default' : 'pointer',
                  padding: '5px 6px',
                  margin: '0 -6px',
                  borderRadius: 5,
                  background: isFocused ? '#ECEEFF' : 'transparent',
                  opacity: isFaded ? 0.45 : 1,
                  transition: 'opacity 150ms ease, background 150ms ease',
                }}
              >
                <Box
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    backgroundColor: day.color,
                    flexShrink: 0,
                  }}
                />
                <Text
                  style={{ fontSize: '0.6875rem' }}
                  fw={isFocused ? 600 : 500}
                  c={isFocused ? 'navy.8' : 'navy.6'}
                >
                  Day {day.id} · {day.label}
                </Text>
              </Group>
            );
          })}
        </Stack>
      )}
    </Box>
  );
}

// ─── Inner map (needs to be inside APIProvider) ───────────────────────────────

function MapInner({
  days,
  center,
  zoom,
  focusDayId: externalFocusDayId,
  highlightedStop: externalHighlightedStop,
  onStopClick: externalOnStopClick,
  hideLegend = false,
  onFocusDayChange,
}: Omit<MultiDayRouteMapProps, 'height'>) {
  const mapId = import.meta.env.VITE_GOOGLE_MAPS_MAP_ID as string | undefined;
  const visibleIds = useMemo(() => new Set(days.map((d) => d.id)), [days]);
  const [localFocusDayId, setLocalFocusDayId] = useState<number | null>(null);
  const [localHighlightedStop, setLocalHighlightedStop] = useState<{
    dayId: number;
    stopIndex: number;
  } | null>(null);

  const focusDayId = externalFocusDayId ?? localFocusDayId;
  const highlightedStop =
    externalHighlightedStop !== undefined ? externalHighlightedStop : localHighlightedStop;

  const allStops = days.flatMap((d) => d.stops);
  const defaultCenter = center ?? {
    lat: allStops.reduce((s, p) => s + p.lat, 0) / Math.max(1, allStops.length),
    lng: allStops.reduce((s, p) => s + p.lng, 0) / Math.max(1, allStops.length),
  };

  const highlightedDay = highlightedStop
    ? days.find((d) => d.id === highlightedStop.dayId)
    : null;
  const highlightedStopCoords = highlightedDay?.stops[highlightedStop?.stopIndex ?? -1] ?? null;

  const handleStopClick = (dayId: number, stopIndex: number) => {
    const isSame =
      localHighlightedStop?.dayId === dayId && localHighlightedStop?.stopIndex === stopIndex;
    const next = isSame ? null : { dayId, stopIndex };
    setLocalHighlightedStop(next);
    if (next) externalOnStopClick?.(dayId, stopIndex);
  };

  const handleDayFocus = (id: number | null) => {
    if (onFocusDayChange) {
      onFocusDayChange(id);
    } else {
      setLocalFocusDayId(id);
    }
    setLocalHighlightedStop(null);
  };

  const legendInteractive = onFocusDayChange != null || externalFocusDayId == null;

  return (
    <Box style={{ width: '100%', height: '100%', position: 'relative' }}>
      <Map
        defaultCenter={defaultCenter}
        defaultZoom={zoom ?? 12}
        style={{ width: '100%', height: '100%' }}
        gestureHandling="greedy"
        disableDefaultUI={false}
        mapId={mapId}
      >
        <MapTypeControlPosition />
        <FitBounds
          days={days}
          visibleIds={visibleIds}
          focusDayId={focusDayId}
          skip={highlightedStop != null}
        />
        <PanToStop
          lat={highlightedStopCoords?.lat ?? null}
          lng={highlightedStopCoords?.lng ?? null}
        />

        {/* Polylines — hidden for non-focused days when a day is selected */}
        {days.map((day) => {
          const isVisible =
            visibleIds.has(day.id) && (focusDayId == null || focusDayId === day.id);
          return <DayPolyline key={day.id} day={day} visible={isVisible} />;
        })}

        {/* Markers — non-focused days are completely hidden */}
        {days.flatMap((day) => {
          if (!visibleIds.has(day.id)) return [];
          if (focusDayId != null && focusDayId !== day.id) return [];
          return day.stops.map((stop, i) => {
            const isHighlighted =
              highlightedStop?.dayId === day.id && highlightedStop?.stopIndex === i;
            const isDimmed = highlightedStop != null && !isHighlighted;
            return (
              <AdvancedMarker
                key={`${day.id}-${i}`}
                position={{ lat: stop.lat, lng: stop.lng }}
                title={stop.name}
                zIndex={isHighlighted ? 20 : 10}
                onClick={() => handleStopClick(day.id, i)}
              >
                <PinDot
                  color={day.color}
                  label={i + 1}
                  highlighted={isHighlighted}
                  dimmed={isDimmed}
                />
              </AdvancedMarker>
            );
          });
        })}
      </Map>

      {!hideLegend && (
        <LegendPanel
          days={days}
          focusDayId={focusDayId}
          onFocus={handleDayFocus}
          readOnly={!legendInteractive}
        />
      )}
    </Box>
  );
}

// ─── Public component ─────────────────────────────────────────────────────────

export function MultiDayRouteMap({ height = '500px', ...rest }: MultiDayRouteMapProps) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;

  if (!apiKey?.trim()) {
    return (
      <Box
        style={{
          height,
          borderRadius: 'var(--mantine-radius-md)',
          border: '1px solid var(--mantine-color-gray-2)',
          backgroundColor: 'var(--mantine-color-gray-0)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Text size="sm" c="navy.5" ta="center">
          Map unavailable — set VITE_GOOGLE_MAPS_API_KEY to enable.
        </Text>
      </Box>
    );
  }

  return (
    <Box
      style={{
        height,
        borderRadius: 'var(--mantine-radius-md)',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <APIProvider apiKey={apiKey}>
        <MapInner {...rest} />
      </APIProvider>
    </Box>
  );
}
