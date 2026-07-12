import {
  Bed,
  Dumbbell,
  Flower2,
  UtensilsCrossed,
  Waves,
  Wifi,
  Wine,
  type LucideIcon,
} from 'lucide-react';

import type { HotelItinerary } from '@/types/hotels';
import type { RoomOccupancy, RoomRate } from '@/types/hotels';

import { formatHotelPrice } from '../../utils';
import { resolveHotelImageUrl } from '../../utils';

import type { HotelAmenityItem } from './HotelAmenities';
import { resolveRoomStayPricing } from './roomStayPricing';

/** Narrow shape for APIs that use `hotelName` instead of `name`. */
type HotelLikeForDisplay = {
  name?: string;
  hotelName?: string;
} | null;

/**
 * Display name for search/detail UIs: prefers `name`, then alternate `hotelName`.
 */
export function getHotelDisplayName(hotel: HotelLikeForDisplay, fallback = 'Hotel'): string {
  if (!hotel) return fallback;
  const primary = typeof hotel.name === 'string' ? hotel.name.trim() : '';
  if (primary) return primary;
  const alt = typeof hotel.hotelName === 'string' ? hotel.hotelName.trim() : '';
  if (alt) return alt;
  return fallback;
}

const AMENITY_ICONS: LucideIcon[] = [
  UtensilsCrossed,
  Dumbbell,
  Waves,
  Wine,
  Flower2,
  Wifi,
  Bed,
];

/**
 * Ordered unique image URLs for the property gallery: hotel `images`, then thumbnail/main
 * if distinct, then each room's `images`. Omits invalid URLs; dedupes after resolving.
 */
export function buildGalleryImageList(
  hotel: HotelItinerary | null | undefined,
  rooms?: readonly RoomRate[] | null
): string[] {
  const orderedRaw: string[] = [];
  if (hotel?.images?.length) orderedRaw.push(...hotel.images);
  if (hotel?.thumbnailUrl) orderedRaw.push(hotel.thumbnailUrl);
  if (hotel?.imageUrl) orderedRaw.push(hotel.imageUrl);
  if (rooms?.length) {
    for (const room of rooms) {
      if (room.images?.length) orderedRaw.push(...room.images);
    }
  }
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of orderedRaw) {
    const resolved = resolveHotelImageUrl(raw);
    if (!resolved || seen.has(resolved)) continue;
    seen.add(resolved);
    out.push(resolved);
  }
  return out;
}

/**
 * Labels for the detail amenities section: search API uses `facilities`; some paths use `amenities`.
 * Prefers non-empty `facilities`, otherwise falls back to `amenities`.
 */
export function hotelSearchFacilityLabels(hotel: HotelItinerary | null | undefined): string[] {
  if (!hotel) return [];
  const fromFacilities = hotel.facilities;
  const fromAmenities = hotel.amenities;
  const raw =
    Array.isArray(fromFacilities) && fromFacilities.length > 0
      ? fromFacilities
      : Array.isArray(fromAmenities)
        ? fromAmenities
        : [];
  return raw.filter((f): f is string => typeof f === 'string' && f.trim() !== '');
}

export function amenityStringsToColumns(labels: string[]): {
  columnOne: HotelAmenityItem[];
  columnTwo: HotelAmenityItem[];
} {
  if (labels.length === 0) return { columnOne: [], columnTwo: [] };
  const items: HotelAmenityItem[] = labels.map((label, i) => ({
    id: `amenity-${i}-${label}`,
    label,
    Icon: AMENITY_ICONS[i % AMENITY_ICONS.length] ?? UtensilsCrossed,
  }));
  const mid = Math.ceil(items.length / 2);
  return {
    columnOne: items.slice(0, mid),
    columnTwo: items.slice(mid),
  };
}

export function buildRoomsAndGuestsLabel(occupancy: RoomOccupancy[] | null): string {
  if (!occupancy || occupancy.length === 0) return '—';
  const roomCount = occupancy.length;
  const adults = occupancy.reduce((s, r) => s + r.adult, 0);
  const children = occupancy.reduce((s, r) => s + (r.child ?? 0), 0);
  const parts: string[] = [];
  parts.push(`${roomCount} room${roomCount !== 1 ? 's' : ''}`);
  parts.push(`${adults} adult${adults !== 1 ? 's' : ''}`);
  if (children > 0) parts.push(`${children} child${children !== 1 ? 'ren' : ''}`);
  return parts.join(' · ');
}

export function buildStayPriceRangeLabel(rooms: RoomRate[], stayNights: number): string {
  if (rooms.length === 0) return '—';

  const currencyFor = (r: RoomRate) =>
    r.currency ?? r.price?.currency ?? 'USD';

  if (rooms.length === 1) {
    const r = rooms[0]!;
    const total = resolveRoomStayPricing(r, stayNights).total;
    if (!Number.isFinite(total)) return '—';
    const currency = currencyFor(r);
    return formatHotelPrice(total, currency);
  }

  const priced = rooms.map((room) => {
    const p = resolveRoomStayPricing(room, stayNights);
    return { total: p.total, currency: p.currency };
  });
  const currencies = new Set(priced.map((p) => p.currency));
  if (currencies.size > 1) {
    return 'See room options';
  }

  const totals = priced.map((p) => p.total).filter((n) => Number.isFinite(n));
  if (totals.length === 0) return '—';
  const min = Math.min(...totals);
  const max = Math.max(...totals);
  const currency = priced[0]?.currency ?? 'USD';
  if (min === max) {
    return formatHotelPrice(min, currency);
  }
  return `${formatHotelPrice(min, currency)} – ${formatHotelPrice(max, currency)}`;
}
