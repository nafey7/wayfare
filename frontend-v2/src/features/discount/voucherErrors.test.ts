import { describe, it, expect } from 'vitest';

import { parseVoucherApplyError } from './voucherErrors';

describe('parseVoucherApplyError', () => {
  it('marks VoucherReservedByOtherError (another user) as reservedConflict with clear copy', () => {
    const r = parseVoucherApplyError(
      { status: 409, data: { detail: 'Voucher is reserved by another user or booking' } },
      { reservationTtlMinutes: 15 }
    );
    expect(r.reservedConflict).toBe(true);
    expect(r.message).toContain('in use on another booking');
    expect(r.message).toContain('15');
  });

  it('marks different-booking reservation as reservedConflict', () => {
    const r = parseVoucherApplyError(
      { status: 409, data: { detail: 'Voucher is reserved for a different booking' } },
      { reservationTtlMinutes: 20 }
    );
    expect(r.reservedConflict).toBe(true);
    expect(r.message).toContain('different checkout');
    expect(r.message).toContain('20');
  });

  it('does not treat invalid state 409 as reserved conflict', () => {
    const r = parseVoucherApplyError({
      status: 409,
      data: { detail: 'Could not apply voucher' },
    });
    expect(r.reservedConflict).toBe(false);
    expect(r.message).toContain('Could not apply');
  });

  it('maps 404 without reservedConflict', () => {
    const r = parseVoucherApplyError({ status: 404, data: { detail: 'Not found' } });
    expect(r.reservedConflict).toBe(false);
    expect(r.message).toMatch(/couldn't find/i);
  });
});
