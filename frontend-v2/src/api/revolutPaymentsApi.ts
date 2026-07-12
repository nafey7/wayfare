import { baseApi } from './baseApi';
import { toCamelCase, toSnakeCase } from '@/utils/transforms';

/** Request to create Revolut order (camelCase; API expects snake_case) */
export interface RevolutOrderCreateRequest {
  bookingAmount: number; // Cents
  currency: string; // e.g. "usd"
  /** Required for flight; optional for hotel (backend generates nanoid) */
  voyaBookingReference?: string;
  /** 'flight' (default) or 'hotel' - affects Revolut metadata/industry_type */
  orderType?: 'flight' | 'hotel';
  /** From POST /vouchers/apply; stored on booking event when set */
  voucherRedemptionId?: string;
  /** LCC skips PENDING GDS row after create-order; omit for hotel */
  carrierType?: 'GDS' | 'LCC';
}

/** Response from create-order or existing-order (camelCase) */
export interface RevolutOrderCreateResponse {
  orderId: string;
  publicOrderId: string;
  amount: number;
  currency: string;
  platformFee: number;
  supplierAmount: number;
  publicKey: string;
  /** VOYA ref used in Revolut metadata - use for book API clientRef (hotel: nanoid, flight: echoed) */
  voyaBookingReference: string;
}

/** Revolut transaction (camelCase) */
export interface RevolutTransactionResponse {
  id: string;
  revolutOrderId: string;
  voyaBookingReference: string;
  amount: number;
  currency: string;
  platformFee: number;
  supplierAmount: number;
  status: 'pending' | 'authorized' | 'completed' | 'succeeded' | 'failed' | 'canceled' | 'refunded';
  createdAt: string;
  updatedAt: string;
  paidAt: string | null;
}

export const revolutPaymentsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    createRevolutOrder: builder.mutation<RevolutOrderCreateResponse, RevolutOrderCreateRequest>({
      query: (body) => {
        // Hotel: backend generates voya ref; flight: caller must provide voyaBookingReference (no API fallback)
        const ref =
          typeof body.voyaBookingReference === 'string' && body.voyaBookingReference
            ? body.voyaBookingReference
            : undefined;
        return {
          url: '/revolut-payments/create-order',
          method: 'POST',
          body: toSnakeCase({ ...body, voyaBookingReference: ref }),
        };
      },
      transformResponse: (response: unknown) => toCamelCase(response) as RevolutOrderCreateResponse,
    }),

    getExistingRevolutOrder: builder.query<RevolutOrderCreateResponse, string>({
      query: (voyaBookingReference) =>
        `/revolut-payments/existing-order/${encodeURIComponent(voyaBookingReference)}`,
      transformResponse: (response: unknown) => toCamelCase(response) as RevolutOrderCreateResponse,
    }),

    getRevolutTransaction: builder.query<RevolutTransactionResponse, string>({
      query: (orderId) => `/revolut-payments/transaction/${encodeURIComponent(orderId)}`,
      transformResponse: (response: unknown) => toCamelCase(response) as RevolutTransactionResponse,
    }),

    getRevolutTransactionsByBooking: builder.query<RevolutTransactionResponse[], string>({
      query: (bookingReference) =>
        `/revolut-payments/booking/${encodeURIComponent(bookingReference)}`,
      transformResponse: (response: unknown) =>
        (toCamelCase(response) as RevolutTransactionResponse[]) ?? [],
    }),
  }),
});

export const {
  useCreateRevolutOrderMutation,
  useGetExistingRevolutOrderQuery,
  useLazyGetExistingRevolutOrderQuery,
  useGetRevolutTransactionQuery,
  useLazyGetRevolutTransactionQuery,
  useGetRevolutTransactionsByBookingQuery,
} = revolutPaymentsApi;
