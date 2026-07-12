/** Flight number info from backend (formatted_number, number, airline_prefix) */
export interface FlightNumberInfo {
  formatted_number?: string;
  number?: string;
  airline_prefix?: string;
}

/**
 * Flight segment (single leg of a flight)
 */
export interface FlightSegment {
  departure_date?: string;
  departure_time?: string;
  arrival_date?: string;
  arrival_time?: string;
  duration?: string;
  origin_code?: string;
  origin_city?: string;
  origin_airport?: string;
  destination_code?: string;
  destination_city?: string;
  destination_airport?: string;
  airline_code?: string;
  airline_name?: string;
  /** Airline display name (backend may send "airline" instead of airline_name) */
  airline?: string;
  flight_number?: string;
  /** Backend flight-booker format for display (preferred over flight_number when present) */
  flight_number_info?: FlightNumberInfo;
  // Alternative naming (LangGraph uses departure_* instead of origin_*)
  departure_code?: string;
  departure_city?: string;
  departure_airport?: string;
  /** Layover duration at this stop (e.g. "2h 30m") when available */
  layover_duration?: string;
  /** For layover calculation (backend may send datetime with .value) */
  arrival_datetime?: { value?: string } | string;
  departure_datetime?: { value?: string } | string;
  /** Enriched logo URL from API (FlightLogic airline_list) */
  logo_url?: string;
}

/**
 * Calculated segment data (result of calculateSegment)
 */
export interface SegmentData {
  duration: string;
  stops: number;
  /** When present with layovers, shown as "Flight Duration" (airborne time only) */
  flight_duration?: string;
  departure_date?: string;
  departure_time?: string;
  arrival_date?: string;
  arrival_time?: string;
  origin_code?: string;
  origin_city?: string;
  origin_airport?: string;
  destination_code?: string;
  destination_city?: string;
  destination_airport?: string;
  layovers: FlightSegment[];
}

/**
 * Mapped flight (output of flightMapper)
 */
export interface MappedFlight {
  id?: string;
  price?: number;
  currency?: string;
  is_round_trip: boolean;
  outbound: SegmentData;
  return?: SegmentData;
  segments?: FlightSegment[];
  origin_code?: string;
  destination_code?: string;
  airline_codes?: string[];
  airline_names?: string[];
  /** Single airline code (backend/chat sends airline_code) */
  airline_code?: string;
  /** Single airline name (backend/chat sends airline) */
  airline?: string;
  /** Flight number at flight level (backend/chat) */
  flight_number?: string;
  // Platform fee info
  platform_fee_percentage?: number;
  platform_fee_amount?: number;
  /** Original fare before platform fee (backend sends original_total_fare) */
  original_total_fare?: number;
  original_ticket_amount?: number;
  /** Enriched logo URL from API (for header display) */
  logo_url?: string;
}

/**
 * Flight search summary
 */
export interface FlightSearchSummary {
  total_flights: number;
  direct_count: number;
  price_range: {
    min: number;
    max: number;
  };
  airlines?: string[];
}

/**
 * Flight category (cheapest, fastest, best_value)
 */
export interface FlightCategory {
  flights: MappedFlight[];
}

/**
 * Flight search parameters
 */
export interface FlightSearchParams {
  origin: string;
  destination: string;
  departure_date: string;
  return_date?: string;
  journey_type: 'OneWay' | 'Return' | 'Circle';
  cabin_class?: string;
  passengers?: {
    adults: number;
    children: number;
    infants: number;
  };
  adults?: number;
  children?: number;
  infants?: number;
}

/**
 * Flight search results data (from backend extraData.data)
 */
export interface FlightSearchResultsData {
  summary: FlightSearchSummary;
  /** @deprecated Removed by backend issue #1034 — flights are flat on the envelope. */
  categories?: {
    cheapest: FlightCategory;
    fastest: FlightCategory;
    best_value: FlightCategory;
  };
  search_params: FlightSearchParams;
}

/**
 * Flight search extra data (full extraData from backend)
 */
export interface FlightSearchExtraData {
  data: FlightSearchResultsData;
  flights?: MappedFlight[];
  session_id: string;
}

/**
 * Flight selection response
 */
export interface FlightSelectResponse {
  redirect_url: string;
}

/**
 * Flight search redirect response
 */
export interface FlightSearchRedirectResponse {
  redirect_url: string;
}

/**
 * Flight leg (for UI display in FlightCard and FlightResults)
 */
export interface FlightLeg {
  departure: {
    city: string;
    airport: string;
    date: string;
    time: string;
  };
  arrival: {
    city: string;
    airport: string;
    date: string;
    time: string;
  };
  duration: string;
  totalTimeDisplay?: string | null;
  hasLayover?: boolean;
  stops: number;
  stopsText: string;
  legLabel?: string; // "OUTBOUND", "RETURN", or "LEG N" for multi-city
  airlinesInfo?: Array<{ name: string; code: string; flights: string[]; logoUrl?: string }>; // Airline and flight number info (grouped by airline code)
  segments?: unknown[]; // Original flight segments for detailed display
}
