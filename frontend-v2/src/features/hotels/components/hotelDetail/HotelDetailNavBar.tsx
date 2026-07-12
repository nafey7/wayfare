import { useState } from 'react';
import { Box, Group, UnstyledButton } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';

import { HOTEL_DETAIL_TOKENS } from './hotelDetailTokens';

/** Section ids — use matching `id` on scroll targets in the hotel detail layout. */
export const HOTEL_DETAIL_NAV_SECTION_IDS = {
  overview: 'hotel-detail-section-overview',
  /** Scroll target for gallery / "more photos" (not a nav tab). */
  photos: 'hotel-detail-section-photos',
  amenities: 'hotel-detail-section-amenities',
  location: 'hotel-detail-section-location',
  rooms: 'hotel-detail-section-rooms',
} as const;

export type HotelDetailNavSectionId =
  (typeof HOTEL_DETAIL_NAV_SECTION_IDS)[keyof typeof HOTEL_DETAIL_NAV_SECTION_IDS];

const NAV_ITEMS: { id: HotelDetailNavSectionId; label: string }[] = [
  { id: HOTEL_DETAIL_NAV_SECTION_IDS.overview, label: 'Overview' },
  { id: HOTEL_DETAIL_NAV_SECTION_IDS.amenities, label: 'Amenities' },
  { id: HOTEL_DETAIL_NAV_SECTION_IDS.location, label: 'Location' },
  { id: HOTEL_DETAIL_NAV_SECTION_IDS.rooms, label: 'Rooms' },
];

/** Same order as tabs — use for scroll-spy (`HotelDetailPage`). */
export const HOTEL_DETAIL_NAV_SCROLL_IDS: readonly HotelDetailNavSectionId[] = NAV_ITEMS.map(
  (item) => item.id,
);

export interface HotelDetailNavBarProps {
  activeSectionId: HotelDetailNavSectionId;
  onNavigate: (sectionId: HotelDetailNavSectionId) => void;
}

/**
 * Horizontal tabs with active underline on a full-width bottom rule.
 */
export function HotelDetailNavBar({ activeSectionId, onNavigate }: HotelDetailNavBarProps) {
  const isMd = useMediaQuery('(min-width: 768px)') ?? false;
  const isSm = useMediaQuery('(min-width: 600px)') ?? false;
  const fontSize = isMd ? 18 : isSm ? 15 : 13;
  const lineHeight = isMd ? '25px' : isSm ? '21px' : '18px';

  return (
    <Group
      align="flex-end"
      gap="md"
      wrap="nowrap"
      pt="md"
      style={{
        backgroundColor: 'var(--mantine-color-body)',
        borderBottom: `1px solid ${HOTEL_DETAIL_TOKENS.textHighlight}`,
        width: '100%',
        overflowX: 'auto',
        WebkitOverflowScrolling: 'touch',
      }}
    >
      {NAV_ITEMS.map((item) => {
        const isActive = activeSectionId === item.id;
        return (
          <NavBarTab
            key={item.id}
            label={item.label}
            isActive={isActive}
            onClick={() => onNavigate(item.id)}
            fontSize={fontSize}
            lineHeight={lineHeight}
          />
        );
      })}
    </Group>
  );
}

interface NavBarTabProps {
  label: string;
  isActive: boolean;
  onClick: () => void;
  fontSize: number;
  lineHeight: string;
}

function NavBarTab({ label, isActive, onClick, fontSize, lineHeight }: NavBarTabProps) {
  const [hovered, setHovered] = useState(false);
  const inactiveColor = hovered
    ? HOTEL_DETAIL_TOKENS.navInactiveHover
    : HOTEL_DETAIL_TOKENS.navInactive;
  const color = isActive ? HOTEL_DETAIL_TOKENS.baseColor : inactiveColor;

  return (
    <UnstyledButton
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-end',
        color,
      }}
    >
      <span
        style={{
          fontSize,
          fontWeight: 700,
          lineHeight,
          letterSpacing: '0.15px',
          fontFamily: HOTEL_DETAIL_TOKENS.fontFamily.display,
          color: 'inherit',
          display: 'block',
        }}
      >
        {label}
      </span>
      <Box
        mt="md"
        style={{
          height: 3,
          width: '100%',
          backgroundColor: isActive ? HOTEL_DETAIL_TOKENS.baseColor : 'transparent',
        }}
      />
    </UnstyledButton>
  );
}
