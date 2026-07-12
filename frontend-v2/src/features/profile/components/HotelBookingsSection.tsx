import { Alert, Box, Button, Group, Loader, Stack, Text } from '@mantine/core';
import { Link as RouterLink } from 'react-router-dom';
import { useGetMyHotelBookingsQuery } from '@/api/hotelsApi';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import { ROUTES } from '@/features/routing/constants';
import { ProfileHotelBookingCard } from '@/features/profile/components/bookings/ProfileHotelBookingCard';
import { mapHotelMyBookingToRow } from '@/features/profile/components/bookings/mapHotelBookingEvent';

const LIMIT = 20;

export function HotelBookingsSection() {
  const { data, isLoading, isError, refetch } = useGetMyHotelBookingsQuery({ limit: LIMIT });
  const count = data?.length;
  const title =
    count != null && !isLoading && !isError ? `Hotel bookings (${count})` : 'Hotel bookings';

  return (
    <Stack gap={0}>
      <Text
        style={{
          fontFamily: LANDING_TOKENS.fontFamily.display,
          fontWeight: 700,
          fontSize: 28,
          lineHeight: '36px',
          color: LANDING_TOKENS.textColor,
          margin: 0,
          display: 'block',
          padding: '10px 16px',
        }}
      >
        {title}
      </Text>
      {isLoading ? (
        <Group justify="center" py="lg" px="md">
          <Loader size={28} />
        </Group>
      ) : isError ? (
        <Box px="md">
          <Stack gap="xs">
            <Alert color="red">Could not load hotel bookings.</Alert>
            <Button variant="outline" size="xs" tt="none" onClick={() => void refetch()}>
              Retry
            </Button>
          </Stack>
        </Box>
      ) : !data?.length ? (
        <Stack gap="md" align="flex-start" px="md">
          <Text
            style={{
              fontSize: 15,
              color: LANDING_TOKENS.textHighlight,
              fontFamily: LANDING_TOKENS.fontFamily.display,
            }}
          >
            No hotel bookings yet. Plan a trip in chat.
          </Text>
          <Button component={RouterLink} to={ROUTES.CHAT} size="xs" tt="none">
            Open chat
          </Button>
        </Stack>
      ) : (
        <Stack gap="md" px="md" role="region" aria-label="Hotel bookings">
          {data.map((item, index) => (
            <ProfileHotelBookingCard
              key={`${item.voyaBookingReference ?? `idx-${index}`}-${item.timestamp}`}
              row={mapHotelMyBookingToRow(item)}
            />
          ))}
        </Stack>
      )}
    </Stack>
  );
}
