import { useCallback } from 'react';
import {
  useApplyVoucherMutation,
  useReleaseVoucherMutation,
} from '@/api/vouchersApi';
import { parseVoucherApplyError, type VoucherApplyErrorOptions } from '../voucherErrors';

export interface AppliedVoucherState {
  redemptionId: string;
  discountCents: number;
  code: string;
  reservationExpiresAt: string;
}

export function useVoucherRedemption() {
  const [applyVoucherMut, { isLoading: applying }] = useApplyVoucherMutation();
  const [releaseVoucherMut, { isLoading: releasing }] = useReleaseVoucherMutation();

  const applyVoucher = useCallback(
    async (params: {
      code: string;
      voyaBookingReference: string;
      amountCents: number;
      bookingType: 'flight' | 'hotel';
      applyErrorOptions?: VoucherApplyErrorOptions;
    }) => {
      const parseOpts = params.applyErrorOptions;
      try {
        const res = await applyVoucherMut({
          code: params.code,
          voyaBookingReference: params.voyaBookingReference,
          amountCents: params.amountCents,
          bookingType: params.bookingType,
        }).unwrap();
        const applied: AppliedVoucherState = {
          redemptionId: res.redemptionId,
          discountCents: res.discountCents,
          code: res.code,
          reservationExpiresAt: res.reservationExpiresAt,
        };
        return { ok: true as const, applied, newTotalCents: res.newTotalCents };
      } catch (e) {
        const { message, reservedConflict } = parseVoucherApplyError(e, parseOpts);
        return { ok: false as const, error: message, reservedConflict };
      }
    },
    [applyVoucherMut]
  );

  const releaseVoucher = useCallback(
    async (redemptionId: string, reason?: string) => {
      try {
        await releaseVoucherMut({ redemptionId, reason }).unwrap();
        return { ok: true as const };
      } catch {
        return { ok: false as const };
      }
    },
    [releaseVoucherMut]
  );

  return {
    applyVoucher,
    releaseVoucher,
    applying,
    releasing,
    busy: applying || releasing,
  };
}
