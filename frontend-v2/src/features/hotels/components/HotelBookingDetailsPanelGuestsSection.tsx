import { Box, Stack, Text } from '@mantine/core';

import type { HotelGuestPassengerRow } from '@/features/hotels/utils/hotelBookingDetailsUtils';
import { HOTEL_BOOKING_DETAILS_FF, hotelBookingDetailsPalette as palette } from './hotelBookingDetailsPanel.theme';
import { PassengerListItem } from './HotelBookingDetailsPanelPrimitives';

export function HotelBookingDetailsPanelGuestsSection({ guests }: { guests: HotelGuestPassengerRow[] }) {
  return (
    <Box
      p="md"
      style={{
        border: `1px solid ${palette.neutralBorder}`,
        borderRadius: 16,
        width: '100%',
        minWidth: 0,
      }}
    >
      <Stack gap="md">
        <Text
          component="span"
          style={{
            margin: 0,
            display: 'block',
            width: '100%',
            fontFamily: HOTEL_BOOKING_DETAILS_FF,
            fontSize: '1.375rem',
            fontWeight: 700,
            lineHeight: '28px',
            color: 'black',
          }}
        >
          Passenger Information
        </Text>
        <Stack gap="md">
          {guests.map((g, idx) => (
            <PassengerListItem key={`${g.roleLabel}-${idx}`} row={g} />
          ))}
        </Stack>
      </Stack>
    </Box>
  );
}
