import type { LinkedBookingEventSummary } from '@/types/itineraries';

/** Returns "DEP → ARR", "DEP ↔ ARR" for a round-trip, or "Flight" as a fallback. */
export function getFlightRouteLabel(
  event: LinkedBookingEventSummary | null | undefined,
): string {
  const legs = event?.routeLegs;
  if (legs && legs.length > 0) {
    const first = legs[0];
    const dep = first?.departureIata?.trim();
    const arr = first?.arrivalIata?.trim();
    if (dep && arr) {
      if (
        event?.flightTripType === 'round_trip' &&
        legs.length === 2 &&
        legs[1]?.arrivalIata?.trim() === dep
      ) {
        return `${dep} ↔ ${arr}`;
      }
      return `${dep} → ${arr}`;
    }
  }
  const dep = event?.departureAirportIata?.trim();
  const arr = event?.arrivalAirportIata?.trim();
  if (dep && arr) return `${dep} → ${arr}`;
  if (dep) return dep;
  return 'Flight';
}
