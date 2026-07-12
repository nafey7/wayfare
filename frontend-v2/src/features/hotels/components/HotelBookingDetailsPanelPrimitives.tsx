import type { CSSProperties, ReactNode } from 'react';
import { Box, Group, Stack, Text } from '@mantine/core';
import { User } from 'lucide-react';

import type { HotelGuestPassengerRow } from '@/features/hotels/utils/hotelBookingDetailsUtils';
import {
  HOTEL_BOOKING_DETAILS_FF,
  hotelBookingDetailsPalette as palette,
} from './hotelBookingDetailsPanel.theme';

const baseLabelStyle: CSSProperties = {
  margin: 0,
  display: 'block',
  fontFamily: HOTEL_BOOKING_DETAILS_FF,
  fontSize: 12,
  fontWeight: 600,
  lineHeight: '16px',
  letterSpacing: '0.1px',
  color: 'var(--mantine-color-dimmed)',
};

const valueStyle: CSSProperties = {
  margin: 0,
  display: 'block',
  fontFamily: HOTEL_BOOKING_DETAILS_FF,
  fontSize: '1rem',
  fontWeight: 600,
  lineHeight: '20px',
  color: palette.text,
};

export function TextLabel({
  children,
  style = {},
}: {
  children: ReactNode;
  style?: CSSProperties;
}) {
  return <span style={{ ...baseLabelStyle, ...style }}>{children}</span>;
}

export function TextCapsLabel({ children }: { children: ReactNode }) {
  return (
    <TextLabel style={{ letterSpacing: '1.1px', textTransform: 'uppercase' }}>
      {children}
    </TextLabel>
  );
}

export function PassengerListItem({ row }: { row: HotelGuestPassengerRow }) {
  return (
    <Box
      style={{
        backgroundColor: 'white',
        border: `1px solid ${palette.cardBorder}`,
        borderRadius: 14,
        padding: '13px 17px',
        width: '100%',
        minWidth: 0,
      }}
    >
      <Group align="flex-start" gap="md" wrap="wrap" style={{ width: '100%' }}>
        <Group align="flex-start" gap="sm" wrap="nowrap" style={{ minWidth: 0, flexShrink: 0 }}>
          <Box style={{ display: 'flex', justifyContent: 'center', padding: 3, width: 36, flexShrink: 0 }}>
            <Box
              style={{
                backgroundColor: palette.iconLightBg,
                borderRadius: 8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 6,
              }}
            >
              <User size={18} color={palette.base} />
            </Box>
          </Box>

          <Stack gap={2} style={{ minWidth: 0, flex: '0 1 auto' }}>
            <Box pb={2}>
              <TextLabel>{row.roleLabel}</TextLabel>
            </Box>
            <Text component="span" style={valueStyle}>
              {row.fullName}
            </Text>
          </Stack>
        </Group>

        {row.dob ? (
          <Stack gap={2} style={{ minWidth: 116 }}>
            <Box pb={2}>
              <TextCapsLabel>DOB</TextCapsLabel>
            </Box>
            <Text component="span" style={valueStyle}>
              {row.dob}
            </Text>
          </Stack>
        ) : null}

        {row.nationality ? (
          <Stack gap={2} style={{ minWidth: 116 }}>
            <Box pb={2}>
              <TextCapsLabel>Nationality</TextCapsLabel>
            </Box>
            <Text component="span" style={valueStyle}>
              {row.nationality}
            </Text>
          </Stack>
        ) : null}

        {row.passportLines && row.passportLines.length > 0 ? (
          <Stack gap={2} style={{ minWidth: 179, maxWidth: 220 }}>
            <Box pb={2}>
              <TextCapsLabel>Passport</TextCapsLabel>
            </Box>
            <Stack gap={0}>
              {row.passportLines.map((line, i) => (
                <Text key={i} component="span" style={{ ...valueStyle, whiteSpace: 'pre-wrap' }}>
                  {line}
                </Text>
              ))}
            </Stack>
          </Stack>
        ) : null}

        {row.contactLines && row.contactLines.length > 0 ? (
          <Stack gap={2} style={{ minWidth: 177, flex: 1 }}>
            <Box pb={2}>
              <TextCapsLabel>Contact Info</TextCapsLabel>
            </Box>
            <Stack gap={0}>
              {row.contactLines.map((line, i) => (
                <Text key={i} component="span" style={valueStyle}>
                  {line}
                </Text>
              ))}
            </Stack>
          </Stack>
        ) : null}
      </Group>
    </Box>
  );
}
