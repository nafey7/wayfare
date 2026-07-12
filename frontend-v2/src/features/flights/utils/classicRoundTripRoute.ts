/**
 * Classic round trip: outbound A→B and return B→A → single display line `A ⇆ B`.
 * Only applies when {@link flightTripType} is `round_trip` and both legs have valid 3-letter IATAs.
 */

export type FlightTripTypeForRoute =
  | 'one_way'
  | 'round_trip'
  | 'multi_city'
  | null
  | undefined;

function normIata(s: string | null | undefined): string {
  return (s ?? '').trim().toUpperCase();
}

/**
 * @returns e.g. `LHR ⇆ JFK` when the second leg is the inverse of the first; otherwise `null`.
 */
export function tryClassicRoundTripLine(
  outboundDep: string | null | undefined,
  outboundArr: string | null | undefined,
  returnDep: string | null | undefined,
  returnArr: string | null | undefined,
  flightTripType: FlightTripTypeForRoute,
): string | null {
  if (flightTripType !== 'round_trip') return null;
  const o1 = normIata(outboundDep);
  const d1 = normIata(outboundArr);
  const o2 = normIata(returnDep);
  const d2 = normIata(returnArr);
  if (o1.length !== 3 || d1.length !== 3 || o2.length !== 3 || d2.length !== 3) {
    return null;
  }
  if (o1 !== d2 || d1 !== o2) return null;
  return `${o1} ⇆ ${d1}`;
}
