/**
 * Persist hotel rooms context for re-fetch on refresh/bookmark.
 * When user navigates to /hotels/rooms/:tokenId, we store sessionId, productId, hotelId, selectedHotel
 * so that on refresh (Redux lost) we can restore and re-fetch room rates instead of redirecting.
 */
import type { HotelItinerary, HotelSearchFormParams } from '@/types/hotels';

const STORAGE_KEY_PREFIX = 'voya_hotel_rooms_';

export interface HotelRoomsContext {
  tokenId: string;
  sessionId: string;
  productId: string;
  hotelId: string;
  selectedHotel: HotelItinerary;
  searchFormParams: HotelSearchFormParams;
}

export function persistHotelRoomsContext(context: HotelRoomsContext): void {
  try {
    const key = `${STORAGE_KEY_PREFIX}${context.tokenId}`;
    sessionStorage.setItem(key, JSON.stringify(context));
  } catch {
    // Ignore storage errors (private mode, quota, etc.)
  }
}

export function loadHotelRoomsContext(tokenId: string): HotelRoomsContext | null {
  try {
    const key = `${STORAGE_KEY_PREFIX}${tokenId}`;
    const stored = sessionStorage.getItem(key);
    if (!stored) return null;
    const parsed = JSON.parse(stored) as HotelRoomsContext;
    if (parsed.tokenId !== tokenId || !parsed.sessionId || !parsed.productId || !parsed.hotelId || !parsed.selectedHotel) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}
