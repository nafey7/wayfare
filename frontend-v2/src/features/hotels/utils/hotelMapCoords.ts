import { parseCoord } from '@/utils/parseCoord';
import type { Hotel, HotelItinerary } from '@/types/hotels';

export function hasValidCoords(h: Hotel | HotelItinerary): boolean {
  const lat = parseCoord(h.latitude ?? (h as { lat?: unknown }).lat);
  const lng = parseCoord(
    h.longitude ?? (h as { lng?: unknown }).lng ?? (h as { lon?: unknown }).lon
  );
  if (Number.isNaN(lat) || Number.isNaN(lng)) return false;
  if (lat === 0 && lng === 0) return false;
  if (lat === -1 && lng === -1) return false;
  return true;
}

export function getPosition(h: Hotel | HotelItinerary): { lat: number; lng: number } {
  const lat = parseCoord(h.latitude ?? (h as { lat?: unknown }).lat);
  const lng = parseCoord(
    h.longitude ?? (h as { lng?: unknown }).lng ?? (h as { lon?: unknown }).lon
  );
  return {
    lat: Number.isNaN(lat) ? 0 : lat,
    lng: Number.isNaN(lng) ? 0 : lng,
  };
}

export function getHotelKey(h: Hotel | HotelItinerary): string {
  return (h.tokenId ?? h.id ?? '') as string;
}
