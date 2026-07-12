import { Box, Group, Select, Stack, Text } from '@mantine/core';
import type { RoomOccupancy } from '@/types/hotels';

const ADULTS_OPTIONS = [1, 2, 3, 4, 5, 6, 7, 8];
const CHILDREN_OPTIONS = [0, 1, 2, 3, 4];
/** Default age per child at search (matches dev_ui; actual ages collected on guest form). */
const DEFAULT_CHILD_AGE = 5;

const DEFAULT_ROOM: RoomOccupancy = { roomNo: 1, adult: 2, child: 0, childAge: [0] };

export interface RoomConfiguratorProps {
  rooms: RoomOccupancy[];
  onChange: (rooms: RoomOccupancy[]) => void;
  /** Optional: hide the "Number of rooms" dropdown (e.g. when embedded in a single-room flow) */
  showRoomCount?: boolean;
}

export function RoomConfigurator({
  rooms,
  onChange,
  showRoomCount = true,
}: RoomConfiguratorProps) {
  const totalAdults = rooms.reduce((sum, r) => sum + (r.adult ?? 0), 0);
  const totalChildren = rooms.reduce((sum, r) => sum + (r.child ?? 0), 0);

  const updateRoom = (index: number, patch: Partial<RoomOccupancy>) => {
    const next = rooms.map((r, i) =>
      i === index
        ? {
            ...r,
            ...patch,
            childAge:
              patch.child !== undefined
                ? patch.child === 0
                  ? [0]
                  : Array.from({ length: patch.child }, (_, j) => r.childAge?.[j] ?? DEFAULT_CHILD_AGE)
                : patch.childAge ?? r.childAge,
          }
        : r
    );
    onChange(normalizeRooms(next));
  };

  const setRoomCount = (n: number) => {
    const count = Math.min(5, Math.max(1, n));
    if (count > rooms.length) {
      const added: RoomOccupancy[] = Array.from({ length: count - rooms.length }, (_, i) => ({
        ...DEFAULT_ROOM,
        roomNo: rooms.length + i + 1,
      }));
      onChange(normalizeRooms([...rooms, ...added]));
    } else if (count < rooms.length) {
      onChange(normalizeRooms(rooms.slice(0, count)));
    }
  };

  return (
    <Stack gap="md">
      {showRoomCount && (
        <Select
          label="Rooms"
          size="sm"
          value={String(rooms.length)}
          onChange={(v) => v && setRoomCount(Number(v))}
          data={[1, 2, 3, 4, 5].map((n) => ({
            value: String(n),
            label: `${n} ${n === 1 ? 'room' : 'rooms'}`,
          }))}
          style={{ minWidth: 140 }}
          allowDeselect={false}
        />
      )}

      {rooms.map((room, index) => (
        <Box
          key={room.roomNo}
          p="sm"
          style={{
            borderRadius: 8,
            backgroundColor: 'var(--mantine-color-gray-0)',
            border: '1px solid var(--mantine-color-gray-2)',
          }}
        >
          <Text fw={600} size="sm" c="dimmed" mb="xs">
            Room {index + 1}
          </Text>
          <Group align="flex-start" gap="md" wrap="wrap">
            <Select
              label="Adults"
              size="sm"
              value={String(room.adult ?? 2)}
              onChange={(v) => v && updateRoom(index, { adult: Number(v) })}
              data={ADULTS_OPTIONS.map((n) => ({ value: String(n), label: String(n) }))}
              style={{ minWidth: 80 }}
              allowDeselect={false}
            />
            <Select
              label="Children"
              size="sm"
              value={String(room.child ?? 0)}
              onChange={(v) => v && updateRoom(index, { child: Number(v) })}
              data={CHILDREN_OPTIONS.map((n) => ({ value: String(n), label: String(n) }))}
              style={{ minWidth: 90 }}
              allowDeselect={false}
            />
          </Group>
        </Box>
      ))}

      <Text size="sm" c="dimmed">
        {totalAdults} adult{totalAdults !== 1 ? 's' : ''}, {totalChildren} child
        {totalChildren !== 1 ? 'ren' : ''}
      </Text>
    </Stack>
  );
}

function normalizeRooms(rooms: RoomOccupancy[]): RoomOccupancy[] {
  return rooms.map((r, i) => ({
    roomNo: i + 1,
    adult: Math.min(8, Math.max(1, r.adult ?? 2)),
    child: Math.min(4, Math.max(0, r.child ?? 0)),
    childAge:
      (r.child ?? 0) > 0
        ? Array.from({ length: r.child! }, (_, j) =>
            typeof r.childAge?.[j] === 'number' && r.childAge![j] >= 0 && r.childAge![j] <= 17
              ? r.childAge![j]
              : DEFAULT_CHILD_AGE
          )
        : [0],
  }));
}
