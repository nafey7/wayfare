import { useState } from 'react';

import { Box, Button, Stack, Text, Title, Tooltip } from '@mantine/core';
import type { LucideIcon } from 'lucide-react';

import { HOTEL_DETAIL_TOKENS } from './hotelDetailTokens';

const ICON_COLUMN_PX = 20;
const DEFAULT_VISIBLE_COUNT = 6;

const chipStyle: React.CSSProperties = {
  backgroundColor: 'var(--mantine-color-body)',
  borderRadius: 24,
  boxSizing: 'border-box',
  height: 'auto',
  margin: 0,
  padding: '7px 12px',
  gap: 6,
  width: 220,
  maxWidth: '100%',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'flex-start',
  border: '1px solid var(--mantine-color-default-border)',
  cursor: 'default',
};

const iconColumnStyle: React.CSSProperties = {
  flexShrink: 0,
  width: ICON_COLUMN_PX,
  minWidth: ICON_COLUMN_PX,
  maxWidth: ICON_COLUMN_PX,
  height: ICON_COLUMN_PX,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'var(--mantine-color-dark-8)',
};

const chipLabelStyle: React.CSSProperties = {
  flex: '1 1 0%',
  margin: 0,
  padding: 0,
  minWidth: 0,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  fontSize: 13,
  fontWeight: 500,
  lineHeight: '18px',
  color: 'var(--mantine-color-dark-8)',
  textAlign: 'left',
};

export interface HotelAmenityItem {
  id: string;
  label: string;
  Icon: LucideIcon;
}

function AmenityChip({ label, Icon }: Pick<HotelAmenityItem, 'label' | 'Icon'>) {
  return (
    <Tooltip label={label} position="top" openDelay={300} withArrow>
      <div style={chipStyle}>
        <span style={iconColumnStyle}>
          <Icon size={16} />
        </span>
        <span style={chipLabelStyle}>{label}</span>
      </div>
    </Tooltip>
  );
}

export interface HotelAmenitiesProps {
  title?: string;
  columnOneItems?: readonly HotelAmenityItem[];
  columnTwoItems?: readonly HotelAmenityItem[];
  totalAmenityCount?: number;
}

/**
 * Amenities block — two-column grid of icon chips with expand/collapse.
 * Merges columnOneItems + columnTwoItems into a flat list rendered via CSS grid.
 */
export function HotelAmenities({
  title = 'Amenities',
  columnOneItems = [],
  columnTwoItems = [],
  totalAmenityCount = 0,
}: HotelAmenitiesProps) {
  const [expanded, setExpanded] = useState(false);

  const allItems = [...columnOneItems, ...columnTwoItems];
  const hasAny = allItems.length > 0;
  const canExpand = allItems.length > DEFAULT_VISIBLE_COUNT;
  const visibleItems = expanded || !canExpand ? allItems : allItems.slice(0, DEFAULT_VISIBLE_COUNT);
  const displayCount = totalAmenityCount > 0 ? totalAmenityCount : allItems.length;

  return (
    <Stack gap="md" align="flex-start" style={{ width: '100%' }}>
      <Title order={2} m={0} fw={700} style={{ fontSize: 28, lineHeight: '36px' }}>
        {title}
      </Title>

      {!hasAny ? (
        <Text size="sm" c="dimmed">
          No amenities listed for this property.
        </Text>
      ) : (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 8,
            width: '100%',
          }}
        >
          {visibleItems.map((item) => (
            <AmenityChip key={item.id} label={item.label} Icon={item.Icon} />
          ))}
        </div>
      )}

      {hasAny && canExpand ? (
        <Box style={{ width: '100%' }}>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setExpanded((prev) => !prev)}
            tt="none"
            radius="md"
            styles={{
              root: {
                minWidth: 102,
                height: 40,
                padding: '8px 16px',
                borderColor: HOTEL_DETAIL_TOKENS.baseColor,
                color: HOTEL_DETAIL_TOKENS.baseColor,
                fontSize: 16,
                fontWeight: 500,
                fontFamily: HOTEL_DETAIL_TOKENS.fontFamily.body,
              },
            }}
          >
            {expanded ? 'Show less' : `Show all ${displayCount} amenities`}
          </Button>
        </Box>
      ) : null}
    </Stack>
  );
}
