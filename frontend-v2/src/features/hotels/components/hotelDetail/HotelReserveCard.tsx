import { Box, Divider, Group, Stack, Text, UnstyledButton } from '@mantine/core';
import { Calendar } from 'lucide-react';

import { HOTEL_DETAIL_TOKENS } from './hotelDetailTokens';

export interface HotelReserveCardProps {
  checkInDate?: string;
  checkOutDate?: string;
  /** e.g. "1 room・2 adults" */
  roomsAndGuestsLabel?: string;
  /** Total for one rate, or min–max when several rates (see `priceSectionTitle`). */
  priceRangeLabel?: string;
  /** Shown above the price line: use "Price range:" when multiple room rates, "Price:" for a single rate. */
  priceSectionTitle?: string;
  /** Entire bordered block — dates + rooms (change booking details). */
  onEditDetails?: () => void;
}

const labelStyle: React.CSSProperties = {
  fontSize: 18,
  fontWeight: 700,
  lineHeight: '25px',
  letterSpacing: '0.15px',
  color: HOTEL_DETAIL_TOKENS.textColor,
  textAlign: 'left',
  margin: 0,
  display: 'block',
};

const valueStyle: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 400,
  lineHeight: '21px',
  letterSpacing: '0.1px',
  color: HOTEL_DETAIL_TOKENS.textColor,
  margin: 0,
  display: 'block',
};

/**
 * Dates, guests, and price summary for the hotel detail layout.
 */
export function HotelReserveCard({
  checkInDate = '—',
  checkOutDate = '—',
  roomsAndGuestsLabel = '—',
  priceRangeLabel = '—',
  priceSectionTitle = 'Price range:',
  onEditDetails,
}: HotelReserveCardProps) {
  return (
    <Stack
      gap={33}
      align="flex-start"
      p={24}
      style={{
        backgroundColor: 'var(--mantine-color-body)',
        borderRadius: 24,
        boxShadow: HOTEL_DETAIL_TOKENS.reserveCardShadow,
        width: '100%',
        maxWidth: '100%',
        minWidth: 0,
        boxSizing: 'border-box',
      }}
    >
      <UnstyledButton
        onClick={onEditDetails}
        style={{
          padding: 8,
          borderRadius: 24,
          border: `1px solid ${HOTEL_DETAIL_TOKENS.neutralHighlight}`,
          width: '100%',
          display: 'block',
          color: 'inherit',
        }}
      >
        <Stack gap={8} align="stretch" style={{ width: '100%' }}>
          <Group align="stretch" gap={0} wrap="nowrap" style={{ minHeight: 76, width: '100%' }}>
            <Stack gap={10} px="md" py="md" style={{ flex: 1, minWidth: 0, justifyContent: 'center', alignItems: 'flex-start' }}>
              <Group align="center" gap={10} style={{ width: '100%' }}>
                <Calendar size={24} color={HOTEL_DETAIL_TOKENS.textColor} />
                <span style={{ ...labelStyle, flex: 1 }}>Check-in</span>
              </Group>
              <span style={{ ...valueStyle, width: '100%', textAlign: 'center' }}>{checkInDate}</span>
            </Stack>

            <Divider
              orientation="vertical"
              style={{
                alignSelf: 'center',
                borderColor: HOTEL_DETAIL_TOKENS.neutralHighlight,
                height: 58,
              }}
            />

            <Stack gap={10} px="md" py="md" style={{ flex: 1, minWidth: 0, justifyContent: 'center', alignItems: 'center' }}>
              <Group align="center" gap={10} style={{ width: '100%' }}>
                <Calendar size={24} color={HOTEL_DETAIL_TOKENS.textColor} />
                <span style={{ ...labelStyle, flex: 1 }}>Check-out</span>
              </Group>
              <span style={{ ...valueStyle, width: '100%', textAlign: 'center' }}>{checkOutDate}</span>
            </Stack>
          </Group>

          <Divider style={{ borderColor: HOTEL_DETAIL_TOKENS.neutralHighlight }} />

          <Stack gap={4} px="md" py="xs" style={{ minHeight: 72, justifyContent: 'center', alignItems: 'flex-start', width: '100%' }}>
            <span style={labelStyle}>Rooms and Guests</span>
            <Box py={4}>
              <span style={valueStyle}>{roomsAndGuestsLabel}</span>
            </Box>
          </Stack>
        </Stack>
      </UnstyledButton>

      <Stack gap={8} style={{ width: '100%' }}>
        <Text
          component="span"
          fw={700}
          style={{ fontSize: 22, lineHeight: '28px', color: HOTEL_DETAIL_TOKENS.textPrimary }}
        >
          {priceSectionTitle}
        </Text>
        <Text component="span" style={valueStyle}>
          {priceRangeLabel}
        </Text>
      </Stack>
    </Stack>
  );
}
