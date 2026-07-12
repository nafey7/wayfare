import type { HotelSearchFormParams, HotelSearchRequest, RoomOccupancy } from '@/types/hotels';
import { normalizeHotelSearchFormParams } from './normalizeHotelSearchFormParams';

/**
 * Build API hotel search request from Redux form params (same rules as the search bar).
 */
export function buildHotelSearchRequestFromFormParams(
  searchFormParams: HotelSearchFormParams
): HotelSearchRequest | null {
  const normalized = normalizeHotelSearchFormParams(searchFormParams, { fillCheckout: false });
  if (!normalized) return null;
  const { checkin, checkout, destination } = normalized;

  const occupancy: RoomOccupancy[] = (searchFormParams.rooms ?? []).map((r) => ({
    roomNo: r.roomNo,
    adult: r.adult ?? 1,
    child: r.child ?? 0,
    childAge:
      (r.child ?? 0) > 0
        ? Array.from({ length: r.child! }, (_, j) => r.childAge?.[j] ?? 5)
        : [0],
  }));

  return {
    checkin,
    checkout,
    cityName: destination,
    occupancy,
    nationality: searchFormParams.nationality || 'US',
  };
}
