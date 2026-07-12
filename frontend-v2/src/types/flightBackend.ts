/**
 * Backend (snake_case) flight API types.
 * Matches backend_python/app/domains/flight/schemas.py response/request shapes.
 * Used to type API responses and remove `as any` / `any` in flight features.
 */

/** Origin/destination segment for search request */
export interface OriginDestinationSegmentBackend {
  departure_date: string;
  origin_airport: { iata_code: string };
  destination_airport: { iata_code: string };
}

/** Flight search request body (snake_case) sent to POST /flights/search */
export interface FlightSearchRequestBackend {
  journey_type: 'OneWay' | 'Return' | 'Circle';
  origin_destination_info: OriginDestinationSegmentBackend[];
  adults: number;
  children: number;
  infants: number;
  cabin_class: string;
  direct_flight?: number;
  city_wise_search_origin?: boolean;
  city_wise_search_destination?: boolean;
  /** Number of flights to revalidate after search (0–10); omit to skip revalidation */
  revalidate_flights_count?: number;
}

/** Error detail item (snake_case) — matches backend ErrorDetails when present on a multicity leg */
export interface FlightSearchErrorDetailBackend {
  message?: string;
  code?: string;
  [key: string]: unknown;
}

/** One leg of a parallel multicity (Circle) search (snake_case) */
export interface MulticityLegSearchResultBackend {
  leg_index: number;
  origin: string;
  destination: string;
  /** ISO date string from API */
  departure_date: string;
  session_id: string;
  supplier: string;
  fare_itineraries: FareItineraryBackend[];
  inbound_fare_itineraries?: FareItineraryBackend[] | null;
  errors?: FlightSearchErrorDetailBackend[] | null;
}

/** Flight search response (snake_case) from POST /flights/search */
export interface FlightSearchResponseBackend {
  session_id: string;
  fare_itineraries: FareItineraryBackend[];
  inbound_fare_itineraries?: FareItineraryBackend[] | null;
  supplier?: string;
  errors?: unknown[] | null;
  /** Parallel OneWay results per leg; Circle searches only */
  multicity_legs?: MulticityLegSearchResultBackend[] | null;
}

/** Single fare itinerary (one flight option). */
export interface FareItineraryBackend {
  flight_legs: FlightLegBackend[];
  /** Optional on frontend for defensive coding (partial/error responses); backend requires it. */
  pricing?: FarePricingBackend;
  journey_type?: string;
  sequence_number?: string;
  ticket_type?: string;
  validating_airline?: { airline_name?: string; iata_code?: string };
  requires_passport?: boolean;
}

/** Flight leg (outbound, return, or multi-city leg) */
export interface FlightLegBackend {
  flight_segments: FlightSegmentBackend[];
  total_stops?: number;
}

/** Minimal segment shape for processLeg and display. Backend DateTime serializes as { value: "2026-02-06T20:00:00" }. */
export interface FlightSegmentBackend {
  departure_datetime?: { value?: string } | string;
  arrival_datetime?: { value?: string } | string;
  flight_duration?: { total_minutes?: number };
  departure_airport?: { iata_code?: string; city_name?: string };
  arrival_airport?: { iata_code?: string; city_name?: string };
  marketing_airline?: { airline_name?: string; iata_code?: string };
  operating_airline?: { airline_name?: string; iata_code?: string };
  marketing_flight_number?: { formatted_number?: string };
}

/** Shared pricing totals (fare_totals or validated_fare_totals) */
export interface FareTotalsLike {
  total_fare?: { amount?: string | number; currency?: string };
  original_total_fare?: { amount?: string | number };
  base_fare?: { amount?: string | number };
  total_tax?: { amount?: string | number };
  platform_fee_percentage?: number;
}

/** Pricing block on fare itinerary (search response) */
export interface FarePricingBackend {
  fare_source_code?: string;
  fare_type?: string;
  fare_totals?: FareTotalsLike;
  validated_fare_totals?: FareTotalsLike; // present after revalidate
  passenger_fare_breakdown?: PassengerFareBreakdownItemBackend[];
  is_refundable?: boolean;
}

/** Penalty details (cancellation/change). All fields optional on frontend for defensive coding; backend schema requires them. */
export interface PenaltyDetailsBackend {
  cancellation_penalty?: { amount?: string | number; currency?: string };
  change_penalty?: { amount?: string | number; currency?: string };
  is_cancellation_allowed?: boolean;
  is_change_allowed?: boolean;
}

/** Passenger type breakdown item (ADT, CHD, INF) */
export interface PassengerFareBreakdownItemBackend {
  passenger_type_info?: {
    passenger_type?: string;
    passenger_count?: number;
    quantity?: number; // alternative field name from API
  };
  individual_passenger_fare?: {
    total_fare?: { amount?: string | number; currency?: string };
    total_tax?: { amount?: string | number };
    base_fare?: { amount?: string | number };
  };
  penalty_details?: PenaltyDetailsBackend;
}

/** Fare rules response from POST /flights/fare-rules */
export interface FlightFareRulesResponseBackend {
  session_id: string;
  fare_source_code: string;
  fare_rules?: Array<{ rule_description?: string }>;
  baggage_information?: unknown[];
  inbound_fare_data?: {
    fare_rules?: Array<{ rule_description?: string }>;
  } | null;
  errors?: unknown[] | null;
}

/** Validated fare itinerary (revalidate response item) */
export interface ValidatedFareItineraryBackend {
  flight_legs: FlightLegBackend[];
  updated_pricing?: UpdatedFarePricingBackend;
  /** Present on search itinerary; revalidate uses updated_pricing */
  pricing?: FarePricingBackend;
}

/** Updated pricing after revalidation */
export interface UpdatedFarePricingBackend {
  fare_type?: string;
  fare_totals?: FareTotalsLike; // fallback
  validated_fare_totals?: FareTotalsLike;
  passenger_fare_breakdown?: PassengerFareBreakdownItemBackend[];
  is_refundable?: boolean;
}

/** Revalidate response from POST /flights/revalidate */
export interface FlightRevalidateResponseBackend {
  session_id: string;
  fare_source_code: string;
  return_fare_source_code?: string | null;
  is_fare_available: boolean;
  validated_fare_itineraries: ValidatedFareItineraryBackend[];
  available_extra_services?: unknown | null;
  errors?: unknown[] | null;
}

/** Processed leg display data (shared by FlightDetailsPage and FlightSearchPage). */
export interface ProcessedLeg {
  legLabel: string;
  departure: {
    city: string;
    airport: string;
    time: string;
    date: string;
  };
  arrival: {
    city: string;
    airport: string;
    time: string;
    date: string;
  };
  duration: string;
  totalTimeDisplay: string | null;
  hasLayover: boolean;
  stops: number;
  stopsText: string;
  segments: unknown[];
  airlinesInfo: Array<{ name: string; code: string; flights: string[] }>;
}

/** Selected flight card data (built in FlightSearchPage from itinerary + processed legs). Uses camelCase itinerary after transform. */
export interface SelectedFlightDataFromSearch {
  id: string;
  aircraftName: string;
  flightNumber: string;
  tags: string[];
  passengers: number;
  passengerCounts: { adults: number; children: number; infants: number };
  legs: ProcessedLeg[];
  price: number;
  _originalItinerary?: FareItineraryCamel;
}

/** Booking response from POST /flights/book. Snake_case from backend; camelCase included for defensive coding. */
export interface FlightBookingResultBackend {
  voya_booking_reference?: string;
  voyaBookingReference?: string;
  external_booking_reference?: string;
  externalBookingReference?: string;
  booking_status?: string;
  status?: string;
  total_amount?: number;
  totalAmount?: number;
  currency?: string;
}

// ---------------------------------------------------------------------------
// Frontend (camelCase) – shapes after API transformResponse (toCamelCase).
// Use these for Redux state, processLeg input, and components.
// ---------------------------------------------------------------------------

/**
 * Airline-like value for logo extraction. Extra keys allowed; only `logoUrl` and
 * `logo_url` are read by `getAirlineLogoUrl` in flightUtils.
 */
export type AirlineLogoSource = {
  logoUrl?: string;
  logo_url?: string;
  [key: string]: unknown;
};

/** Airline on a segment after transform (names/codes + optional logo fields from API). */
export interface FlightSegmentAirlineCamel extends AirlineLogoSource {
  airlineName?: string;
  iataCode?: string;
}

/** Segment shape after transform; DateTime is { value?: string } | string. */
export interface FlightSegmentCamel {
  departureDatetime?: { value?: string } | string;
  arrivalDatetime?: { value?: string } | string;
  flightDuration?: { totalMinutes?: number };
  departureAirport?: { iataCode?: string; cityName?: string };
  arrivalAirport?: { iataCode?: string; cityName?: string };
  marketingAirline?: FlightSegmentAirlineCamel;
  operatingAirline?: FlightSegmentAirlineCamel;
  marketingFlightNumber?: { formattedNumber?: string };
  cabinClass?: string;
}

/** Leg shape after transform (camelCase). */
export interface FlightLegCamel {
  flightSegments: FlightSegmentCamel[];
  totalStops?: number;
}

/**
 * Segment shape returned by the trip-details API (camelCase post-transform).
 * Used by `/flights/bookings/:ref` and `BookingDetailsSegmentsCard`.
 */
export interface TripDetailsSegmentCamel {
  segmentId?: number;
  departureDatetime?: string | { value?: string };
  arrivalDatetime?: string | { value?: string };
  departureAirport?: { iataCode?: string; cityName?: string; airportName?: string };
  arrivalAirport?: { iataCode?: string; cityName?: string; airportName?: string };
  marketingFlightNumber?: { flightNumber?: string; formattedNumber?: string };
  marketingAirline?: { airlineName?: string; iataCode?: string };
  operatingAirline?: { airlineName?: string; iataCode?: string };
}

/** Fare totals (camelCase) after transform. */
export interface FareTotalsCamel {
  totalFare?: { amount?: string | number; currency?: string };
  originalTotalFare?: { amount?: string | number };
  baseFare?: { amount?: string | number };
  totalTax?: { amount?: string | number };
  platformFeePercentage?: number;
}

/** Pricing block (camelCase) after transform. */
export interface FarePricingCamel {
  fareSourceCode?: string;
  fareType?: string;
  fareTotals?: FareTotalsCamel;
  validatedFareTotals?: FareTotalsCamel;
  passengerFareBreakdown?: PassengerFareBreakdownItemCamel[];
  isRefundable?: boolean;
}

/** Penalty details (camelCase) after transform. */
export interface PenaltyDetailsCamel {
  cancellationPenalty?: { amount?: string | number; currency?: string };
  changePenalty?: { amount?: string | number; currency?: string };
  isCancellationAllowed?: boolean;
  isChangeAllowed?: boolean;
}

export interface PassengerFareBreakdownItemCamel {
  passengerTypeInfo?: {
    passengerType?: string;
    passengerCount?: number;
    quantity?: number;
  };
  individualPassengerFare?: {
    totalFare?: { amount?: string | number; currency?: string };
    totalTax?: { amount?: string | number };
    baseFare?: { amount?: string | number };
  };
  penaltyDetails?: PenaltyDetailsCamel;
}

/** Validated itinerary item (camelCase) from revalidate response. */
export interface ValidatedFareItineraryCamel {
  flightLegs: FlightLegCamel[];
  updatedPricing?: FarePricingCamel;
  pricing?: FarePricingCamel;
}

/** Revalidate response (camelCase) – use for Redux revalidationResponse. */
export interface FlightRevalidateResponseCamel {
  sessionId: string;
  fareSourceCode: string;
  returnFareSourceCode?: string | null;
  isFareAvailable: boolean;
  validatedFareItineraries: ValidatedFareItineraryCamel[];
  availableExtraServices?: unknown | null;
  errors?: unknown[] | null;
}

/** Fare rules response (camelCase) – use for Redux fareRules. */
export interface FlightFareRulesResponseCamel {
  sessionId: string;
  fareSourceCode: string;
  fareRules?: Array<{ ruleDescription?: string }>;
  baggageInformation?: unknown[];
  inboundFareData?: { fareRules?: Array<{ ruleDescription?: string }> } | null;
  errors?: unknown[] | null;
}

/** Single fare itinerary (camelCase) from search response. */
export interface FareItineraryCamel {
  flightLegs: FlightLegCamel[];
  pricing?: FarePricingCamel;
  journeyType?: string;
  sequenceNumber?: string;
  ticketType?: string;
  validatingAirline?: { airlineName?: string; iataCode?: string };
  requiresPassport?: boolean;
}

/** One multicity leg after transformResponse (camelCase) */
export interface MulticityLegSearchResultCamel {
  legIndex: number;
  origin: string;
  destination: string;
  departureDate: string;
  sessionId: string;
  supplier: string;
  fareItineraries: FareItineraryCamel[];
  inboundFareItineraries?: FareItineraryCamel[] | null;
  errors?: Array<{ message?: string; code?: string; [key: string]: unknown }> | null;
}

/** Search response (camelCase) after transform. */
export interface FlightSearchResponseCamel {
  sessionId: string;
  fareItineraries: FareItineraryCamel[];
  inboundFareItineraries?: FareItineraryCamel[] | null;
  supplier?: string;
  errors?: unknown[] | null;
  multicityLegs?: MulticityLegSearchResultCamel[] | null;
}
