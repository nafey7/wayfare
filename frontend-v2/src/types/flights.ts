/**
 * Currency amount conventions (frontend-v2 flights/payments)
 * --------------------------------------------------------
 * - **Major units (base currency):** Display amounts, e.g. 199.50 for $199.50.
 *   Used by: API fare_totals (total_fare.amount), FlightPrice, FilterableFlight.price.
 * - **Cents (minor units):** Integer amounts for Revolut and booking totals, e.g. 19950 for $199.50.
 *   Used by: FlightBookingResponse.totalAmount, Redux bookingResult.totalAmount,
 *   PaymentIntentCreateRequest.booking_amount, and all payment API amount fields.
 * - **GET /flights/my-bookings:** `amount` on each item is major units when stored on booking_events (not cents).
 */

/**
 * Flight search request
 */
export interface FlightSearchRequest {
  originIata: string;
  destinationIata: string;
  departureDate: string;
  returnDate?: string;
  adults: number;
  children?: number;
  infants?: number;
  cabinClass?: CabinClass;
}

/**
 * Cabin class options
 */
export type CabinClass = 'economy' | 'premium_economy' | 'business' | 'first';

/**
 * Flight segment (single leg)
 */
export interface FlightSegment {
  airline: string;
  airlineName: string;
  flightNumber: string;
  departureAirport: string;
  departureCity: string;
  departureTime: string;
  arrivalAirport: string;
  arrivalCity: string;
  arrivalTime: string;
  duration: number;
  cabinClass: string;
  aircraft?: string;
}

/**
 * Flight option (may have multiple segments)
 */
export interface FlightOption {
  id: string;
  fareSourceCode: string;
  segments: FlightSegment[];
  totalDuration: number;
  stops: number;
  price: FlightPrice;
  baggageAllowance?: BaggageAllowance;
  refundable: boolean;
}

/**
 * Flight price breakdown.
 * All amount fields are in base currency (major units), e.g. 199.50 for $199.50.
 */
export interface FlightPrice {
  currency: string;
  /** Total price in base currency (major units) */
  totalAmount: number;
  /** Base fare in base currency (major units) */
  baseAmount: number;
  /** Tax in base currency (major units) */
  taxAmount: number;
  perPassenger: {
    adult: number;
    child?: number;
    infant?: number;
  };
}

/**
 * Baggage allowance
 */
export interface BaggageAllowance {
  cabin: {
    pieces: number;
    weight?: number;
    unit?: string;
  };
  checked?: {
    pieces: number;
    weight?: number;
    unit?: string;
  };
}

/**
 * Flight search response
 */
export interface FlightSearchResponse {
  sessionId: string;
  flights: FlightOption[];
  searchParams: FlightSearchRequest;
  curatedFlights?: {
    cheapest?: FlightOption;
    fastest?: FlightOption;
    bestValue?: FlightOption;
  };
}

/**
 * Flight select request
 */
export interface FlightSelectRequest {
  sessionId: string;
  flightId: string;
  adults: number;
  children?: number;
  infants?: number;
}

/**
 * Passenger details for booking
 */
export interface PassengerDetails {
  type: 'adult' | 'child' | 'infant';
  title: 'Mr' | 'Mrs' | 'Ms' | 'Miss' | 'Dr';
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  nationality: string;
  passportNumber?: string;
  passportExpiry?: string;
  passportCountry?: string;
}

/**
 * Contact information for booking
 */
export interface ContactInformation {
  email: string;
  phone?: string;
}

/**
 * Flight booking request
 */
export interface FlightBookingRequest {
  sessionId: string;
  fareSourceCode: string;
  contactInformation: ContactInformation;
  passengers: PassengerDetails[];
  paymentIntentId?: string;
}

/**
 * Flight booking response
 */
export interface FlightBookingResponse {
  voyaBookingReference: string;
  externalBookingReference?: string;
  status: BookingStatus;
  /** Total amount in cents (minor units), e.g. 19950 for $199.50 */
  totalAmount: number;
  currency: string;
  passengers: PassengerDetails[];
  flights: FlightOption[];
}

/**
 * Booking status
 */
export type BookingStatus = 'pending' | 'confirmed' | 'ticketed' | 'cancelled' | 'failed';

/** Leg-level snapshot from trip_details sync (`flight_leg_summaries` on booking_events). */
export interface FlightLegSummaryItem {
  departureDate: string;
  originIata: string;
  destinationIata: string;
}

/**
 * GET /flights/my-bookings item after RTK `toCamelCase` (matches BookingEventResponse).
 */
export interface FlightRouteSegment {
  departureIata: string;
  arrivalIata: string;
}

export interface FlightRouteLeg {
  legIndex: number;
  departureIata: string;
  arrivalIata: string;
  segmentCount: number;
  segments: FlightRouteSegment[];
}

export interface FlightBookingListItem {
  id: string;
  userId: string;
  voyaBookingReference: string;
  externalBookingReference: string;
  action: 'BOOKED' | 'CANCELLED' | 'PENDING';
  timestamp: string;
  eventType: 'FLIGHT' | 'HOTEL';
  airlinePnrCode?: string | null;
  airlinePnrAirlineName?: string | null;
  /** Legacy TTL / first hop; prefer routeLegs when present. */
  departureAirportIata?: string | null;
  flightTripType?: 'one_way' | 'round_trip' | 'multi_city' | null;
  routeLegs?: FlightRouteLeg[] | null;
  primaryMarketingAirlineName?: string | null;
  ticketStatus?: string | null;
  /** Total amount in major units when stored (e.g. USD), same as booking_events.amount */
  amount?: number | null;
  dateBooked?: string | null;
  parentVoyaBookingReference?: string | null;
  multistayLegIndex?: number | null;
  carrierType?: 'GDS' | 'LCC' | null;
  /** Populated after trip_details sync; used for travel dates in profile list. */
  flightLegSummaries?: FlightLegSummaryItem[] | null;
  /** One YYYY-MM-DD per segment (UTC), trip_details order; after sync. */
  flightSegmentDepartureDates?: string[] | null;
}

/**
 * Airport option (for autocomplete component)
 */
export interface AirportOption {
  iata: string;
  name: string;
  city: string;
  state?: string;
  country: string;
  isCityOption?: boolean;
}

/**
 * Trip type for search form
 */
export type TripType = 'one-way' | 'round-trip' | 'multi-city';

/**
 * Cabin class for UI (capitalized display format)
 */
export type CabinClassUI = 'Economy' | 'Business' | 'First' | 'Premium Economy';

/**
 * Travellers data for search form
 */
export interface TravellersData {
  adults: number | null;
  children: number | null;
  infants: number | null;
  cabinClass: CabinClassUI | null;
}

/**
 * Flight segment for search form (component state)
 */
export interface FlightSearchSegment {
  from: string;
  to: string;
  date: Date | null;
  /** Set when user picks from airport autocomplete (resolution / city-wise search) */
  fromAirport?: AirportOption | null;
  toAirport?: AirportOption | null;
}

/**
 * Flight search params for component (with Date objects)
 */
export interface FlightSearchParamsUI {
  from: string;
  to: string;
  date: Date | null;
  returnDate?: Date | null;
  segments?: FlightSearchSegment[]; // For multi-city
  travellers: TravellersData;
  tripType: TripType | null;
  originIsCity?: boolean;
  destinationIsCity?: boolean;
  originIata?: string;
  destinationIata?: string;
  /** Selected airport from autocomplete (for resolution - mirrors flight-booker) */
  fromAirport?: AirportOption | null;
  /** Selected airport from autocomplete (for resolution - mirrors flight-booker) */
  toAirport?: AirportOption | null;
}
