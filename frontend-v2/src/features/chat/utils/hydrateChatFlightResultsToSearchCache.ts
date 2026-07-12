/**
 * Converts chat-pipeline flight data shapes into the FlightSearchResponseCamel + FlightSearchFormParams
 * shape consumed by FlightSearchPage / setCachedFlightResults.
 *
 * Chat produces FlightInfo[] (snake_case, flat). FlightSearchPage reads FareItineraryCamel[]
 * (camelCase, nested). This module is the boundary adapter.
 */
import type {
  ExtractedFlightSearchData,
  FlightInfo,
  FlightSearchParams,
  FlightSegmentInfo,
} from '@/types/api.helpers';
import type {
  FareItineraryCamel,
  FlightLegCamel,
  FlightSearchResponseCamel,
  FlightSegmentCamel,
  MulticityLegSearchResultCamel,
} from '@/types/flightBackend';
import type {
  FlightSearchFormParams,
  SerializableAirportOption,
} from '@/store/slices/flightBookingSlice';
import type { MulticityChatPayloadNormalized } from '@/features/chat/utils/extractMulticityFlightSearchResults';
import { mapCabinClass } from '@/features/chat/utils/chatSearchParamsToUI';
import type { TripType } from '@/types/flights';

function segmentInfoToSegmentCamel(seg: FlightSegmentInfo): FlightSegmentCamel {
  return {
    departureDatetime: `${seg.departure_date}T${seg.departure_time}`,
    arrivalDatetime: `${seg.arrival_date}T${seg.arrival_time}`,
    departureAirport: {
      iataCode: seg.origin_code ?? seg.departure_code,
      cityName: seg.origin_city ?? seg.departure_city,
    },
    arrivalAirport: {
      iataCode: seg.destination_code,
      cityName: seg.destination_city,
    },
    flightDuration: seg.duration_minutes != null ? { totalMinutes: seg.duration_minutes } : undefined,
    marketingAirline: seg.airline_code
      ? {
          iataCode: seg.airline_code,
          airlineName: seg.airline,
          logo_url: seg.logo_url,
        }
      : undefined,
    marketingFlightNumber: seg.flight_number
      ? { formattedNumber: seg.flight_number }
      : undefined,
    cabinClass: seg.cabin_class,
  };
}

function buildValidatingAirline(flight: FlightInfo): FareItineraryCamel['validatingAirline'] {
  if (!flight.validating_airline) return undefined;
  return {
    airlineName: flight.validating_airline.airline_name,
    iataCode: flight.validating_airline.iata_code,
  };
}

function buildFlightSegments(flight: FlightInfo): FlightSegmentCamel[] {
  if (flight.segments && flight.segments.length > 0) {
    return flight.segments.map(segmentInfoToSegmentCamel);
  }
  return [
    {
      departureDatetime: `${flight.departure_date}T${flight.departure_time}`,
      arrivalDatetime: `${flight.arrival_date}T${flight.arrival_time}`,
      departureAirport: {
        iataCode: flight.origin_code,
        cityName: flight.origin_city ?? undefined,
      },
      arrivalAirport: {
        iataCode: flight.destination_code,
        cityName: flight.destination_city ?? undefined,
      },
      marketingAirline: {
        iataCode: flight.airline_code,
        airlineName: flight.airline,
      },
      flightDuration: {
        totalMinutes: flight.duration_minutes,
      },
    },
  ];
}

export function flightInfoToFareItinerary(flight: FlightInfo): FareItineraryCamel {
  if (!flight.id) {
    console.warn('[hydrateChatFlightResultsToSearchCache] FlightInfo.id is empty — fareSourceCode will be empty; booking from this result will fail');
  }

  // For round trips with leg_index-tagged segments, reconstruct separate outbound/return legs.
  // Without this, all segments end up in one flightLeg and mapFareItinerariesToFlightCards
  // treats the result as one-way (allLegs.length > 1 check fails).
  const hasLegIndex =
    flight.is_round_trip &&
    flight.segments != null &&
    flight.segments.length > 0 &&
    flight.segments.some((s) => s.leg_index !== undefined);

  if (hasLegIndex) {
    const legMap = new Map<number, FlightSegmentInfo[]>();
    for (const seg of flight.segments!) {
      const legIdx = seg.leg_index ?? 0;
      if (!legMap.has(legIdx)) legMap.set(legIdx, []);
      legMap.get(legIdx)!.push(seg);
    }
    const flightLegs: FlightLegCamel[] = Array.from(legMap.entries())
      .sort(([a], [b]) => a - b)
      .map(([, segs]) => ({
        flightSegments: segs.map(segmentInfoToSegmentCamel),
        totalStops: Math.max(0, segs.length - 1),
      }));
    return {
      flightLegs,
      pricing: {
        fareSourceCode: flight.id ?? '',
        fareTotals: {
          totalFare: {
            amount: flight.price,
            currency: flight.currency,
          },
        },
      },
      journeyType: 'Return',
      validatingAirline: buildValidatingAirline(flight),
    };
  }

  const segments = buildFlightSegments(flight);
  const leg: FlightLegCamel = {
    flightSegments: segments,
    totalStops: flight.stops,
  };

  return {
    flightLegs: [leg],
    pricing: {
      fareSourceCode: flight.id ?? '',
      fareTotals: {
        totalFare: {
          amount: flight.price,
          currency: flight.currency,
        },
      },
    },
    journeyType: flight.is_round_trip ? 'Return' : 'OneWay',
    validatingAirline: buildValidatingAirline(flight),
  };
}

function buildAirportOption(
  iata: string | undefined,
  city: string | null | undefined
): SerializableAirportOption | undefined {
  if (!iata) return undefined;
  return { iata, city: city ?? '', name: city ?? iata, country: '' };
}

export function searchParamsToFormParams(params: FlightSearchParams): FlightSearchFormParams {
  const passengers = params.passengers ?? { adults: 1, children: 0, infants: 0 };

  let tripType: TripType;
  if (params.journey_type === 'MultiCity') {
    tripType = 'multi-city';
  } else {
    switch (params.journey_type) {
      case 'Return':
      case 'RoundTrip':
      case 'Circle':
        tripType = 'round-trip';
        break;
      default:
        tripType = 'one-way';
    }
  }

  return {
    tripType,
    from: params.origin_city || params.origin,
    to: params.destination_city || params.destination,
    fromAirport: buildAirportOption(params.origin_iata, params.origin_city),
    toAirport: buildAirportOption(params.destination_iata, params.destination_city),
    date: params.departure_date || null,
    returnDate: params.return_date || null,
    travellers: {
      adults: passengers.adults,
      children: passengers.children,
      infants: passengers.infants,
      cabinClass: mapCabinClass(params.cabin_class),
    },
    originIsCity: params.origin_is_city,
    destinationIsCity: params.destination_is_city,
  };
}

export function extractedToSearchResponse(extracted: ExtractedFlightSearchData): {
  data: FlightSearchResponseCamel;
  params: FlightSearchFormParams;
} {
  const fareItineraries = extracted.flights.map(flightInfoToFareItinerary);
  const params = searchParamsToFormParams(extracted.data.search_params);

  const data: FlightSearchResponseCamel = {
    sessionId: extracted.session_id ?? '',
    fareItineraries,
  };

  return { data, params };
}

export function multicityToSearchResponse(normalized: MulticityChatPayloadNormalized): {
  data: FlightSearchResponseCamel;
  params: FlightSearchFormParams;
} {
  const multicityLegs: MulticityLegSearchResultCamel[] = normalized.legs.map((leg, idx) => ({
    legIndex: leg.legIndex ?? idx,
    origin: leg.origin,
    destination: leg.destination,
    departureDate: leg.departureDate,
    sessionId: leg.sessionId,
    supplier: '',
    fareItineraries: leg.flights.map(flightInfoToFareItinerary),
  }));

  const firstLeg = normalized.legs[0]!;
  const lastLeg = normalized.legs[normalized.legs.length - 1]!;
  const baseParams = normalized.searchParams;
  const passengers = baseParams.passengers ?? { adults: 1, children: 0, infants: 0 };

  const params: FlightSearchFormParams = {
    tripType: 'multi-city',
    from: firstLeg.origin,
    to: lastLeg.destination,
    date: firstLeg.departureDate,
    returnDate: null,
    travellers: {
      adults: passengers.adults,
      children: passengers.children,
      infants: passengers.infants,
      cabinClass: mapCabinClass(baseParams.cabin_class),
    },
    segments: normalized.legs.map((l) => ({
      from: l.origin,
      to: l.destination,
      date: l.departureDate,
    })),
  };

  const data: FlightSearchResponseCamel = {
    sessionId: firstLeg.sessionId ?? '',
    fareItineraries: firstLeg.flights.map(flightInfoToFareItinerary),
    multicityLegs,
  };

  return { data, params };
}
