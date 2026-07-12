import { Box, Group, Text, UnstyledButton } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { zIndex } from '@/theme';
import { MultiDayRouteMap } from '../MultiDayRouteMap';
import type { RouteDay } from '../MultiDayRouteMap';
import { ItinerarySortFilterBar } from '../ItinerarySortFilterBar';
import type { ItinerarySortFilterBarProps } from '../ItinerarySortFilterBar';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ItineraryFullMapViewProps {
  days: RouteDay[];
  /** Number shown in the List pill badge and mobile top bar. */
  count: number;
  center?: { lat: number; lng: number };
  zoom?: number;
  onClose: () => void;
  defaultSort?: ItinerarySortFilterBarProps['defaultSort'];
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

// ─── Mobile slim top bar ───────────────────────────────────────────────────────

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
        Itinerary{' '}
        <Text span style={{ fontSize: 13, fontWeight: 500, color: '#636e9d' }}>
          · {count} {count === 1 ? 'day' : 'days'}
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

/** Full-screen map overlay — set up for a forthcoming full-map mode, not yet used by ItineraryPage. */
export function ItineraryFullMapView({
  days,
  count,
  center,
  zoom,
  onClose,
  defaultSort,
  onOpenFiltersPanel,
}: ItineraryFullMapViewProps) {
  const isMobile = useMediaQuery('(max-width: 899px)') ?? false;

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

  return (
    <Box style={outerStyle}>
      {isMobile ? (
        <MobileTopBar count={count} onOpenFiltersPanel={onOpenFiltersPanel} />
      ) : (
        <ItinerarySortFilterBar
          defaultSort={defaultSort}
          onOpenFiltersPanel={onOpenFiltersPanel}
        />
      )}

      <Box style={{ flex: 1, position: 'relative', minHeight: 0 }}>
        <MultiDayRouteMap
          days={days}
          center={center}
          zoom={zoom}
          height="100%"
          hideLegend={isMobile}
        />

        <FloatingListPill count={count} onClick={onClose} />
      </Box>
    </Box>
  );
}
