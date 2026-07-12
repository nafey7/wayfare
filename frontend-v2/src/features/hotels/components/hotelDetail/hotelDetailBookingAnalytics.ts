import type { RoomRate } from '@/types/hotels';

import { resolveRoomStayPricing } from './roomStayPricing';

/** GTM `hotel_room_selected` payload — kept in one place for tests and `HotelDetailPage`. */
export interface HotelRoomSelectedEventPayload extends Record<string, unknown> {
  room_name: string;
  total_price: number;
  currency: string;
  nights: number;
}

export function buildHotelRoomSelectedEventPayload(
  room: RoomRate,
  nights: number,
): HotelRoomSelectedEventPayload {
  const stayPricing = resolveRoomStayPricing(room, nights);
  return {
    room_name: room.roomType ?? room.roomName ?? '',
    total_price: stayPricing.total,
    currency: stayPricing.currency,
    nights,
  };
}
