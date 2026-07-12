import type {
  FlightRevalidateResponseCamel,
  SelectedFlightDataFromSearch,
} from '@/types/flightBackend';

/** Shared state for flight booking flow (details, passenger, review pages) */
export interface FlightBookingState {
  revalidateResponse?: FlightRevalidateResponseCamel;
  selectedFlightData?: SelectedFlightDataFromSearch;
  searchSessionId?: string;
}

/** Revolut order shape passed from ReviewBookingPage to PaymentPage */
export interface RevolutOrderFromState {
  orderId: string;
  publicOrderId: string;
  amount: number;
  currency: string;
  platformFee: number;
  supplierAmount: number;
}

/** USD voucher snapshot from review (mirrors hotel carrying authoritative refs in navigation state). */
export interface FlightVoucherNavState {
  redemptionId: string;
  discountCents: number;
  checkoutVoyaReference: string;
  code: string;
  reservationExpiresAt: string | null;
}

/** Payment page state – extends booking state with payment-related fields */
export interface PaymentPageState {
  revalidateResponse?: FlightRevalidateResponseCamel;
  selectedFlightData?: SelectedFlightDataFromSearch;
  searchSessionId?: string;
  /** Multicity: pay once, book per leg after payment */
  multicityMode?: boolean;
  multicityGroupReference?: string;
  bookingResult?: {
    voyaBookingReference: string;
    externalBookingReference?: string;
    status: string;
    totalAmount: number;
    currency: string;
  };
  revolutOrder?: RevolutOrderFromState;
  /** When set, PaymentPage hydrates Redux if voucher fields are missing (survives tab/navigation edge cases). */
  flightVoucher?: FlightVoucherNavState;
}

/** Per-leg refs after multicity checkout (optional; also in Redux). */
export interface MulticityLegBookingResultNav {
  legIndex: number;
  voyaBookingReference: string;
  externalBookingReference?: string;
}

/** Confirmation page state */
export interface ConfirmationPageState {
  bookingResult?: {
    voyaBookingReference: string;
    externalBookingReference?: string;
    status: string;
    totalAmount: number;
    currency: string;
  };
  paymentIntentId?: string;
  multicityGroupReference?: string;
  multicityLegBookingResults?: MulticityLegBookingResultNav[];
}

/** Flight search page state (minimal – fromChat flag) */
export interface FlightSearchState {
  fromChat?: boolean;
}

function isObject(v: unknown): v is Record<string, unknown> {
  return v != null && typeof v === 'object' && !Array.isArray(v);
}

/**
 * Build voucher payload for navigate({ state }) from review-step Redux selectors.
 */
export function buildFlightVoucherNavState(params: {
  voucherRedemptionId: string | null | undefined;
  voucherCheckoutRef: string | null | undefined;
  voucherAppliedCode: string | null | undefined;
  voucherDiscountCents: number | null | undefined;
  voucherReservationExpiresAt: string | null | undefined;
}): FlightVoucherNavState | undefined {
  const {
    voucherRedemptionId,
    voucherCheckoutRef,
    voucherAppliedCode,
    voucherDiscountCents,
    voucherReservationExpiresAt,
  } = params;
  if (
    !voucherRedemptionId ||
    !voucherCheckoutRef ||
    !voucherAppliedCode ||
    voucherDiscountCents == null
  ) {
    return undefined;
  }
  return {
    redemptionId: voucherRedemptionId,
    discountCents: voucherDiscountCents,
    checkoutVoyaReference: voucherCheckoutRef,
    code: voucherAppliedCode,
    reservationExpiresAt: voucherReservationExpiresAt ?? null,
  };
}

/** Parse optional flightVoucher from React Router location.state. */
export function parseFlightVoucherNavState(state: unknown): FlightVoucherNavState | undefined {
  if (!isObject(state)) return undefined;
  const v = state.flightVoucher;
  if (!isObject(v)) return undefined;
  const redemptionId = v.redemptionId;
  const discountCents = v.discountCents;
  const checkoutVoyaReference = v.checkoutVoyaReference;
  const code = v.code;
  if (
    typeof redemptionId !== 'string' ||
    typeof discountCents !== 'number' ||
    typeof checkoutVoyaReference !== 'string' ||
    typeof code !== 'string'
  ) {
    return undefined;
  }
  const reservationExpiresAt = v.reservationExpiresAt;
  if (
    reservationExpiresAt !== undefined &&
    reservationExpiresAt !== null &&
    typeof reservationExpiresAt !== 'string'
  ) {
    return undefined;
  }
  return {
    redemptionId,
    discountCents,
    checkoutVoyaReference,
    code,
    reservationExpiresAt:
      reservationExpiresAt === undefined || reservationExpiresAt === null ? null : reservationExpiresAt,
  };
}

/**
 * Safely parse location.state into FlightBookingState.
 * Returns undefined when state is invalid.
 */
export function parseFlightBookingState(
  state: unknown
): FlightBookingState | undefined {
  if (!isObject(state)) return undefined;
  const s = state;
  const rr = s.revalidateResponse;
  if (
    rr !== undefined &&
    (rr === null || !isObject(rr) || !Array.isArray(rr.validatedFareItineraries))
  ) {
    return undefined;
  }
  const sd = s.selectedFlightData;
  if (
    sd !== undefined &&
    (sd === null || !isObject(sd) || typeof sd.id !== 'string')
  ) {
    return undefined;
  }
  if (
    s.searchSessionId !== undefined &&
    typeof s.searchSessionId !== 'string'
  ) {
    return undefined;
  }
  return state as FlightBookingState;
}

/**
 * Safely parse location.state into PaymentPageState.
 * Delegates to parseFlightBookingState for shared fields, then validates
 * payment-specific fields (bookingResult, revolutOrder).
 * Falls back to parsePaymentPageStateMinimal when full parse fails (e.g. GDS flow from Review).
 */
export function parsePaymentPageState(
  state: unknown
): PaymentPageState | undefined {
  const base = parseFlightBookingState(state);
  if (base === undefined) return parsePaymentPageStateMinimal(state);
  const s = state as Record<string, unknown>;
  const br = s.bookingResult;
  if (
    br !== undefined &&
    (br === null || !isObject(br) || typeof br.voyaBookingReference !== 'string')
  ) {
    return parsePaymentPageStateMinimal(state);
  }
  const ro = s.revolutOrder;
  if (
    ro !== undefined &&
    (ro === null ||
      !isObject(ro) ||
      typeof ro.orderId !== 'string' ||
      typeof ro.publicOrderId !== 'string')
  ) {
    return parsePaymentPageStateMinimal(state);
  }
  return state as PaymentPageState;
}

/**
 * Minimal parse for GDS payment flow: only validates revolutOrder + bookingResult.
 * Used when full parse fails – ensures Revolut widget can initialize
 * when arriving from Review with create-order.
 */
export function parsePaymentPageStateMinimal(
  state: unknown
): PaymentPageState | undefined {
  if (!isObject(state)) return undefined;
  const s = state as Record<string, unknown>;
  const ro = s.revolutOrder;
  const br = s.bookingResult;
  if (
    !ro ||
    !isObject(ro) ||
    typeof ro.orderId !== 'string' ||
    typeof ro.publicOrderId !== 'string'
  ) {
    return undefined;
  }
  if (
    !br ||
    !isObject(br) ||
    typeof br.voyaBookingReference !== 'string'
  ) {
    return undefined;
  }
  if (s.multicityMode !== undefined && typeof s.multicityMode !== 'boolean') {
    return undefined;
  }
  if (
    s.multicityGroupReference !== undefined &&
    typeof s.multicityGroupReference !== 'string'
  ) {
    return undefined;
  }
  return state as PaymentPageState;
}

/**
 * Safely parse location.state into ConfirmationPageState.
 * Accepts state with only paymentIntentId (bookingResult may come from Redux).
 */
export function parseConfirmationPageState(
  state: unknown
): ConfirmationPageState | undefined {
  if (!isObject(state)) return undefined;
  const s = state;
  const br = s.bookingResult;
  if (
    br != null &&
    (!isObject(br) || typeof br.voyaBookingReference !== 'string')
  ) {
    return undefined;
  }
  if (
    s.paymentIntentId != null &&
    typeof s.paymentIntentId !== 'string'
  ) {
    return undefined;
  }
  if (
    s.multicityGroupReference != null &&
    typeof s.multicityGroupReference !== 'string'
  ) {
    return undefined;
  }
  const ml = s.multicityLegBookingResults;
  if (ml != null) {
    if (!Array.isArray(ml)) return undefined;
    for (const item of ml) {
      if (
        !isObject(item) ||
        typeof item.legIndex !== 'number' ||
        typeof item.voyaBookingReference !== 'string'
      ) {
        return undefined;
      }
    }
  }
  return state as ConfirmationPageState;
}

/**
 * Safely parse location.state into FlightSearchState.
 */
export function parseFlightSearchState(
  state: unknown
): FlightSearchState | undefined {
  if (!isObject(state)) return undefined;
  if (
    state.fromChat !== undefined &&
    typeof state.fromChat !== 'boolean'
  ) {
    return undefined;
  }
  return state as FlightSearchState;
}
