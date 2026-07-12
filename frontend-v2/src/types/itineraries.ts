/**
 * Trip metadata on saved itineraries from the API.
 * RTK `transformResponse` uses recursive `toCamelCase`, so wire fields are camelCase.
 */
export interface TripMeta {
  origin?: string;
  destination?: string;
  departureDate?: string;
  returnDate?: string;
  adults?: number;
  children?: number;
  infants?: number;
  tripType?: string;
  /** City center from chat itinerary flow; used for map when present. */
  destinationLocation?: TripMetaLocation;
  /**
   * Same coords as `destinationLocation`, snake_case as in chat `trip_meta` / navigation state.
   * When both this and `destinationLocation` are present, map logic prefers this key.
   */
  destination_location?: TripMetaLocation;
  /**
   * Optional origin city-center coords. Symmetric with `destinationLocation`;
   * frontend treats it as optional today because the backend's chat trip_meta
   * does not always emit it. When present, used to pin the origin marker on
   * the flight-search map (with the same stale-itinerary guard as destination).
   */
  originLocation?: TripMetaLocation;
  /** Snake_case variant from chat `trip_meta` / navigation state. */
  origin_location?: TripMetaLocation;
}

/** Nested coords from backend trip_meta (camelCase after RTK toCamelCase). */
export interface TripMetaLocation {
  latitude: number;
  longitude: number;
}

/** @deprecated Use `TripMetaLocation`. Retained for backwards compatibility. */
export type TripMetaDestinationLocation = TripMetaLocation;

import type { FlightRouteLeg, FlightRouteSegment } from './flights';

/** Same wire shape as ``BookingEventResponse`` / ``GET /flights/my-bookings`` (see ``types/flights``). */
export type RouteLeg = FlightRouteLeg;
export type RouteSegment = FlightRouteSegment;

/** Row from booking_events for linked-booking list UI (GET /itineraries, camelCase). */
export interface LinkedBookingEventSummary {
  voyaBookingReference: string;
  eventType: 'FLIGHT' | 'HOTEL';
  timestamp: string;
  amount?: number | null;
  ticketStatus?: string | null;
  airlinePnrCode?: string | null;
  airlinePnrAirlineName?: string | null;
  /** Marketing carrier for list cards; may be set when PNR airline name is absent. */
  primaryMarketingAirlineName?: string | null;
  flightTripType?: 'one_way' | 'round_trip' | 'multi_city' | null;
  routeLegs?: RouteLeg[] | null;
  /** First-hop departure; legacy TTL field, also derivable from routeLegs[0]. */
  departureAirportIata?: string | null;
  /** Legacy flat IATAs on older rows; prefer routeLegs when absent. */
  arrivalAirportIata?: string | null;
  returnDepartureAirportIata?: string | null;
  returnArrivalAirportIata?: string | null;
  hotelReferenceNumber?: string | null;
  dateBooked?: string | null;
}

/** Linked VOYA booking refs from GET /itineraries (camelCase from API). */
export interface LinkedBookings {
  flightVoyaReferences: string[];
  hotelVoyaReferences: string[];
  /** Aligned with flightVoyaReferences (newest first). */
  flightEvents?: LinkedBookingEventSummary[];
  /** Aligned with hotelVoyaReferences (newest first). */
  hotelEvents?: LinkedBookingEventSummary[];
}

/** Saved itinerary from API */
export interface SavedItinerary {
  id: string;
  structuredItinerary: Record<string, unknown>;
  tripMeta: TripMeta | null;
  createdAt: string;
  /** Last server write time (create or upsert); mirrors MongoDB ``updated_at``. */
  updatedAt: string;
  linkedBookings?: LinkedBookings;
}

/** Request body for saving an itinerary */
export interface SaveItineraryRequest {
  structuredItinerary: Record<string, unknown>;
  tripMeta?: TripMeta | null;
}
