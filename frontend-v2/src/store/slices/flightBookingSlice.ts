import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import { readWithTTL, writeWithTTL, removeWithTTL, TTL_24H_MS } from '@/utils/localStorageWithTTL';
import type { MappedFlight, FlightSearchParams } from '@/types/flight';
import type { TripType, TravellersData, AirportOption } from '@/types/flights';
import type {
  FlightFareRulesResponseCamel,
  FlightRevalidateResponseCamel,
  FlightSearchResponseCamel,
  SelectedFlightDataFromSearch,
} from '@/types/flightBackend';
import type { FlightFilterState } from '@/features/flights/utils/flightFilters';
import { defaultFlightFilterState } from '@/features/flights/utils/flightFilters';

/** Per-leg selection for multicity (Circle) parallel search — at most one entry per leg index; any non-empty subset may proceed to checkout */
export interface MulticityLegSelection {
  legIndex: number;
  sessionId: string;
  fareSourceCode: string;
  selectedFlightData: SelectedFlightDataFromSearch;
  revalidateResponse: FlightRevalidateResponseCamel;
}

/** Per-leg booking outcome after multicity checkout (confirmation / details UI). */
export interface MulticityLegBookingResult {
  legIndex: number;
  voyaBookingReference: string;
  externalBookingReference?: string;
}

/** Per-leg selection for multicity (Circle) parallel search — at most one entry per leg index; any non-empty subset may proceed to checkout */
export interface MulticityLegSelection {
  legIndex: number;
  sessionId: string;
  fareSourceCode: string;
  selectedFlightData: SelectedFlightDataFromSearch;
  revalidateResponse: FlightRevalidateResponseCamel;
}

/** Per-leg booking outcome after multicity checkout (confirmation / details UI). */
export interface MulticityLegBookingResult {
  legIndex: number;
  voyaBookingReference: string;
  externalBookingReference?: string;
}

/**
 * Flight booking wizard steps
 */
export type BookingStep =
  | 'search'
  | 'results'
  | 'rules'
  | 'passengers'
  | 'review'
  | 'payment'
  | 'confirmation';

/**
 * Passenger details for booking
 */
export interface PassengerDetails {
  type: 'adult' | 'child' | 'infant';
  title: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  nationality: string;
  passportNumber?: string;
  passportExpiry?: string;
  passportCountry?: string;
}

/**
 * Contact info for booking (matches backend dev_ui passenger_data.contact)
 */
export interface BookingContact {
  email: string;
  country_code: string; // dial code e.g. "1", "44" (prefix with + for API)
  phone: string; // number without country code
}

/**
 * Airport option (serializable version for storage)
 * Based on AirportOption from @/types/flights
 */
export interface SerializableAirportOption {
  iata: string;
  name: string;
  city: string;
  state?: string;
  country: string;
  isCityOption?: boolean;
}

// Re-export for convenience
export type { AirportOption };

/**
 * Flight segment (serializable version for storage)
 */
export interface SerializableFlightSegment {
  from: string;
  to: string;
  date: string | null; // ISO date string
  fromAirport?: SerializableAirportOption;
  toAirport?: SerializableAirportOption;
}

// Re-export shared types for convenience
export type { TripType, TravellersData };

/**
 * Form-level search parameters (component state)
 */
export interface FlightSearchFormParams {
  tripType: TripType | null;
  from: string;
  to: string;
  fromAirport?: SerializableAirportOption;
  toAirport?: SerializableAirportOption;
  date: string | null; // ISO date string
  returnDate: string | null; // ISO date string
  travellers: TravellersData;
  segments?: SerializableFlightSegment[]; // For multi-city
  originIsCity?: boolean;
  destinationIsCity?: boolean;
}

// Storage keys
const SEARCH_FORM_PARAMS_KEY = 'flightSearchFormParams';

function loadSearchFormParams(): FlightSearchFormParams | null {
  return readWithTTL<FlightSearchFormParams>(SEARCH_FORM_PARAMS_KEY);
}

function saveSearchFormParams(params: FlightSearchFormParams | null) {
  if (params) {
    writeWithTTL(SEARCH_FORM_PARAMS_KEY, params, TTL_24H_MS);
  } else {
    removeWithTTL(SEARCH_FORM_PARAMS_KEY);
  }
}

/**
 * Get default search form params
 */
/**
 * Default form params for a "fresh" state (e.g. on new chat).
 *
 * All user-selectable fields default to `null` / empty so the unified-header
 * search chips render placeholders ("Trip type", "Cabin", "Travellers", "Select
 * dates") rather than carrying values from a previous session. The chat
 * hydration layer (see `chatSearchParamsToFormParams`) populates everything
 * when chat returns flight_search_results or itinerary_results.
 *
 * If product later prefers minimum-viable defaults instead of nulls (e.g.
 * `adults: 1`, `tripType: 'one-way'`, `cabinClass: 'Economy'`), change them
 * here — every consumer already null-guards.
 */
function getDefaultSearchFormParams(): FlightSearchFormParams {
  return {
    tripType: null,
    from: '',
    to: '',
    date: null,
    returnDate: null,
    travellers: {
      adults: null,
      children: null,
      infants: null,
      cabinClass: null,
    },
  };
}

const persistedFormParams = loadSearchFormParams();

/**
 * Flight booking state
 */
export interface FlightBookingState {
  // Current step in booking flow
  currentStep: BookingStep;

  // Search parameters (API format)
  searchParams: FlightSearchParams | null;

  // Form-level search parameters (component state)
  searchFormParams: FlightSearchFormParams;

  // Selected flight
  selectedFlight: MappedFlight | null;
  sessionId: string | null;
  fareSourceCode: string | null;

  // Fare rules (camelCase from API transformResponse)
  fareRules: FlightFareRulesResponseCamel | null;

  // Passenger details
  passengers: PassengerDetails[];

  // Contact info (matches backend dev_ui passenger_data.contact)
  contact: BookingContact;

  // Optional postal code for booking request
  postalCode: string | null;

  // Booking status
  loading: boolean;
  error: string | null;

  // Booking confirmation
  bookingReference: string | null;

  // Payment and booking result (totalAmount in cents – see types/flights.ts conventions)
  bookingResult: {
    voyaBookingReference: string;
    externalBookingReference?: string;
    status: string;
    /** Total amount in cents (minor units), e.g. 19950 for $199.50 */
    totalAmount: number;
    currency: string;
  } | null;
  paymentIntentId: string | null;
  isLCC: boolean; // true if fare_type === 'WebFare'
  revalidationResponse: FlightRevalidateResponseCamel | null;

  /** Selected flight card data from search (for tab-switch persistence) */
  selectedFlightData: SelectedFlightDataFromSearch | null;

  // Flight search results filters (persists on back/forward)
  flightFilters: FlightFilterState;

  /** Slot index → saved passenger id (backend resolves travel_documents) */
  savedPassengerIds: Record<number, string>;

  /** Incremented when chip dialogs apply/confirm – triggers search from FlightSearchPage */
  searchTriggerFromChips: number;

  /** Multicity: leg index → selected fare + revalidation for that leg */
  multicitySelectedLegs: Record<number, MulticityLegSelection>;

  /** Set when starting multicity review/payment; shared parent for all leg booking events */
  multicityGroupReference: string | null;

  /** After successful multicity payment: one VOYA ref per leg (order matches leg indices) */
  multicityLegBookingResults: MulticityLegBookingResult[] | null;

  /** Multi-city route editor dialog (opened from search bar or dates chip) */
  flightRouteModalOpen: boolean;

  /** In-memory results cache (5 min TTL, cleared on logout / hard refresh). */
  cachedFlightResults: FlightSearchResponseCamel | null;
  flightResultsCacheTimestamp: number | null;
  flightResultsCachedParams: FlightSearchFormParams | null;
  /**
   * True when the cache was populated by a live-chat hydrator (a fresh chat
   * response in the current session). FlightSearchPage trusts the cache when
   * this is true and skips the strict params-equality check on mount. Set to
   * false by `clearCachedFlightResults` and by page-side fetches (RTK Query
   * results writes), so subsequent edits use the normal equality flow.
   * See docs/CHAT_NAV_BAR_SYNC.md.
   */
  cachedFlightResultsTrusted: boolean;

  /** G2A / manual voucher (USD); discounts collection _id from POST /vouchers/apply */
  voucherRedemptionId: string | null;
  voucherDiscountCents: number | null;
  /** VOYA-XXXXXXXXXX used for reservation + create-order when a voucher is applied */
  voucherCheckoutVoyaReference: string | null;
  voucherAppliedCode: string | null;
  /** ISO time when the voucher reservation expires (from POST /vouchers/apply reservation_expires_at) */
  voucherReservationExpiresAt: string | null;
}

const initialState: FlightBookingState = {
  currentStep: 'search',
  searchParams: null,
  searchFormParams: persistedFormParams || getDefaultSearchFormParams(),
  selectedFlight: null,
  sessionId: null,
  fareSourceCode: null,
  fareRules: null,
  passengers: [],
  contact: { email: '', country_code: '', phone: '' },
  postalCode: null,
  loading: false,
  error: null,
  bookingReference: null,
  bookingResult: null,
  paymentIntentId: null,
  isLCC: false,
  revalidationResponse: null,
  selectedFlightData: null,
  flightFilters: defaultFlightFilterState,
  savedPassengerIds: {},
  searchTriggerFromChips: 0,
  multicitySelectedLegs: {},
  multicityGroupReference: null,
  multicityLegBookingResults: null,
  flightRouteModalOpen: false,
  cachedFlightResults: null,
  flightResultsCacheTimestamp: null,
  flightResultsCachedParams: null,
  cachedFlightResultsTrusted: false,
  voucherRedemptionId: null,
  voucherDiscountCents: null,
  voucherCheckoutVoyaReference: null,
  voucherAppliedCode: null,
  voucherReservationExpiresAt: null,
};

/**
 * Flight booking slice
 */
const flightBookingSlice = createSlice({
  name: 'flightBooking',
  initialState,
  reducers: {
    /**
     * Set current step
     */
    setStep: (state, action: PayloadAction<BookingStep>) => {
      state.currentStep = action.payload;
    },

    /**
     * Set search parameters (API format)
     */
    setSearchParams: (state, action: PayloadAction<FlightSearchParams>) => {
      state.searchParams = action.payload;
    },

    /**
     * Set form-level search parameters
     */
    setSearchFormParams: (state, action: PayloadAction<FlightSearchFormParams>) => {
      state.searchFormParams = action.payload;
      saveSearchFormParams(action.payload);
    },

    /**
     * Update trip type
     */
    setTripType: (state, action: PayloadAction<TripType | null>) => {
      const prev = state.searchFormParams.tripType;
      state.searchFormParams.tripType = action.payload;
      if (prev !== action.payload) {
        state.flightRouteModalOpen = false;
      }
      // Clear return date if switching to one-way
      if (action.payload === 'one-way') {
        state.searchFormParams.returnDate = null;
      }
      // Initialize multi-city segments if switching to multi-city
      if (
        action.payload === 'multi-city' &&
        (!state.searchFormParams.segments || state.searchFormParams.segments.length < 2)
      ) {
        state.searchFormParams.segments = [
          {
            from: state.searchFormParams.from,
            to: state.searchFormParams.to,
            date: state.searchFormParams.date,
            fromAirport: state.searchFormParams.fromAirport,
            toAirport: state.searchFormParams.toAirport,
          },
          { from: '', to: '', date: null },
        ];
      }
      saveSearchFormParams(state.searchFormParams);
    },

    openFlightRouteModal: (state) => {
      state.flightRouteModalOpen = true;
    },

    closeFlightRouteModal: (state) => {
      state.flightRouteModalOpen = false;
    },

    /**
     * Update from airport
     */
    setFrom: (
      state,
      action: PayloadAction<{ value: string; airport?: SerializableAirportOption }>
    ) => {
      state.searchFormParams.from = action.payload.value;
      state.searchFormParams.fromAirport = action.payload.airport;
      saveSearchFormParams(state.searchFormParams);
    },

    /**
     * Update to airport
     */
    setTo: (
      state,
      action: PayloadAction<{ value: string; airport?: SerializableAirportOption }>
    ) => {
      state.searchFormParams.to = action.payload.value;
      state.searchFormParams.toAirport = action.payload.airport;
      saveSearchFormParams(state.searchFormParams);
    },

    /**
     * Swap from and to airports
     */
    swapAirports: (state) => {
      const tempFrom = state.searchFormParams.from;
      const tempTo = state.searchFormParams.to;
      const tempFromAirport = state.searchFormParams.fromAirport;
      const tempToAirport = state.searchFormParams.toAirport;

      state.searchFormParams.from = tempTo;
      state.searchFormParams.to = tempFrom;
      state.searchFormParams.fromAirport = tempToAirport;
      state.searchFormParams.toAirport = tempFromAirport;
      saveSearchFormParams(state.searchFormParams);
    },

    /**
     * Update departure date
     */
    setDate: (state, action: PayloadAction<string | null>) => {
      state.searchFormParams.date = action.payload;
      saveSearchFormParams(state.searchFormParams);
    },

    /**
     * Update return date
     */
    setReturnDate: (state, action: PayloadAction<string | null>) => {
      state.searchFormParams.returnDate = action.payload;
      saveSearchFormParams(state.searchFormParams);
    },

    /**
     * Update travellers data
     */
    setTravellers: (state, action: PayloadAction<TravellersData>) => {
      state.searchFormParams.travellers = action.payload;
      saveSearchFormParams(state.searchFormParams);
    },

    /**
     * Update multi-city segments
     */
    setMultiCitySegments: (state, action: PayloadAction<SerializableFlightSegment[]>) => {
      state.searchFormParams.segments = action.payload;
      saveSearchFormParams(state.searchFormParams);
    },

    /**
     * Update a single multi-city segment
     */
    updateMultiCitySegment: (
      state,
      action: PayloadAction<{ index: number; segment: SerializableFlightSegment }>
    ) => {
      if (
        state.searchFormParams.segments &&
        state.searchFormParams.segments[action.payload.index]
      ) {
        state.searchFormParams.segments[action.payload.index] = action.payload.segment;
        saveSearchFormParams(state.searchFormParams);
      }
    },

    /**
     * Select a flight
     */
    selectFlight: (
      state,
      action: PayloadAction<{ flight: MappedFlight; sessionId: string; fareSourceCode: string }>
    ) => {
      state.selectedFlight = action.payload.flight;
      state.sessionId = action.payload.sessionId;
      state.fareSourceCode = action.payload.fareSourceCode;
    },

    /**
     * Set fare rules
     */
    setFareRules: (state, action: PayloadAction<FlightBookingState['fareRules']>) => {
      state.fareRules = action.payload;
    },

    /**
     * Set passenger details
     */
    setPassengers: (state, action: PayloadAction<PassengerDetails[]>) => {
      state.passengers = action.payload;
    },

    /**
     * Set contact info (email, country_code, phone). Matches backend passenger_data.contact.
     */
    setContact: (state, action: PayloadAction<Partial<BookingContact>>) => {
      if (action.payload.email !== undefined) state.contact.email = action.payload.email;
      if (action.payload.country_code !== undefined)
        state.contact.country_code = action.payload.country_code;
      if (action.payload.phone !== undefined) state.contact.phone = action.payload.phone;
    },

    /**
     * Set postal code for booking request
     */
    setPostalCode: (state, action: PayloadAction<string | null>) => {
      state.postalCode = action.payload;
    },

    /**
     * Update a single passenger
     */
    updatePassenger: (
      state,
      action: PayloadAction<{ index: number; details: Partial<PassengerDetails> }>
    ) => {
      const { index, details } = action.payload;
      // Ensure passenger exists, create with defaults if not
      if (!state.passengers[index]) {
        state.passengers[index] = {
          type: 'adult', // Default, will be overridden by details if provided
          title: '',
          firstName: '',
          lastName: '',
          dateOfBirth: '',
          nationality: '',
        };
      }
      state.passengers[index] = { ...state.passengers[index], ...details };
    },

    /**
     * Set loading state
     */
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },

    /**
     * Set error
     */
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },

    /**
     * Set booking confirmation
     */
    setBookingConfirmation: (state, action: PayloadAction<string>) => {
      state.bookingReference = action.payload;
      state.currentStep = 'confirmation';
    },

    /** Set booking result; totalAmount must be in cents (minor units). */
    setBookingResult: (
      state,
      action: PayloadAction<{
        voyaBookingReference: string;
        externalBookingReference?: string;
        status: string;
        /** Total amount in cents (minor units) */
        totalAmount: number;
        currency: string;
      }>
    ) => {
      state.bookingResult = action.payload;
      state.bookingReference = action.payload.voyaBookingReference;
    },

    /**
     * Set payment intent ID
     */
    setPaymentIntentId: (state, action: PayloadAction<string | null>) => {
      state.paymentIntentId = action.payload;
    },

    /**
     * Set isLCC flag (from revalidation response)
     */
    setIsLCC: (state, action: PayloadAction<boolean>) => {
      state.isLCC = action.payload;
    },

    /**
     * Set revalidation response
     */
    setRevalidationResponse: (
      state,
      action: PayloadAction<FlightRevalidateResponseCamel | null>
    ) => {
      state.revalidationResponse = action.payload;
      if (action.payload?.validatedFareItineraries?.[0]) {
        const itinerary = action.payload.validatedFareItineraries[0];
        const pricing = itinerary?.updatedPricing ?? itinerary?.pricing;
        const fareType = pricing?.fareType;
        state.isLCC = fareType === 'WebFare';
      }
    },

    /**
     * Set selected flight data from search (for tab-switch persistence)
     */
    setSelectedFlightData: (
      state,
      action: PayloadAction<SelectedFlightDataFromSearch | null>
    ) => {
      state.selectedFlightData = action.payload;
    },

    /**
     * Set saved passenger id for a slot (backend resolves travel_documents)
     */
    setSavedPassengerId: (
      state,
      action: PayloadAction<{ index: number; id: string } | { index: number; id: null }>
    ) => {
      const { index, id } = action.payload;
      if (id === null) {
        delete state.savedPassengerIds[index];
      } else {
        state.savedPassengerIds[index] = id;
      }
    },

    /**
     * Clear all saved passenger refs
     */
    clearSavedPassengerIds: (state) => {
      state.savedPassengerIds = {};
    },

    /**
     * Set flight results filters
     */
    setFlightFilters: (state, action: PayloadAction<FlightFilterState>) => {
      state.flightFilters = action.payload;
    },

    /**
     * Reset flight results filters to defaults
     */
    resetFlightFilters: (state) => {
      state.flightFilters = defaultFlightFilterState;
    },

    /**
     * Reset booking state
     */
    resetBooking: () => {
      saveSearchFormParams(getDefaultSearchFormParams());
      return {
        ...initialState,
        searchFormParams: getDefaultSearchFormParams(),
        flightRouteModalOpen: false,
      };
    },

    /**
     * Trigger search from chip dialogs (Apply/radio). FlightSearchPage useEffect reacts.
     */
    triggerSearchFromChips: (state) => {
      state.searchTriggerFromChips += 1;
    },

    /** Reset after FlightSearchPage consumes a chip trigger so remount does not re-run search. */
    resetSearchTriggerFromChips: (state) => {
      state.searchTriggerFromChips = 0;
    },

    /**
     * Store multicity per-leg selection (revalidate succeeds)
     */
    setMulticityLegSelection: (state, action: PayloadAction<MulticityLegSelection>) => {
      const { legIndex } = action.payload;
      state.multicitySelectedLegs[legIndex] = action.payload;
    },

    /**
     * Clear selection for one multicity leg
     */
    clearMulticityLegSelection: (state, action: PayloadAction<number>) => {
      delete state.multicitySelectedLegs[action.payload];
    },

    /**
     * Clear all multicity leg selections (new search or abandon flow)
     */
    clearMulticityLegSelections: (state) => {
      state.multicitySelectedLegs = {};
      state.multicityGroupReference = null;
      state.multicityLegBookingResults = null;
    },

    setMulticityGroupReference: (state, action: PayloadAction<string | null>) => {
      state.multicityGroupReference = action.payload;
    },

    setMulticityLegBookingResults: (
      state,
      action: PayloadAction<MulticityLegBookingResult[] | null>
    ) => {
      state.multicityLegBookingResults = action.payload;
    },

    setFlightVoucher: (
      state,
      action: PayloadAction<{
        redemptionId: string;
        discountCents: number;
        checkoutVoyaReference: string;
        code: string;
        reservationExpiresAt?: string | null;
      } | null>
    ) => {
      if (!action.payload) {
        state.voucherRedemptionId = null;
        state.voucherDiscountCents = null;
        state.voucherCheckoutVoyaReference = null;
        state.voucherAppliedCode = null;
        state.voucherReservationExpiresAt = null;
        return;
      }
      state.voucherRedemptionId = action.payload.redemptionId;
      state.voucherDiscountCents = action.payload.discountCents;
      state.voucherCheckoutVoyaReference = action.payload.checkoutVoyaReference;
      state.voucherAppliedCode = action.payload.code;
      state.voucherReservationExpiresAt = action.payload.reservationExpiresAt ?? null;
    },

    setCachedFlightResults: (
      state,
      action: PayloadAction<{
        data: FlightSearchResponseCamel;
        params: FlightSearchFormParams;
        /**
         * Pass `trusted: true` from live-chat hydrators (current-session chat
         * response). Defaults to false for page-side fetches (RTK Query
         * results write) so normal strict-equality applies thereafter.
         */
        trusted?: boolean;
      }>
    ) => {
      state.cachedFlightResults = action.payload.data;
      state.flightResultsCachedParams = action.payload.params;
      state.flightResultsCacheTimestamp = Date.now();
      state.cachedFlightResultsTrusted = action.payload.trusted === true;
    },

    clearCachedFlightResults: (state) => {
      state.cachedFlightResults = null;
      state.flightResultsCacheTimestamp = null;
      state.flightResultsCachedParams = null;
      state.cachedFlightResultsTrusted = false;
    },

    /**
     * Clear selected flight and fare rules (but keep search params)
     */
    clearSelection: (state) => {
      state.selectedFlight = null;
      state.sessionId = null;
      state.fareSourceCode = null;
      state.fareRules = null;
      state.revalidationResponse = null;
      state.selectedFlightData = null;
      state.multicitySelectedLegs = {};
      state.multicityGroupReference = null;
      state.multicityLegBookingResults = null;
      state.currentStep = 'results';
      state.voucherRedemptionId = null;
      state.voucherDiscountCents = null;
      state.voucherCheckoutVoyaReference = null;
      state.voucherAppliedCode = null;
      state.voucherReservationExpiresAt = null;
    },
  },
});

export const {
  setStep,
  setSearchParams,
  setSearchFormParams,
  setTripType,
  setFrom,
  setTo,
  swapAirports,
  setDate,
  setReturnDate,
  setTravellers,
  setMultiCitySegments,
  updateMultiCitySegment,
  selectFlight,
  setFareRules,
  setPassengers,
  setContact,
  setPostalCode,
  updatePassenger,
  setLoading,
  setError,
  setBookingConfirmation,
  setBookingResult,
  setPaymentIntentId,
  setIsLCC,
  setRevalidationResponse,
  setSelectedFlightData,
  setSavedPassengerId,
  clearSavedPassengerIds,
  setFlightFilters,
  resetFlightFilters,
  resetBooking,
  clearSelection,
  triggerSearchFromChips,
  resetSearchTriggerFromChips,
  setMulticityLegSelection,
  clearMulticityLegSelection,
  clearMulticityLegSelections,
  setMulticityGroupReference,
  setMulticityLegBookingResults,
  openFlightRouteModal,
  closeFlightRouteModal,
  setFlightVoucher,
  setCachedFlightResults,
  clearCachedFlightResults,
} = flightBookingSlice.actions;

export default flightBookingSlice.reducer;

// Selectors
export const selectCurrentStep = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.currentStep;
export const selectSearchParams = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.searchParams;
export const selectSearchFormParams = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.searchFormParams;
export const selectSelectedFlight = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.selectedFlight;
export const selectSessionId = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.sessionId;
export const selectFareSourceCode = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.fareSourceCode;
export const selectFareRules = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.fareRules;
export const selectPassengers = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.passengers;
export const selectContact = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.contact;
export const selectPostalCode = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.postalCode;
export const selectBookingLoading = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.loading;
export const selectBookingError = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.error;
export const selectBookingReference = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.bookingReference;
export const selectBookingResult = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.bookingResult;
export const selectPaymentIntentId = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.paymentIntentId;
export const selectIsLCC = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.isLCC;
export const selectRevalidationResponse = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.revalidationResponse;
export const selectSelectedFlightData = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.selectedFlightData;
export const selectSavedPassengerIds = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.savedPassengerIds;
export const selectFlightFilters = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.flightFilters;
export const selectSearchTriggerFromChips = (state: {
  flightBooking: FlightBookingState;
}) => state.flightBooking.searchTriggerFromChips;
export const selectMulticitySelectedLegs = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.multicitySelectedLegs;

export const selectFlightRouteModalOpen = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.flightRouteModalOpen;
export const selectMulticityGroupReference = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.multicityGroupReference;
export const selectMulticityLegBookingResults = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.multicityLegBookingResults;

export const selectFlightVoucherRedemptionId = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.voucherRedemptionId;
export const selectFlightVoucherDiscountCents = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.voucherDiscountCents;
export const selectFlightVoucherCheckoutRef = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.voucherCheckoutVoyaReference;
export const selectFlightVoucherAppliedCode = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.voucherAppliedCode;
export const selectFlightVoucherReservationExpiresAt = (state: {
  flightBooking: FlightBookingState;
}) => state.flightBooking.voucherReservationExpiresAt;

export const selectCachedFlightResults = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.cachedFlightResults;
export const selectCachedFlightResultsTrusted = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.cachedFlightResultsTrusted;
export const selectFlightResultsCacheTimestamp = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.flightResultsCacheTimestamp;
export const selectFlightResultsCachedParams = (state: { flightBooking: FlightBookingState }) =>
  state.flightBooking.flightResultsCachedParams;
