import type {
  AirlineLogoSource,
  FlightLegCamel,
  FlightSegmentCamel,
  ProcessedLeg,
} from '@/types/flightBackend';
import type { MappedFlight, SegmentData, FlightSegment } from '@/types/flight';
import type { FlightSearchParamsUI, TravellersData, TripType } from '@/types/flights';

export type { ProcessedLeg, AirlineLogoSource };

/**
 * True when round-trip UI state would build an invalid Return payload (single O&D row)
 * per the FlightLogic contract — e.g. malformed URL restore without returnDate.
 */
export function isRoundTripSearchMissingReturnDate(
  params: FlightSearchParamsUI | null | undefined,
): boolean {
  if (!params) return false;
  return params.tripType === 'round-trip' && !params.returnDate;
}

/**
 * Date Utilities
 */

/**
 * Get tomorrow's date (current date + 1 day)
 */
export function getTomorrow(): Date {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return tomorrow;
}

/**
 * Format a Date object to YYYY-MM-DD string for API requests
 */
export function formatDateForAPI(date: Date | null): string {
  if (!date) return '';
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Normalize datetime value from various formats to ISO string
 * Handles string, Date objects, and objects with .value or .isoString properties
 */
export function normalizeDateTime(dtValue: unknown): string | null {
  if (!dtValue) return null;

  // If it's already a string, check if it's a valid ISO string
  if (typeof dtValue === 'string') {
    // Check if it looks like an ISO datetime string (with T separator)
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(dtValue)) {
      return dtValue;
    }
    // If it's a string but not ISO format, try to parse it
    try {
      const date = new Date(dtValue);
      if (!isNaN(date.getTime())) {
        return date.toISOString();
      }
    } catch {
      // Failed to parse datetime string
    }
  }

  // If it's an object, try to extract value
  if (typeof dtValue === 'object' && dtValue !== null) {
    const o = dtValue as Record<string, unknown>;
    if (o.value !== undefined && o.value !== null) {
      return normalizeDateTime(o.value);
    }
    if (typeof o.isoString === 'string') {
      return normalizeDateTime(o.isoString);
    }
    if (dtValue instanceof Date) {
      return dtValue.toISOString();
    }
  }

  return null;
}

/**
 * Extract time from ISO string in HH:MM format
 */
export function extractTimeFromISO(isoString: unknown): string {
  if (!isoString) return 'TBD';

  // Normalize the datetime value first
  const normalized = normalizeDateTime(isoString);
  if (!normalized) return 'TBD';

  // Extract HH:MM from ISO format (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SS.fff)
  const match = normalized.match(/T(\d{2}):(\d{2})/);
  if (match) {
    return `${match[1]}:${match[2]}`;
  }
  return 'TBD';
}

/**
 * Travellers Utilities
 */

/**
 * Format travellers data into display text
 * Example: "2 Adults, 1 Child, Economy"
 */
export function formatTravellersDisplayText(travellers: TravellersData): string {
  const adults = travellers.adults ?? 0;
  const children = travellers.children ?? 0;
  const infants = travellers.infants ?? 0;
  const parts: string[] = [];
  if (adults > 0) {
    parts.push(`${adults} ${adults === 1 ? 'Adult' : 'Adults'}`);
  }
  if (children > 0) {
    parts.push(`${children} ${children === 1 ? 'Child' : 'Children'}`);
  }
  if (infants > 0) {
    parts.push(`${infants} ${infants === 1 ? 'Infant' : 'Infants'}`);
  }
  const cabin = travellers.cabinClass ?? 'Economy';
  if (parts.length === 0 && travellers.adults == null && !travellers.cabinClass) {
    return 'Travellers';
  }
  return parts.length > 0 ? `${parts.join(', ')}, ${cabin}` : cabin;
}

/**
 * Format passenger counts only for display (e.g. on FlightCard).
 * Omits types with quantity 0. Example: "2 Adults, 1 Infant"
 */
export function formatPassengerCountsDisplay(
  adults: number,
  children: number,
  infants: number
): string {
  const parts: string[] = [];
  if (adults > 0) {
    parts.push(`${adults} ${adults === 1 ? 'Adult' : 'Adults'}`);
  }
  if (children > 0) {
    parts.push(`${children} ${children === 1 ? 'Child' : 'Children'}`);
  }
  if (infants > 0) {
    parts.push(`${infants} ${infants === 1 ? 'Infant' : 'Infants'}`);
  }
  return parts.length > 0 ? parts.join(', ') : '1 Adult';
}

/**
 * Default currency when API does not provide one.
 */
export const DEFAULT_CURRENCY = 'USD';

/**
 * Flight shape used by FlightCard (search results).
 * Legs may include segments (from processLeg) for layover details in FlightDetailsModal.
 */
export interface FlightCardFlightInput {
  id: string;
  aircraftName: string;
  flightNumber?: string;
  /** From fare itinerary (`OneWay` | `Return` | `Circle`); drives round-trip vs multi-city UI. */
  journeyType?: string;
  tags: string[];
  passengers: number;
  legs: Array<{
    departure: { city: string; airport: string; date: string; time: string };
    arrival: { city: string; airport: string; date: string; time: string };
    duration: string;
    /** Total time including layovers (when leg has stops). */
    totalTimeDisplay?: string | null;
    stops: number;
    stopsText: string;
    airlinesInfo?: Array<{ name: string; code: string; flights: string[]; logoUrl?: string }>;
    /** Flight segments from API (processLeg) – used to build layovers for details modal. */
    segments?: unknown[];
  }>;
  price: number;
  /** Original ticket amount before platform fee – for price breakdown in modal. */
  original_total_fare?: number;
  /** Platform fee percentage – for price breakdown in modal. */
  platform_fee_percentage?: number;
}

/**
 * Extract logo URL from airline object (handles both camelCase and snake_case).
 */
export function getAirlineLogoUrl(
  airline: AirlineLogoSource | null | undefined
): string | undefined {
  return airline?.logoUrl ?? airline?.logo_url;
}

/**
 * Build layover objects from FlightSegmentCamel[] for FlightDetailsModal.
 * Each layover represents a connection point between consecutive segments.
 */
function buildLayoversFromFlightSegments(
  segments: FlightSegmentCamel[]
): FlightSegment[] {
  const layovers: FlightSegment[] = [];
  for (let i = 0; i < segments.length - 1; i++) {
    const currentSeg = segments[i]!;
    const nextSeg = segments[i + 1]!;
    const currentArr = normalizeDateTime(currentSeg.arrivalDatetime);
    const nextDep = normalizeDateTime(nextSeg.departureDatetime);
    if (!currentArr || !nextDep) continue;
    const arrDate = new Date(currentArr);
    const depDate = new Date(nextDep);
    if (isNaN(arrDate.getTime()) || isNaN(depDate.getTime())) continue;
    const layoverMins = (depDate.getTime() - arrDate.getTime()) / 60000;
    if (layoverMins <= 0) continue;

    const layoverHours = Math.floor(layoverMins / 60);
    const layoverMinsRem = Math.floor(layoverMins % 60);
    const layoverDuration = `${layoverHours}h ${layoverMinsRem}m`;

    const arrAirport = currentSeg.arrivalAirport;
    const arrCode = arrAirport?.iataCode ?? '';
    const arrCity = arrAirport?.cityName ?? arrCode;
    const arrAirportDisplay =
      arrCity && arrCode ? `${arrCity} (${arrCode})` : arrCode;

    const nextAirline =
      nextSeg.marketingAirline ?? nextSeg.operatingAirline;
    const nextAirlineCode = nextAirline?.iataCode ?? '';
    const nextAirlineName =
      nextAirline?.airlineName ?? nextAirlineCode;
    const nextFlightNumber =
      nextSeg.marketingFlightNumber?.formattedNumber ?? '';
    const nextLogoUrl = nextAirline ? getAirlineLogoUrl(nextAirline) : undefined;

    layovers.push({
      arrival_time: extractTimeFromISO(currentArr),
      arrival_date: currentArr ? new Date(currentArr).toLocaleDateString() : '',
      departure_time: extractTimeFromISO(nextDep),
      departure_date: nextDep ? new Date(nextDep).toLocaleDateString() : '',
      destination_code: arrCode,
      destination_city: arrCity,
      destination_airport: arrAirportDisplay,
      airline_code: nextAirlineCode,
      airline: nextAirlineName,
      airline_name: nextAirlineName,
      flight_number: nextFlightNumber || undefined,
      layover_duration: layoverDuration,
      ...(nextLogoUrl && { logo_url: nextLogoUrl }),
    });
  }
  return layovers;
}

/** Search-result cards do not show per-leg text labels (LEG n / OUTBOUND / RETURN). */
function stripLegLabelsForSearchCards(legs: ProcessedLeg[]): ProcessedLeg[] {
  return legs.map((l) => ({ ...l, legLabel: '' }));
}

/**
 * Build ProcessedLeg rows for search results.
 * Circle itineraries with a single API leg but multiple segments (supplier pattern B)
 * expand to one card row per segment so each city pair is visible.
 */
export function buildProcessedLegsForSearchItinerary(
  journeyType: string | undefined,
  flightLegs: FlightLegCamel[]
): ProcessedLeg[] {
  if (flightLegs.length === 0) return [];

  const jt = (journeyType ?? '').trim();
  if (jt === 'Circle' && flightLegs.length === 1) {
    const segs = flightLegs[0]?.flightSegments ?? [];
    if (segs.length > 1) {
      return stripLegLabelsForSearchCards(
        segs
          .map((seg) => processSegmentAsCircleLegRow(seg))
          .filter((l): l is ProcessedLeg => l !== null)
      );
    }
  }

  const isReturnPairing =
    flightLegs.length > 1 && jt === 'Return';
  return stripLegLabelsForSearchCards(
    flightLegs
      .map((leg, legIndex) => processLeg(leg, legIndex, isReturnPairing))
      .filter((l): l is ProcessedLeg => l !== null)
  );
}

/**
 * One segment shown as a single non-stop row (Circle / multi-city hop).
 */
function processSegmentAsCircleLegRow(segment: FlightSegmentCamel): ProcessedLeg | null {
  const syntheticLeg: FlightLegCamel = { flightSegments: [segment] };
  return processLeg(syntheticLeg, 0, false);
}

/**
 * Convert FlightCard flight shape to MappedFlight for use with FlightDetailsModal.
 * Builds layovers from leg.segments when available so layover details render
 * consistently regardless of whether the flight originated from a direct search
 * or was hydrated from a cached chat result.
 */
export function flightCardToMappedFlight(
  flight: FlightCardFlightInput
): MappedFlight {
  const legToSegmentData = (
    leg: FlightCardFlightInput['legs'][number] | ProcessedLeg
  ): SegmentData => {
    const segments = leg.segments as FlightSegmentCamel[] | undefined;
    const hasSegmentsForLayovers =
      leg.stops > 0 && segments && segments.length > 1;
    const layovers = hasSegmentsForLayovers
      ? buildLayoversFromFlightSegments(segments)
      : [];

    const duration =
      layovers.length > 0 && leg.totalTimeDisplay
        ? leg.totalTimeDisplay
        : leg.duration;
    const flight_duration =
      layovers.length > 0 ? leg.duration : undefined;

    return {
      duration,
      stops: leg.stops,
      ...(flight_duration && { flight_duration }),
      origin_code: leg.departure.airport,
      origin_city: leg.departure.city,
      origin_airport:
        leg.departure.city && leg.departure.airport
          ? `${leg.departure.city} (${leg.departure.airport})`
          : leg.departure.airport,
      destination_code: leg.arrival.airport,
      destination_city: leg.arrival.city,
      destination_airport:
        leg.arrival.city && leg.arrival.airport
          ? `${leg.arrival.city} (${leg.arrival.airport})`
          : leg.arrival.airport,
      departure_time: leg.departure.time,
      departure_date: leg.departure.date,
      arrival_time: leg.arrival.time,
      arrival_date: leg.arrival.date,
      layovers,
    };
  };

  const allSegmentsFlat = flight.legs.flatMap(
    (l) => (l.segments as FlightSegmentCamel[] | undefined) ?? []
  );

  let outbound: SegmentData;
  let returnLeg: SegmentData | undefined;

  if (flight.journeyType === 'Circle' && allSegmentsFlat.length > 0) {
    const merged = processLeg({ flightSegments: allSegmentsFlat }, 0, false);
    outbound = merged
      ? legToSegmentData(merged)
      : legToSegmentData(flight.legs[0]!);
    returnLeg = undefined;
  } else {
    outbound = legToSegmentData(flight.legs[0]!);
    returnLeg =
      flight.legs.length > 1 ? legToSegmentData(flight.legs[1]!) : undefined;
  }

  const isRoundTripMapped =
    flight.journeyType != null && flight.journeyType !== ''
      ? flight.journeyType === 'Return' && flight.legs.length > 1
      : flight.legs.length > 1;

  const firstAirline = flight.legs[0]?.airlinesInfo?.[0];
  const flightNumber =
    firstAirline?.flights?.[0] ?? flight.flightNumber;

  return {
    id: flight.id,
    price: flight.price,
    currency: 'USD',
    is_round_trip: isRoundTripMapped,
    outbound,
    return: returnLeg,
    airline_code: firstAirline?.code,
    airline: firstAirline?.name ?? flight.aircraftName,
    flight_number: flightNumber,
    original_total_fare: flight.original_total_fare,
    platform_fee_percentage: flight.platform_fee_percentage,
    ...(firstAirline?.logoUrl && { logo_url: firstAirline.logoUrl }),
  };
}

/** Fare totals shape from API (validatedFareTotals or fareTotals). */
interface FareTotalsLike {
  totalFare?: { amount?: string | number; currency?: string };
  platformFeePercentage?: number;
}

/** Extract total fare and currency from a flight revalidate API response. */
export function parseFareFromRevalidateResponse(
  response: {
    validatedFareItineraries?: Array<{
      updatedPricing?: { validatedFareTotals?: FareTotalsLike; fareTotals?: FareTotalsLike };
      pricing?: { validatedFareTotals?: FareTotalsLike; fareTotals?: FareTotalsLike };
    }>;
  } | null | undefined
): { amount: number; currency: string; platformFeePercentage?: number } {
  if (!response?.validatedFareItineraries?.[0]) {
    return { amount: 0, currency: DEFAULT_CURRENCY };
  }
  const itinerary = response.validatedFareItineraries[0];
  const pricing = itinerary?.updatedPricing ?? itinerary?.pricing;
  const fareTotals: FareTotalsLike | undefined =
    pricing?.validatedFareTotals ?? pricing?.fareTotals;
  const totalFareObj = fareTotals?.totalFare;
  const amount =
    totalFareObj?.amount != null ? Number(totalFareObj.amount) : 0;
  const currency = (totalFareObj?.currency ?? DEFAULT_CURRENCY).toUpperCase();
  const platformFeePercentage = fareTotals?.platformFeePercentage;
  return {
    amount: Number.isFinite(amount) ? amount : 0,
    currency,
    platformFeePercentage,
  };
}

/**
 * Currency amount helpers (convention: booking/payment amounts are in cents – see types/flights.ts)
 */

/**
 * Format amount in cents as locale-aware currency (same pattern as RevolutPaymentForm).
 * Supports USD, EUR, GBP, etc. without hardcoded symbols.
 */
export function formatCurrencyFromCents(
  cents: number | undefined | null,
  currency: string
): string {
  const code = (currency || 'USD').toUpperCase();
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: code,
  }).format((cents ?? 0) / 100);
}

/**
 * Format amount in major units as locale-aware currency (e.g. fare totals from API).
 */
export function formatCurrency(
  amount: number | undefined | null,
  currency: string
): string {
  const code = (currency || 'USD').toUpperCase();
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: code,
  }).format(amount ?? 0);
}

/**
 * Trip Type Utilities
 */

/**
 * Format flight dates for chip display (depart only or depart–return)
 */
export function formatFlightDates(
  date: Date | null,
  returnDate: Date | null,
  tripType: TripType | null
): string {
  if (!date) return 'Select dates';
  const fmt = (d: Date) =>
    d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  if (tripType === 'round-trip' && returnDate) {
    return date.getMonth() === returnDate.getMonth()
      ? `${fmt(date)}–${returnDate.getDate()}`
      : `${fmt(date)}–${fmt(returnDate)}`;
  }
  return fmt(date);
}

/** ISO date strings per leg (from Redux `segments`) for the flights header chip */
export function formatMulticityChipDatesFromIso(
  segmentDates: Array<string | null | undefined> | undefined
): string {
  if (!segmentDates?.length) return 'Select dates';
  const parsed = segmentDates
    .map((d) => (d ? new Date(d) : null))
    .filter((d): d is Date => d !== null && !Number.isNaN(d.getTime()));
  if (parsed.length === 0) return 'Select dates';
  const fmt = (d: Date) =>
    d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  if (parsed.length === 1) return fmt(parsed[0]!);
  const first = parsed[0]!;
  const last = parsed[parsed.length - 1]!;
  return `${fmt(first)} → ${fmt(last)} · ${parsed.length} legs`;
}

/**
 * Get human-readable label for trip type
 */
export function getTripTypeLabel(type: TripType | null): string {
  switch (type) {
    case 'one-way':
      return 'One way';
    case 'round-trip':
      return 'Round trip';
    case 'multi-city':
      return 'Multi city';
    default:
      return 'Trip type';
  }
}

/**
 * Process a single flight leg into display-ready data.
 * Expects camelCase leg (from API transformResponse).
 */
export function processLeg(
  leg: FlightLegCamel,
  legIndex: number,
  isRoundTrip: boolean
): ProcessedLeg | null {
  const segments = leg?.flightSegments ?? [];
  if (segments.length === 0) return null;

  const firstSegment = segments[0];
  const lastSegment = segments[segments.length - 1];
  if (!firstSegment || !lastSegment) return null;

  const depDateTime = normalizeDateTime(firstSegment.departureDatetime);
  const arrDateTime = normalizeDateTime(lastSegment.arrivalDatetime);

  let legMinutes = 0;
  segments.forEach((seg: FlightSegmentCamel) => {
    const fd = seg.flightDuration;
    legMinutes += fd?.totalMinutes ?? 0;
  });
  const hours = Math.floor(legMinutes / 60);
  const mins = legMinutes % 60;
  const duration = `${hours}h ${mins}m`;

  let totalLayoverMinutes = 0;
  for (let i = 0; i < segments.length - 1; i++) {
    const segCur = segments[i];
    const segNext = segments[i + 1];
    if (!segCur || !segNext) continue;
    const currentArr = normalizeDateTime(segCur.arrivalDatetime);
    const nextDep = normalizeDateTime(segNext.departureDatetime);
    if (currentArr && nextDep) {
      try {
        const arr = new Date(currentArr);
        const dep = new Date(nextDep);
        if (!isNaN(arr.getTime()) && !isNaN(dep.getTime())) {
          totalLayoverMinutes += (dep.getTime() - arr.getTime()) / 60000;
        }
      } catch {
        // Skip invalid dates
      }
    }
  }

  const totalTimeMinutes = legMinutes + totalLayoverMinutes;
  const totalHours = Math.floor(totalTimeMinutes / 60);
  const totalMins = Math.floor(totalTimeMinutes % 60);
  const totalTimeDisplay =
    totalLayoverMinutes > 0 ? `${totalHours}h ${totalMins}m` : null;

  const stops = segments.length - 1;
  const stopsText =
    stops === 0 ? 'Non-stop' : `${stops} stop${stops > 1 ? 's' : ''}`;

  const depAirport = firstSegment.departureAirport?.iataCode ?? 'N/A';
  const arrAirport = lastSegment.arrivalAirport?.iataCode ?? 'N/A';
  const depCity =
    firstSegment.departureAirport?.cityName ?? depAirport;
  const arrCity =
    lastSegment.arrivalAirport?.cityName ?? arrAirport;

  const airlinesMap = new Map<
    string,
    { name: string; code: string; flights: string[]; logoUrl?: string }
  >();
  segments.forEach((seg: FlightSegmentCamel) => {
    const airlineCode =
      seg.marketingAirline?.iataCode ?? seg.operatingAirline?.iataCode ?? '';
    const airlineName =
      seg.marketingAirline?.airlineName ??
      seg.operatingAirline?.airlineName ??
      (airlineCode || 'Unknown');
    const flightNumber = seg.marketingFlightNumber?.formattedNumber ?? '';
    const logoUrl =
      getAirlineLogoUrl(seg.marketingAirline) ??
      getAirlineLogoUrl(seg.operatingAirline);

    if (airlineCode) {
      if (!airlinesMap.has(airlineCode)) {
        airlinesMap.set(airlineCode, {
          name: airlineName || airlineCode,
          code: airlineCode,
          flights: [],
          logoUrl,
        });
      }
      const entry = airlinesMap.get(airlineCode)!;
      if (flightNumber) {
        entry.flights.push(flightNumber);
      }
      if (logoUrl && !entry.logoUrl) {
        entry.logoUrl = logoUrl;
      }
    }
  });
  const airlinesInfo = Array.from(airlinesMap.values());

  let legLabel = '';
  if (isRoundTrip) {
    legLabel = legIndex === 0 ? 'OUTBOUND' : 'RETURN';
  } else if (legIndex > 0) {
    legLabel = `LEG ${legIndex + 1}`;
  }

  return {
    legLabel,
    departure: {
      city: depCity,
      airport: depAirport,
      time: extractTimeFromISO(depDateTime),
      date: depDateTime ? new Date(depDateTime).toLocaleDateString() : '',
    },
    arrival: {
      city: arrCity,
      airport: arrAirport,
      time: extractTimeFromISO(arrDateTime),
      date: arrDateTime ? new Date(arrDateTime).toLocaleDateString() : '',
    },
    duration,
    totalTimeDisplay,
    hasLayover: totalLayoverMinutes > 0,
    stops,
    stopsText,
    segments,
    airlinesInfo,
  };
}

/** IATA normalization for trip-details segment graphs (matches backend route_snapshot). */
function normTripDetailsIata(code: string | undefined | null): string | null {
  if (code == null || !String(code).trim()) return null;
  const s = String(code).trim().toUpperCase();
  return s.length === 3 ? s : null;
}

function tripDetailsSegDepArr(seg: {
  departureAirport?: { iataCode?: string };
  arrivalAirport?: { iataCode?: string };
}): [string | null, string | null] {
  return [
    normTripDetailsIata(seg.departureAirport?.iataCode),
    normTripDetailsIata(seg.arrivalAirport?.iataCode),
  ];
}

function tripDetailsRtPartitionValid(
  a: Array<{
    departureAirport?: { iataCode?: string };
    arrivalAirport?: { iataCode?: string };
  }>,
  b: Array<{
    departureAirport?: { iataCode?: string };
    arrivalAirport?: { iataCode?: string };
  }>,
  orig: string,
): boolean {
  if (!a.length || !b.length) return false;
  for (let i = 0; i < a.length - 1; i++) {
    const ar = tripDetailsSegDepArr(a[i]!)[1];
    const d2 = tripDetailsSegDepArr(a[i + 1]!)[0];
    if (!ar || !d2 || ar !== d2) return false;
  }
  const hub = tripDetailsSegDepArr(a[a.length - 1]!)[1];
  const dRet = tripDetailsSegDepArr(b[0]!)[0];
  if (!hub || !dRet || hub !== dRet) return false;
  for (let i = 0; i < b.length - 1; i++) {
    const ar = tripDetailsSegDepArr(b[i]!)[1];
    const d2 = tripDetailsSegDepArr(b[i + 1]!)[0];
    if (!ar || !d2 || ar !== d2) return false;
  }
  const bLastArr = tripDetailsSegDepArr(b[b.length - 1]!)[1];
  return bLastArr === orig;
}

/**
 * Split index after the first half of segments when length is even and the two halves form a
 * valid round trip (matches backend `_find_round_trip_split_equal_halves`).
 */
export function findRoundTripSegmentSplitIndex(
  segments: Array<{
    departureAirport?: { iataCode?: string };
    arrivalAirport?: { iataCode?: string };
  }>,
): number | null {
  const n = segments.length;
  if (n < 2 || n % 2 !== 0) return null;
  const orig = tripDetailsSegDepArr(segments[0]!)[0];
  const lastArr = tripDetailsSegDepArr(segments[n - 1]!)[1];
  if (!orig || !lastArr || lastArr !== orig) return null;
  const mid = n / 2;
  const a = segments.slice(0, mid);
  const b = segments.slice(mid);
  return tripDetailsRtPartitionValid(a, b, orig) ? mid : null;
}

/**
 * Per-segment OUTBOUND / RETURN labels for trip-details style flat segment lists.
 * Returns null when the itinerary is not a recognizable round trip (caller avoids misleading labels).
 */
export function tripDetailsSegmentOutboundReturnLabels(
  segments: Array<{
    departureAirport?: { iataCode?: string };
    arrivalAirport?: { iataCode?: string };
  }>,
): ('OUTBOUND' | 'RETURN')[] | null {
  if (segments.length <= 1) return null;
  const split = findRoundTripSegmentSplitIndex(segments);
  if (split === null) return null;
  return segments.map((_, idx) => (idx < split ? 'OUTBOUND' : 'RETURN'));
}

/**
 * One label per vendor `flightLeg` for confirmation-style UIs when multiple API legs exist
 * per direction (e.g. one leg per segment on a connecting round trip).
 *
 * When a vendor leg spans the outbound/return segment boundary (split falls strictly inside
 * that leg’s segments), the label is **null** — a single OUTBOUND/RETURN tag would be misleading.
 */
export function roundTripBoundLabelPerVendorLeg(
  flightLegs: Array<{
    flightSegments?: Array<{
      departureAirport?: { iataCode?: string };
      arrivalAirport?: { iataCode?: string };
    }>;
  }>,
): ('OUTBOUND' | 'RETURN' | null)[] {
  if (flightLegs.length === 0) return [];
  const flat = flightLegs.flatMap((lg) => lg.flightSegments ?? []);
  const split = findRoundTripSegmentSplitIndex(flat);
  if (split === null) {
    return flightLegs.map(() => null);
  }
  const labels: ('OUTBOUND' | 'RETURN' | null)[] = [];
  let offset = 0;
  for (const lg of flightLegs) {
    const n = (lg.flightSegments ?? []).length;
    const start = offset;
    const end = offset + n;
    if (end <= split) {
      labels.push('OUTBOUND');
    } else if (start >= split) {
      labels.push('RETURN');
    } else {
      labels.push(null);
    }
    offset = end;
  }
  return labels;
}
