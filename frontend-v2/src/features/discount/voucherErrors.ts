/**
 * Map /vouchers/apply HTTP errors to traveler-facing copy.
 * Server detail strings come from `app.domains.discount.service` (VoucherReservedByOtherError, etc.).
 */

export interface VoucherApplyErrorOptions {
  /** From GET /config; used in reserved-conflict copy. */
  reservationTtlMinutes?: number;
}

function detailStringFromUnknown(raw: unknown): string {
  if (typeof raw === 'string') return raw;
  if (Array.isArray(raw) && raw.length > 0) {
    const first = raw[0];
    if (first && typeof first === 'object' && 'msg' in first && typeof (first as { msg: unknown }).msg === 'string') {
      return (first as { msg: string }).msg;
    }
  }
  return '';
}

function getHttpInfo(err: unknown): { status: number; detail: string } | null {
  if (typeof err !== 'object' || err === null || !('status' in err)) return null;
  const e = err as { status: number; data?: { detail?: unknown } };
  return { status: e.status, detail: detailStringFromUnknown(e.data?.detail) };
}

/**
 * When true, the UI should show the message as a toast (not an inline field alert) —
 * applies to "code is reserved for another booking / user" conflicts (HTTP 409).
 */
export function parseVoucherApplyError(
  err: unknown,
  options?: VoucherApplyErrorOptions
): { message: string; reservedConflict: boolean } {
  const ttl = options?.reservationTtlMinutes;
  const waitForHold = ttl != null ? `about ${ttl} minutes` : 'a little while';
  const tryAgainIn = ttl != null ? `about ${ttl} minutes` : 'a few minutes';

  const info = getHttpInfo(err);
  if (info) {
    const { status, detail: d } = info;

    if (status === 404) {
      return {
        message: "We couldn't find that promo code. Check the code and try again.",
        reservedConflict: false,
      };
    }

    if (status === 409) {
      // Same checkout ref path is success; these are from live reservation for another user/booking.
      if (/Voucher is reserved for a different booking/i.test(d)) {
        return {
          message: `This code is already held for a different checkout. Continue that trip, remove the code there, or wait ${waitForHold} and try again here.`,
          reservedConflict: true,
        };
      }
      if (/Voucher is reserved by another user or booking/i.test(d)) {
        return {
          message: `This promo is in use on another booking. Try again in ${tryAgainIn}, or use a different code.`,
          reservedConflict: true,
        };
      }
      if (/used|disabled/i.test(d)) {
        return { message: 'This promo code is no longer available.', reservedConflict: false };
      }
      return {
        message: d || 'This promo code cannot be applied right now.',
        reservedConflict: false,
      };
    }

    if (status === 410) {
      if (/reservation expired|try again/i.test(d)) {
        return {
          message: 'That reservation has ended. You can try applying the code again.',
          reservedConflict: false,
        };
      }
      return { message: 'This promo code has expired.', reservedConflict: false };
    }

    if (status === 422) {
      if (/below|partial|USD|currency/i.test(d)) {
        return { message: d, reservedConflict: false };
      }
      return {
        message: d || 'This promo code cannot be applied to this total.',
        reservedConflict: false,
      };
    }

    if (status >= 500) {
      return {
        message: "We couldn't apply that promo code right now. Please try again in a moment.",
        reservedConflict: false,
      };
    }

    return { message: d || 'Something went wrong. Please try again.', reservedConflict: false };
  }

  if (err instanceof Error) return { message: err.message, reservedConflict: false };
  return { message: 'Something went wrong. Please try again.', reservedConflict: false };
}

export function mapVoucherApplyError(err: unknown, options?: VoucherApplyErrorOptions): string {
  return parseVoucherApplyError(err, options).message;
}
