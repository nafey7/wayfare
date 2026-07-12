import { useParams, useNavigate } from 'react-router-dom';
import { Box, Container, Group, Stack, Text, Title } from '@mantine/core';
import { Hotel as HotelIcon } from 'lucide-react';
import { useGetItineraryQuery } from '@/api/itinerariesApi';
import { hotelBookingDetail } from '@/features/routing';
import { ItineraryHotelBookingsList } from '../components/linkedBookings';
import type { LinkedBookingEventSummary } from '@/types/itineraries';

function mergeHotelRows(
  refs: string[],
  events: LinkedBookingEventSummary[] | undefined,
): { voyaReference: string; event?: LinkedBookingEventSummary | null }[] {
  return refs.map((voyaReference, i) => ({
    voyaReference,
    event: events?.[i],
  }));
}

/**
 * Lists linked hotel VOYA refs for a saved itinerary; row opens hotel booking detail.
 */
export function ItineraryHotelBookingsListPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data, isLoading, error } = useGetItineraryQuery(id ?? '', {
    skip: !id,
  });

  const refs = data?.linkedBookings?.hotelVoyaReferences ?? [];
  const events = data?.linkedBookings?.hotelEvents;
  const items = mergeHotelRows(refs, events);

  const handleSelect = (ref: string) => {
    navigate(hotelBookingDetail(ref), {
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
                backgroundColor: 'rgba(156, 39, 176, 0.1)',
                color: 'var(--mantine-color-grape-6)',
              }}
            >
              <HotelIcon />
            </Box>
            <Box>
              <Title order={1} fw={700}>
                Hotel bookings
              </Title>
              {destination ? (
                <Text size="sm" c="dimmed">
                  {destination}
                </Text>
              ) : null}
            </Box>
          </Group>
          <Text size="md" c="dimmed" style={{ maxWidth: 480 }}>
            Select a booking to view confirmation, stay details, and status.
          </Text>
        </Box>

        <ItineraryHotelBookingsList
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
