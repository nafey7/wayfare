/**
 * Hotel sorting utilities.
 * Sort by: Recommended (nearest first), Price (low→high), Price (high→low),
 * Rating (high→low), Rating (low→high), Name (A→Z).
 */

import type { FilterableHotel } from './hotelFilters';

export type HotelSortOption =
  | 'recommended'
  | 'price-low'
  | 'price-high'
  | 'rating-high'
  | 'rating-low'
  | 'name-az'
  | 'preference-match';

export const DEFAULT_HOTEL_SORT: HotelSortOption = 'price-low';

/** Labels for hotel search sort menus (shared by HotelResults and mobile toolbar). */
const HOTEL_SORT_MENU_ITEMS_BASE: { value: HotelSortOption; label: string }[] = [
  { value: 'price-low', label: 'Price: Low to High' },
  { value: 'price-high', label: 'Price: High to Low' },
  { value: 'rating-high', label: 'Rating: High to Low' },
  { value: 'rating-low', label: 'Rating: Low to High' },
  { value: 'name-az', label: 'Name: A to Z' },
];

export function getHotelSortMenuItems(
  hasNearbyLocation: boolean
): { value: HotelSortOption; label: string }[] {
  const base = hasNearbyLocation
    ? [{ value: 'recommended' as const, label: 'Nearest First' }, ...HOTEL_SORT_MENU_ITEMS_BASE]
    : HOTEL_SORT_MENU_ITEMS_BASE;
  return [{ value: 'preference-match' as const, label: 'Your preferences' }, ...base];
}

export const HOTEL_SORT_OPTIONS: HotelSortOption[] = [
  'preference-match',
  'recommended',
  ...HOTEL_SORT_MENU_ITEMS_BASE.map((i) => i.value),
];

export function getHotelPrice(hotel: FilterableHotel): number {
  return hotel.total ?? 0;
}

export function getHotelRating(hotel: FilterableHotel): number {
  return hotel.starRating ?? 0;
}

export function getHotelName(hotel: FilterableHotel): string {
  return hotel.name ?? '';
}

/**
 * Sort hotels by the given option.
 */
export function sortHotels<T extends FilterableHotel>(
  hotels: T[],
  sortBy: HotelSortOption
): T[] {
  const sorted = [...hotels];
  switch (sortBy) {
    case 'recommended':
      sorted.sort((a, b) => {
        const da = a.nearbyDistanceKm ?? Infinity;
        const db = b.nearbyDistanceKm ?? Infinity;
        return da - db;
      });
      break;
    case 'price-low':
      sorted.sort((a, b) => getHotelPrice(a) - getHotelPrice(b));
      break;
    case 'price-high':
      sorted.sort((a, b) => getHotelPrice(b) - getHotelPrice(a));
      break;
    case 'rating-high':
      sorted.sort((a, b) => getHotelRating(b) - getHotelRating(a));
      break;
    case 'rating-low':
      sorted.sort((a, b) => getHotelRating(a) - getHotelRating(b));
      break;
    case 'name-az':
      sorted.sort((a, b) => getHotelName(a).localeCompare(getHotelName(b)));
      break;
    case 'preference-match':
      throw new Error('preference-match must be sorted via sortHotelsByPreference');
    default:
      sorted.sort((a, b) => getHotelPrice(a) - getHotelPrice(b));
  }
  return sorted;
}
