import { ActionIcon, Box, Button, Group, Paper, SimpleGrid, Stack, Text, TextInput } from '@mantine/core';
import { MapPin, Plus, Trash2 } from 'lucide-react';
import type { HotelMultistaySegment } from '@/types/hotels';

interface HotelMultistaySegmentFormProps {
  segments: HotelMultistaySegment[];
  onChange: (index: number, field: keyof HotelMultistaySegment, value: string) => void;
  onAddSegment: () => void;
  onRemoveSegment: (index: number) => void;
}

const MAX_SEGMENTS = 5;
const MIN_SEGMENTS = 2;

export function HotelMultistaySegmentForm({
  segments,
  onChange,
  onAddSegment,
  onRemoveSegment,
}: HotelMultistaySegmentFormProps) {
  const today = new Date().toISOString().slice(0, 10);
  return (
    <Stack gap="md" style={{ width: '100%' }}>
      <Text size="sm" c="dimmed" fw={600}>
        Add destinations for your multi-stay trip (2–{MAX_SEGMENTS} cities)
      </Text>

      {segments.map((seg, i) => (
        <Paper key={i} withBorder p="md" radius="md" style={{ position: 'relative' }}>
          <Group align="center" gap="xs" mb="sm">
            <MapPin size={20} color="var(--mantine-color-navy-7)" />
            <Text fw={600} size="sm">
              Stay {i + 1}
            </Text>
            {segments.length > MIN_SEGMENTS && (
              <ActionIcon
                size="sm"
                variant="subtle"
                color="gray"
                onClick={() => onRemoveSegment(i)}
                aria-label={`Remove stay ${i + 1}`}
                style={{ marginLeft: 'auto' }}
              >
                <Trash2 size={16} />
              </ActionIcon>
            )}
          </Group>

          <Stack gap="sm">
            <TextInput
              label="City / Destination"
              value={seg.destination}
              onChange={(e) => onChange(i, 'destination', e.currentTarget.value)}
              size="sm"
              placeholder="e.g. Paris"
            />
            <SimpleGrid cols={2} spacing="sm">
              <TextInput
                label="Check-in"
                type="date"
                value={seg.checkin ?? ''}
                onChange={(e) => onChange(i, 'checkin', e.currentTarget.value)}
                size="sm"
                min={today}
              />
              <TextInput
                label="Check-out"
                type="date"
                value={seg.checkout ?? ''}
                onChange={(e) => onChange(i, 'checkout', e.currentTarget.value)}
                size="sm"
                min={seg.checkin ?? today}
              />
            </SimpleGrid>
          </Stack>
        </Paper>
      ))}

      {segments.length < MAX_SEGMENTS && (
        <Box>
          <Button
            leftSection={<Plus size={16} />}
            onClick={onAddSegment}
            variant="outline"
            size="xs"
            radius="md"
          >
            Add another city
          </Button>
        </Box>
      )}
    </Stack>
  );
}
