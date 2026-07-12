import { ActionIcon, Button, Group, Modal, Stack, TextInput, Title } from '@mantine/core';
import { CirclePlus, X } from 'lucide-react';
import { useState, useCallback, useEffect } from 'react';

export interface LocationDialogProps {
  open: boolean;
  onClose: () => void;
  /** Current location value (e.g. from itinerary). */
  initialLocation: string;
  /** Called when user confirms with "Save". */
  onUpdate?: (location: string) => void;
  /** Called when user clicks "Add place". */
  onAddPlace?: () => void;
}

/**
 * Location edit dialog – "Where" title, location input with clear, "Add place", "Save".
 * Implements Figma design (node 257-20919): rounded corners, centered title.
 */
export function LocationDialog({
  open,
  onClose,
  initialLocation,
  onUpdate,
  onAddPlace,
}: LocationDialogProps) {
  const [location, setLocation] = useState(initialLocation);

  useEffect(() => {
    if (open) {
      setLocation(initialLocation);
    }
  }, [open, initialLocation]);

  const handleUpdate = useCallback(() => {
    onUpdate?.(location);
    onClose();
  }, [location, onUpdate, onClose]);

  return (
    <Modal
      opened={open}
      onClose={onClose}
      withCloseButton={false}
      centered
      radius="md"
      size="md"
      padding="lg"
      shadow="md"
    >
      <Stack gap={0}>
        <Group justify="space-between" align="center" mb="md">
          <ActionIcon
            aria-label="Close"
            onClick={onClose}
            variant="filled"
            color="gray.3"
            radius="xl"
            size="lg"
            styles={{ root: { color: 'var(--mantine-color-dimmed)' } }}
          >
            <X size={20} />
          </ActionIcon>
          <Title order={5} fw={700} style={{ flex: 1, textAlign: 'center', marginRight: 36 }}>
            Where
          </Title>
        </Group>

        <TextInput
          value={location}
          onChange={(e) => setLocation(e.currentTarget.value)}
          placeholder="Enter location"
          mb="md"
          rightSection={
            location ? (
              <ActionIcon
                size="sm"
                aria-label="Clear"
                onClick={() => setLocation('')}
                variant="subtle"
                color="gray"
              >
                <X size={18} />
              </ActionIcon>
            ) : null
          }
        />

        <Button
          variant="subtle"
          leftSection={<CirclePlus size={22} color="var(--mantine-color-brand-6)" />}
          onClick={onAddPlace}
          tt="none"
          fw={500}
          color="dark.8"
          px={0}
          style={{ alignSelf: 'flex-start' }}
        >
          Add place
        </Button>

        <Group justify="flex-end" mt="md" pt={4}>
          <Button onClick={handleUpdate} radius="md" tt="none" fw={600} px="lg" color="brand.7">
            Update
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
