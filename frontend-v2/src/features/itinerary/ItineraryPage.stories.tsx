import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { Box, Stack, Text, Group, UnstyledButton } from '@mantine/core';
import { ItinerarySortFilterBar } from '@/features/itinerary/components/ItinerarySortFilterBar';
import { ItineraryDayCard } from '@/features/itinerary/components/ItineraryDayCard';
import { MultiDayRouteMap } from '@/features/itinerary/components/MultiDayRouteMap';
import { ItineraryStopDetail } from '@/features/itinerary/components/ItineraryStopDetail';
import { ItineraryFullMapView } from '@/features/itinerary/components/map/ItineraryFullMapView';
import type { ItineraryDay, ItineraryStop, ItineraryStopEntry } from '@/features/itinerary/components/ItineraryDayCard';
import type { RouteDay } from '@/features/itinerary/components/MultiDayRouteMap';

// ── Itinerary day fixtures ────────────────────────────────────────────────────

const DAYS: ItineraryDay[] = [
  {
    dayNumber: 1,
    date: 'FRI 15 MAY',
    title: 'Arrival in Lisbon & Riverside Welcome',
    description: 'Settle in, explore the riverside and grab your first pastéis de nata.',
    stopCount: 5,
    imageUrl: 'https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=200',
  },
  {
    dayNumber: 2,
    date: 'SAT 16 MAY',
    title: 'Sintra Palaces & Mountain Villages',
    description: 'Day trip into fairy-tale palaces, viewpoints and pine forests.',
    stopCount: 5,
    imageUrl: 'https://images.unsplash.com/photo-1548707309-dcebeab9ea9b?w=200',
  },
  {
    dayNumber: 3,
    date: 'SUN 17 MAY',
    title: 'Belém · Monasteries, Pastéis & Museums',
    description: 'Morning at Jerónimos, pastéis de nata, then the waterfront.',
    stopCount: 6,
    imageUrl: 'https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=200',
  },
  {
    dayNumber: 4,
    date: 'MON 18 MAY',
    title: 'LX Factory, Shopping & Departure',
    description: 'Lazy morning at LX Factory market, then head to the airport.',
    stopCount: 4,
    imageUrl: 'https://images.unsplash.com/photo-1562883676-8c7feb83f09b?w=200',
  },
];

// ── Map route data ────────────────────────────────────────────────────────────

const MAP_DAYS: RouteDay[] = [
  {
    id: 1, label: 'Day 1', color: '#4d5a8a',
    stops: [
      { lat: 38.7749, lng: -9.1342, name: 'Airport' },
      { lat: 38.7228, lng: -9.1393, name: 'Hotel Avenida Palace' },
      { lat: 38.7139, lng: -9.1394, name: 'Time Out Market' },
    ],
  },
  {
    id: 2, label: 'Day 2', color: '#2a9d8f',
    stops: [
      { lat: 38.7975, lng: -9.3900, name: 'Sintra National Palace' },
      { lat: 38.7879, lng: -9.3947, name: 'Pena Palace' },
      { lat: 38.7873, lng: -9.4010, name: 'Moorish Castle' },
    ],
  },
  {
    id: 3, label: 'Day 3', color: '#a0681e',
    stops: [
      { lat: 38.6979, lng: -9.2059, name: 'Jerónimos Monastery' },
      { lat: 38.6937, lng: -9.2159, name: 'Tower of Belém' },
      { lat: 38.6969, lng: -9.2080, name: 'Pastéis de Belém' },
    ],
  },
  {
    id: 4, label: 'Day 4', color: '#7b4f8e',
    stops: [
      { lat: 38.7071, lng: -9.1773, name: 'LX Factory' },
      { lat: 38.7749, lng: -9.1342, name: 'Airport departure' },
    ],
  },
];

const MAP_CENTER = { lat: 38.7369, lng: -9.1427 };

// ── Mobile stop fixture ───────────────────────────────────────────────────────

const STOP_FIXTURE: ItineraryStop = {
  id: 's1',
  startTime: '09:00',
  endTime: '11:00',
  name: 'Time Out Market',
  description: "Lisbon's best food hall — 40+ chefs from Michelin-starred restaurants under one beautiful iron roof.",
  duration: '2h',
  cost: '€15–30',
  rating: 4.6,
  reviewCount: 12400,
  imageUrl: 'https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=600',
  location: 'Mercado da Ribeira, Lisbon',
  category: 'Food & drink',
  tip: 'Go early — by noon the queues are long.',
  address: 'Av. 24 de Julho 49, 1200-479 Lisboa',
  phone: '+351 213 951 274',
  website: 'timeoutmarket.com',
};

const DAY_1_STOPS: ItineraryStopEntry[] = [
  { stop: STOP_FIXTURE, connector: [{ mode: 'walk', label: '8 min · 600m' }] },
  {
    stop: {
      id: 's2', startTime: '12:00', endTime: '13:30',
      name: 'Alfama Viewpoint',
      description: 'Panoramic views over the terracotta rooftops of Alfama and the Tagus.',
      duration: '1h 30m', cost: 'Free',
      imageUrl: 'https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=600',
      category: 'Sightseeing',
    },
    connector: [{ mode: 'transit', label: '15 min' }],
  },
  {
    stop: {
      id: 's3', startTime: '15:00', endTime: '17:00',
      name: 'Pastéis de Belém',
      description: 'The original custard tarts, made fresh to a secret recipe since 1837.',
      duration: '45m', cost: '€3', rating: 4.9, reviewCount: 32000,
      imageUrl: 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=600',
      category: 'Food & drink',
    },
  },
];

const DAY_1_EXPANDED: ItineraryDay = {
  dayNumber: 1,
  date: 'FRI 15 MAY',
  title: 'Arrival in Lisbon & Riverside Welcome',
  description: 'Settle in, explore the riverside and grab your first pastéis de nata.',
  stopCount: 5,
  imageUrl: 'https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=200',
  stops: DAY_1_STOPS,
};

// ── Shared ────────────────────────────────────────────────────────────────────

const noop = () => {};

// ── Mobile sheet primitives ───────────────────────────────────────────────────

const SHEET_STYLE: React.CSSProperties = {
  background: 'white',
  borderRadius: '18px 18px 0 0',
  boxShadow: '0 -4px 20px rgba(42,47,95,0.12)',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
};

function DragHandle() {
  return (
    <Box style={{ display: 'flex', justifyContent: 'center', padding: '8px 0 4px', flexShrink: 0 }}>
      <Box style={{ width: 36, height: 4, background: '#d4d8ea', borderRadius: 2 }} />
    </Box>
  );
}

function VibeControls() {
  return (
    <Group gap={4} style={{ flexShrink: 0 }}>
      <UnstyledButton style={{ padding: '4px 12px', borderRadius: 9999, fontSize: 12, fontWeight: 600, background: '#5C6494', border: '1px solid #5C6494', color: 'white' }}>
        Balanced
      </UnstyledButton>
      <UnstyledButton style={{ width: 28, height: 28, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(42,47,95,0.08)', border: 'none', borderRadius: '50%' }}>
        <svg viewBox="0 0 24 24" width={13} height={13} fill="none" stroke="#636e9d" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
          <circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>
        </svg>
      </UnstyledButton>
    </Group>
  );
}

function SheetHeader({ title, sub }: { title: string; sub: string }) {
  return (
    <Box style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '6px 14px 10px', borderBottom: '1px solid #E4E6F5', flexShrink: 0 }}>
      <Box>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#2A2F5F' }}>{title}</div>
        <div style={{ fontSize: 12, color: '#636e9d', marginTop: 2 }}>{sub}</div>
      </Box>
      <VibeControls />
    </Box>
  );
}

function BackHeader({ dayLabel, title, date, nextLabel, onBack }: { dayLabel: string; title: string; date: string; nextLabel?: string; onBack?: () => void }) {
  return (
    <Box style={{ padding: '8px 14px 10px', borderBottom: '1px solid #E4E6F5', flexShrink: 0 }}>
      <Box style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <UnstyledButton onClick={onBack} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 13, color: '#5C6494', fontWeight: 600 }}>
          <svg viewBox="0 0 24 24" width={14} height={14} fill="none" stroke="#5C6494" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="m15 18-6-6 6-6"/>
          </svg>
          {dayLabel}
        </UnstyledButton>
        {nextLabel && (
          <UnstyledButton style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 13, color: '#5C6494', fontWeight: 600 }}>
            {nextLabel}
            <svg viewBox="0 0 24 24" width={14} height={14} fill="none" stroke="#5C6494" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="m9 18 6-6-6-6"/>
            </svg>
          </UnstyledButton>
        )}
      </Box>
      <div style={{ fontSize: 15, fontWeight: 700, color: '#2A2F5F', lineHeight: 1.3 }}>{title}</div>
      <div style={{ fontSize: 12, color: '#636e9d', marginTop: 2 }}>{date}</div>
    </Box>
  );
}

// ── Simple app header placeholder ─────────────────────────────────────────────

function AppHeaderPlaceholder() {
  return (
    <Box style={{ height: 52, background: '#2A2F5F', display: 'flex', alignItems: 'center', paddingLeft: 16, paddingRight: 16, flexShrink: 0 }}>
      <Text style={{ color: 'white', fontWeight: 700, fontSize: 16, letterSpacing: '-0.02em' }}>Voya</Text>
      <Box style={{ flex: 1 }} />
      <Box style={{ width: 28, height: 28, borderRadius: '50%', background: 'rgba(255,255,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <svg viewBox="0 0 24 24" width={14} height={14} fill="none" stroke="white" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
        </svg>
      </Box>
    </Box>
  );
}

function TripHeaderPlaceholder() {
  return (
    <Box style={{ padding: '8px 16px', background: 'white', borderBottom: '1px solid #E4E6F5', display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
      <svg viewBox="0 0 24 24" width={14} height={14} fill="none" stroke="#2A2F5F" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
        <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21 4 19.5 2.5S18 1 16.5 2.5L13 6l-8.2-1.8C3.6 3.9 2.5 5.4 3.3 6.5L9 12l-2 3.5L5 15l-1.5 1.5 2.5 1.5 1.5 2.5L9 19l0-2 3.5-2 5.7 5.7c1.1.8 2.6-.3 2.3-1.5z"/>
      </svg>
      <Text style={{ fontSize: 13, fontWeight: 700, color: '#2A2F5F' }}>London → Lisbon · 15–18 May · 2 adults</Text>
    </Box>
  );
}

const mobile = { viewport: { defaultViewport: 'mobile1' } };

// ═══════════════════════════════════════════════════════════════════════════════
//  MOBILE LAYOUTS
// ═══════════════════════════════════════════════════════════════════════════════

// ── B1 · Map + sheet (50/50) ──────────────────────────────────────────────────

function B1Layout() {
  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppHeaderPlaceholder />
      <TripHeaderPlaceholder />
      <Box style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <MultiDayRouteMap days={MAP_DAYS} height="100%" hideLegend />
        <Box style={{ ...SHEET_STYLE, position: 'absolute', bottom: 0, left: 0, right: 0, height: 280 }}>
          <DragHandle />
          <SheetHeader title="Itinerary · 15–18 May" sub="Drag up for full list · down to hide" />
          <Box style={{ flex: 1, overflowY: 'auto' }}>
            <Stack gap={8} p={8}>
              <ItineraryDayCard day={DAYS[0]!} />
              <ItineraryDayCard day={DAYS[1]!} />
            </Stack>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

// ── B2 · Sheet minimized ──────────────────────────────────────────────────────

function B2Layout() {
  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppHeaderPlaceholder />
      <TripHeaderPlaceholder />
      <Box style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <MultiDayRouteMap days={MAP_DAYS} height="100%" hideLegend />
        <Box style={{ ...SHEET_STYLE, position: 'absolute', bottom: 0, left: 0, right: 0, height: 72 }}>
          <DragHandle />
          <Box style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 14px 10px' }}>
            <Box>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#2A2F5F' }}>Itinerary · 15–18 May</div>
              <div style={{ fontSize: 12, color: '#636e9d', marginTop: 1 }}>Drag up to show list</div>
            </Box>
            <VibeControls />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

// ── Default · 80% sheet ───────────────────────────────────────────────────────

function MobileDefaultLayout() {
  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppHeaderPlaceholder />
      <TripHeaderPlaceholder />
      <Box style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <MultiDayRouteMap days={MAP_DAYS} height="100%" hideLegend />
        <Box style={{ ...SHEET_STYLE, position: 'absolute', bottom: 0, left: 0, right: 0, height: '82%' }}>
          <DragHandle />
          <SheetHeader title="Itinerary · 15–18 May" sub="Drag down for map" />
          <ItinerarySortFilterBar defaultSort="balanced" />
          <Box style={{ flex: 1, overflowY: 'auto' }}>
            <Stack gap={8} p={8}>
              {DAYS.map((day) => <ItineraryDayCard key={day.dayNumber} day={day} />)}
            </Stack>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

// ── Full list · sheet fills body, map hidden ──────────────────────────────────

function MobileFullListLayout() {
  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppHeaderPlaceholder />
      <TripHeaderPlaceholder />
      <Box style={{ ...SHEET_STYLE, flex: 1, borderRadius: 0 }}>
        <DragHandle />
        <SheetHeader title="Itinerary · 15–18 May" sub="Drag down for map" />
        <ItinerarySortFilterBar defaultSort="balanced" />
        <Box style={{ flex: 1, overflowY: 'auto', position: 'relative' }}>
          <Stack gap={8} p={8}>
            {DAYS.map((day) => <ItineraryDayCard key={day.dayNumber} day={day} />)}
          </Stack>
          {/* Floating Map pill */}
          <Box style={{ position: 'sticky', bottom: 16, display: 'flex', justifyContent: 'center', pointerEvents: 'none' }}>
            <UnstyledButton style={{ pointerEvents: 'auto', display: 'inline-flex', alignItems: 'center', gap: 7, padding: '10px 20px', background: '#2A2F5F', color: 'white', borderRadius: 9999, fontSize: 14, fontWeight: 600, boxShadow: '0 4px 14px rgba(42,47,95,0.35)' }}>
              <svg viewBox="0 0 24 24" width={15} height={15} fill="none" stroke="white" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 18V6l6 4v12z"/><path d="M3 6v12l6-2"/><path d="M15 10l6-2v12l-6 2"/>
              </svg>
              Map
            </UnstyledButton>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

// ── Day tapped · stops list ───────────────────────────────────────────────────

function DayTappedLayout() {
  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppHeaderPlaceholder />
      <TripHeaderPlaceholder />
      <Box style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <MultiDayRouteMap days={MAP_DAYS} focusDayId={1} height="100%" hideLegend />
        <Box style={{ ...SHEET_STYLE, position: 'absolute', bottom: 0, left: 0, right: 0, height: '82%' }}>
          <DragHandle />
          <BackHeader dayLabel="All days" title={DAY_1_EXPANDED.title} date="Fri 15 May" nextLabel="Day 2" onBack={noop} />
          <Box style={{ flex: 1, overflowY: 'auto' }}>
            <ItineraryDayCard day={DAY_1_EXPANDED} isExpanded hideBanner />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

// ── Stop tapped · overlay ─────────────────────────────────────────────────────

function StopTappedLayout() {
  const [open, setOpen] = useState(true);
  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppHeaderPlaceholder />
      <TripHeaderPlaceholder />
      <Box style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <MultiDayRouteMap days={MAP_DAYS.slice(0, 1)} focusDayId={1} height="100%" hideLegend />
        {open && (
          <Box style={{ ...SHEET_STYLE, position: 'absolute', bottom: 0, left: 0, right: 0 }}>
            <ItineraryStopDetail
              stop={STOP_FIXTURE}
              dayNumber={1}
              dayDate="Fri 15 May"
              onClose={() => setOpen(false)}
            />
          </Box>
        )}
      </Box>
    </Box>
  );
}

// ─── Desktop layout ───────────────────────────────────────────────────────────

function DesktopLayout() {
  const [expandedDay, setExpandedDay] = useState<number | null>(null);
  const [showFullMap, setShowFullMap] = useState(false);

  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppHeaderPlaceholder />
      <TripHeaderPlaceholder />

      <Box style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Content area: sort bar above, then list + map */}
        <Box style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {showFullMap ? (
            <ItineraryFullMapView
              days={MAP_DAYS}
              count={DAYS.length}
              center={MAP_CENTER}
              zoom={11}
              defaultSort="balanced"
              onClose={() => setShowFullMap(false)}
            />
          ) : (
            <>
              <ItinerarySortFilterBar defaultSort="balanced" />

              <Box style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                {/* Itinerary list */}
                <Box style={{ width: 400, flexShrink: 0, borderRight: '1px solid #E4E6F5', overflowY: 'auto', background: 'white', padding: '12px 12px 24px' }}>
                  <Stack gap={8}>
                    {DAYS.map((day) => (
                      <ItineraryDayCard
                        key={day.dayNumber}
                        day={day}
                        isExpanded={expandedDay === day.dayNumber}
                        onToggle={() => setExpandedDay((prev) => prev === day.dayNumber ? null : day.dayNumber)}
                      />
                    ))}
                  </Stack>
                </Box>

                {/* Map */}
                <Box style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
                  <MultiDayRouteMap
                    days={MAP_DAYS}
                    center={MAP_CENTER}
                    zoom={11}
                    height="100%"
                  />
                  <UnstyledButton
                    onClick={() => setShowFullMap(true)}
                    aria-label="Expand to full map"
                    style={{
                      position: 'absolute', top: 10, right: 10, zIndex: 10,
                      width: 32, height: 32, borderRadius: '50%',
                      background: 'white', border: '1px solid #E4E6F5',
                      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
                    }}
                  >
                    <svg viewBox="0 0 24 24" width={14} height={14} fill="none" stroke="#2A2F5F" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
                      <path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>
                    </svg>
                  </UnstyledButton>
                </Box>
              </Box>
            </>
          )}
        </Box>
      </Box>
    </Box>
  );
}

// ─── Meta ─────────────────────────────────────────────────────────────────────

const meta: Meta = {
  title: 'Itinerary/ItineraryPage',
  parameters: { layout: 'fullscreen' },
};

export default meta;
type Story = StoryObj;

export const DesktopResultsPopulated: Story = {
  name: 'Desktop · results populated',
  render: () => <DesktopLayout />,
};

// ── Mobile stories ────────────────────────────────────────────────────────────

export const MobileB1MapSheet: Story = {
  name: 'Mobile · B1 · Map + sheet (50/50)',
  parameters: mobile,
  render: () => <B1Layout />,
};

export const MobileB2Minimized: Story = {
  name: 'Mobile · B2 · Sheet minimized',
  parameters: mobile,
  render: () => <B2Layout />,
};

export const MobileDefault: Story = {
  name: 'Mobile · default (80% sheet)',
  parameters: mobile,
  render: () => <MobileDefaultLayout />,
};

export const MobileFullList: Story = {
  name: 'Mobile · full list',
  parameters: mobile,
  render: () => <MobileFullListLayout />,
};

export const MobileDayTapped: Story = {
  name: 'Mobile · Day tapped · stops list',
  parameters: mobile,
  render: () => <DayTappedLayout />,
};

export const MobileStopTapped: Story = {
  name: 'Mobile · Stop tapped · overlay',
  parameters: mobile,
  render: () => <StopTappedLayout />,
};
