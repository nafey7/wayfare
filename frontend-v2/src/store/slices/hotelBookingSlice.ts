import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import { readWithTTL, writeWithTTL, removeWithTTL, TTL_24H_MS } from '@/utils/localStorageWithTTL';
import type {
  HotelSearchRequest,
  HotelSearchFormParams,
  HotelSearchResponse,
  HotelItinerary,
  RoomRate,
  RateRulesResponse,
  RoomRatesResponse,
  HotelGuestDetails,
  HotelBookingResponse,
  HotelTripType,
  HotelMultistaySegment,
  HotelMultistayLegState,
  HotelMultistayLegBookingResult,
} from '@/types/hotels';
import type { HotelFilterState } from '@/features/hotels/utils/hotelFilters';
import { defaultHotelFilterState } from '@/features/hotels/utils/hotelFilters';
import { devLog } from '@/utils/devLog';

/**
 * Hotel booking wizard steps
 */
export type HotelBookingStep =
  | 'search'
  | 'results'
  | 'rooms'
  | 'guest'
  | 'review'
  | 'payment'
  | 'confirmation';

const SEARCH_FORM_PARAMS_KEY = 'hotelSearchFormParams';

function loadSearchFormParams(): HotelSearchFormParams | null {
  return readWithTTL<HotelSearchFormParams>(SEARCH_FORM_PARAMS_KEY);
}

function saveSearchFormParams(params: HotelSearchFormParams | null) {
  if (params) {
    writeWithTTL(SEARCH_FORM_PARAMS_KEY, params, TTL_24H_MS);
  } else {
    removeWithTTL(SEARCH_FORM_PARAMS_KEY);
  }
}

/**
 * Default form params for a "fresh" state (e.g. on new chat).
 *
 * All user-selectable fields default to `null` / empty so the unified-header
 * search chips render placeholders ("Destination", "Select dates", "Guests")
 * rather than carrying values from a previous session. The chat hydration
 * layer (`chatSearchParamsToFormParams` in
 * `hydrateChatHotelResultsToSearchCache.ts`) populates everything when chat
 * returns hotel_search_results or itinerary_results.
 *
 * If product later prefers minimum-viable defaults instead of nulls (e.g.
 * `rooms: [1×1-adult]`, `checkin: tomorrow`), change them here — every
 * consumer already null-guards.
 *
 * `nationality` stays as 'US' — chat never sends it, the request builder
 * always falls back to 'US', and the UI does not surface this field today.
 */
function getDefaultSearchFormParams(): HotelSearchFormParams {
  return {
    destination: '',
    checkin: null,
    checkout: null,
    rooms: null,
    nationality: 'US',
  };
}

function makeDefaultMultistaySegment(index: number): HotelMultistaySegment {
  const base = new Date();
  base.setDate(base.getDate() + 1 + index * 3);
  const checkout = new Date(base);
  checkout.setDate(checkout.getDate() + 2);
  return {
    destination: '',
    checkin: base.toISOString().slice(0, 10),
    checkout: checkout.toISOString().slice(0, 10),
    rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
  };
}

function makeEmptyMultistayLeg(segmentIndex: number): HotelMultistayLegState {
  return {
    segmentIndex,
    sessionId: null,
    internalSessionId: null,
    hotels: [],
    selectedHotel: null,
    tokenId: null,
    productId: null,
    hotelId: null,
    selectedRoom: null,
    rateBasisId: null,
    rateRulesResponse: null,
    roomRatesResponse: null,
    currency: null,
  };
}

const persistedFormParams = loadSearchFormParams();

export interface HotelBookingState {
  currentStep: HotelBookingStep;

  searchFormParams: HotelSearchFormParams;
  searchParams: HotelSearchRequest | null;

  sessionId: string | null;
  internalSessionId: string | null;

  selectedHotel: HotelItinerary | null;
  tokenId: string | null;
  productId: string | null;
  hotelId: string | null;

  selectedRoom: RoomRate | null;
  rateBasisId: string | null;
  rateRulesResponse: RateRulesResponse | null;
  /** Cached room rates when navigating from search/chat after successful getRoomRates; cleared when hotel changes. */
  roomRatesResponse: RoomRatesResponse | null;

  guests: HotelGuestDetails[];
  contactEmail: string;
  contactPhone: string;
  specialRequests: string;

  bookingResult: HotelBookingResponse | null;
  paymentIntentId: string | null;
  bookingReference: string | null;

  loading: boolean;
  error: string | null;

  hotelFilters: HotelFilterState;

  /** Incremented when header chips apply dates/rooms so HotelSearchPage runs search (mirrors flights). */
  searchTriggerFromChips: number;

  voucherRedemptionId: string | null;
  voucherDiscountCents: number | null;
  voucherCheckoutVoyaReference: string | null;
  voucherAppliedCode: string | null;
  /** ISO time when the voucher reservation expires (from POST /vouchers/apply reservation_expires_at) */
  voucherReservationExpiresAt: string | null;

  /** In-memory results cache (5 min TTL, cleared on logout / hard refresh). */
  cachedHotelResults: HotelSearchResponse | null;
  hotelResultsCacheTimestamp: number | null;
  hotelResultsCachedParams: HotelSearchFormParams | null;
  /**
   * True when the cache was populated by a live-chat hydrator. HotelSearchPage
   * trusts the cache when this is true and skips the strict params-equality
   * check on mount. See docs/CHAT_NAV_BAR_SYNC.md.
   */
  cachedHotelResultsTrusted: boolean;

  // ── Multi-stay fields ──────────────────────────────────────────
  /**
   * Trip type: 'single', 'multi-stay', or `null` for the fresh/unset state
   * (placeholder on the search chip). All consumers that gate rendering on
   * `tripType === 'single'` or `'multi-stay'` treat null as "no selection
   * yet" — falls through to a fresh-state UI.
   */
  tripType: HotelTripType | null;
  /** Segment forms for multi-stay (one per city). */
  multistaySegments: HotelMultistaySegment[];
  /** Per-leg search results + selection state for multi-stay. */
  multistayLegs: HotelMultistayLegState[];
  /** Shared parent reference across all legs of a multi-stay booking. */
  multistayGroupReference: string | null;
  /** Per-leg booking results after payment. */
  multistayLegBookingResults: HotelMultistayLegBookingResult[];
  /** Active leg tab index in the multi-stay results view. */
  multistayActiveLegTab: number;
}

const initialState: HotelBookingState = {
  currentStep: 'search',
  searchFormParams: persistedFormParams || getDefaultSearchFormParams(),
  searchParams: null,
  sessionId: null,
  internalSessionId: null,
  selectedHotel: null,
  tokenId: null,
  productId: null,
  hotelId: null,
  selectedRoom: null,
  rateBasisId: null,
  rateRulesResponse: null,
  roomRatesResponse: null,
  guests: [],
  contactEmail: '',
  contactPhone: '',
  specialRequests: '',
  bookingResult: null,
  paymentIntentId: null,
  bookingReference: null,
  loading: false,
  error: null,
  hotelFilters: defaultHotelFilterState,
  searchTriggerFromChips: 0,
  voucherRedemptionId: null,
  voucherDiscountCents: null,
  voucherCheckoutVoyaReference: null,
  voucherAppliedCode: null,
  voucherReservationExpiresAt: null,
  cachedHotelResults: null,
  hotelResultsCacheTimestamp: null,
  hotelResultsCachedParams: null,
  cachedHotelResultsTrusted: false,
  // Future: change to 'single' if product wants a default-selected stay type.
  tripType: null,
  multistaySegments: [makeDefaultMultistaySegment(0), makeDefaultMultistaySegment(1)],
  multistayLegs: [],
  multistayGroupReference: null,
  multistayLegBookingResults: [],
  multistayActiveLegTab: 0,
};

const hotelBookingSlice = createSlice({
  name: 'hotelBooking',
  initialState,
  reducers: {
    setStep: (state, action: PayloadAction<HotelBookingStep>) => {
      state.currentStep = action.payload;
    },

    setSearchFormParams: (state, action: PayloadAction<HotelSearchFormParams>) => {
      state.searchFormParams = action.payload;
      saveSearchFormParams(action.payload);
    },

    setSearchParams: (state, action: PayloadAction<HotelSearchRequest | null>) => {
      state.searchParams = action.payload;
    },

    setSessionId: (state, action: PayloadAction<string | null>) => {
      state.sessionId = action.payload;
    },

    setInternalSessionId: (state, action: PayloadAction<string | null>) => {
      state.internalSessionId = action.payload;
    },

    setSelectedHotel: (
      state,
      action: PayloadAction<{
        hotel: HotelItinerary | null;
        tokenId: string | null;
        productId: string | null;
        hotelId: string | null;
      }>
    ) => {
      state.selectedHotel = action.payload.hotel;
      state.tokenId = action.payload.tokenId;
      state.productId = action.payload.productId;
      state.hotelId = action.payload.hotelId;
      // Clear room-level state when switching hotel so rateBasisId/selectedRoom don't carry over from previous hotel (avoids wrong rate on back/forward navigation).
      state.selectedRoom = null;
      state.rateBasisId = null;
      state.rateRulesResponse = null;
      state.roomRatesResponse = null;
      devLog('hotel booking (cleared in setSelectedHotel)', {
        rateBasisId: null,
        sessionId: state.sessionId,
        productId: state.productId,
      });
    },

    setSelectedRoom: (state, action: PayloadAction<RoomRate | null>) => {
      state.selectedRoom = action.payload;
      state.rateBasisId = action.payload?.rateBasisId ?? null;
      devLog('hotel booking (set in setSelectedRoom)', {
        rateBasisId: state.rateBasisId,
        sessionId: state.sessionId,
        productId: state.productId,
      });
      // Sync selectedHotel price from the selected room (fix: use room price, not hotel's lowest)
      if (state.selectedHotel && action.payload) {
        const room = action.payload;
        const total = room.totalPrice ?? room.price?.amount ?? 0;
        if (total > 0) {
          state.selectedHotel = {
            ...state.selectedHotel,
            total,
            originalTotal:
              room.originalTotalPrice ??
              (total * 0.895), // 10.5% fee: display = hotel/0.895, so hotel = display*0.895
          };
        }
      }
    },

    setRoomRatesResponse: (state, action: PayloadAction<RoomRatesResponse | null>) => {
      state.roomRatesResponse = action.payload;
    },

    setRateRules: (state, action: PayloadAction<RateRulesResponse | null>) => {
      state.rateRulesResponse = action.payload;
      // Sync selectedHotel price from validated rate (authoritative source)
      if (state.selectedHotel && action.payload) {
        const rr = action.payload;
        const total = rr.netPrice ?? 0;
        if (total > 0) {
          state.selectedHotel = {
            ...state.selectedHotel,
            total,
            originalTotal:
              rr.originalNetPrice ?? (total * 0.895),
            platformFeePercentage: rr.platformFeePercentage ?? 10.5,
          };
        }
      }
    },

    setGuests: (state, action: PayloadAction<HotelGuestDetails[]>) => {
      state.guests = action.payload;
    },

    setContactEmail: (state, action: PayloadAction<string>) => {
      state.contactEmail = action.payload;
    },

    setContactPhone: (state, action: PayloadAction<string>) => {
      state.contactPhone = action.payload;
    },

    setSpecialRequests: (state, action: PayloadAction<string>) => {
      state.specialRequests = action.payload;
    },

    setBookingResult: (state, action: PayloadAction<HotelBookingResponse | null>) => {
      state.bookingResult = action.payload;
      state.bookingReference = action.payload?.voyaBookingReference ?? null;
    },

    setPaymentIntentId: (state, action: PayloadAction<string | null>) => {
      state.paymentIntentId = action.payload;
    },

    setBookingReference: (state, action: PayloadAction<string | null>) => {
      state.bookingReference = action.payload;
    },

    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },

    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },

    setHotelFilters: (state, action: PayloadAction<HotelFilterState>) => {
      state.hotelFilters = action.payload;
    },

    triggerSearchFromChips: (state) => {
      state.searchTriggerFromChips += 1;
    },

    /** Reset after HotelSearchPage consumes a chip trigger so remount does not re-run search. */
    resetSearchTriggerFromChips: (state) => {
      state.searchTriggerFromChips = 0;
    },

    resetHotelFilters: (state) => {
      state.hotelFilters = defaultHotelFilterState;
    },

    setHotelVoucher: (
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

    setCachedHotelResults: (
      state,
      action: PayloadAction<{
        data: HotelSearchResponse;
        params: HotelSearchFormParams;
        trusted?: boolean;
      }>
    ) => {
      state.cachedHotelResults = action.payload.data;
      state.hotelResultsCachedParams = action.payload.params;
      state.hotelResultsCacheTimestamp = Date.now();
      state.cachedHotelResultsTrusted = action.payload.trusted === true;
    },

    clearCachedHotelResults: (state) => {
      state.cachedHotelResults = null;
      state.hotelResultsCacheTimestamp = null;
      state.hotelResultsCachedParams = null;
      state.cachedHotelResultsTrusted = false;
    },

    resetBooking: () => {
      saveSearchFormParams(getDefaultSearchFormParams());
      return {
        ...initialState,
        searchFormParams: getDefaultSearchFormParams(),
        hotelFilters: defaultHotelFilterState,
      };
    },

    clearSelection: (state) => {
      state.selectedHotel = null;
      state.tokenId = null;
      state.productId = null;
      state.hotelId = null;
      state.selectedRoom = null;
      state.rateBasisId = null;
      state.rateRulesResponse = null;
      state.roomRatesResponse = null;
      state.currentStep = 'results';
      state.voucherRedemptionId = null;
      state.voucherDiscountCents = null;
      state.voucherCheckoutVoyaReference = null;
      state.voucherAppliedCode = null;
      state.voucherReservationExpiresAt = null;
      devLog('hotel booking (cleared in clearSelection)', {
        rateBasisId: null,
        sessionId: state.sessionId,
        productId: null,
      });
    },

    /** Clear sensitive session data on confirmation; keep bookingResult for display. */
    clearConfirmationSession: (state) => {
      state.sessionId = null;
      state.internalSessionId = null;
      state.selectedHotel = null;
      state.tokenId = null;
      state.productId = null;
      state.hotelId = null;
      state.selectedRoom = null;
      state.rateBasisId = null;
      state.rateRulesResponse = null;
      state.roomRatesResponse = null;
      devLog('hotel booking (cleared in clearConfirmationSession)', {
        rateBasisId: null,
        sessionId: null,
        productId: null,
      });
      state.guests = [];
      state.contactEmail = '';
      state.contactPhone = '';
      state.specialRequests = '';
      state.paymentIntentId = null;
      state.currentStep = 'confirmation';
      state.loading = false;
      state.error = null;
      state.voucherRedemptionId = null;
      state.voucherDiscountCents = null;
      state.voucherCheckoutVoyaReference = null;
      state.voucherAppliedCode = null;
      state.voucherReservationExpiresAt = null;
      state.multistayLegs = [];
      state.multistayGroupReference = null;
    },

    // ── Multi-stay reducers ─────────────────────────────────────

    setTripType: (state, action: PayloadAction<HotelTripType | null>) => {
      state.tripType = action.payload;
      if (action.payload === 'multi-stay' && state.multistaySegments.length < 2) {
        state.multistaySegments = [makeDefaultMultistaySegment(0), makeDefaultMultistaySegment(1)];
        state.multistayLegs = [];
      }
    },

    setMultistaySegments: (state, action: PayloadAction<HotelMultistaySegment[]>) => {
      state.multistaySegments = action.payload;
      // Resize legs array to match segments
      const n = action.payload.length;
      while (state.multistayLegs.length < n) {
        state.multistayLegs.push(makeEmptyMultistayLeg(state.multistayLegs.length));
      }
      state.multistayLegs = state.multistayLegs.slice(0, n);
    },

    updateMultistaySegment: (
      state,
      action: PayloadAction<{ index: number; segment: Partial<HotelMultistaySegment> }>
    ) => {
      const { index, segment } = action.payload;
      if (state.multistaySegments[index]) {
        state.multistaySegments[index] = { ...state.multistaySegments[index]!, ...segment };
      }
    },

    setMultistayLegSearchResults: (
      state,
      action: PayloadAction<{ legIndex: number; sessionId: string; hotels: HotelItinerary[] }>
    ) => {
      const { legIndex, sessionId, hotels } = action.payload;
      if (!state.multistayLegs[legIndex]) {
        state.multistayLegs[legIndex] = makeEmptyMultistayLeg(legIndex);
      }
      state.multistayLegs[legIndex]!.sessionId = sessionId;
      state.multistayLegs[legIndex]!.hotels = hotels;
      // Clear prior selection when new search results arrive
      state.multistayLegs[legIndex]!.selectedHotel = null;
      state.multistayLegs[legIndex]!.selectedRoom = null;
      state.multistayLegs[legIndex]!.rateBasisId = null;
      state.multistayLegs[legIndex]!.rateRulesResponse = null;
    },

    setMultistayLegSelection: (
      state,
      action: PayloadAction<{
        legIndex: number;
        hotel: HotelItinerary;
        tokenId: string;
        productId: string;
        hotelId: string;
        room: RoomRate;
        rateRules: RateRulesResponse;
        internalSessionId: string;
        roomRatesResponse: RoomRatesResponse | null;
        currency: string;
      }>
    ) => {
      const { legIndex, hotel, tokenId, productId, hotelId, room, rateRules, internalSessionId, roomRatesResponse, currency } = action.payload;
      if (!state.multistayLegs[legIndex]) {
        state.multistayLegs[legIndex] = makeEmptyMultistayLeg(legIndex);
      }
      const leg = state.multistayLegs[legIndex]!;
      leg.selectedHotel = hotel;
      leg.tokenId = tokenId;
      leg.productId = productId;
      leg.hotelId = hotelId;
      leg.selectedRoom = room;
      leg.rateBasisId = room.rateBasisId;
      leg.rateRulesResponse = rateRules;
      leg.internalSessionId = internalSessionId;
      leg.roomRatesResponse = roomRatesResponse;
      leg.currency = currency;
    },

    clearMultistayLegSelection: (state, action: PayloadAction<number>) => {
      const legIndex = action.payload;
      if (state.multistayLegs[legIndex]) {
        state.multistayLegs[legIndex] = {
          ...makeEmptyMultistayLeg(legIndex),
          sessionId: state.multistayLegs[legIndex]!.sessionId,
          hotels: state.multistayLegs[legIndex]!.hotels,
        };
      }
    },

    clearAllMultistayLegSelections: (state) => {
      state.multistayLegs = state.multistayLegs.map((leg) => ({
        ...makeEmptyMultistayLeg(leg.segmentIndex),
        sessionId: leg.sessionId,
        hotels: leg.hotels,
      }));
      state.multistayGroupReference = null;
      state.multistayLegBookingResults = [];
    },

    setMultistayGroupReference: (state, action: PayloadAction<string | null>) => {
      state.multistayGroupReference = action.payload;
    },

    setMultistayLegBookingResults: (
      state,
      action: PayloadAction<HotelMultistayLegBookingResult[]>
    ) => {
      state.multistayLegBookingResults = action.payload;
    },

    setMultistayActiveLegTab: (state, action: PayloadAction<number>) => {
      state.multistayActiveLegTab = action.payload;
    },
  },
});

export const {
  setStep,
  setSearchFormParams,
  setSearchParams,
  setSessionId,
  setInternalSessionId,
  setSelectedHotel,
  setSelectedRoom,
  setRoomRatesResponse,
  setRateRules,
  setGuests,
  setContactEmail,
  setContactPhone,
  setSpecialRequests,
  setBookingResult,
  setPaymentIntentId,
  setBookingReference,
  setLoading,
  setError,
  setHotelFilters,
  triggerSearchFromChips,
  resetSearchTriggerFromChips,
  resetHotelFilters,
  setHotelVoucher,
  resetBooking,
  clearSelection,
  clearConfirmationSession,
  // Multi-stay
  setTripType,
  setMultistaySegments,
  updateMultistaySegment,
  setMultistayLegSearchResults,
  setMultistayLegSelection,
  clearMultistayLegSelection,
  clearAllMultistayLegSelections,
  setMultistayGroupReference,
  setMultistayLegBookingResults,
  setMultistayActiveLegTab,
  setCachedHotelResults,
  clearCachedHotelResults,
} = hotelBookingSlice.actions;

export default hotelBookingSlice.reducer;

// Selectors
export const selectHotelCurrentStep = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.currentStep;
export const selectHotelSearchFormParams = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.searchFormParams;
export const selectHotelSearchParams = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.searchParams;
export const selectHotelSessionId = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.sessionId;
export const selectHotelInternalSessionId = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.internalSessionId;
export const selectSelectedHotel = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.selectedHotel;
export const selectHotelTokenId = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.tokenId;
export const selectHotelProductId = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.productId;
export const selectHotelId = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.hotelId;
export const selectSelectedRoom = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.selectedRoom;
export const selectHotelRateBasisId = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.rateBasisId;
export const selectRateRulesResponse = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.rateRulesResponse;
export const selectRoomRatesResponse = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.roomRatesResponse;
export const selectHotelGuests = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.guests;
export const selectHotelContactEmail = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.contactEmail;
export const selectHotelContactPhone = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.contactPhone;
export const selectHotelSpecialRequests = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.specialRequests;
export const selectHotelBookingResult = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.bookingResult;
export const selectHotelPaymentIntentId = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.paymentIntentId;
export const selectHotelBookingReference = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.bookingReference;
export const selectHotelBookingLoading = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.loading;
export const selectHotelBookingError = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.error;
export const selectHotelFilters = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.hotelFilters;
export const selectHotelSearchTriggerFromChips = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.searchTriggerFromChips;

export const selectHotelVoucherRedemptionId = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.voucherRedemptionId;
export const selectHotelVoucherDiscountCents = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.voucherDiscountCents;
export const selectHotelVoucherCheckoutRef = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.voucherCheckoutVoyaReference;
export const selectHotelVoucherAppliedCode = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.voucherAppliedCode;
export const selectHotelVoucherReservationExpiresAt = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.voucherReservationExpiresAt;

// Multi-stay selectors
export const selectHotelTripType = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.tripType;
export const selectMultistaySegments = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.multistaySegments;
export const selectMultistayLegs = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.multistayLegs;
export const selectMultistayGroupReference = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.multistayGroupReference;
export const selectMultistayLegBookingResults = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.multistayLegBookingResults;
export const selectMultistayActiveLegTab = (state: {
  hotelBooking: HotelBookingState;
}) => state.hotelBooking.multistayActiveLegTab;

export const selectCachedHotelResults = (state: { hotelBooking: HotelBookingState }) =>
  state.hotelBooking.cachedHotelResults;
export const selectCachedHotelResultsTrusted = (state: { hotelBooking: HotelBookingState }) =>
  state.hotelBooking.cachedHotelResultsTrusted;
export const selectHotelResultsCacheTimestamp = (state: { hotelBooking: HotelBookingState }) =>
  state.hotelBooking.hotelResultsCacheTimestamp;
export const selectHotelResultsCachedParams = (state: { hotelBooking: HotelBookingState }) =>
  state.hotelBooking.hotelResultsCachedParams;
