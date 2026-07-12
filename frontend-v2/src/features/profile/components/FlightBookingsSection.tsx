import { Alert, Box, Button, Group, Loader, Stack, Text } from '@mantine/core';
import { Link as RouterLink } from 'react-router-dom';
import { useGetMyBookingsQuery } from '@/api/flightsApi';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import { ROUTES } from '@/features/routing/constants';
import { ProfileFlightBookingCard } from '@/features/profile/components/bookings/ProfileFlightBookingCard';
import { mapFlightMyBookingToRow } from '@/features/profile/components/bookings/mapFlightBookingEvent';

const LIMIT = 20;

export function FlightBookingsSection() {
  const { data, isLoading, isError, refetch } = useGetMyBookingsQuery({ limit: LIMIT });
  const count = data?.length;
  const title =
    count != null && !isLoading && !isError ? `Flight bookings (${count})` : 'Flight bookings';

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
            <Alert color="red">Could not load flight bookings.</Alert>
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
            No flight bookings yet. Plan a trip in chat.
          </Text>
          <Button component={RouterLink} to={ROUTES.CHAT} size="xs" tt="none">
            Open chat
          </Button>
        </Stack>
      ) : (
        <Stack gap="md" px="md" role="region" aria-label="Flight bookings">
          {data.map((item, index) => (
            <ProfileFlightBookingCard
              key={`${item.voyaBookingReference ?? `idx-${index}`}-${item.timestamp}`}
              row={mapFlightMyBookingToRow(item)}
            />
          ))}
        </Stack>
      )}
    </Stack>
  );
}
