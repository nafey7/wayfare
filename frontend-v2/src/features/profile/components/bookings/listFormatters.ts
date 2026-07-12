/** Shared formatters for profile flight/hotel booking list rows (major units, dates, status). */

export type BookingListAction = 'BOOKED' | 'CANCELLED' | 'PENDING';

export function formatBookingAction(action: BookingListAction): string {
  switch (action) {
    case 'CANCELLED':
      return 'Cancelled';
    case 'PENDING':
      return 'Pending';
    default:
      return 'Booked';
  }
}

export function parseIso(d: string | null | undefined): Date | null {
  if (d == null || d === '') return null;
  const x = new Date(d);
  return Number.isNaN(x.getTime()) ? null : x;
}

/** Parse `YYYY-MM-DD` at UTC noon so locale formatting stays on the intended calendar day. */
export function parseDateOnlyUtc(ymd: string | null | undefined): Date | null {
  if (ymd == null || ymd === '') return null;
  const t = ymd.trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(t)) return null;
  const x = new Date(`${t}T12:00:00.000Z`);
  return Number.isNaN(x.getTime()) ? null : x;
}

export function formatDateShort(d: Date): string {
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Parse YYYY-MM-DD as local calendar date (avoids UTC-only Date parsing shifts). */
export function parseYmdLocal(ymd: string | null | undefined): Date | null {
  if (ymd == null || ymd === '') return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(ymd.trim());
  if (!m) return null;
  const y = Number(m[1]);
  const mo = Number(m[2]) - 1;
  const d = Number(m[3]);
  const dt = new Date(y, mo, d);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

/** Day-first short date for stay lines, e.g. "2 Jul 2026" (stable across user locale). */
function formatStayCalendarDay(d: Date): string {
  return d.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/** Short label for hotel stay: "2 Jul 2026 – 10 Jul 2026 (8 nights)" or fallbacks when partial. */
export function formatHotelStayLabel(
  checkInYmd: string | null | undefined,
  checkOutYmd: string | null | undefined,
  nights: number | null | undefined,
): string | null {
  const dIn = parseYmdLocal(checkInYmd ?? null);
  const dOut = parseYmdLocal(checkOutYmd ?? null);
  if (dIn && dOut) {
    const a = formatStayCalendarDay(dIn);
    const b = formatStayCalendarDay(dOut);
    const n =
      nights != null && nights > 0
        ? nights
        : Math.max(0, Math.round((dOut.getTime() - dIn.getTime()) / 86400000));
    if (n > 0) return `${a} – ${b} (${n} night${n === 1 ? '' : 's'})`;
    return `${a} – ${b}`;
  }
  if (dIn) return formatStayCalendarDay(dIn);
  if (dOut) return formatStayCalendarDay(dOut);
  return null;
}

/**
 * Formats amount as currency (major units).
 * TODO: booking_events do not persist currency; non-USD bookings display incorrectly until the API exposes currency.
 */
export function formatListAmountMajor(amount: number | null): string | null {
  if (amount == null) return null;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}
