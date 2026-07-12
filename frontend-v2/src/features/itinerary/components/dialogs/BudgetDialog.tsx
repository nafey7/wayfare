import { ActionIcon, Button, Group, Modal, Radio, Stack, Text, Title } from '@mantine/core';
import { X } from 'lucide-react';
import { useState, useCallback, useEffect } from 'react';

/** Budget option value matching Figma design (node 257-29223). */
export type BudgetOption = 'any' | 'budget' | 'normal' | 'luxury';

export interface BudgetDialogProps {
  open: boolean;
  onClose: () => void;
  /** Initial selected budget (e.g. from itinerary). */
  initialBudget?: BudgetOption | null;
  /** Called when user confirms with "Update". */
  onUpdate?: (budget: BudgetOption) => void;
}

const BUDGET_OPTIONS: { value: BudgetOption; label: string }[] = [
  { value: 'any', label: 'Any budget' },
  { value: 'budget', label: 'On a budget' },
  { value: 'normal', label: 'Normal' },
  { value: 'luxury', label: 'Luxury' },
];

/**
 * Budget dialog – title "Budget", subtitle "Select your budget range",
 * four radio options, Update button.
 */
export function BudgetDialog({
  open,
  onClose,
  initialBudget = 'any',
  onUpdate,
}: BudgetDialogProps) {
  const [selected, setSelected] = useState<BudgetOption>(initialBudget ?? 'any');

  useEffect(() => {
    if (open) {
      setSelected(initialBudget ?? 'any');
    }
  }, [open, initialBudget]);

  const handleUpdate = useCallback(() => {
    onUpdate?.(selected);
    onClose();
  }, [selected, onUpdate, onClose]);

  return (
    <Modal
      opened={open}
      onClose={onClose}
      withCloseButton={false}
      centered
      // 22 px corner radius matches Figma node 257-29223; outside Mantine's xl scale.
      radius={22}
      size="sm"
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
            <Title order={4} fw={700} ta="center">
              Budget
            </Title>
            <Text c="dimmed" ta="center">
              Select your budget range
            </Text>
          </Stack>
        </Group>

        <Radio.Group
          value={selected}
          onChange={(value) => setSelected(value as BudgetOption)}
        >
          <Stack gap={12} mt="md" mb="md">
            {BUDGET_OPTIONS.map((opt) => (
              <Radio key={opt.value} value={opt.value} label={opt.label} size="sm" />
            ))}
          </Stack>
        </Radio.Group>

        <Group justify="flex-end" pt={4}>
          <Button onClick={handleUpdate} radius={10} tt="none" fw={600} px="lg" color="brand.7">
            Update
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
