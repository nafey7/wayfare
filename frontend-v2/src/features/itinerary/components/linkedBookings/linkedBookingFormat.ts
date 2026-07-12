/** Format ISO date strings for linked booking cards (user locale, medium date). */
export function formatBookingDate(iso: string | undefined | null): string | null {
  if (!iso?.trim()) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatUsdAmount(amount: number | undefined | null): string | null {
  if (amount == null || Number.isNaN(amount)) return null;
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/** One line like `JFK → LHR`, or a single code if only one end is known. */
export function formatAirportPairLine(
  dep: string | undefined | null,
  arr: string | undefined | null,
): string | null {
  const d = dep?.trim();
  const a = arr?.trim();
  if (d && a) return `${d} → ${a}`;
  if (d) return d;
  if (a) return a;
  return null;
}
