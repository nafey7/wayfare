import { baseApi } from './baseApi';
import { toCamelCase, toSnakeCase } from '@/utils/transforms';

export interface VoucherApplyRequest {
  code: string;
  voyaBookingReference: string;
  amountCents: number;
  bookingType?: 'flight' | 'hotel';
  /** Omit or 'usd' only; backend is USD-only for vouchers. */
  currency?: 'usd' | 'USD';
}

export interface VoucherApplyResponse {
  redemptionId: string;
  code: string;
  discountCents: number;
  newTotalCents: number;
  currency: 'usd';
  /** When the reservation hold ends (TTL from apply), not the voucher catalog expiry. */
  reservationExpiresAt: string;
}

export interface VoucherReleaseRequest {
  redemptionId: string;
  reason?: string;
}

export const vouchersApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    applyVoucher: builder.mutation<VoucherApplyResponse, VoucherApplyRequest>({
      query: (body) => ({
        url: '/vouchers/apply',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) => toCamelCase(response) as VoucherApplyResponse,
    }),
    releaseVoucher: builder.mutation<{ released: boolean }, VoucherReleaseRequest>({
      query: (body) => ({
        url: '/vouchers/release',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as { released: boolean },
    }),
  }),
});

export const { useApplyVoucherMutation, useReleaseVoucherMutation } = vouchersApi;
