/**
 * Flight filter state and application logic.
 * Replicates dev_ui flight-booker filter behavior with a typed, modular approach.
 */

/** Time string "HH:MM" */
type TimeString = string;

export interface FlightFilterState {
  priceMin: number | null;
  priceMax: number | null;
  directOnly: boolean;
  stops1: boolean;
  stops2Plus: boolean;
  returnDirectOnly: boolean;
  returnStops1: boolean;
  returnStops2Plus: boolean;
  airlines: string[];
  cabinClasses: string[];
  departureAirports: string[];
  arrivalAirports: string[];
  returnDepartureAirports: string[];
  returnArrivalAirports: string[];
  outboundDurationMin: number | null;
  outboundDurationMax: number | null;
  inboundDurationMin: number | null;
  inboundDurationMax: number | null;
  departureTimeMin: TimeString | null;
  departureTimeMax: TimeString | null;
  arrivalTimeMin: TimeString | null;
  arrivalTimeMax: TimeString | null;
  returnDepartureTimeMin: TimeString | null;
  returnDepartureTimeMax: TimeString | null;
  returnArrivalTimeMin: TimeString | null;
  returnArrivalTimeMax: TimeString | null;
}

export const defaultFlightFilterState: FlightFilterState = {
  priceMin: null,
  priceMax: null,
  directOnly: false,
  stops1: false,
  stops2Plus: false,
  returnDirectOnly: false,
  returnStops1: false,
  returnStops2Plus: false,
  airlines: [],
  cabinClasses: [],
  departureAirports: [],
  arrivalAirports: [],
  returnDepartureAirports: [],
  returnArrivalAirports: [],
  outboundDurationMin: null,
  outboundDurationMax: null,
  inboundDurationMin: null,
  inboundDurationMax: null,
  departureTimeMin: null,
  departureTimeMax: null,
  arrivalTimeMin: null,
  arrivalTimeMax: null,
  returnDepartureTimeMin: null,
  returnDepartureTimeMax: null,
  returnArrivalTimeMin: null,
  returnArrivalTimeMax: null,
};

/** UI flight item shape (from FlightSearchPage flights array) */
export interface FilterableFlight {
  id: string;
  price: number;
  legs: Array<{
    stops: number;
    departure: { time: string };
    arrival: { time: string };
    duration?: string;
    totalTimeDisplay?: string | null;
    airlinesInfo?: Array<{ code: string; name: string }>;
    segments?: unknown[];
  }>;
  _originalItinerary?: import('@/types/flightBackend').FareItineraryCamel;
}

function timeToMinutes(timeStr: TimeString | null): number | null {
  if (!timeStr) return null;
  const parts = timeStr.split(':').map(Number);
  if (parts.length < 2) return null;
  const h = parts[0];
  const m = parts[1];
  return (h != null && m != null ? h * 60 + m : null);
}

/** Parse "Xh Ym" or "Xh" to hours (decimal). */
function parseDurationToHours(text: string | null | undefined): number | null {
  if (!text || typeof text !== 'string') return null;
  const hMatch = text.match(/(\d+)\s*h/);
  const mMatch = text.match(/(\d+)\s*m/);
  const hours = hMatch && hMatch[1] != null ? parseInt(hMatch[1], 10) : 0;
  const minutes = mMatch && mMatch[1] != null ? parseInt(mMatch[1], 10) : 0;
  return hours + minutes / 60;
}

function matchesStopsFilter(stops: number, direct: boolean, one: boolean, twoPlus: boolean): boolean {
  if (!direct && !one && !twoPlus) return true;
  if (direct && stops === 0) return true;
  if (one && stops === 1) return true;
  if (twoPlus && stops >= 2) return true;
  return false;
}

function matchesAirlineFilter(flight: FilterableFlight, selectedCodes: string[]): boolean {
  if (selectedCodes.length === 0) return true;
  for (const leg of flight.legs || []) {
    for (const info of leg.airlinesInfo || []) {
      if (info.code && selectedCodes.includes(info.code)) return true;
    }
  }
  return false;
}

function matchesCabinFilter(flight: FilterableFlight, selectedCabins: string[]): boolean {
  if (selectedCabins.length === 0) return true;
  const itinerary = flight._originalItinerary;
  if (!itinerary?.flightLegs) return false;
  for (const leg of itinerary.flightLegs) {
    for (const seg of leg.flightSegments || []) {
      if (seg.cabinClass && selectedCabins.includes(seg.cabinClass)) return true;
    }
  }
  return false;
}

function getLegAirport(
  flight: FilterableFlight,
  legIndex: number,
  position: 'departure' | 'arrival'
): string | null {
  const segments = flight._originalItinerary?.flightLegs?.[legIndex]?.flightSegments ?? [];
  const seg = position === 'departure' ? segments[0] : segments[segments.length - 1];
  return (position === 'departure' ? seg?.departureAirport?.iataCode : seg?.arrivalAirport?.iataCode) ?? null;
}

/**
 * Filter flights by the given filter state.
 * Uses the same logic as backend_python dev_ui flight-booker.
 * Preserves the input element type (generic) so display fields are retained.
 */
export function filterFlights<T extends FilterableFlight>(
  flights: T[],
  state: FlightFilterState
): T[] {
  return flights.filter((flight) => {
    if (state.priceMin !== null && flight.price < state.priceMin) return false;
    if (state.priceMax !== null && flight.price > state.priceMax) return false;

    const outboundStops = flight.legs[0]?.stops ?? 0;
    if (
      state.directOnly ||
      state.stops1 ||
      state.stops2Plus
    ) {
      if (!matchesStopsFilter(outboundStops, state.directOnly, state.stops1, state.stops2Plus)) {
        return false;
      }
    }

    const isRoundTrip = (flight.legs?.length ?? 0) > 1;
    if (
      isRoundTrip &&
      (state.returnDirectOnly || state.returnStops1 || state.returnStops2Plus)
    ) {
      const returnStops = flight.legs[1]?.stops ?? 0;
      if (
        !matchesStopsFilter(
          returnStops,
          state.returnDirectOnly,
          state.returnStops1,
          state.returnStops2Plus
        )
      ) {
        return false;
      }
    }

    if (!matchesAirlineFilter(flight, state.airlines)) return false;
    if (!matchesCabinFilter(flight, state.cabinClasses)) return false;

    if (state.departureAirports.length > 0) {
      const depCode = getLegAirport(flight, 0, 'departure');
      if (!depCode || !state.departureAirports.includes(depCode)) return false;
    }
    if (state.arrivalAirports.length > 0) {
      const arrCode = getLegAirport(flight, 0, 'arrival');
      if (!arrCode || !state.arrivalAirports.includes(arrCode)) return false;
    }

    const isRoundTripFilter = (flight.legs?.length ?? 0) > 1;
    if (isRoundTripFilter && state.returnDepartureAirports.length > 0) {
      const retDepCode = getLegAirport(flight, 1, 'departure');
      if (!retDepCode || !state.returnDepartureAirports.includes(retDepCode)) return false;
    }
    if (isRoundTripFilter && state.returnArrivalAirports.length > 0) {
      const retArrCode = getLegAirport(flight, 1, 'arrival');
      if (!retArrCode || !state.returnArrivalAirports.includes(retArrCode)) return false;
    }

    const outboundDurationHours = parseDurationToHours(
      flight.legs[0]?.totalTimeDisplay ?? flight.legs[0]?.duration
    );
    if (
      state.outboundDurationMin !== null ||
      state.outboundDurationMax !== null
    ) {
      if (outboundDurationHours === null) return false;
      if (
        state.outboundDurationMin !== null &&
        outboundDurationHours < state.outboundDurationMin
      )
        return false;
      if (
        state.outboundDurationMax !== null &&
        outboundDurationHours > state.outboundDurationMax
      )
        return false;
    }

    const inboundDurationHours =
      flight.legs[1] != null
        ? parseDurationToHours(flight.legs[1].totalTimeDisplay ?? flight.legs[1].duration)
        : null;
    if (
      state.inboundDurationMin !== null ||
      state.inboundDurationMax !== null
    ) {
      if (inboundDurationHours === null) return true;
      if (
        state.inboundDurationMin !== null &&
        inboundDurationHours < state.inboundDurationMin
      )
        return false;
      if (
        state.inboundDurationMax !== null &&
        inboundDurationHours > state.inboundDurationMax
      )
        return false;
    }

    const depTime = flight.legs[0]?.departure?.time;
    if (state.departureTimeMin != null || state.departureTimeMax != null) {
      if (depTime) {
        const depMinutes = timeToMinutes(depTime);
        if (depMinutes !== null) {
          const minM = timeToMinutes(state.departureTimeMin);
          const maxM = timeToMinutes(state.departureTimeMax);
          if (minM !== null && depMinutes < minM) return false;
          if (maxM !== null && depMinutes > maxM) return false;
        }
      }
    }

    const arrTime = flight.legs[0]?.arrival?.time;
    if (state.arrivalTimeMin != null || state.arrivalTimeMax != null) {
      if (arrTime) {
        const arrMinutes = timeToMinutes(arrTime);
        if (arrMinutes !== null) {
          const minM = timeToMinutes(state.arrivalTimeMin);
          const maxM = timeToMinutes(state.arrivalTimeMax);
          if (minM !== null && arrMinutes < minM) return false;
          if (maxM !== null && arrMinutes > maxM) return false;
        }
      }
    }

    const returnLeg = flight.legs[1];
    if (returnLeg != null) {
      const returnDepTime = returnLeg.departure?.time;
      if (
        state.returnDepartureTimeMin != null ||
        state.returnDepartureTimeMax != null
      ) {
        if (returnDepTime) {
          const depMinutes = timeToMinutes(returnDepTime);
          if (depMinutes !== null) {
            const minM = timeToMinutes(state.returnDepartureTimeMin);
            const maxM = timeToMinutes(state.returnDepartureTimeMax);
            if (minM !== null && depMinutes < minM) return false;
            if (maxM !== null && depMinutes > maxM) return false;
          }
        }
      }
      const returnArrTime = returnLeg.arrival?.time;
      if (
        state.returnArrivalTimeMin != null ||
        state.returnArrivalTimeMax != null
      ) {
        if (returnArrTime) {
          const arrMinutes = timeToMinutes(returnArrTime);
          if (arrMinutes !== null) {
            const minM = timeToMinutes(state.returnArrivalTimeMin);
            const maxM = timeToMinutes(state.returnArrivalTimeMax);
            if (minM !== null && arrMinutes < minM) return false;
            if (maxM !== null && arrMinutes > maxM) return false;
          }
        }
      }
    }

    return true;
  });
}

/** Minutes since midnight to "HH:MM" */
export function minutesToTime(minutes: number): string {
  const h = Math.floor(minutes / 60) % 24;
  const m = minutes % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/** Extract unique airlines from flights for filter options */
export function extractAirlinesFromFlights(
  flights: FilterableFlight[]
): Array<{ code: string; name: string }> {
  const map = new Map<string, string>();
  for (const flight of flights) {
    for (const leg of flight.legs || []) {
      for (const info of leg.airlinesInfo || []) {
        if (info.code && info.name && !map.has(info.code)) {
          map.set(info.code, info.name);
        }
      }
    }
  }
  return Array.from(map.entries())
    .map(([code, name]) => ({ code, name }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** Extract unique cabin classes from flights (uses _originalItinerary) */
export function extractCabinClassesFromFlights(
  flights: FilterableFlight[]
): string[] {
  const set = new Set<string>();
  for (const flight of flights) {
    const it = flight._originalItinerary;
    for (const leg of it?.flightLegs ?? []) {
      for (const seg of leg.flightSegments ?? []) {
        if (seg.cabinClass) set.add(seg.cabinClass);
      }
    }
  }
  return Array.from(set).sort();
}

/** Airport option for filter UI (code + display name). */
export interface AirportFilterOption {
  code: string;
  name: string;
}

function extractAirportsHelper(
  flights: FilterableFlight[],
  legIndex: number,
  position: 'departure' | 'arrival'
): AirportFilterOption[] {
  const map = new Map<string, string>();
  for (const flight of flights) {
    const segments = flight._originalItinerary?.flightLegs?.[legIndex]?.flightSegments ?? [];
    const seg = position === 'departure' ? segments[0] : segments[segments.length - 1];
    const airport = position === 'departure' ? seg?.departureAirport : seg?.arrivalAirport;
    const code = airport?.iataCode;
    if (code && !map.has(code)) map.set(code, airport?.cityName ?? code);
  }
  return Array.from(map.entries())
    .map(([code, name]) => ({ code, name }))
    .sort((a, b) => a.code.localeCompare(b.code));
}

/** Extract unique departure airports from first leg (outbound). */
export function extractDepartureAirportsFromFlights(flights: FilterableFlight[]): AirportFilterOption[] {
  return extractAirportsHelper(flights, 0, 'departure');
}

/** Extract unique arrival airports from first leg (outbound). */
export function extractArrivalAirportsFromFlights(flights: FilterableFlight[]): AirportFilterOption[] {
  return extractAirportsHelper(flights, 0, 'arrival');
}

/** Extract unique departure airports from second leg (inbound/return). */
export function extractReturnDepartureAirportsFromFlights(flights: FilterableFlight[]): AirportFilterOption[] {
  return extractAirportsHelper(flights, 1, 'departure');
}

/** Extract unique arrival airports from second leg (inbound/return). */
export function extractReturnArrivalAirportsFromFlights(flights: FilterableFlight[]): AirportFilterOption[] {
  return extractAirportsHelper(flights, 1, 'arrival');
}

/**
 * Count the number of filter categories with active (non-default) values.
 *
 * Each accordion section counts as at most 1, regardless of how many individual
 * sub-filters within it are set. For example, selecting both outbound and return
 * departure airports increments the count by 1 (not 2), because they share the
 * same "Departure airports" accordion section. This keeps the badge count aligned
 * with the number of visible sections that have any active state.
 */
export function countActiveFilters(state: FlightFilterState): number {
  let count = 0;
  if (state.priceMin !== null || state.priceMax !== null) count++;
  if (
    state.directOnly ||
    state.stops1 ||
    state.stops2Plus ||
    state.returnDirectOnly ||
    state.returnStops1 ||
    state.returnStops2Plus
  )
    count++;
  if (state.airlines.length > 0) count++;
  if (state.cabinClasses.length > 0) count++;
  if (state.departureAirports.length > 0 || state.returnDepartureAirports.length > 0) count++;
  if (state.arrivalAirports.length > 0 || state.returnArrivalAirports.length > 0) count++;
  if (
    state.outboundDurationMin !== null ||
    state.outboundDurationMax !== null ||
    state.inboundDurationMin !== null ||
    state.inboundDurationMax !== null
  )
    count++;
  if (
    state.departureTimeMin !== null ||
    state.departureTimeMax !== null ||
    state.returnDepartureTimeMin !== null ||
    state.returnDepartureTimeMax !== null
  )
    count++;
  if (
    state.arrivalTimeMin !== null ||
    state.arrivalTimeMax !== null ||
    state.returnArrivalTimeMin !== null ||
    state.returnArrivalTimeMax !== null
  )
    count++;
  return count;
}
