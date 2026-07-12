import { baseApi } from './baseApi';
import { toCamelCase, toSnakeCase } from '@/utils/transforms';

/** Single discount / voucher document (admin, camelCase). */
export interface AdminVoucherDoc {
  id: string;
  code: string;
  amountCents: number;
  currency: string;
  status: string;
  source: string;
  batchId: string;
  createdAt: string;
  createdByAdminId?: string | null;
  expiresAt?: string | null;
  reservedByUserId?: string | null;
  reservedForBookingReference?: string | null;
  reservationExpiresAt?: string | null;
  redeemedAt?: string | null;
  userId?: string | null;
  bookingReference?: string | null;
}

export interface AdminDiscountListResponse {
  items: AdminVoucherDoc[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminBatchSummary {
  batchId: string;
  total: number;
  used: number;
  reserved: number;
  active: number;
  expired: number;
  disabled: number;
  source: string;
  createdAt: string | null;
  totalAmountCents: number | null;
}

export interface AdminBatchListResponse {
  batches: AdminBatchSummary[];
}

export interface AdminBatchDetailResponse {
  batchId: string;
  source: string;
  createdAt: string | null;
  summary: AdminBatchSummary;
  codes: AdminVoucherDoc[];
  totalCodes: number;
  limit: number;
  offset: number;
}

export interface CreateAdminDiscountBatchBody {
  count: number;
  amountCents: number;
  source: string;
  prefix?: string;
  expiresAt?: string | null;
}

export interface CreateAdminDiscountBatchResponse {
  batchId: string;
  count: number;
  totalAmountCents: number;
  currency: string;
  createdAt: string;
  sampleCodes: string[];
}

export interface ListAdminDiscountsParams {
  status?: string;
  batchId?: string;
  source?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface GetAdminBatchDetailParams {
  batchId: string;
  status?: string;
  limit?: number;
  offset?: number;
}

function buildDiscountsQuery(params: ListAdminDiscountsParams): string {
  const sp = new URLSearchParams();
  if (params.status != null) sp.set('status', params.status);
  if (params.batchId != null) sp.set('batch_id', params.batchId);
  if (params.source != null) sp.set('source', params.source);
  if (params.search != null) sp.set('search', params.search);
  if (params.limit != null) sp.set('limit', String(params.limit));
  if (params.offset != null) sp.set('offset', String(params.offset));
  const q = sp.toString();
  return q ? `/admin/discounts?${q}` : '/admin/discounts';
}

function buildBatchDetailQuery({
  batchId,
  status,
  limit,
  offset,
}: GetAdminBatchDetailParams): string {
  const sp = new URLSearchParams();
  if (status != null) sp.set('status', status);
  if (limit != null) sp.set('limit', String(limit));
  if (offset != null) sp.set('offset', String(offset));
  const q = sp.toString();
  const base = `/admin/discounts/batches/${encodeURIComponent(batchId)}`;
  return q ? `${base}?${q}` : base;
}

export const adminDiscountsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listAdminDiscounts: builder.query<
      AdminDiscountListResponse,
      ListAdminDiscountsParams | void
    >({
      query: (params) => buildDiscountsQuery(params ?? {}),
      providesTags: ['AdminDiscounts'],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as AdminDiscountListResponse,
    }),
    getAdminDiscount: builder.query<AdminVoucherDoc, string>({
      query: (discountId) =>
        `/admin/discounts/${encodeURIComponent(discountId)}`,
      providesTags: (_r, _e, id) => [{ type: 'AdminDiscounts', id }],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as AdminVoucherDoc,
    }),
    disableAdminDiscount: builder.mutation<AdminVoucherDoc, string>({
      query: (discountId) => ({
        url: `/admin/discounts/${encodeURIComponent(discountId)}/disable`,
        method: 'POST',
      }),
      invalidatesTags: (result) =>
        result
          ? [
              'AdminDiscounts',
              'AdminDiscountBatches',
              { type: 'AdminDiscountBatches', id: result.batchId },
            ]
          : ['AdminDiscounts', 'AdminDiscountBatches'],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as AdminVoucherDoc,
    }),
    listAdminDiscountBatches: builder.query<AdminBatchListResponse, void>({
      query: () => '/admin/discounts/batches',
      providesTags: ['AdminDiscountBatches'],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as AdminBatchListResponse,
    }),
    createAdminDiscountBatch: builder.mutation<
      CreateAdminDiscountBatchResponse,
      CreateAdminDiscountBatchBody
    >({
      query: (body) => ({
        url: '/admin/discounts/batches',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      invalidatesTags: ['AdminDiscountBatches', 'AdminDiscounts'],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as CreateAdminDiscountBatchResponse,
    }),
    getAdminBatchDetail: builder.query<
      AdminBatchDetailResponse,
      GetAdminBatchDetailParams
    >({
      query: (params) => buildBatchDetailQuery(params),
      providesTags: (_r, _e, arg) => [
        { type: 'AdminDiscountBatches', id: arg.batchId },
      ],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as AdminBatchDetailResponse,
    }),
    getAdminBatchCsv: builder.query<Blob, string>({
      query: (batchId) => ({
        url: `/admin/discounts/batches/${encodeURIComponent(batchId)}/export.csv`,
        responseHandler: async (response) => response.blob(),
      }),
    }),
  }),
});

export const {
  useListAdminDiscountsQuery,
  useGetAdminDiscountQuery,
  useDisableAdminDiscountMutation,
  useListAdminDiscountBatchesQuery,
  useCreateAdminDiscountBatchMutation,
  useGetAdminBatchDetailQuery,
  useLazyGetAdminBatchCsvQuery,
} = adminDiscountsApi;
