/**
 * Hotel trip type: single destination or multi-stay (multiple cities).
 */
export type HotelTripType = 'single' | 'multi-stay';

/**
 * One segment in a multi-stay search (one city with its own dates + rooms).
 */
export interface HotelMultistaySegment {
  destination: string;
  checkin: string | null;
  checkout: string | null;
  rooms: RoomOccupancy[];
}

/**
 * Per-leg state for a multi-stay search: results + selection.
 */
export interface HotelMultistayLegState {
  segmentIndex: number;
  sessionId: string | null;
  internalSessionId: string | null;
  hotels: HotelItinerary[];
  selectedHotel: HotelItinerary | null;
  tokenId: string | null;
  productId: string | null;
  hotelId: string | null;
  selectedRoom: RoomRate | null;
  rateBasisId: string | null;
  rateRulesResponse: RateRulesResponse | null;
  roomRatesResponse: RoomRatesResponse | null;
  /** Currency resolved from selected room/rate (for combined pricing). */
  currency: string | null;
}

/**
 * Per-leg booking result after payment for a multi-stay booking.
 */
export interface HotelMultistayLegBookingResult {
  legIndex: number;
  voyaBookingReference: string;
  externalBookingReference?: string | null;
  hotelName?: string | null;
  hotelCity?: string | null;
}

/**
 * Room occupancy for hotel search
 */
export interface RoomOccupancy {
  roomNo: number;
  adult: number;
  child?: number;
  childAge?: number[];
}

/**
 * Form-level hotel search parameters (persisted to localStorage).
 */
export interface HotelSearchFormParams {
  destination: string;
  checkin: string | null;
  checkout: string | null;
  /**
   * `null` represents the "fresh / unset" state (placeholder shown on the
   * search chip). Picker dialogs seed a default room `[{roomNo:1, adult:1, child:0, childAge:[]}]`
   * when the user first opens them.
   */
  rooms: RoomOccupancy[] | null;
  nationality: string;
}

/**
 * Hotel search request
 */
export interface HotelSearchRequest {
  checkin: string;
  checkout: string;
  cityName?: string;
  countryName?: string;
  latitude?: number;
  longitude?: number;
  radius?: number;
  hotelCodes?: string[];
  occupancy: RoomOccupancy[];
  requiredCurrency?: string;
  requiredLanguage?: string;
  nationality?: string;
  maxResult?: number;
  resultsPerPage?: number;
  /** Reference point for distance-based sorting (nearest first). */
  nearbyLocation?: { lat: number; lng: number };
}

/**
 * Hotel information
 */
export interface Hotel {
  id: string;
  tokenId: string;
  name: string;
  address: string;
  city: string;
  country: string;
  starRating: number;
  latitude: number;
  longitude: number;
  imageUrl?: string;
  images?: string[];
  /** Property facilities from search API (FlightLogic / backend itineraries). */
  facilities?: string[];
  amenities?: string[];
  description?: string;
  startingPrice: HotelPrice;
  /** Haversine distance (km) from the requested nearby_location. Set by backend when nearby_location is provided. */
  nearbyDistanceKm?: number;
}

/**
 * Full hotel object from search results (itinerary).
 * Extends Hotel with optional fields from search API (thumbnailUrl, fareType, etc.).
 */
export interface HotelItinerary extends Hotel {
  thumbnailUrl?: string;
  fareType?: string;
  /** Total price for stay (API may return as top-level total). */
  total?: number;
  originalTotal?: number;
  platformFeePercentage?: number;
  propertyType?: string;
  perNightArray?: { nightIndex: number; currency: string; price: number }[];
  productId?: string;
}

/**
 * Hotel price
 */
export interface HotelPrice {
  currency: string;
  amount: number;
  perNight: number;
}

/**
 * Hotel search response
 */
export interface HotelSearchResponse {
  sessionId: string;
  hotels: Hotel[];
  nextToken?: string;
  totalResults: number;
  searchParams: HotelSearchRequest;
  curatedHotels?: {
    bestValue?: HotelItinerary | Hotel;
    cheapest?: HotelItinerary | Hotel;
    highestRated?: HotelItinerary | Hotel;
  };
}

/**
 * Max occupancy from room-rates API (camelCase from backend).
 */
export interface RoomMaxOccupancy {
  adults?: number;
  children?: number;
}

/**
 * Room rate (from room-rates API or normalized).
 * API returns roomType, mealPlan, totalPrice, pricePerNight, currency, etc.;
 * price (nested) is used when normalized from other flows.
 */
export interface RoomRate {
  productId?: string;
  rateBasisId: string;
  roomName?: string;
  /** From API as roomType */
  roomType?: string;
  roomDescription?: string;
  boardBasis?: string;
  /** From API as mealPlan (e.g. "Breakfast included", "Room Only") */
  mealPlan?: string;
  price?: HotelPrice;
  /** Total price from API (flat, with platform fee) */
  totalPrice?: number;
  /** Original total price before platform fee (for breakdown) */
  originalTotalPrice?: number;
  /** Price per night from API (flat) */
  pricePerNight?: number;
  /** Currency from API (flat) */
  currency?: string;
  cancellationPolicy?: CancellationPolicy | string;
  maxOccupancy?: RoomMaxOccupancy;
  roomsAvailable?: number;
  images?: string[];
  inclusions?: string[];
}

/**
 * Cancellation policy
 */
export interface CancellationPolicy {
  refundable: boolean;
  deadline?: string;
  penaltyAmount?: number;
  penaltyCurrency?: string;
  description?: string;
}

/**
 * Room rates response (backend returns sessionId, tokenId, rooms; hotel from selectedHotel in Redux).
 */
export interface RoomRatesResponse {
  sessionId: string;
  tokenId: string;
  hotel?: Hotel;
  rooms: RoomRate[];
}

/**
 * Rate rules response from /rate-rules endpoint (validated rate for booking).
 */
export interface RateRulesResponse {
  sessionId: string;
  hotelId: string;
  tokenId: string;
  roomType: string;
  description: string;
  roomCode: string;
  fareType: string;
  rateBasisId: string;
  currency: string;
  netPrice: number;
  boardBasis: string;
  maxOccupancyPerRoom: number;
  inventoryType: string;
  cancellationPolicy: string;
  facilities: string[];
  images: string[];
  remark: string;
  originalNetPrice?: number;
  platformFeePercentage?: number;
}

/**
 * Hotel booking guest details
 */
/** Title values match backend_python/dev_ui/hotel-booker/index.html (adults: Mr, Mrs, Miss; children: Master, Miss). */
export interface GuestDetails {
  title: 'Mr' | 'Mrs' | 'Miss' | 'Master';
  firstName: string;
  lastName: string;
  email?: string;
  phone?: string;
}

/**
 * Guest details for hotel booking (per-room, with room number and child flag).
 */
export interface HotelGuestDetails extends GuestDetails {
  roomNumber: number;
  isChild: boolean;
  age?: number;
}

/**
 * Hotel booking request
 */
export interface HotelBookingRequest {
  sessionId: string;
  tokenId: string;
  productId: string;
  rateBasisId: string;
  clientRef: string;
  customerEmail: string;
  customerPhone: string;
  bookingNote: string;
  guests: HotelGuestDetails[];
  roomCount: number;
  paymentIntentId: string | null;
  /** Persisted on booking_events for profile list; optional. */
  hotelImageUrl?: string;
  hotelName?: string;
  hotelCity?: string;
  /** Persisted on booking_events for confirmation / trip-details address line. */
  hotelAddress?: string;
  /** WGS84; persisted on booking_events for maps link on trip-details / confirmation. */
  hotelLatitude?: number;
  hotelLongitude?: number;
  /** When set, backend links booking_events to this saved itinerary after validation. */
  savedItineraryId?: string | null;
  voucherRedemptionId?: string | null;
  /** Shared parent reference for multi-stay bookings (all legs share this ref). */
  parentVoyaBookingReference?: string | null;
  /** Zero-based leg index for multi-stay bookings. */
  multistayLegIndex?: number | null;
}

/**
 * Hotel booking response
 */
export interface HotelBookingResponse {
  voyaBookingReference: string;
  status: HotelBookingStatus;
  /** Supplier confirmation number from FlightLogic (optional; API may return in booking_details). */
  supplierConfirmationNum?: string;
  hotel?: Hotel;
  roomName?: string;
  checkin?: string;
  checkout?: string;
  /** Total amount in cents (minor units), e.g. 19950 for $199.50. Same convention as flights (types/flights.ts). */
  totalAmount?: number;
  currency?: string;
  guests?: GuestDetails[];
}

/**
 * Hotel booking status
 */
export type HotelBookingStatus = 'pending' | 'confirmed' | 'cancelled' | 'failed';

/**
 * Hotel booking details request (for getHotelBookingDetails)
 */
export interface HotelBookingDetailsRequest {
  supplierConfirmationNum: string;
  referenceNum: string;
}

/**
 * Hotel booking details response (from get_booking_details API)
 */
export interface HotelBookingDetailsResponse {
  bookingDetails?: Record<string, unknown>;
  errors?: Record<string, unknown>;
}

/**
 * Hotel trip details response (from POST /hotels/trip-details).
 * Used by HotelBookingDetailsPage to display booking info from email link.
 */
export interface HotelTripDetailsResponse {
  success: boolean;
  voyaBookingReference?: string | null;
  bookingStatus?: string | null;
  bookingDetails?: Record<string, unknown>;
  errors?: string[] | null;
}

/**
 * Hotel session response (from GET /hotels/session/:id).
 * Used to restore booking context for payment/email link flow.
 */
export interface HotelSessionResponse {
  sessionId: string;
  hotelData: Record<string, unknown>;
  roomData: Record<string, unknown>;
}

/**
 * Select hotel request (chat → hotel-booker redirect)
 * Used when user picks a hotel from chat search results.
 */
export interface SelectHotelRequest {
  sessionId: string;
  tokenId: string;
  productId: string;
  hotelId: string;
  selectedHotelDisplay?: Record<string, unknown>;
  searchParams?: Record<string, unknown>;
}

/**
 * Select hotel response (redirect URL to hotel-booker)
 * Frontend convention: camelCase.
 */
export interface SelectHotelResponse {
  redirectUrl: string;
}

/**
 * Hotel search redirect request (chat → hotel-booker with auto_search).
 * Frontend convention: camelCase; API layer converts to snake_case.
 */
export interface HotelSearchRedirectRequest {
  destinationCity: string;
  country?: string | null;
  checkInDate: string;
  checkOutDate: string;
  rooms?: number;
  adults?: number;
  children?: number;
}

/**
 * GET /hotels/multistay-booking-context — one leg in a multi-stay booking group.
 */
export interface MultistayLegSummary {
  voyaBookingReference: string;
  externalBookingReference?: string | null;
  hotelName?: string | null;
  hotelCity?: string | null;
  legIndex?: number | null;
}

/**
 * GET /hotels/multistay-booking-context response.
 */
export interface MultistayBookingGroupResponse {
  parentVoyaBookingReference?: string | null;
  legs: MultistayLegSummary[];
}

/**
 * GET /hotels/my-bookings list item (camelCase after RTK `toCamelCase`).
 * Mirrors backend `HotelMyBookingListItem`.
 */
export interface HotelMyBookingListItem {
  voyaBookingReference: string | null;
  action: 'BOOKED' | 'CANCELLED' | 'PENDING';
  timestamp: string;
  dateBooked: string | null;
  /** Major currency units when present on the event (not cents). */
  amount: number | null;
  hotelImageUrl: string | null;
  hotelName: string | null;
  hotelCity: string | null;
  /** YYYY-MM-DD when stored (property-local). Omitted on legacy rows. */
  hotelCheckInDate?: string | null;
  hotelCheckOutDate?: string | null;
  hotelNights?: number | null;
}
