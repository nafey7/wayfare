import { useParams, useNavigate } from 'react-router-dom';
import { Box, Container, Group, Stack, Text, Title } from '@mantine/core';
import { PlaneTakeoff } from 'lucide-react';
import { useGetItineraryQuery } from '@/api/itinerariesApi';
import { flightBookingDetail } from '@/features/routing';
import { ItineraryFlightBookingsList } from '../components/linkedBookings';
import type { LinkedBookingEventSummary } from '@/types/itineraries';

function mergeFlightRows(
  refs: string[],
  events: LinkedBookingEventSummary[] | undefined,
): { voyaReference: string; event?: LinkedBookingEventSummary | null }[] {
  return refs.map((voyaReference, i) => ({
    voyaReference,
    event: events?.[i],
  }));
}

/**
 * Lists linked flight VOYA refs for a saved itinerary; row opens flight booking detail.
 */
export function ItineraryFlightBookingsListPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data, isLoading, error } = useGetItineraryQuery(id ?? '', {
    skip: !id,
  });

  const refs = data?.linkedBookings?.flightVoyaReferences ?? [];
  const events = data?.linkedBookings?.flightEvents;
  const items = mergeFlightRows(refs, events);

  const handleSelect = (ref: string) => {
    navigate(flightBookingDetail(ref), {
      state: { fromItinerary: id },
    });
  };

  const destination = data?.tripMeta?.destination;

  return (
    <Container size="md" py="lg">
      <Stack gap="lg">
        <Box>
          <Group align="center" gap="sm" mb="xs">
            <Box
              style={{
                width: 44,
                height: 44,
                borderRadius: 8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'rgba(25, 118, 210, 0.1)',
                color: 'var(--mantine-color-brand-6)',
              }}
            >
              <PlaneTakeoff />
            </Box>
            <Box>
              <Title order={1} fw={700}>
                Flight bookings
              </Title>
              {destination ? (
                <Text size="sm" c="dimmed">
                  {destination}
                </Text>
              ) : null}
            </Box>
          </Group>
          <Text size="md" c="dimmed" style={{ maxWidth: 480 }}>
            Select a booking to view full details, tickets, and status.
          </Text>
        </Box>

        <ItineraryFlightBookingsList
          itineraryId={id ?? ''}
          items={items}
          onSelectReference={handleSelect}
          isLoading={Boolean(id) && isLoading}
          error={Boolean(error)}
        />
      </Stack>
    </Container>
  );
}
