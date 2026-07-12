/**
 * Parse coordinate value to number.
 * API may return string (e.g. "51.5074"); returns NaN for invalid.
 */
export function parseCoord(v: unknown): number {
  if (v == null) return NaN;
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  return typeof n === 'number' && !Number.isNaN(n) ? n : NaN;
}
