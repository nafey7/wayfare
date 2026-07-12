import { processLeg } from './flightUtils';
import type { FareItineraryCamel, FlightLegCamel, ProcessedLeg } from '@/types/flightBackend';
import type { TravellersData } from '@/types/flights';

/** One row for FlightResults / FlightCard (matches FlightSearchPage mapping). */
export interface FlightCardRowFromSearch {
  id: string;
  aircraftName: string;
  flightNumber: string;
  tags: string[];
  passengers: number;
  passengerCounts: { adults: number; children: number; infants: number };
  legs: ProcessedLeg[];
  price: number;
  original_total_fare?: number;
  platform_fee_percentage?: number;
  _originalItinerary: FareItineraryCamel;
}

export interface MapFareItinerariesOptions {
  fareItineraries: FareItineraryCamel[];
  travellers: TravellersData;
  /**
   * When set (multicity), card ids are `${legIndex}::${fareSourceCode}` to avoid collisions
   * and to identify the leg in handlers.
   */
  legIndex?: number;
}

/**
 * Maps search API fare itineraries to flight card rows (shared by one-way/round-trip and multicity legs).
 */
export function mapFareItinerariesToFlightCards(
  options: MapFareItinerariesOptions
): FlightCardRowFromSearch[] {
  const { fareItineraries, travellers, legIndex } = options;
  if (fareItineraries.length === 0) return [];

  const adults = travellers.adults ?? 1;
  const children = travellers.children ?? 0;
  const infants = travellers.infants ?? 0;
  const totalPassengers = adults + children + infants;

  const out: FlightCardRowFromSearch[] = [];

  fareItineraries.forEach((itinerary: FareItineraryCamel, index: number) => {
    const allLegs = itinerary.flightLegs ?? [];
    if (allLegs.length === 0) return;

    const isRoundTrip = allLegs.length > 1;
    const processedLegs = allLegs
      .map((leg: FlightLegCamel, li: number) => processLeg(leg, li, isRoundTrip))
      .filter((leg): leg is ProcessedLeg => leg !== null);

    if (processedLegs.length === 0) return;

    const firstLeg = allLegs[0];
    const firstSegment = firstLeg?.flightSegments?.[0];
    const airlineCode =
      firstSegment?.marketingAirline?.iataCode ??
      firstSegment?.operatingAirline?.iataCode ??
      '';
    const airlineName =
      firstSegment?.marketingAirline?.airlineName ??
      firstSegment?.operatingAirline?.airlineName ??
      (airlineCode || 'Unknown Airline');
    const flightNumber = firstSegment?.marketingFlightNumber?.formattedNumber ?? '';

    const pricing = itinerary.pricing;
    const fareTotals = pricing?.validatedFareTotals ?? pricing?.fareTotals;
    const totalFareAmount = fareTotals?.totalFare?.amount;
    const price = totalFareAmount != null ? Number(totalFareAmount) : 0;

    const originalTotalFareAmount = fareTotals?.originalTotalFare?.amount;
    const original_total_fare =
      originalTotalFareAmount != null ? Number(originalTotalFareAmount) : undefined;
    const platform_fee_percentage = fareTotals?.platformFeePercentage;

    const fareType = pricing?.fareType;
    const bookingType = fareType === 'WebFare' ? 'LCC' : 'GDS';

    const firstLegStops = processedLegs[0]?.stops ?? 0;
    const tags: string[] = [];
    if (firstLegStops === 0) {
      tags.push('Direct');
    } else {
      tags.push(processedLegs[0]?.stopsText ?? '');
    }
    tags.push(bookingType);

    const fareSourceCode = pricing?.fareSourceCode;
    const id =
      legIndex !== undefined
        ? `${legIndex}::${fareSourceCode ?? `flight-${index}`}`
        : (fareSourceCode ?? `flight-${index}`);

    const row: FlightCardRowFromSearch = {
      id,
      aircraftName: airlineName,
      flightNumber,
      tags,
      passengers: totalPassengers,
      passengerCounts: { adults, children, infants },
      legs: processedLegs,
      price,
      _originalItinerary: itinerary,
    };
    if (original_total_fare !== undefined) row.original_total_fare = original_total_fare;
    if (platform_fee_percentage !== undefined) row.platform_fee_percentage = platform_fee_percentage;
    out.push(row);
  });

  return out;
}
