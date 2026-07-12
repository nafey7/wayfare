/**
 * Hotel-specific display and calculation helpers.
 */

/** Default currency when API does not provide one (e.g. hotel totals without currency). */
export const DEFAULT_CURRENCY = 'USD';

/**
 * Format amount in major units as locale-aware currency (e.g. hotel totals from API).
 */
export function formatHotelPrice(
  amount: number | undefined | null,
  currency: string
): string {
  const code = (currency || 'USD').toUpperCase();
  const safeAmount = Number(amount ?? 0);
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: code,
  }).format(Number.isFinite(safeAmount) ? safeAmount : 0);
}

/**
 * Format ISO date for display (e.g. "Mon, Jan 15, 2026").
 */
export function formatHotelDate(isoDate: string | null | undefined): string {
  if (!isoDate) return '';
  try {
    const d = new Date(isoDate);
    return d.toLocaleDateString(undefined, {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return isoDate;
  }
}

/**
 * Calculate number of nights between check-in and check-out (inclusive of check-in, exclusive of check-out).
 */
export function getNightsBetweenDates(checkin: string | null, checkout: string | null): number {
  if (!checkin || !checkout) return 0;
  try {
    const start = new Date(checkin);
    const end = new Date(checkout);
    const diffMs = end.getTime() - start.getTime();
    return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
  } catch {
    return 0;
  }
}

/**
 * Compact stay line for booking review headers, e.g. "May 10–14 · 4 nights".
 */
export function formatCompactHotelStayLine(
  checkin: string | null,
  checkout: string | null,
  nights: number
): string {
  if (!checkin || !checkout) return '';
  try {
    const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
    const a = new Date(checkin).toLocaleDateString(undefined, opts);
    const b = new Date(checkout).toLocaleDateString(undefined, opts);
    return `${a}–${b} · ${nights} night${nights !== 1 ? 's' : ''}`;
  } catch {
    return '';
  }
}
