import { useState, useCallback } from 'react';
import { Box, Group, Text, UnstyledButton } from '@mantine/core';
import { zIndex } from '@/theme';
import { useMediaQuery } from '@mantine/hooks';
import { APIProvider } from '@vis.gl/react-google-maps';
import { HotelMobileMapView } from '../HotelMobileMapView';
import type { HotelMapPin } from '../HotelMobileMapView';
import { HotelPinCard } from '../HotelPinCard';
import type { HotelPinCardData } from '../HotelPinCard';
import { HotelSortFilterBar } from '../HotelSortFilterBar';
import type { HotelSortFilterBarProps } from '../HotelSortFilterBar';

// Future-use: not yet wired into HotelSearchPage; currently only rendered in Storybook stories.
// ─── Types ────────────────────────────────────────────────────────────────────

export interface HotelFullMapPin extends HotelMapPin {
  area?: string;
  stars?: number;
  reviewScore?: number;
  reviewCount?: number;
  reviewLabel?: string;
  totalPrice?: string;
  thumbnail?: string;
}

export interface HotelsFullMapViewProps {
  hotels: HotelFullMapPin[];
  /** Total result count shown in the List pill and mobile top bar. */
  count: number;
  onClose: () => void;
  onViewDetails?: (id: string) => void;
  sortValues?: HotelSortFilterBarProps['sortValues'];
  onOpenFiltersPanel?: () => void;
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function IconSortLines() {
  return (
    <svg viewBox="0 0 24 24" width={14} height={14} fill="none" stroke="#2A2F5F" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h13"/><path d="M3 12h9"/><path d="M3 18h5"/>
      <path d="m16 16 4 4 4-4"/><path d="M20 4v16"/>
    </svg>
  );
}

function IconFunnel() {
  return (
    <svg viewBox="0 0 24 24" width={14} height={14} fill="none" stroke="#2A2F5F" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
    </svg>
  );
}

function IconList() {
  return (
    <svg viewBox="0 0 24 24" width={15} height={15} fill="none" stroke="white" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18"/><path d="M3 12h18"/><path d="M3 18h18"/>
    </svg>
  );
}

// ─── Mobile slim top bar ──────────────────────────────────────────────────────

function MobileTopBar({ count, onOpenFiltersPanel }: { count: number; onOpenFiltersPanel?: () => void }) {
  const iconBtnStyle = {
    width: 32,
    height: 32,
    borderRadius: '50%' as const,
    border: '1px solid #E4E6F5',
    background: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  return (
    <Group
      px={14}
      py={10}
      justify="space-between"
      align="center"
      style={{ background: 'white', borderBottom: '1px solid #E4E6F5', flexShrink: 0 }}
    >
      <Text style={{ fontSize: 18, fontWeight: 700, color: '#2A2F5F', letterSpacing: '-0.01em' }}>
        Hotels{' '}
        <Text span style={{ fontSize: 13, fontWeight: 500, color: '#636e9d' }}>
          · {count} on map
        </Text>
      </Text>

      <Group gap={6}>
        <UnstyledButton style={iconBtnStyle} aria-label="Sort">
          <IconSortLines />
        </UnstyledButton>
        <UnstyledButton style={iconBtnStyle} aria-label="Filter" onClick={onOpenFiltersPanel}>
          <IconFunnel />
        </UnstyledButton>
      </Group>
    </Group>
  );
}

// ─── Floating "≡ List [N]" pill ───────────────────────────────────────────────

function FloatingListPill({ count, onClick }: { count: number; onClick: () => void }) {
  return (
    <Box
      style={{
        position: 'absolute',
        bottom: 16,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 20,
        pointerEvents: 'auto',
      }}
    >
      <UnstyledButton
        onClick={onClick}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '11px 20px',
          background: '#2A2F5F',
          color: 'white',
          borderRadius: 9999,
          fontSize: 14,
          fontWeight: 600,
          boxShadow: '0 4px 16px rgba(42,47,95,0.4)',
          whiteSpace: 'nowrap',
        }}
      >
        <IconList />
        List
        <Box
          component="span"
          style={{
            background: 'white',
            color: '#2A2F5F',
            padding: '1px 7px',
            borderRadius: 9999,
            fontSize: 11,
            fontWeight: 700,
            marginLeft: 4,
          }}
        >
          {count}
        </Box>
      </UnstyledButton>
    </Box>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function HotelsFullMapView({
  hotels,
  count,
  onClose,
  onViewDetails,
  sortValues,
  onOpenFiltersPanel,
}: HotelsFullMapViewProps) {
  const isMobile = useMediaQuery('(max-width: 767px)') ?? false;

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewedIds, setViewedIds] = useState<string[]>([]);
  const [showSearchPill, setShowSearchPill] = useState(false);

  const handlePinTap = useCallback(
    (id: string | null) => {
      if (id && !viewedIds.includes(id)) setViewedIds((prev) => [...prev, id]);
      setSelectedId(id);
      if (id) setShowSearchPill(false);
    },
    [viewedIds],
  );

  const handleClose = useCallback(() => {
    setSelectedId(null);
  }, []);

  const selectedHotel = selectedId ? hotels.find((h) => h.id === selectedId) : null;

  const pinCardData: HotelPinCardData | null = selectedHotel
    ? {
        id: selectedHotel.id,
        name: selectedHotel.name,
        area: selectedHotel.area ?? '',
        stars: selectedHotel.stars ?? 4,
        reviewScore: selectedHotel.reviewScore ?? 0,
        reviewCount: selectedHotel.reviewCount ?? 0,
        reviewLabel: selectedHotel.reviewLabel ?? '',
        pricePerNight: selectedHotel.price,
        totalPrice: selectedHotel.totalPrice ?? '',
        thumbnail: selectedHotel.thumbnail,
      }
    : null;

  const mapPins: HotelMapPin[] = hotels;

  const outerStyle: React.CSSProperties = isMobile
    ? {
        position: 'fixed',
        inset: 0,
        zIndex: zIndex.mapOverlay,
        display: 'flex',
        flexDirection: 'column',
        background: 'white',
      }
    : {
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        overflow: 'hidden',
      };

  const mapsApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;

  const content = (
    <Box style={outerStyle}>
      {isMobile ? (
        <MobileTopBar count={count} onOpenFiltersPanel={onOpenFiltersPanel} />
      ) : (
        <HotelSortFilterBar sortValues={sortValues} onOpenFiltersPanel={onOpenFiltersPanel} />
      )}

      <Box style={{ flex: 1, position: 'relative', minHeight: 0 }}>
        <HotelMobileMapView
          hotels={mapPins}
          selectedId={selectedId}
          viewedIds={viewedIds}
          onPinTap={handlePinTap}
          onPan={() => setShowSearchPill(true)}
          showSearchPill={showSearchPill}
          onSearchThisArea={() => setShowSearchPill(false)}
          height="100%"
        />

        {pinCardData && (
          <HotelPinCard
            hotel={pinCardData}
            onClose={handleClose}
            onViewDetails={() => { if (selectedId) onViewDetails?.(selectedId); }}
          />
        )}

        {!pinCardData && <FloatingListPill count={count} onClick={onClose} />}
      </Box>
    </Box>
  );

  return mapsApiKey ? <APIProvider apiKey={mapsApiKey}>{content}</APIProvider> : content;
}
