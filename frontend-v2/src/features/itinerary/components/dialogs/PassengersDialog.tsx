import { ActionIcon, Anchor, Button, Group, Modal, Stack, Text, Title } from '@mantine/core';
import { Minus, Plus, X } from 'lucide-react';
import { useState, useCallback, useEffect } from 'react';

export interface PassengerCounts {
  adults: number;
  children: number;
  infants: number;
  pets: number;
}

export interface PassengersDialogProps {
  open: boolean;
  onClose: () => void;
  /** Initial passenger counts (e.g. from itinerary). */
  initialCounts: PassengerCounts;
  /** Called when user confirms with "Update". */
  onUpdate?: (counts: PassengerCounts) => void;
  /** Optional handler for "Bringing a service animal?" link. */
  onServiceAnimalClick?: () => void;
}

const MIN_ADULTS = 1;
const MIN_OTHERS = 0;

function formatSummary(counts: PassengerCounts): string {
  const parts: string[] = [];
  if (counts.adults > 0) parts.push(`${counts.adults} Adult${counts.adults !== 1 ? 's' : ''}`);
  if (counts.children > 0) parts.push(`${counts.children} Child${counts.children !== 1 ? 'ren' : ''}`);
  if (counts.infants > 0) parts.push(`${counts.infants} Infant${counts.infants !== 1 ? 's' : ''}`);
  if (counts.pets > 0) parts.push(`${counts.pets} Pet${counts.pets !== 1 ? 's' : ''}`);
  return parts.length ? parts.join(', ') : '0 Adults';
}

interface PassengerRowProps {
  label: string;
  description?: string;
  extra?: React.ReactNode;
  value: number;
  min: number;
  onIncrement: () => void;
  onDecrement: () => void;
}

function PassengerRow({
  label,
  description,
  extra,
  value,
  min,
  onIncrement,
  onDecrement,
}: PassengerRowProps) {
  return (
    <Group justify="space-between" align="center" py="xs">
      <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
        <Text fw={700} size="sm">
          {label}
        </Text>
        {description && (
          <Text size="sm" c="dimmed">
            {description}
          </Text>
        )}
        {extra}
      </Stack>
      <Group align="center" gap="sm" style={{ flexShrink: 0 }}>
        <ActionIcon
          aria-label={`Decrease ${label}`}
          onClick={onDecrement}
          disabled={value <= min}
          variant="default"
          size="md"
        >
          <Minus size={18} />
        </ActionIcon>
        <Text fw={700} size="sm" style={{ minWidth: 24, textAlign: 'center' }}>
          {value}
        </Text>
        <ActionIcon
          aria-label={`Increase ${label}`}
          onClick={onIncrement}
          variant="default"
          size="md"
        >
          <Plus size={18} />
        </ActionIcon>
      </Group>
    </Group>
  );
}

/**
 * Who (passengers) dialog – adults, children, infants, pets with +/- controls.
 * Implements Figma design (node 257-29017): "Who" title, summary, Update button.
 */
export function PassengersDialog({
  open,
  onClose,
  initialCounts,
  onUpdate,
  onServiceAnimalClick,
}: PassengersDialogProps) {
  const [counts, setCounts] = useState<PassengerCounts>(initialCounts);

  useEffect(() => {
    if (open) {
      setCounts(initialCounts);
    }
  }, [open, initialCounts]);

  const handleUpdate = useCallback(() => {
    onUpdate?.(counts);
    onClose();
  }, [counts, onUpdate, onClose]);

  const setAdults = useCallback((v: number) => setCounts((c) => ({ ...c, adults: Math.max(MIN_ADULTS, v) })), []);
  const setChildren = useCallback((v: number) => setCounts((c) => ({ ...c, children: Math.max(MIN_OTHERS, v) })), []);
  const setInfants = useCallback((v: number) => setCounts((c) => ({ ...c, infants: Math.max(MIN_OTHERS, v) })), []);
  const setPets = useCallback((v: number) => setCounts((c) => ({ ...c, pets: Math.max(MIN_OTHERS, v) })), []);

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
        <Group justify="space-between" align="flex-start" mb="md">
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
          <Stack gap={4} style={{ flex: 1, marginRight: 36 }}>
            <Title order={5} fw={700} ta="center">
              Who
            </Title>
            <Text size="sm" c="dimmed" ta="center">
              {formatSummary(counts)}
            </Text>
          </Stack>
        </Group>

        <PassengerRow
          label="Adults"
          description="Ages 13 or above"
          value={counts.adults}
          min={MIN_ADULTS}
          onIncrement={() => setAdults(counts.adults + 1)}
          onDecrement={() => setAdults(counts.adults - 1)}
        />
        <PassengerRow
          label="Children"
          description="Ages 2-12"
          value={counts.children}
          min={MIN_OTHERS}
          onIncrement={() => setChildren(counts.children + 1)}
          onDecrement={() => setChildren(counts.children - 1)}
        />
        <PassengerRow
          label="Infants"
          description="Under 2"
          value={counts.infants}
          min={MIN_OTHERS}
          onIncrement={() => setInfants(counts.infants + 1)}
          onDecrement={() => setInfants(counts.infants - 1)}
        />
        <PassengerRow
          label="Pets"
          extra={
            <Anchor
              href="#"
              size="sm"
              onClick={(e) => {
                e.preventDefault();
                onServiceAnimalClick?.();
              }}
              c="brand.6"
              style={{ marginTop: 2 }}
            >
              Bringing a service animal?
            </Anchor>
          }
          value={counts.pets}
          min={MIN_OTHERS}
          onIncrement={() => setPets(counts.pets + 1)}
          onDecrement={() => setPets(counts.pets - 1)}
        />

        <Group justify="flex-end" mt="md" pt={4}>
          <Button onClick={handleUpdate} radius="md" px="lg" fw={600} tt="none" color="brand.7">
            Update
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
