/**
 * Flight data transformation utilities
 */

import type { FlightSegment, MappedFlight, SegmentData } from '@/types/flight';

/**
 * Calculates the time difference between an arrival and a departure time,
 * handling cases that cross midnight, and formats the result as "Xh Ym".
 *
 * @param arriveTime - The arrival time string (e.g., "14:00")
 * @param departTime - The departure time string (e.g., "20:00")
 * @returns The formatted time difference (e.g., "6h 0m" or "3h")
 */
export function formatTimeDifference(
  arriveTime: string | undefined,
  departTime: string | undefined
): string {
  if (!arriveTime || !departTime) return 'N/A';

  const parseTime = (timeStr: string): number => {
    const parts = timeStr.split(':').map(Number);
    const hours = parts[0] ?? 0;
    const minutes = parts[1] ?? 0;
    return hours * 60 + minutes;
  };

  const arriveMinutes = parseTime(arriveTime);
  const departMinutes = parseTime(departTime);

  let diffMinutes: number;

  if (departMinutes < arriveMinutes) {
    diffMinutes = departMinutes + 24 * 60 - arriveMinutes;
  } else {
    diffMinutes = departMinutes - arriveMinutes;
  }

  const hours = Math.floor(diffMinutes / 60);
  const minutes = diffMinutes % 60;

  return minutes === 0 ? `${hours}h` : `${hours}h ${minutes}m`;
}

/**
 * Adds two durations in the format "Xh Ym"
 * @param d1 - First duration (e.g., "23h 21m")
 * @param d2 - Second duration (e.g., "2h 45m")
 * @returns The summed duration
 */
export function addDurations(d1: string, d2: string): string {
  const parseToMinutes = (str: string | undefined): number => {
    if (!str || typeof str !== 'string') return 0;
    const hoursMatch = str.match(/(\d+)[hu]/i);
    const minutesMatch = str.match(/(\d+)m/i);
    const hours = parseInt(hoursMatch?.[1] || '0');
    const minutes = parseInt(minutesMatch?.[1] || '0');
    return hours * 60 + minutes;
  };

  const formatDuration = (totalMinutes: number): string => {
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    return `${h}h ${m}m`;
  };

  const total = parseToMinutes(d1) + parseToMinutes(d2);
  return formatDuration(total);
}

/**
 * Separates flight segments into outbound and inbound legs
 */
function separateFlightSegments(
  segments: FlightSegment[],
  finalDestinationCode: string
): { outbound: FlightSegment[]; inbound: FlightSegment[] } {
  const turningPointIndex = segments.findIndex(
    (segment) => segment.destination_code === finalDestinationCode
  );

  if (turningPointIndex === -1) {
    return {
      outbound: segments,
      inbound: [],
    };
  }

  const outbound = segments.slice(0, turningPointIndex + 1);
  const inbound = segments.slice(turningPointIndex + 1);

  return {
    outbound,
    inbound,
  };
}

/** Parse segment datetime for layover calculation (matches frontend utils) */
function parseSegmentDatetime(
  dt: FlightSegment['arrival_datetime'] | FlightSegment['departure_datetime']
): string | null {
  if (!dt) return null;
  const value = typeof dt === 'object' && dt !== null && 'value' in dt ? (dt as { value?: string }).value : dt;
  return typeof value === 'string' ? value : null;
}

/**
 * Calculate segment stats (duration, stops, layovers).
 * Matches frontend FlightResultMessage/utils.js: flight duration sum, total time with layovers,
 * and explicit layover objects with layover_duration.
 */
function calculateSegment(segments: FlightSegment[]): SegmentData {
  if (!segments || segments.length === 0) {
    return { duration: '0h 0m', flight_duration: '0h 0m', stops: 0, layovers: [] };
  }

  const lastLeg = segments[segments.length - 1]!;
  const firstLeg = segments[0]!;

  // Flight duration = sum of all segment flight times (matches frontend)
  const flightDurationStr = segments.reduce(
    (acc, segment) => addDurations(acc, segment.duration || '0h 0m'),
    '0h 0m'
  );

  const layovers: FlightSegment[] = [];
  let totalLayoverMinutes = 0;

  for (let i = 0; i < segments.length - 1; i++) {
    const currentSeg = segments[i]!;
    const nextSeg = segments[i + 1]!;

    const currentArrValue =
      parseSegmentDatetime(currentSeg.arrival_datetime) ??
      (currentSeg.arrival_date && currentSeg.arrival_time
        ? `${currentSeg.arrival_date}T${currentSeg.arrival_time}:00`
        : null);
    const nextDepValue =
      parseSegmentDatetime(nextSeg.departure_datetime) ??
      (nextSeg.departure_date && nextSeg.departure_time
        ? `${nextSeg.departure_date}T${nextSeg.departure_time}:00`
        : null);

    if (currentArrValue && nextDepValue) {
      const currentArr = new Date(currentArrValue);
      const nextDep = new Date(nextDepValue);
      if (
        !isNaN(currentArr.getTime()) &&
        !isNaN(nextDep.getTime())
      ) {
        const layoverMins = (nextDep.getTime() - currentArr.getTime()) / 60000;
        if (layoverMins > 0) {
          totalLayoverMinutes += layoverMins;
          const layoverHours = Math.floor(layoverMins / 60);
          const layoverMinsRem = Math.floor(layoverMins % 60);
          const layoverDuration = `${layoverHours}h ${layoverMinsRem}m`;

          const nextFlightNumber =
            nextSeg.flight_number ||
            (nextSeg.flight_number_info?.formatted_number ?? '') ||
            (nextSeg.flight_number_info?.number
              ? `${nextSeg.flight_number_info?.airline_prefix ?? ''}${nextSeg.flight_number_info.number}`
              : '');

          layovers.push({
            arrival_time: currentSeg.arrival_time,
            arrival_date: currentSeg.arrival_date,
            departure_time: nextSeg.departure_time,
            departure_date: nextSeg.departure_date,
            destination_code: currentSeg.destination_code,
            destination_city: currentSeg.destination_city,
            destination_airport: currentSeg.destination_airport,
            airline_code: nextSeg.airline_code,
            airline: nextSeg.airline ?? nextSeg.airline_name,
            airline_name: nextSeg.airline_name ?? nextSeg.airline,
            flight_number: nextFlightNumber || undefined,
            layover_duration: layoverDuration,
          });
        }
      }
    }
  }

  const parseToMinutes = (str: string | undefined): number => {
    if (!str || typeof str !== 'string') return 0;
    const hoursMatch = str.match(/(\d+)[hu]/i);
    const minutesMatch = str.match(/(\d+)m/i);
    const h = parseInt(hoursMatch?.[1] || '0');
    const m = parseInt(minutesMatch?.[1] || '0');
    return h * 60 + m;
  };
  const formatDuration = (totalMinutes: number): string => {
    const h = Math.floor(totalMinutes / 60);
    const m = Math.floor(totalMinutes % 60);
    return `${h}h ${m}m`;
  };
  const flightMinutes = parseToMinutes(flightDurationStr);
  const totalTimeMinutes = flightMinutes + totalLayoverMinutes;
  const totalTimeDisplay = formatDuration(totalTimeMinutes);

  return {
    duration: totalTimeDisplay,
    flight_duration: flightDurationStr,
    stops: segments.length - 1,
    departure_date: firstLeg.departure_date,
    departure_time: firstLeg.departure_time,
    destination_airport: lastLeg.destination_airport,
    destination_city: lastLeg.destination_city,
    destination_code: lastLeg.destination_code,
    origin_airport: firstLeg.origin_airport || firstLeg.departure_airport,
    origin_city: firstLeg.origin_city || firstLeg.departure_city,
    origin_code: firstLeg.origin_code || firstLeg.departure_code,
    arrival_date: lastLeg.arrival_date,
    arrival_time: lastLeg.arrival_time,
    layovers,
  };
}

/**
 * Maps raw flight data to a structured format with outbound/return segments
 */
export function flightMapper(
  flight: Record<string, unknown> | undefined,
  finalDestinationCode: string,
  journeyType: string | null = null
): MappedFlight {
  if (!flight) {
    return {
      price: undefined,
      currency: undefined,
      outbound: { duration: '0h 0m', stops: 0, layovers: [] },
      is_round_trip: false,
    } as MappedFlight;
  }

  const segments = flight.segments as FlightSegment[] | undefined;
  const originCode = flight.origin_code as string | undefined;
  const destinationCode = flight.destination_code as string | undefined;

  // Use flight.destination_code (outbound destination IATA from backend) for splitting.
  // search_params.destination can be a city name (e.g. "Paris") when user searched by city,
  // but segments always have destination_code as airport IATA (e.g. "CDG"). Using the flight's
  // destination_code ensures we split outbound/inbound correctly and the return leg shows valid data.
  const splitDestinationCode = destinationCode || finalDestinationCode;

  // Check if it's a round trip
  let isRoundTrip = false;

  // First check journey_type from search params (most reliable indicator)
  if (journeyType && (journeyType === 'Return' || journeyType === 'RoundTrip')) {
    isRoundTrip = true;
  } else if (originCode === destinationCode) {
    // Direct check: flight returns to origin
    isRoundTrip = true;
  } else if (segments && segments.length > 0) {
    const firstSegment = segments[0]!;
    const lastSegment = segments[segments.length - 1]!;
    const firstOrigin = firstSegment.origin_code || firstSegment.departure_code;
    const lastDestination = lastSegment.destination_code;

    // Check if last segment returns to origin (round trip indicator)
    if (firstOrigin && lastDestination && firstOrigin === lastDestination) {
      isRoundTrip = true;
    } else {
      // Check if there are segments beyond the final destination (inbound segments)
      const { inbound } = separateFlightSegments(segments, splitDestinationCode);
      if (inbound && inbound.length > 0) {
        isRoundTrip = true;
      }
    }
  }

  const newFlight: MappedFlight = {
    ...(flight as unknown as MappedFlight),
    is_round_trip: isRoundTrip,
    outbound: { duration: '0h 0m', stops: 0, layovers: [] },
  };

  if (isRoundTrip && segments) {
    const { outbound, inbound } = separateFlightSegments(segments, splitDestinationCode);
    newFlight.outbound = calculateSegment(outbound);
    newFlight.return = calculateSegment(inbound);
  } else if (segments) {
    newFlight.outbound = calculateSegment(segments);
  }

  return newFlight;
}

/**
 * Total journey duration for display on flight cards.
 * One-way: outbound duration. Round-trip: outbound + return.
 */
export function getTotalJourneyDuration(flight: MappedFlight): string {
  const out = flight.outbound?.duration || '0h 0m';
  if (!flight.is_round_trip || !flight.return?.duration) return out;
  return addDurations(out, flight.return.duration);
}

/**
 * Extract display flight number from a segment (backend may send flight_number_info or flight_number).
 */
export function getSegmentFlightNumber(seg: FlightSegment): string {
  const info = seg.flight_number_info;
  if (info?.formatted_number) return info.formatted_number;
  if (seg.flight_number) return seg.flight_number;
  if (info?.number) return `${info.airline_prefix ?? ''}${info.number}`;
  return '';
}

/**
 * Get label for number of stops
 */
export function getStopsLabel(stops: number): string {
  if (stops === 0) return 'Direct';
  if (stops === 1) return '1 Stop';
  return `${stops} Stops`;
}
