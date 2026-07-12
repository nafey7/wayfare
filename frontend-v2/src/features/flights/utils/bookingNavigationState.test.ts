import { describe, it, expect } from 'vitest';
import {
  buildFlightVoucherNavState,
  parseFlightVoucherNavState,
  parsePaymentPageState,
  parsePaymentPageStateMinimal,
} from './bookingNavigationState';

/** GDS flow from Review: revalidate shape may not pass full parse — minimal parse still works */
const gdsReviewState = {
  revolutOrder: {
    orderId: 'ord_rev_1',
    publicOrderId: 'tok_public_1',
    amount: 50000,
    currency: 'usd',
    platformFee: 2500,
    supplierAmount: 47500,
  },
  bookingResult: {
    voyaBookingReference: 'VOYA-GDS-ABC12',
    externalBookingReference: undefined,
    status: 'pending',
    totalAmount: 500,
    currency: 'USD',
  },
};

describe('parsePaymentPageStateMinimal', () => {
  it('returns state when revolutOrder and bookingResult are valid', () => {
    const parsed = parsePaymentPageStateMinimal(gdsReviewState);
    expect(parsed).toBeDefined();
    expect(parsed?.revolutOrder?.orderId).toBe('ord_rev_1');
    expect(parsed?.bookingResult?.voyaBookingReference).toBe('VOYA-GDS-ABC12');
  });

  it('returns undefined when revolutOrder is missing', () => {
    expect(
      parsePaymentPageStateMinimal({ ...gdsReviewState, revolutOrder: undefined })
    ).toBeUndefined();
  });

  it('returns undefined when orderId or publicOrderId is not a string', () => {
    expect(
      parsePaymentPageStateMinimal({
        ...gdsReviewState,
        revolutOrder: { ...gdsReviewState.revolutOrder, orderId: 1 as unknown as string },
      })
    ).toBeUndefined();
  });

  it('returns undefined when bookingResult.voyaBookingReference is missing', () => {
    expect(
      parsePaymentPageStateMinimal({
        ...gdsReviewState,
        bookingResult: { ...gdsReviewState.bookingResult, voyaBookingReference: undefined as unknown as string },
      })
    ).toBeUndefined();
  });

  it('returns undefined for non-object state', () => {
    expect(parsePaymentPageStateMinimal(null)).toBeUndefined();
    expect(parsePaymentPageStateMinimal('x')).toBeUndefined();
  });
});

describe('parsePaymentPageState', () => {
  it('falls back to minimal parse when full flight booking state is invalid', () => {
    const state = {
      ...gdsReviewState,
      revalidateResponse: { invalid: true },
    };
    const parsed = parsePaymentPageState(state);
    expect(parsed?.revolutOrder?.publicOrderId).toBe('tok_public_1');
  });

  it('falls back to minimal when bookingResult shape fails full validation', () => {
    const state = {
      revolutOrder: gdsReviewState.revolutOrder,
      bookingResult: { status: 'pending' },
    };
    expect(parsePaymentPageState(state)).toEqual(
      parsePaymentPageStateMinimal(state)
    );
  });

  it('parses full state when revalidateResponse and shared fields are valid', () => {
    const full = {
      revalidateResponse: {
        validatedFareItineraries: [],
        returnFareSourceCode: null,
      },
      searchSessionId: 'sess-1',
      ...gdsReviewState,
    };
    const parsed = parsePaymentPageState(full);
    expect(parsed?.searchSessionId).toBe('sess-1');
    expect(parsed?.revolutOrder?.orderId).toBe('ord_rev_1');
  });
});

describe('buildFlightVoucherNavState / parseFlightVoucherNavState', () => {
  it('builds and parses a round-trippable voucher nav payload', () => {
    const built = buildFlightVoucherNavState({
      voucherRedemptionId: 'rid-1',
      voucherCheckoutRef: 'VOYA-ABCDEFGHJK',
      voucherAppliedCode: 'SAVE10',
      voucherDiscountCents: 2500,
      voucherReservationExpiresAt: '2026-01-01T12:00:00Z',
    });
    expect(built).toEqual({
      redemptionId: 'rid-1',
      discountCents: 2500,
      checkoutVoyaReference: 'VOYA-ABCDEFGHJK',
      code: 'SAVE10',
      reservationExpiresAt: '2026-01-01T12:00:00Z',
    });
    expect(parseFlightVoucherNavState({ flightVoucher: built })).toEqual(built);
  });

  it('returns undefined when any required voucher field is missing', () => {
    expect(
      buildFlightVoucherNavState({
        voucherRedemptionId: 'r',
        voucherCheckoutRef: 'VOYA-ABCDEFGHJK',
        voucherAppliedCode: 'X',
        voucherDiscountCents: null,
        voucherReservationExpiresAt: null,
      })
    ).toBeUndefined();
  });

  it('parseFlightVoucherNavState returns undefined for invalid shapes', () => {
    expect(parseFlightVoucherNavState(null)).toBeUndefined();
    expect(parseFlightVoucherNavState({ flightVoucher: { redemptionId: 1 } })).toBeUndefined();
  });
});
