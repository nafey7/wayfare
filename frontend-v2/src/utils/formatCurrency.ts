/**
 * Format integer cents (USD) as a locale-aware USD string. Returns "—" when
 * `cents` is null/undefined — for "no value" cells in admin tables.
 *
 * For non-USD or non-cents money, see `formatCurrencyFromCents` /
 * `formatCurrency` in `features/flights/utils/flightUtils.ts`.
 */
export function formatUsdCentsOrDash(cents: number | null | undefined): string {
  if (cents == null) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(cents / 100);
}
