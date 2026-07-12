/**
 * Form field definition for dynamic forms
 */
export interface FormField {
  parameter: string;
  label: string;
  type:
    | 'text'
    | 'textarea'
    | 'number'
    | 'date'
    | 'select'
    | 'radio'
    | 'checkbox'
    | 'multiCheckbox'
    | 'switch'
    | 'file'
    | 'autocomplete';
  required?: boolean;
  value?: string | number | boolean | string[];
  options?: Array<{ label: string; value: string }>;
  placeholder?: string;
  min?: number;
  max?: number;
  validation?: {
    pattern?: string;
    message?: string;
  };
}

/**
 * Form definition for dynamic chat forms
 */
export interface FormDefinition {
  title?: string;
  description?: string;
  fields: FormField[];
  submitLabel?: string;
  actionMessage?: string;
}

/**
 * Chat message suggestion
 */
export interface ChatSuggestion {
  title: string;
  command: string;
}

/**
 * Chat message content
 */
export interface ChatMessageContent {
  messages: Array<{ text: string }>;
  suggestions?: ChatSuggestion[];
  form?: FormDefinition;
}

/**
 * Message types
 */
export type ChatMessageType =
  | 'message'
  | 'typing'
  | 'flight_search_results'
  | 'multicity_flight_search_results'
  | 'flight_date_range_results'
  | 'hotel_search_results'
  | 'itinerary_results';

/**
 * Flight search extra data structure
 */
export interface FlightSearchExtraData {
  data: {
    summary: {
      total_flights: number;
      direct_count: number;
      price_range: { min: number; max: number };
      airlines?: string[];
    };
    /** @deprecated Removed by backend issue #1034 — read flat `flights[]` instead. */
    categories?: {
      cheapest: { flights: unknown[] };
      fastest: { flights: unknown[] };
      best_value: { flights: unknown[] };
    };
    search_params: {
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
      origin_location?: DestinationLocation;
      destination_location?: DestinationLocation;
    };
  };
  flights?: unknown[];
  session_id: string;
  origin_location?: DestinationLocation;
  destination_location?: DestinationLocation;
}

/** Optional destination coordinates from backend (city center). Used for map centering. */
export interface DestinationLocation {
  latitude: number;
  longitude: number;
}

/**
 * Itinerary search extra data structure.
 *
 * Canonical contract:
 * - `structured_itinerary` is at `data` top-level (service.py spreads `**metadata` so
 *   `metadata.structured_itinerary` is promoted directly into `ChatResponse.data`).
 * - Keys inside the payload use camelCase: `itineraryItems`, `footerSectionTitle`,
 *   `localExperiences`, `budgetSnapshot`.
 * - Trip meta fields (origin, destination, dates) are also at `data` top-level.
 */
export interface ItinerarySearchExtraData {
  message?: string;
  structured_itinerary?: Record<string, unknown>;
  session_id?: string;
  stage?: string;
  saved_itinerary_id?: string;
  origin?: string;
  destination?: string;
  departure_date?: string;
  return_date?: string;
  adults?: number;
  children?: number;
  infants?: number;
  trip_type?: string;
  /** Optional destination coordinates for map (city center). Fallback to default coordinates when missing. */
  destination_location?: DestinationLocation;
  /** Optional origin coordinates for map (trip departure city). */
  origin_location?: DestinationLocation;
  /**
   * Personalized itinerary (#1038): full best-value-sorted flight list. The
   * LLM never saw these — they ride on the response side-channel for the
   * "Recommended flights" rail and (with the stitcher) Day 1 / Day N
   * inline cards. ``flights[0]`` is the same flight stitched into the day
   * plan; ``flights[1:]`` are the alternatives the rail renders.
   */
  flights?: Record<string, unknown>[];
  /** Personalized itinerary (#1038): full best-value-sorted hotel list. */
  hotels?: Record<string, unknown>[];
  /** FlightLogic session for revalidation/booking from the pre-fetched list. */
  flight_session_id?: string | null;
  /** FlightLogic session for revalidation/booking from the pre-fetched hotels. */
  hotel_session_id?: string | null;
  /** Search params the orchestrator used — needed to hydrate the FE
   * recommendations slice so the user's filter chips/headers match. */
  flight_search_params?: Record<string, unknown> | null;
  hotel_search_params?: Record<string, unknown> | null;
}

/**
 * Hotel search extra data structure
 */
export interface HotelSearchExtraData {
  data: {
    summary: {
      total_hotels: number;
      price_range: { min: number; max: number };
    };
    /** @deprecated Removed by backend issue #1034 — read flat `hotels[]` instead. */
    categories?: {
      cheapest: { hotels: unknown[] };
      highest_rated: { hotels: unknown[] };
      best_value: { hotels: unknown[] };
    };
    search_params: {
      destination: string;
      check_in_date: string;
      check_out_date: string;
      rooms: number;
      adults: number;
      children?: number;
    };
  };
  hotels?: unknown[];
  session_id: string;
}

/**
 * Chat message structure
 *
 * Uses a flexible extraData type internally.
 * Use type guards (isFlightSearchResults, isHotelSearchResults, isItinerarySearchResults) for type-safe access.
 */
export interface ChatMessage {
  _id: string;
  content: ChatMessageContent;
  from: 'bot' | 'user';
  type: ChatMessageType;
  contentType: 'message' | 'form';
  timestamp: Date | string;
  intentName?: string;
  messageId?: string;
  extraData?: Record<string, unknown>;
  status?: number;
}

/**
 * Type guard: Check if message has flight search results
 */
export function isFlightSearchResults(
  message: ChatMessage
): message is ChatMessage & { type: 'flight_search_results'; extraData: FlightSearchExtraData } {
  return message.type === 'flight_search_results' && message.extraData !== undefined;
}

/**
 * Type guard: Check if message has hotel search results
 */
export function isHotelSearchResults(
  message: ChatMessage
): message is ChatMessage & { type: 'hotel_search_results'; extraData: HotelSearchExtraData } {
  return message.type === 'hotel_search_results' && message.extraData !== undefined;
}

/**
 * Type guard: Check if message has itinerary search results
 */
export function isItinerarySearchResults(
  message: ChatMessage
): message is ChatMessage & {
  type: 'itinerary_results';
  extraData: ItinerarySearchExtraData;
} {
  return message.type === 'itinerary_results' && message.extraData !== undefined;
}

/**
 * Type guard: Check if message is typing indicator
 */
export function isTypingMessage(message: ChatMessage): boolean {
  return message.type === 'typing';
}

/**
 * Type guard: Check if message is regular text
 */
export function isTextMessage(message: ChatMessage): boolean {
  return message.type === 'message';
}

/**
 * Chat API response (snake_case to match API)
 */
export interface ChatResponse {
  message: string;
  message_id?: string;
  chat_id: string;
  intent_name: string;
  confidence: number;
  type: string;
  data?: Record<string, unknown>;
  event?: ChatEvent;
  /** Guest-only: JWT for loading Places images on `/api/public/places/photos/.../media`. */
  places_session_token?: string | null;
}

/**
 * Chat event for navigation/actions
 */
export interface ChatEvent {
  event_name: 'Activities' | 'Food' | 'Accommodation' | 'Travel' | 'Itinerary';
  event_data: Record<string, unknown>;
}

/**
 * Chat message request (snake_case for API)
 */
export interface ChatMessageRequest {
  message: string;
  chat_id?: string;
}

/**
 * Chat history response (snake_case)
 */
export interface ChatHistoryResponse {
  chat_id: string;
  messages: ChatMessage[];
  count: number;
}

/**
 * Chat feedback request (snake_case)
 */
export interface ChatFeedbackRequest {
  message_id: string;
  chat_id?: string;
  feedback_type: 'thumbs_up' | 'thumbs_down';
  comment?: string;
}

/**
 * Frontend config from backend API (snake_case to match API)
 */
export interface FrontendConfigResponse {
  chat_feedback_enabled: boolean;
  public_chat_enabled: boolean;
  langgraph_flights_enabled: boolean;
  langgraph_hotels_enabled: boolean;
  environment: string;
  /** Promo / G2A voucher reservation window in minutes (discount service TTL). */
  voucher_reservation_ttl_minutes: number;
}

/**
 * Frontend config for internal use (camelCase)
 */
export interface FrontendConfig {
  chatFeedbackEnabled: boolean;
  publicChatEnabled: boolean;
  langgraphFlightsEnabled: boolean;
  langgraphHotelsEnabled: boolean;
  environment: string;
  /** From GET /config; used for voucher copy. Omitted until config is loaded. */
  voucherReservationTtlMinutes?: number;
}

/**
 * Feedback submission state
 */
export type FeedbackState = Record<string, 'thumbs_up' | 'thumbs_down'>;

// ---------------------------------------------------------------------------
// Multi-conversation types
// ---------------------------------------------------------------------------

/**
 * POST /api/chat/claim — request (snake_case to match API).
 */
export interface ClaimChatRequest {
  chat_id?: string;
  max_age_minutes?: number;
}

export type ClaimChatStatus =
  | 'claimed'
  | 'already_claimed'
  | 'nothing_to_claim'
  | 'rejected_fingerprint_mismatch'
  | 'rejected_too_old'
  | 'rejected_too_large'
  | 'rejected_owned_by_other_user';

export interface ClaimChatResponse {
  status: ClaimChatStatus;
  chat_id: string | null;
  message_count: number;
}

/**
 * Conversation metadata for sidebar display (snake_case — matches API)
 */
export interface ConversationMeta {
  chat_id: string;
  name: string;
  message_count: number;
  last_message_at: string | null;
  last_message_preview: string;
  created_at: string | null;
}

/**
 * Response from GET /api/chat/conversations
 */
export interface ConversationListResponse {
  conversations: ConversationMeta[];
  total: number;
  has_more: boolean;
}
