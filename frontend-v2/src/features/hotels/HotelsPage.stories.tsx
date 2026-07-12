import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, waitFor, expect } from 'storybook/test';
import { useState, useRef } from 'react';
import { Box, Group, UnstyledButton } from '@mantine/core';
import { APIProvider } from '@vis.gl/react-google-maps';
import { HotelMobileMapView } from './components/HotelMobileMapView';
import type { HotelMapPin } from './components/HotelMobileMapView';
import { HotelCard } from './components/HotelCard';
import { HotelSortFilterBar } from './components/HotelSortFilterBar';
import { HotelsFullMapView } from './components/map/HotelsFullMapView';
import type { HotelFullMapPin } from './components/map/HotelsFullMapView';
import type { HotelItinerary } from '@/types/hotels';

// ── Shared fixtures ───────────────────────────────────────────────────────────

const MAP_HOTELS: HotelMapPin[] = [
  { id: 'h1', lat: 38.7148, lng: -9.1421, price: '£142', name: 'Hotel Avenida Palace'     },
  { id: 'h2', lat: 38.7122, lng: -9.1340, price: '£198', name: 'Memmo Alfama'             },
  { id: 'h3', lat: 38.7364, lng: -9.1534, price: '£168', name: 'Corinthia Lisbon'         },
  { id: 'h4', lat: 38.7140, lng: -9.1470, price: '£98',  name: 'Lisboa Central Boutique' },
  { id: 'h5', lat: 38.7166, lng: -9.1399, price: '£275', name: 'Bairro Alto Hotel'        },
  { id: 'h6', lat: 38.7102, lng: -9.1590, price: '£156', name: 'Martinhal Lisbon'         },
];

const FULL_MAP_PINS: HotelFullMapPin[] = [
  { id: 'h1', lat: 38.7148, lng: -9.1421, price: '£142', name: 'Hotel Avenida Palace',    area: 'Baixa · 4 min to river',       stars: 5, reviewScore: 9.4, reviewCount: 1241, reviewLabel: 'Exceptional', totalPrice: '£1,420' },
  { id: 'h2', lat: 38.7122, lng: -9.1340, price: '£198', name: 'Memmo Alfama',            area: 'Alfama · riverside view',       stars: 4, reviewScore: 9.3, reviewCount: 964,  reviewLabel: 'Exceptional', totalPrice: '£1,980' },
  { id: 'h3', lat: 38.7364, lng: -9.1534, price: '£168', name: 'Corinthia Lisbon',        area: 'Praça de Espanha',              stars: 4, reviewScore: 9.1, reviewCount: 2187, reviewLabel: 'Superb',      totalPrice: '£1,680' },
  { id: 'h4', lat: 38.7140, lng: -9.1470, price: '£98',  name: 'Lisboa Central Boutique', area: 'Bairro Alto · 8 min to centre', stars: 3, reviewScore: 8.7, reviewCount: 611,  reviewLabel: 'Very good',   totalPrice: '£980'  },
  { id: 'h5', lat: 38.7166, lng: -9.1399, price: '£275', name: 'Bairro Alto Hotel',       area: 'Chiado · city views',           stars: 5, reviewScore: 9.6, reviewCount: 342,  reviewLabel: 'Exceptional', totalPrice: '£2,750' },
  { id: 'h6', lat: 38.7102, lng: -9.1590, price: '£156', name: 'Martinhal Lisbon',        area: 'Belém · riverside',             stars: 4, reviewScore: 9.0, reviewCount: 788,  reviewLabel: 'Superb',      totalPrice: '£1,560' },
];

const mkHotel = (id: string, name: string, stars: number, perNight: number, img: string): HotelItinerary => ({
  id, tokenId: `tok-${id}`, name,
  address: 'Lisbon, Portugal', city: 'Lisbon', country: 'Portugal',
  starRating: stars,
  latitude: 38.7148, longitude: -9.1421,
  imageUrl: img, images: [img],
  startingPrice: { currency: 'GBP', amount: perNight * 10, perNight },
  total: perNight * 10,
  fareType: 'Room Only', propertyType: 'Hotel',
  amenities: ['Free WiFi', 'Pool', 'Spa', 'Restaurant'],
});

const HOTEL_1 = mkHotel('h1', 'Hotel Avenida Palace',    5, 142, 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600');
const HOTEL_2 = mkHotel('h2', 'Memmo Alfama',            4, 198, 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600');
const HOTEL_3 = mkHotel('h3', 'Corinthia Lisbon',        4, 168, 'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=600');
const HOTEL_4 = mkHotel('h4', 'Lisboa Central Boutique', 3,  98, 'https://images.unsplash.com/photo-1445019980597-93fa8acb246c?w=600');

const noop = () => {};

// ── Inline header placeholders ────────────────────────────────────────────────
// Voya's HotelsPage uses the app shell (UnifiedHeader). In Storybook we render
// lightweight stand-ins so the page-level layout is visible without pulling in
// router-dependent components.

function StoryNavbar() {
  return (
    <Box style={{
      height: 52, flexShrink: 0,
      background: '#2A2F5F',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 16px',
    }}>
      <Box style={{ width: 64, height: 20, background: 'rgba(255,255,255,0.25)', borderRadius: 4 }} />
      <Group gap={10}>
        {['Flights', 'Hotels', 'Itinerary'].map((s) => (
          <Box key={s} style={{
            fontSize: 12, color: s === 'Hotels' ? 'white' : 'rgba(255,255,255,0.55)',
            fontWeight: s === 'Hotels' ? 700 : 400,
            borderBottom: s === 'Hotels' ? '2px solid white' : 'none',
            paddingBottom: 2,
          }}>{s}</Box>
        ))}
      </Group>
      <Box style={{ width: 28, height: 28, borderRadius: '50%', background: 'rgba(255,255,255,0.2)' }} />
    </Box>
  );
}

function StoryTripHeader() {
  return (
    <Box style={{
      flexShrink: 0,
      background: 'white',
      borderBottom: '1px solid #E4E6F5',
      padding: '8px 14px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    }}>
      <Box>
        <Box style={{ fontSize: 13, fontWeight: 700, color: '#2A2F5F' }}>London → Lisbon</Box>
        <Box style={{ fontSize: 11, color: '#636e9d' }}>15–25 May · 2 adults</Box>
      </Box>
      <Group gap={6}>
        {['Route', 'Dates', 'Guests'].map((label) => (
          <UnstyledButton key={label} style={{
            fontSize: 11, color: '#5C6494', padding: '3px 8px',
            border: '1px solid #d4d8ea', borderRadius: 9999, background: 'white',
          }}>{label}</UnstyledButton>
        ))}
      </Group>
    </Box>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────

const SVG = { viewBox: '0 0 24 24', fill: 'none', strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
const IcFunnel = ({ size = 15, stroke = '#2A2F5F' }: { size?: number; stroke?: string }) => <svg {...SVG} width={size} height={size} stroke={stroke} strokeWidth={1.75}><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" /></svg>;
const IcDots   = ({ size = 13, stroke = '#636e9d' }: { size?: number; stroke?: string }) => <svg {...SVG} width={size} height={size} stroke={stroke} strokeWidth={1.75}><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></svg>;

// ── Mobile sheet primitives ───────────────────────────────────────────────────

function DragHandle() {
  return (
    <Box style={{ display: 'flex', justifyContent: 'center', padding: '8px 0 4px', flexShrink: 0 }}>
      <Box style={{ width: 36, height: 4, background: '#d4d8ea', borderRadius: 2 }} />
    </Box>
  );
}

type SheetSort = 'best' | 'cheap' | 'top';
const SHEET_SORT_LABELS: Record<SheetSort, string> = { best: 'Best', cheap: 'Cheap', top: 'Top' };

function SheetSortTabs({ sort, onSort }: { sort: SheetSort; onSort: (s: SheetSort) => void }) {
  return (
    <Group gap={4} style={{ flexShrink: 0 }}>
      {(['best', 'cheap', 'top'] as SheetSort[]).map(s => {
        const a = sort === s;
        return (
          <UnstyledButton key={s} onClick={() => onSort(s)} style={{ padding: '4px 10px', borderRadius: 9999, fontSize: 12, fontWeight: a ? 600 : 500, background: a ? '#5C6494' : 'white', border: `1px solid ${a ? '#5C6494' : '#d4d8ea'}`, color: a ? 'white' : '#636e9d', transition: 'all 120ms ease' }}>
            {SHEET_SORT_LABELS[s]}
          </UnstyledButton>
        );
      })}
      <UnstyledButton aria-label="More" style={{ width: 28, height: 28, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: 'white', border: '1px solid #d4d8ea', borderRadius: '50%' }}>
        <IcDots />
      </UnstyledButton>
      <UnstyledButton aria-label="Filters" style={{ height: 28, display: 'inline-flex', alignItems: 'center', gap: 4, padding: '0 8px', background: '#5C6494', border: '1px solid #5C6494', borderRadius: 9999 }}>
        <IcFunnel size={13} stroke="white" />
        <span style={{ background: 'rgba(255,255,255,0.85)', color: '#2A2F5F', borderRadius: 9999, padding: '1px 5px', fontSize: 10, lineHeight: 1.4 }}>1</span>
      </UnstyledButton>
    </Group>
  );
}

function SheetHeader({ title, sub, sort, onSort }: { title: string; sub: string; sort: SheetSort; onSort: (s: SheetSort) => void }) {
  return (
    <Box style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '6px 14px 10px', borderBottom: '1px solid #E4E6F5', flexShrink: 0 }}>
      <Box>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#2A2F5F' }}>{title}</div>
        <div style={{ fontSize: 12, color: '#636e9d', marginTop: 2 }}>{sub}</div>
      </Box>
      <SheetSortTabs sort={sort} onSort={onSort} />
    </Box>
  );
}

const SHEET_STYLE = {
  background: 'white',
  borderRadius: '18px 18px 0 0',
  boxShadow: '0 -4px 20px rgba(42,47,95,0.12)',
  display: 'flex',
  flexDirection: 'column' as const,
  overflow: 'hidden' as const,
};

// ── Desktop chat placeholder ──────────────────────────────────────────────────

function ChatPlaceholder() {
  return (
    <Box style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: '14px 14px 12px', gap: 10 }}>
      <Box style={{ padding: '8px 12px', background: '#F4F5FF', borderRadius: '10px 10px 10px 2px', fontSize: 13, color: '#2A2F5F', alignSelf: 'flex-start', maxWidth: '88%', lineHeight: 1.5 }}>
        I've found hotels in Lisbon for 15–25 May. Here are the top options for 2 guests.
      </Box>
      <Box style={{ padding: '8px 12px', background: '#2A2F5F', color: 'white', borderRadius: '10px 10px 2px 10px', fontSize: 13, alignSelf: 'flex-end', maxWidth: '88%', lineHeight: 1.5 }}>
        Show 4-star and above only
      </Box>
      <Box style={{ padding: '8px 12px', background: '#F4F5FF', borderRadius: '10px 10px 10px 2px', fontSize: 13, color: '#2A2F5F', alignSelf: 'flex-start', maxWidth: '88%', lineHeight: 1.5 }}>
        Filtered to 4★+. Avenida Palace is the top pick at £142/night — great location in Baixa.
      </Box>
      <Box style={{ marginTop: 'auto', padding: '8px 12px', background: 'white', border: '1px solid #E4E6F5', borderRadius: 9999, fontSize: 13, color: '#9aa2c5', display: 'flex', alignItems: 'center', gap: 8 }}>
        <Box style={{ width: 16, height: 16, borderRadius: '50%', background: '#dde1fb', flexShrink: 0 }} />
        Message Voya
      </Box>
    </Box>
  );
}

// ── Desktop layout ────────────────────────────────────────────────────────────

function ExpandIcon() {
  return (
    <svg viewBox="0 0 24 24" width={14} height={14} fill="none" stroke="#2A2F5F" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>
    </svg>
  );
}

function DesktopLayout() {
  const [selectedId, setSelectedId] = useState<string | null>('h1');
  const [showFullMap, setShowFullMap] = useState(false);

  const SORT_VALUES = { best: '£142', cheapest: '£98', 'top-reviews': '9.4' };

  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <StoryNavbar />
      <StoryTripHeader />

      <Box style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Chat — 300px */}
        <Box style={{ width: 300, flexShrink: 0, borderRight: '1px solid #E4E6F5', background: '#FCFCFF', overflow: 'hidden' }}>
          <ChatPlaceholder />
        </Box>

        {/* Content area */}
        <Box style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {showFullMap ? (
            <HotelsFullMapView
              hotels={FULL_MAP_PINS}
              count={FULL_MAP_PINS.length}
              onClose={() => setShowFullMap(false)}
              sortValues={SORT_VALUES}
            />
          ) : (
            <>
              <HotelSortFilterBar
                sortValues={SORT_VALUES}
                defaultSort="best"
                defaultStars="4plus"
              />
              <Box style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                {/* Hotel list — 380px */}
                <Box style={{ width: 380, flexShrink: 0, borderRight: '1px solid #E4E6F5', overflowY: 'auto', background: 'white' }}>
                  <Box p="xs"><HotelCard hotel={HOTEL_1} nights={10} onSelect={() => setSelectedId('h1')} isSelected={selectedId === 'h1'} /></Box>
                  <Box p="xs"><HotelCard hotel={HOTEL_2} nights={10} onSelect={() => setSelectedId('h2')} isSelected={selectedId === 'h2'} /></Box>
                  <Box p="xs"><HotelCard hotel={HOTEL_3} nights={10} onSelect={() => setSelectedId('h3')} isSelected={selectedId === 'h3'} /></Box>
                  <Box p="xs"><HotelCard hotel={HOTEL_4} nights={10} onSelect={() => setSelectedId('h4')} isSelected={selectedId === 'h4'} /></Box>
                </Box>
                {/* Map */}
                <Box style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
                  {(() => {
                    const mapsApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;
                    const mapEl = (
                      <HotelMobileMapView
                        hotels={MAP_HOTELS}
                        selectedId={selectedId}
                        viewedIds={['h2']}
                        onPinTap={id => setSelectedId(id)}
                        height="100%"
                      />
                    );
                    return mapsApiKey ? <APIProvider apiKey={mapsApiKey}>{mapEl}</APIProvider> : mapEl;
                  })()}
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
                    <ExpandIcon />
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

// ── Mobile · B1 · Map + sheet (50/50) ────────────────────────────────────────

function B1Layout() {
  const [sort, setSort] = useState<SheetSort>('best');
  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <StoryNavbar />
      <StoryTripHeader />
      <Box style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <HotelMobileMapView hotels={MAP_HOTELS} viewedIds={['h2']} height="100%" />
        <Box style={{ ...SHEET_STYLE, position: 'absolute', bottom: 0, left: 0, right: 0, height: 280 }}>
          <DragHandle />
          <SheetHeader title="48 hotels in Lisbon" sub="Drag up for full list · down to hide" sort={sort} onSort={setSort} />
          <Box style={{ flex: 1, overflowY: 'auto' }}>
            <Box p="xs"><HotelCard hotel={HOTEL_1} nights={10} onSelect={noop} /></Box>
            <Box p="xs"><HotelCard hotel={HOTEL_2} nights={10} onSelect={noop} /></Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

// ── Mobile · B2 · Sheet minimized ────────────────────────────────────────────

function B2Layout() {
  const [sort, setSort] = useState<SheetSort>('best');
  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <StoryNavbar />
      <StoryTripHeader />
      <Box style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <HotelMobileMapView hotels={MAP_HOTELS} viewedIds={['h2', 'h4']} height="100%" />
        <Box style={{ ...SHEET_STYLE, position: 'absolute', bottom: 0, left: 0, right: 0, height: 72 }}>
          <DragHandle />
          <Box style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 14px 10px' }}>
            <Box>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#2A2F5F' }}>48 hotels in Lisbon</div>
              <div style={{ fontSize: 12, color: '#636e9d', marginTop: 1 }}>Drag up to show list</div>
            </Box>
            <SheetSortTabs sort={sort} onSort={setSort} />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

// ── Mobile · B3 · Full list ───────────────────────────────────────────────────

function B3Layout() {
  const [sort, setSort] = useState<SheetSort>('best');
  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <StoryNavbar />
      <StoryTripHeader />
      <Box style={{ background: 'white' }}><DragHandle /></Box>
      <Box style={{ ...SHEET_STYLE, flex: 1, borderRadius: 0 }}>
        <SheetHeader title="48 hotels found" sub="Drag down for map" sort={sort} onSort={setSort} />
        <Box style={{ flex: 1, overflowY: 'auto', position: 'relative' }}>
          <Box p="xs"><HotelCard hotel={HOTEL_1} nights={10} onSelect={noop} /></Box>
          <Box p="xs"><HotelCard hotel={HOTEL_2} nights={10} onSelect={noop} /></Box>
          <Box p="xs"><HotelCard hotel={HOTEL_3} nights={10} onSelect={noop} /></Box>
          <Box p="xs"><HotelCard hotel={HOTEL_4} nights={10} onSelect={noop} /></Box>
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

// ── Mobile · B4 · Pin tapped · overlay ───────────────────────────────────────

const B4_HOTELS = [HOTEL_1, HOTEL_2, HOTEL_3, HOTEL_4];

const ARROW_BTN: React.CSSProperties = {
  position: 'absolute', top: '50%', transform: 'translateY(-50%)', zIndex: 10,
  width: 28, height: 28, borderRadius: '50%',
  background: 'white', boxShadow: '0 2px 8px rgba(42,47,95,0.18)',
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
};

function B4Layout() {
  const [open, setOpen] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(true);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    setCanLeft(el.scrollLeft > 8);
    setCanRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 8);
  };

  const scroll = (dir: 'left' | 'right') => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({ left: dir === 'right' ? el.clientWidth : -el.clientWidth, behavior: 'smooth' });
  };

  return (
    <Box style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <StoryNavbar />
      <StoryTripHeader />
      <Box style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <HotelMobileMapView hotels={MAP_HOTELS} selectedId="h1" viewedIds={['h2']} height="100%" />
        {open && (
          <Box style={{ ...SHEET_STYLE, position: 'absolute', bottom: 0, left: 0, right: 0 }}>
            <Box style={{ display: 'flex', justifyContent: 'flex-end', padding: '8px 10px 0' }}>
              <UnstyledButton onClick={() => setOpen(false)} style={{ width: 24, height: 24, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: '#F0F1F7', borderRadius: '50%' }}>
                <svg viewBox="0 0 24 24" width={12} height={12} fill="none" stroke="#636e9d" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 6 6 18" /><path d="m6 6 12 12" />
                </svg>
              </UnstyledButton>
            </Box>
            {/* Carousel */}
            <Box style={{ position: 'relative' }}>
              {canLeft && (
                <UnstyledButton onClick={() => scroll('left')} style={{ ...ARROW_BTN, left: 6 }}>
                  <svg viewBox="0 0 24 24" width={14} height={14} fill="none" stroke="#2A2F5F" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M15 18l-6-6 6-6" />
                  </svg>
                </UnstyledButton>
              )}
              <Box
                ref={scrollRef}
                onScroll={onScroll}
                style={{
                  display: 'flex', overflowX: 'auto', scrollSnapType: 'x mandatory',
                  gap: 10, padding: '0 12px 12px',
                  scrollbarWidth: 'none',
                }}
              >
                {B4_HOTELS.map(h => (
                  <Box key={h.id} style={{ flex: '0 0 calc(100% - 24px)', scrollSnapAlign: 'start' }}>
                    <HotelCard hotel={h} nights={10} onSelect={noop} />
                  </Box>
                ))}
              </Box>
              {canRight && (
                <UnstyledButton onClick={() => scroll('right')} style={{ ...ARROW_BTN, right: 6 }}>
                  <svg viewBox="0 0 24 24" width={14} height={14} fill="none" stroke="#2A2F5F" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 18l6-6-6-6" />
                  </svg>
                </UnstyledButton>
              )}
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
}

// ── Meta ──────────────────────────────────────────────────────────────────────

const meta: Meta = {
  title: 'Hotels/HotelsPage',
  parameters: { layout: 'fullscreen' },
};

export default meta;
type Story = StoryObj;

// ── Desktop ───────────────────────────────────────────────────────────────────

export const DesktopResultsPopulated: Story = {
  name: 'Desktop · results populated',
  render: () => <DesktopLayout />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByText('Hotel Avenida Palace')).toBeInTheDocument();
      expect(canvas.getByText('Memmo Alfama')).toBeInTheDocument();
      expect(canvas.getByText('Corinthia Lisbon')).toBeInTheDocument();
      expect(canvas.getByText('Lisboa Central Boutique')).toBeInTheDocument();
    });
  },
};

// ── Mobile ────────────────────────────────────────────────────────────────────

const mobile = { viewport: { defaultViewport: 'mobile1' } };

export const B1MapSheet: Story = {
  name: 'Mobile · B1 · Map + sheet (50/50)',
  parameters: mobile,
  render: () => <B1Layout />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByText('Hotel Avenida Palace')).toBeInTheDocument();
      expect(canvas.getByText('Memmo Alfama')).toBeInTheDocument();
      expect(canvas.getByText('48 hotels in Lisbon')).toBeInTheDocument();
    });
  },
};

export const B2Minimized: Story = {
  name: 'Mobile · B2 · Sheet minimized',
  parameters: mobile,
  render: () => <B2Layout />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByText('48 hotels in Lisbon')).toBeInTheDocument();
    });
  },
};

export const B3FullList: Story = {
  name: 'Mobile · B3 · Full list',
  parameters: mobile,
  render: () => <B3Layout />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByText('Hotel Avenida Palace')).toBeInTheDocument();
      expect(canvas.getByText('Memmo Alfama')).toBeInTheDocument();
      expect(canvas.getByText('Corinthia Lisbon')).toBeInTheDocument();
      expect(canvas.getByText('48 hotels found')).toBeInTheDocument();
    });
  },
};

export const B4PinTapped: Story = {
  name: 'Mobile · B4 · Pin tapped · overlay',
  parameters: mobile,
  render: () => <B4Layout />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByText('Hotel Avenida Palace')).toBeInTheDocument();
    });
  },
};
