import type {
  FlightBookingListItem,
  FlightLegSummaryItem,
  FlightRouteLeg,
} from '@/types/flights';
import { tryClassicRoundTripLine } from '@/features/flights/utils/classicRoundTripRoute';
import {
  formatBookingAction,
  formatDateShort,
  formatListAmountMajor,
  parseDateOnlyUtc,
  parseIso,
  type BookingListAction,
} from '@/features/profile/components/bookings/listFormatters';
import { formatAirportPairLine } from '@/features/itinerary/components/linkedBookings/linkedBookingFormat';

function buildSummaryFromRouteLegs(
  legs: FlightRouteLeg[],
  flightTripType: FlightBookingListItem['flightTripType'],
): string {
  if (legs.length === 2) {
    const leg0 = legs[0];
    const leg1 = legs[1];
    if (!leg0 || !leg1) return 'Flight booking';
    const sym = tryClassicRoundTripLine(
      leg0.departureIata,
      leg0.arrivalIata,
      leg1.departureIata,
      leg1.arrivalIata,
      flightTripType,
    );
    if (sym) return `Flight · ${sym}`;
  }
  const parts: string[] = [];
  for (const leg of legs) {
    const p = formatAirportPairLine(leg.departureIata, leg.arrivalIata);
    if (p) parts.push(p);
  }
  if (parts.length === 0) return 'Flight booking';
  return `Flight · ${parts.join(' · ')}`;
}

function primarySecondaryRoutesFromLegs(
  routeLegs: FlightRouteLeg[] | undefined | null,
  flightTripType: FlightBookingListItem['flightTripType'],
): { primaryRouteLine: string | null; secondaryRouteLine: string | null } {
  const legs = routeLegs?.filter(Boolean) ?? [];
  if (legs.length === 0) return { primaryRouteLine: null, secondaryRouteLine: null };
  const leg0 = legs[0];
  if (!leg0) return { primaryRouteLine: null, secondaryRouteLine: null };
  const first = formatAirportPairLine(leg0.departureIata, leg0.arrivalIata);
  if (legs.length === 1) return { primaryRouteLine: first, secondaryRouteLine: null };
  const leg1 = legs[1];
  if (!leg1) return { primaryRouteLine: first, secondaryRouteLine: null };
  const second = formatAirportPairLine(leg1.departureIata, leg1.arrivalIata);
  if (!second) return { primaryRouteLine: first, secondaryRouteLine: null };
  if (legs.length === 2) {
    const classic = tryClassicRoundTripLine(
      leg0.departureIata,
      leg0.arrivalIata,
      leg1.departureIata,
      leg1.arrivalIata,
      flightTripType,
    );
    if (classic) return { primaryRouteLine: classic, secondaryRouteLine: null };
  }
  if (flightTripType === 'round_trip') {
    return { primaryRouteLine: first, secondaryRouteLine: `Return · ${second}` };
  }
  if (legs.length > 2) {
    return {
      primaryRouteLine: first,
      secondaryRouteLine: `${legs.length} legs · ${second}`,
    };
  }
  return { primaryRouteLine: first, secondaryRouteLine: second };
}

function firstDepartureIataFromRouteLegs(legs: FlightRouteLeg[] | undefined | null): string | null {
  if (!legs?.length) return null;
  const leg0 = legs[0];
  if (!leg0) return null;
  const s0 = leg0.segments?.[0];
  const fromSeg = s0?.departureIata?.trim();
  if (fromSeg) return fromSeg;
  return leg0.departureIata?.trim() ?? null;
}

function formatTravelDateLabel(legs: FlightLegSummaryItem[]): string | null {
  const labels: string[] = [];
  for (const leg of legs) {
    const d = parseDateOnlyUtc(leg.departureDate);
    if (d) labels.push(formatDateShort(d));
  }
  if (labels.length === 0) return null;
  if (labels.length === 1) return labels[0] ?? null;
  if (labels.length === 2) {
    const a = labels[0];
    const b = labels[1];
    if (a && b) return `${a} – ${b}`;
    return null;
  }
  if (legs.length <= 4) return `${legs.length} legs: ${labels.join(', ')}`;
  return `${legs.length} legs: ${labels.slice(0, 3).join(', ')}…`;
}

function buildFlightSummaryLine(
  legs: FlightLegSummaryItem[] | undefined | null,
  departureAirportIata: string | undefined | null,
  flightTripType: FlightBookingListItem['flightTripType'],
): string {
  const list = legs?.filter((l) => l.originIata && l.destinationIata) ?? [];
  const first = list[0];
  if (first) {
    const o0 = first.originIata.trim();
    const d0 = first.destinationIata.trim();
    const firstRoute = `${o0} → ${d0}`;
    if (list.length === 1) return `Flight · ${firstRoute}`;
    const second = list[1];
    if (list.length === 2 && second) {
      const sym = tryClassicRoundTripLine(
        first.originIata,
        first.destinationIata,
        second.originIata,
        second.destinationIata,
        flightTripType,
      );
      if (sym) return `Flight · ${sym}`;
      const o1 = second.originIata.trim();
      const d1 = second.destinationIata.trim();
      return `Flight · ${firstRoute} · ${o1} → ${d1}`;
    }
    return `Flight · ${firstRoute} · ${list.length} legs`;
  }
  const iata = departureAirportIata?.trim();
  return iata ? `Flight booking · departs ${iata}` : 'Flight booking';
}

function primarySecondaryFromLegSummaries(
  legs: FlightLegSummaryItem[] | undefined | null,
  flightTripType: FlightBookingListItem['flightTripType'],
): { primaryRouteLine: string | null; secondaryRouteLine: string | null } {
  const list = legs?.filter((l) => l.originIata && l.destinationIata) ?? [];
  if (list.length === 0) return { primaryRouteLine: null, secondaryRouteLine: null };
  const s0 = list[0];
  if (!s0) return { primaryRouteLine: null, secondaryRouteLine: null };
  const p0 = formatAirportPairLine(s0.originIata, s0.destinationIata);
  if (list.length === 1) return { primaryRouteLine: p0, secondaryRouteLine: null };
  const s1 = list[1];
  if (!s1) return { primaryRouteLine: p0, secondaryRouteLine: null };
  const p1 = formatAirportPairLine(s1.originIata, s1.destinationIata);
  if (!p1) return { primaryRouteLine: p0, secondaryRouteLine: null };
  if (list.length === 2) {
    const classic = tryClassicRoundTripLine(
      s0.originIata,
      s0.destinationIata,
      s1.originIata,
      s1.destinationIata,
      flightTripType,
    );
    if (classic) return { primaryRouteLine: classic, secondaryRouteLine: null };
  }
  if (flightTripType === 'round_trip') {
    return { primaryRouteLine: p0, secondaryRouteLine: `Return · ${p1}` };
  }
  if (list.length > 2) {
    return {
      primaryRouteLine: p0,
      secondaryRouteLine: `${list.length} legs · ${p1}`,
    };
  }
  return { primaryRouteLine: p0, secondaryRouteLine: p1 };
}

export interface ProfileFlightBookingRowModel {
  reference: string | null;
  summaryLine: string;
  /** Hero: first leg or outbound `DEP → ARR` when known. */
  primaryRouteLine: string | null;
  /** Hero: return leg or extra legs hint (e.g. `Return · LHR → JFK`). */
  secondaryRouteLine: string | null;
  /** Marketing carrier or PNR airline name for chips. */
  airlineLabel: string | null;
  statusLabel: string;
  secondaryStatus: string | null;
  dateLabel: string | null;
  amountLabel: string | null;
  canNavigate: boolean;
  action: BookingListAction;
  departureIata: string | null;
  /** First leg origin IATA for prominent display (e.g. "LHR"). */
  originIata: string | null;
  /** First leg destination IATA for prominent display (e.g. "LIS"). */
  destinationIata: string | null;
}

export { formatListAmountMajor } from '@/features/profile/components/bookings/listFormatters';

export function mapFlightMyBookingToRow(item: FlightBookingListItem): ProfileFlightBookingRowModel {
  const ref = item.voyaBookingReference ?? null;
  const tripType = item.flightTripType;
  const routeLegs = item.routeLegs?.length ? item.routeLegs : null;
  const legs = item.flightLegSummaries?.length ? item.flightLegSummaries : null;

  let summaryLine: string;
  let primaryRouteLine: string | null;
  let secondaryRouteLine: string | null;

  if (routeLegs) {
    summaryLine = buildSummaryFromRouteLegs(routeLegs, tripType);
    const rs = primarySecondaryRoutesFromLegs(routeLegs, tripType);
    primaryRouteLine = rs.primaryRouteLine;
    secondaryRouteLine = rs.secondaryRouteLine;
  } else if (legs) {
    summaryLine = buildFlightSummaryLine(legs, item.departureAirportIata, tripType);
    const ps = primarySecondaryFromLegSummaries(legs, tripType);
    primaryRouteLine = ps.primaryRouteLine;
    secondaryRouteLine = ps.secondaryRouteLine;
  } else {
    summaryLine = buildFlightSummaryLine(null, item.departureAirportIata, tripType);
    primaryRouteLine = null;
    secondaryRouteLine = null;
  }

  const iataFromRoute = firstDepartureIataFromRouteLegs(routeLegs);
  const iataFromLegs = legs?.[0]?.originIata?.trim();
  const iataStored = item.departureAirportIata?.trim();
  const iata = iataFromRoute || iataFromLegs || iataStored;

  const travelDates = legs ? formatTravelDateLabel(legs) : null;
  const bookedAt = parseIso(item.dateBooked) ?? parseIso(item.timestamp);
  const dateLabel = travelDates ?? (bookedAt ? formatDateShort(bookedAt) : null);

  const ticket = item.ticketStatus?.trim();
  const secondaryStatus =
    ticket && ticket.toLowerCase() !== 'confirmed' ? ticket : null;

  const airlineLabel =
    item.primaryMarketingAirlineName?.trim() ||
    item.airlinePnrAirlineName?.trim() ||
    null;

  const originIata = iata ?? null;
  const destinationIata =
    routeLegs?.[0]?.arrivalIata?.trim() || legs?.[0]?.destinationIata?.trim() || null;

  return {
    reference: ref,
    summaryLine,
    primaryRouteLine,
    secondaryRouteLine,
    airlineLabel,
    statusLabel: formatBookingAction(item.action),
    secondaryStatus,
    dateLabel,
    amountLabel: formatListAmountMajor(item.amount ?? null),
    canNavigate: Boolean(ref && ref.length > 0),
    action: item.action,
    departureIata: iata ?? null,
    originIata,
    destinationIata,
  };
}
