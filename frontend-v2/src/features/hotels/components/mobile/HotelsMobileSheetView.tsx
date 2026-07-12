import { useState, useCallback, useEffect, useMemo } from 'react';
import { Box, UnstyledButton } from '@mantine/core';
import { SlidersHorizontal } from 'lucide-react';
import { zIndex } from '@/theme';
import { APIProvider } from '@vis.gl/react-google-maps';
import { motion, useMotionValue, animate, useDragControls } from 'framer-motion';
import type { PanInfo } from 'framer-motion';
import type { Hotel, HotelItinerary } from '@/types/hotels';
import { hasValidCoords, getPosition, getHotelKey } from '@/features/hotels/utils/hotelMapCoords';
import { getHotelTotal, getHotelCurrency, hotelCurrencySymbol } from '@/features/hotels/utils/hotelFilters';
import { getHotelThumbnailUrl } from '@/features/hotels/utils/imageUtils';
import type { HotelSortOption } from '@/features/hotels/utils/hotelSort';
import { MobileSortToolbar } from '@/components/layout/MobileSortToolbar';
import { HotelCard } from '../HotelCard';
import { HotelMobileMapView } from '../HotelMobileMapView';
import type { HotelMapPin } from '../HotelMobileMapView';
import { HotelPinCard } from '../HotelPinCard';
import type { HotelPinCardData } from '../HotelPinCard';

// ─── Types ────────────────────────────────────────────────────────────────────

type SheetState = 'peek' | 'half' | 'full';

// BottomNav (48px) + ChatSheet resting (44px) = 92px of viewport chrome that covers the sheet.
const FIXED_BOTTOM_CHROME = 92;
const DRAG_HANDLE_AND_HEADER = 88; // drag handle + first row of pin card
const PEEK_H = FIXED_BOTTOM_CHROME + DRAG_HANDLE_AND_HEADER;
const HALF_H = 300;

export interface HotelsMobileSheetViewProps {
  hotels: (Hotel | HotelItinerary)[];
  nights: number;
  selectingTokenId: string | null;
  onHotelSelect: (hotel: Hotel | HotelItinerary) => void;
  onOpenFilters: () => void;
  activeFilterCount: number;
  sortBy: HotelSortOption;
  onSortChange: (value: HotelSortOption) => void;
  sortMenuItems: { value: HotelSortOption; label: string }[];
  onChangePreferences: () => void;
  /** Y-offset from viewport top (navbar + search bar height) so the overlay starts below them. */
  topOffset?: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtPerNight(hotel: Hotel | HotelItinerary, nights: number): string {
  const symbol = hotelCurrencySymbol(getHotelCurrency(hotel));
  const total = getHotelTotal(hotel);
  const perNight = nights > 0 ? Math.round(total / nights) : Math.round(total);
  return `${symbol}${perNight}`;
}

function toPinCardData(hotel: Hotel | HotelItinerary, nights: number): HotelPinCardData {
  const it = hotel as HotelItinerary;
  const h = hotel as Hotel & { reviewScore?: number; reviewCount?: number };
  const symbol = hotelCurrencySymbol(getHotelCurrency(hotel));
  const total = getHotelTotal(hotel);
  return {
    id: getHotelKey(hotel),
    name: hotel.name ?? '',
    area: it.address ?? it.city ?? '',
    stars: it.starRating ?? 4,
    reviewScore: h.reviewScore ?? 0,
    reviewCount: h.reviewCount ?? 0,
    reviewLabel: '',
    pricePerNight: fmtPerNight(hotel, nights),
    totalPrice: `${symbol}${Math.round(total)}`,
    thumbnail: getHotelThumbnailUrl(hotel),
  };
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function MapLayersIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width={15}
      height={15}
      fill="none"
      stroke="white"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M9 18V6l6 4v12z" />
      <path d="M3 6v12l6-2" />
      <path d="M15 10l6-2v12l-6 2" />
    </svg>
  );
}

// ─── Spring config ─────────────────────────────────────────────────────────────

const SNAP_SPRING = { type: 'spring', stiffness: 400, damping: 40 } as const;

// ─── Component ────────────────────────────────────────────────────────────────

export function HotelsMobileSheetView({
  hotels,
  nights,
  selectingTokenId,
  onHotelSelect,
  onOpenFilters,
  activeFilterCount,
  sortBy,
  onSortChange,
  sortMenuItems,
  onChangePreferences,
  topOffset = 0,
}: HotelsMobileSheetViewProps) {
  const mapsApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;
  const [viewportH, setViewportH] = useState(() => window.visualViewport?.height ?? window.innerHeight);

  // Recalculate snaps when the virtual keyboard opens/closes on mobile.
  useEffect(() => {
    const handler = () => setViewportH(window.visualViewport?.height ?? window.innerHeight);
    window.visualViewport?.addEventListener('resize', handler);
    return () => window.visualViewport?.removeEventListener('resize', handler);
  }, []);

  // Snap positions as y-transform values (0 = top of container = full height visible).
  // The sheet div is position:absolute top:0 bottom:0 within the fixed container,
  // so translateY(availH - HALF_H) reveals only the bottom HALF_H pixels.
  const snaps = useMemo(() => {
    const availH = viewportH - topOffset;
    return {
      full: 0,
      half: Math.max(0, availH - HALF_H),
      peek: Math.max(0, availH - PEEK_H),
    };
  }, [viewportH, topOffset]);

  const y = useMotionValue(snaps.half);
  const dragControls = useDragControls();

  const [sheetState, setSheetState] = useState<SheetState>('half');
  const [selectedPin, setSelectedPin] = useState<Hotel | HotelItinerary | null>(null);
  const [viewedIds, setViewedIds] = useState<string[]>([]);

  const snapTo = useCallback(
    (targetY: number, state: SheetState) => {
      animate(y, targetY, SNAP_SPRING);
      setSheetState(state);
    },
    [y]
  );

  const handleDragEnd = useCallback(
    (_: unknown, info: PanInfo) => {
      // Ignore taps (tiny movement) — onClick on the handle area handles those.
      if (Math.abs(info.offset.y) < 8) return;

      const current = y.get();
      const vel = info.velocity.y;

      let targetY: number;
      let state: SheetState;

      if (vel > 500) {
        // Flick down — go to next lower snap
        if (current < snaps.half) { targetY = snaps.half; state = 'half'; }
        else { targetY = snaps.peek; state = 'peek'; }
      } else if (vel < -500) {
        // Flick up — go to next higher snap
        if (current > snaps.half) { targetY = snaps.half; state = 'half'; }
        else { targetY = snaps.full; state = 'full'; }
      } else {
        // Snap to nearest by position
        const points: [number, SheetState][] = [
          [snaps.full, 'full'],
          [snaps.half, 'half'],
          [snaps.peek, 'peek'],
        ];
        [targetY, state] = points.reduce((a, b) =>
          Math.abs(b[0] - current) < Math.abs(a[0] - current) ? b : a
        );
      }

      snapTo(targetY, state);
    },
    [y, snaps, snapTo]
  );

  // Tap on the drag-handle zone cycles through states.
  const handleHandleClick = useCallback(() => {
    if (sheetState === 'peek') snapTo(snaps.half, 'half');
    else if (sheetState === 'half') snapTo(snaps.full, 'full');
    else snapTo(snaps.half, 'half');
  }, [sheetState, snaps, snapTo]);

  const hotelsWithCoords = useMemo(() => hotels.filter(hasValidCoords), [hotels]);

  const mapPins: HotelMapPin[] = useMemo(
    () =>
      hotelsWithCoords.map((h) => ({
        id: getHotelKey(h),
        lat: getPosition(h).lat,
        lng: getPosition(h).lng,
        price: fmtPerNight(h, nights),
        name: h.name ?? '',
      })),
    [hotelsWithCoords, nights]
  );

  const hotelByKey = useMemo(
    () => new Map(hotels.map((h) => [getHotelKey(h), h])),
    [hotels]
  );

  const handlePinTap = useCallback(
    (id: string | null) => {
      if (!id) {
        setSelectedPin(null);
        return;
      }
      const hotel = hotelByKey.get(id) ?? null;
      if (hotel && !viewedIds.includes(id)) setViewedIds((prev) => [...prev, id]);
      setSelectedPin(hotel);
    },
    [hotelByKey, viewedIds]
  );

  const selectedPinId = selectedPin ? getHotelKey(selectedPin) : null;
  const pinCardData: HotelPinCardData | null = selectedPin
    ? toPinCardData(selectedPin, nights)
    : null;

  const container = (
    <Box
      style={{
        position: 'fixed',
        top: topOffset,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: zIndex.mobileSheet,
        overflow: 'hidden',
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}
    >
      {/* Map — full background */}
      <HotelMobileMapView
        hotels={mapPins}
        selectedId={selectedPinId}
        viewedIds={viewedIds}
        onPinTap={handlePinTap}
        height="100%"
      />

      {/* Pin card — shown when a pin is tapped */}
      {pinCardData && (
        <HotelPinCard
          key={pinCardData.id}
          hotel={pinCardData}
          bottomInset={FIXED_BOTTOM_CHROME}
          onClose={() => setSelectedPin(null)}
          onViewDetails={() => {
            const hotel = selectedPin;
            setSelectedPin(null);
            if (hotel) onHotelSelect(hotel);
          }}
        />
      )}

      {/* Bottom sheet — full-height div shifted by y transform */}
      {!selectedPin && (
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
            background: 'white',
            borderRadius: '18px 18px 0 0',
            boxShadow: '0 -4px 20px rgba(42,47,95,0.12)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Drag-handle zone: pill + header row — pointer down here starts drag */}
          <Box
            style={{ touchAction: 'none', userSelect: 'none', flexShrink: 0, cursor: 'grab' }}
            onPointerDown={(e) => dragControls.start(e)}
            onClick={handleHandleClick}
          >
            {/* Pill */}
            <Box
              style={{
                display: 'flex',
                justifyContent: 'center',
                padding: '10px 0 6px',
              }}
            >
              <Box style={{ width: 36, height: 4, background: '#d4d8ea', borderRadius: 2 }} />
            </Box>

            {/* Header */}
            <Box
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '2px 14px 10px',
                borderBottom: sheetState !== 'peek' ? '1px solid #E4E6F5' : 'none',
              }}
            >
              <Box>
                <div style={{ fontSize: 15, fontWeight: 700, color: '#2A2F5F' }}>
                  {hotels.length} hotel{hotels.length !== 1 ? 's' : ''} found
                </div>
                {sheetState === 'peek' && (
                  <div style={{ fontSize: 12, color: '#636e9d', marginTop: 1 }}>
                    Swipe up to show list
                  </div>
                )}
                {sheetState === 'half' && (
                  <div style={{ fontSize: 12, color: '#636e9d', marginTop: 1 }}>
                    Swipe up for full list
                  </div>
                )}
              </Box>
              {/* stopPropagation on pointer-down so toolbar taps don't start a drag,
                  and on click so taps don't bubble to the handle's expand/collapse handler */}
              <Box
                onPointerDown={(e) => e.stopPropagation()}
                onClick={(e) => e.stopPropagation()}
              >
                <MobileSortToolbar
                  sortVariant="value"
                  menuItems={sortMenuItems}
                  selectedSort={sortBy}
                  onSortChange={onSortChange}
                  secondaryAction={{
                    label: 'Change preferences',
                    icon: <SlidersHorizontal size={18} />,
                    onClick: onChangePreferences,
                  }}
                  primaryButton={{
                    label: activeFilterCount > 0 ? `Filters (${activeFilterCount})` : 'Filters',
                    onClick: onOpenFilters,
                  }}
                />
              </Box>
            </Box>
          </Box>

          {/* Hotel list — always rendered; sheet overflow:hidden clips it in peek state */}
          <Box style={{ flex: 1, overflowY: 'auto', overscrollBehavior: 'contain', paddingBottom: 16 }}>
            {hotels.map((hotel) => {
              const key = getHotelKey(hotel);
              return (
                <Box key={key} px="xs" pb={4}>
                  <HotelCard
                    hotel={hotel}
                    nights={nights}
                    onSelect={() => onHotelSelect(hotel)}
                    isSelected={selectingTokenId === key}
                  />
                </Box>
              );
            })}

            {/* "Map" pill — floats at bottom in full-list state */}
            {sheetState === 'full' && (
              <Box
                style={{
                  position: 'sticky',
                  bottom: 16,
                  display: 'flex',
                  justifyContent: 'center',
                  pointerEvents: 'none',
                }}
              >
                <UnstyledButton
                  onClick={() => snapTo(snaps.half, 'half')}
                  style={{
                    pointerEvents: 'auto',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 7,
                    padding: '10px 20px',
                    background: '#2A2F5F',
                    color: 'white',
                    borderRadius: 9999,
                    fontSize: 14,
                    fontWeight: 600,
                    boxShadow: '0 4px 14px rgba(42,47,95,0.35)',
                  }}
                >
                  <MapLayersIcon />
                  Map
                </UnstyledButton>
              </Box>
            )}
          </Box>
        </motion.div>
      )}
    </Box>
  );

  return mapsApiKey ? <APIProvider apiKey={mapsApiKey}>{container}</APIProvider> : container;
}
