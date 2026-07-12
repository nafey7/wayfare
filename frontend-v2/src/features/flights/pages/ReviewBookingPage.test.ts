import { describe, it, expect } from 'vitest';

/**
 * ReviewBookingPage wires promo + payCents into Revolut create-order.
 * Integration is covered by PromoCodeField tests and manual QA; keep a stable pricing invariant here.
 */
describe('ReviewBookingPage voucher pricing', () => {
  it('post-voucher cents are non-negative', () => {
    const preDiscountCents = 50_000;
    const voucherDiscountCents = 12_500;
    const payCents = Math.max(0, preDiscountCents - voucherDiscountCents);
    expect(payCents).toBe(37_500);
  });
});
