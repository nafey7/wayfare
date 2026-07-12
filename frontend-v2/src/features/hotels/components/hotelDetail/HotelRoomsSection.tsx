import { Stack, Text, Title } from '@mantine/core';

import type { RoomRate } from '@/types/hotels';

import { HotelDetailRoomCard } from './HotelDetailRoomCard';

export interface HotelRoomsSectionProps {
  rooms: RoomRate[];
  /** Nights for the stay (check-out − check-in); drives per-night vs total display. */
  stayNights: number;
  onSelectRoom: (room: RoomRate) => void;
  selectingRateBasisId: string | null;
  isValidatingRate: boolean;
}

/**
 * "Rooms" section — Figma-style room rows with resolved stay pricing.
 */
export function HotelRoomsSection({
  rooms,
  stayNights,
  onSelectRoom,
  selectingRateBasisId,
  isValidatingRate,
}: HotelRoomsSectionProps) {
  return (
    <Stack gap={29} align="flex-start" style={{ width: '100%' }}>
      <Title order={2} m={0} fw={700} style={{ width: '100%', fontSize: 28, lineHeight: '36px' }}>
        Rooms
      </Title>

      {rooms.length === 0 ? (
        <Text c="dimmed" py={4}>
          No rooms available for this hotel.
        </Text>
      ) : (
        <Stack gap="md" style={{ width: '100%' }}>
          {rooms.map((room) => (
            <HotelDetailRoomCard
              key={room.rateBasisId}
              room={room}
              stayNights={stayNights}
              onReserve={() => onSelectRoom(room)}
              isSelecting={isValidatingRate && selectingRateBasisId === room.rateBasisId}
            />
          ))}
        </Stack>
      )}
    </Stack>
  );
}
