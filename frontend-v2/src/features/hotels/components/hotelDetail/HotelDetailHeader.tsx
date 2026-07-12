import { Box, Title } from '@mantine/core';

import { HOTEL_DETAIL_TOKENS } from './hotelDetailTokens';

export interface HotelDetailHeaderProps {
  hotelName?: string;
}

export function HotelDetailHeader({ hotelName = '' }: HotelDetailHeaderProps) {
  return (
    <Box style={{ width: '100%' }}>
      <Title
        order={1}
        m={0}
        fw={700}
        style={{ fontSize: 24, lineHeight: '32px', color: HOTEL_DETAIL_TOKENS.textColor }}
      >
        {hotelName}
      </Title>
    </Box>
  );
}
