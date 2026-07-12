import { Box, Group, Text } from '@mantine/core';
import { Check } from 'lucide-react';

import {
  HOTEL_BOOKING_DETAILS_FF,
  hotelBookingDetailsPalette as palette,
} from './hotelBookingDetailsPanel.theme';

export function HotelBookingDetailsPanelSuccessHeader({ headlineCity }: { headlineCity: string }) {
  return (
    <Group align="center" gap="md" wrap="wrap" style={{ flexShrink: 0 }}>
      <Box
        style={{
          width: 50,
          height: 50,
          borderRadius: 40,
          backgroundColor: palette.successGreenBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <Box
          style={{
            width: 36,
            height: 36,
            borderRadius: 40,
            backgroundColor: palette.successGreen,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Check size={22} color="white" />
        </Box>
      </Box>
      <Text
        component="span"
        style={{
          margin: 0,
          display: 'block',
          minWidth: 0,
          flex: '1 1 200px',
          fontFamily: HOTEL_BOOKING_DETAILS_FF,
          fontSize: '1.75rem',
          fontWeight: 700,
          lineHeight: '36px',
          color: palette.headline,
        }}
      >
        {`You're booked! ${headlineCity} awaits`}
      </Text>
    </Group>
  );
}
