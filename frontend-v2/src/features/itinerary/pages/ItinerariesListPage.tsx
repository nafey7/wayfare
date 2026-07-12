import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Modal,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useState } from 'react';
import { Map as MapIcon } from 'lucide-react';
import {
  useGetItinerariesQuery,
  useDeleteItineraryMutation,
} from '@/api/itinerariesApi';
import { itinerarySavedView } from '@/features/routing';
import { showSuccessToast, showErrorToast } from '@/utils/toast';
import { getSavedItineraryCardSummary } from '@/features/itinerary/utils/savedItineraryCardSummary';
import { SavedItineraryTripCard } from '@/features/itinerary/components/SavedItineraryTripCard';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';

export function ItinerariesListPage() {
  const navigate = useNavigate();
  const { data: itineraries, isLoading, error } = useGetItinerariesQuery();
  const [deleteItinerary, { isLoading: isDeleting }] =
    useDeleteItineraryMutation();
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleView = (id: string) => {
    navigate(itinerarySavedView(id));
  };

  const handleDeleteClick = (id: string) => {
    setDeleteConfirmId(id);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConfirmId) return;
    setDeletingId(deleteConfirmId);
    try {
      await deleteItinerary(deleteConfirmId).unwrap();
      showSuccessToast('Itinerary deleted');
      setDeleteConfirmId(null);
    } catch {
      showErrorToast('Failed to delete itinerary');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmId(null);
  };

  if (isLoading) {
    return (
      <Group justify="center" py="xl">
        <Loader />
      </Group>
    );
  }

  if (error) {
    return (
      <Container size="md" py="lg">
        <Alert color="red">
          Failed to load itineraries. Please try again later.
        </Alert>
      </Container>
    );
  }

  const list = itineraries ?? [];

  return (
    <Container size="lg" py="lg">
      <Stack gap="lg">
        <Title
          order={1}
          style={{
            fontFamily: LANDING_TOKENS.fontFamily.display,
            fontWeight: 700,
            fontSize: 28,
            lineHeight: '36px',
            color: LANDING_TOKENS.textColor,
            margin: 0,
          }}
        >
          Upcoming Trips
        </Title>

        {list.length === 0 ? (
          <Card withBorder>
            <Stack align="center" py="xl" gap="sm">
              <MapIcon size={64} color="var(--mantine-color-dimmed)" />
              <Text size="md" c="dimmed">
                No upcoming trips yet
              </Text>
              <Text size="sm" c="dimmed">
                Generate an itinerary in chat to see it here.
              </Text>
            </Stack>
          </Card>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md" verticalSpacing="md">
            {list.map((itinerary) => {
              const summary = getSavedItineraryCardSummary(itinerary);
              return (
                <SavedItineraryTripCard
                  key={itinerary.id}
                  trip={summary}
                  layout="grid"
                  onView={() => handleView(itinerary.id)}
                  onDelete={() => handleDeleteClick(itinerary.id)}
                  deleteDisabled={itinerary.id === deletingId}
                />
              );
            })}
          </SimpleGrid>
        )}
      </Stack>

      <Modal
        opened={Boolean(deleteConfirmId)}
        onClose={handleDeleteCancel}
        title="Delete itinerary?"
        centered
        radius="md"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            This will permanently delete this itinerary. This action cannot be undone.
          </Text>
          <Group justify="flex-end" gap="xs">
            <Button variant="subtle" onClick={handleDeleteCancel} tt="none">
              Cancel
            </Button>
            <Button
              onClick={handleDeleteConfirm}
              color="red"
              disabled={isDeleting}
              tt="none"
            >
              {isDeleting ? 'Deleting…' : 'Delete'}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
