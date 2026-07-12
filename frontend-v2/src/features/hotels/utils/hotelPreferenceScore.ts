import type { FilterableHotel } from './hotelFilters';
import type { HotelsPreferences, TravelStylePreferences } from '@/types/profile';

const AMENITY_KEYWORD_MAP: Record<string, string[]> = {
  breakfast:      ['breakfast'],
  gym:            ['gym', 'fitness'],
  spa:            ['spa', 'wellness'],
  pool:           ['pool', 'swimming'],
  workspace:      ['business center', 'business centre', 'work desk', 'workspace'],
  familyFriendly: ['family room', 'family friendly', 'family-friendly'],
  petFriendly:    ['pet friendly', 'pets allowed', 'pets welcome', 'pet-friendly'],
  airportShuttle: ['airport shuttle', 'airport transfer', 'shuttle'],
};

function _scoreCancellation(hotel: FilterableHotel, cancellationPref: string[]): 0 | 1 {
  if (cancellationPref.length === 0) return 0;
  const pref = cancellationPref[0]!.toLowerCase();
  const ft = (hotel.fareType ?? '').toLowerCase().trim();
  if (pref === 'refundable') {
    return ft.includes('refundable') && !ft.includes('non') ? 1 : 0;
  }
  if (pref === 'nonrefundable') {
    return ft.includes('non-refundable') || ft.includes('non refundable') ? 1 : 0;
  }
  return 0;
}

function _scoreAmenities(hotel: FilterableHotel, amenities: string[]): 0 | 1 {
  if (amenities.length === 0) return 0;
  const hotelFacilities = hotel.facilities.map((f) => f.toLowerCase());
  for (const pref of amenities) {
    const keywords = AMENITY_KEYWORD_MAP[pref] ?? [];
    if (hotelFacilities.some((f) => keywords.some((k) => f.includes(k)))) {
      return 1;
    }
  }
  return 0;
}

function _scoreStarRating(hotel: FilterableHotel, accommodation: string | null | undefined): 0 | 1 {
  if (!accommodation || accommodation === 'noPref') return 0;
  const rating = hotel.starRating ?? 0;
  if (accommodation === '5' || accommodation === '5star') return rating >= 5 ? 1 : 0;
  if (accommodation === '4' || accommodation === '4star') return rating >= 4 ? 1 : 0;
  return 0;
}

function _scoreRoomType(hotel: FilterableHotel, roomType: string | null | undefined): 0 | 1 {
  if (!roomType || roomType === 'noPreference') return 0;
  const pt = (hotel.propertyType ?? '').toLowerCase();
  if (roomType === 'hotel') return pt.includes('hotel') ? 1 : 0;
  if (roomType === 'apartment') return pt.includes('apartment') ? 1 : 0;
  return 0;
}

export function computeHotelPreferenceScore(
  hotel: FilterableHotel,
  prefs: HotelsPreferences | null,
  travelStyle?: TravelStylePreferences | null
): number {
  if (prefs === null && travelStyle == null) return 0;
  const hotelsScore = prefs
    ? _scoreCancellation(hotel, prefs.cancellation ?? []) +
      _scoreAmenities(hotel, prefs.amenities ?? []) +
      _scoreRoomType(hotel, prefs.roomType)
    : 0;
  return hotelsScore + _scoreStarRating(hotel, travelStyle?.accommodation);
}

export function sortHotelsByPreference<T extends FilterableHotel>(
  hotels: T[],
  prefs: HotelsPreferences | null,
  travelStyle?: TravelStylePreferences | null
): T[] {
  const scores = new Map(hotels.map((h) => [h, computeHotelPreferenceScore(h, prefs, travelStyle)]));
  return [...hotels].sort((a, b) => {
    const diff = (scores.get(b) ?? 0) - (scores.get(a) ?? 0);
    return diff !== 0 ? diff : (a.total ?? 0) - (b.total ?? 0);
  });
}
