import type { DestinationLocation } from '@/types/chat';

/**
 * State passed when navigating from chat itinerary card to ItineraryPage.
 * Matches backend ChatResponse.data structure for itinerary_results.
 */
export interface ItineraryNavigationState {
  /** Structured itinerary from API (itineraryItems, budgetSnapshot, localExperiences, etc.) */
  structuredItinerary: Record<string, unknown>;
  /** ID of the saved itinerary — used to validate Redux state matches the current route. */
  savedItineraryId?: string;
  /** Trip metadata for header chips and map */
  tripMeta?: {
    origin?: string;
    destination?: string;
    departure_date?: string;
    return_date?: string;
    adults?: number;
    children?: number;
    infants?: number;
    trip_type?: string;
    /** Optional destination coordinates for map. Fallback to default coordinates when missing. */
    destination_location?: DestinationLocation;
    /** Optional origin coordinates for map (trip departure city). */
    origin_location?: DestinationLocation;
  };
}
