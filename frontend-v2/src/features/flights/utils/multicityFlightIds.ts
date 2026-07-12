/**
 * Multicity search uses composite card ids: `${legIndex}::${fareSourceCode}`.
 */
export function parseMulticityFlightId(
  id: string
): { legIndex: number; fareSourceCode: string } | null {
  const sep = '::';
  const idx = id.indexOf(sep);
  if (idx <= 0) return null;
  const leg = Number(id.slice(0, idx));
  if (!Number.isInteger(leg) || leg < 0) return null;
  const fareSourceCode = id.slice(idx + sep.length);
  if (!fareSourceCode) return null;
  return { legIndex: leg, fareSourceCode };
}
