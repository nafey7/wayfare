import { describe, it, expect, vi } from 'vitest';
import type { FlightInfo, FlightSearchParams } from '@/types/api.helpers';
import {
  flightInfoToFareItinerary,
  searchParamsToFormParams,
  extractedToSearchResponse,
  multicityToSearchResponse,
} from './hydrateChatFlightResultsToSearchCache';

function makeFlight(overrides: Partial<FlightInfo> = {}): FlightInfo {
  return {
    id: 'fare-1',
    departure_time: '10:00',
    departure_date: '2026-06-01',
    arrival_time: '13:30',
    arrival_date: '2026-06-01',
    origin_code: 'AMS',
    origin_city: 'Amsterdam',
    destination_code: 'BCN',
    destination_city: 'Barcelona',
    duration: '3h 30m',
    duration_minutes: 210,
    stops: 0,
    price: 149.5,
    currency: 'EUR',
    airline: 'KLM',
    airline_code: 'KL',
    flight_number: 'KL1671',
    ...overrides,
  };
}

function makeSearchParams(overrides: Partial<FlightSearchParams> = {}): FlightSearchParams {
  return {
    origin: 'AMS',
    destination: 'BCN',
    departure_date: '2026-06-01',
    return_date: null,
    journey_type: 'OneWay',
    passengers: { adults: 1, children: 0, infants: 0 },
    origin_city: 'Amsterdam',
    destination_city: 'Barcelona',
    origin_iata: 'AMS',
    destination_iata: 'BCN',
    cabin_class: 'Economy',
    ...overrides,
  };
}

describe('flightInfoToFareItinerary', () => {
  it('maps snake_case flight to camelCase FareItinerary with single synthetic segment', () => {
    const fi = flightInfoToFareItinerary(makeFlight());
    expect(fi.flightLegs).toHaveLength(1);
    const leg = fi.flightLegs[0]!;
    expect(leg.totalStops).toBe(0);
    expect(leg.flightSegments).toHaveLength(1);
    const seg = leg.flightSegments[0]!;
    expect(seg.departureDatetime).toBe('2026-06-01T10:00');
    expect(seg.arrivalDatetime).toBe('2026-06-01T13:30');
    expect(seg.departureAirport!.iataCode).toBe('AMS');
    expect(seg.departureAirport!.cityName).toBe('Amsterdam');
    expect(seg.arrivalAirport!.iataCode).toBe('BCN');
    expect(seg.arrivalAirport!.cityName).toBe('Barcelona');
    expect(seg.marketingAirline?.iataCode).toBe('KL');
    expect(seg.marketingAirline?.airlineName).toBe('KLM');
    expect(seg.flightDuration?.totalMinutes).toBe(210);
  });

  it('uses fareSourceCode = flight.id', () => {
    const fi = flightInfoToFareItinerary(makeFlight({ id: 'abc123' }));
    expect(fi.pricing!.fareSourceCode).toBe('abc123');
  });

  it('maps price and currency into fareTotals.totalFare', () => {
    const fi = flightInfoToFareItinerary(makeFlight({ price: 250, currency: 'USD' }));
    expect(fi.pricing!.fareTotals?.totalFare?.amount).toBe(250);
    expect(fi.pricing!.fareTotals?.totalFare?.currency).toBe('USD');
  });

  it('sets journeyType to "Return" when is_round_trip is true, "OneWay" otherwise', () => {
    expect(flightInfoToFareItinerary(makeFlight({ is_round_trip: true })).journeyType).toBe('Return');
    expect(flightInfoToFareItinerary(makeFlight({ is_round_trip: false })).journeyType).toBe('OneWay');
    expect(flightInfoToFareItinerary(makeFlight()).journeyType).toBe('OneWay');
  });

  it('maps validating_airline when present', () => {
    const fi = flightInfoToFareItinerary(
      makeFlight({ validating_airline: { airline_name: 'KLM Royal Dutch', iata_code: 'KL' } })
    );
    expect(fi.validatingAirline?.airlineName).toBe('KLM Royal Dutch');
    expect(fi.validatingAirline?.iataCode).toBe('KL');
  });

  it('leaves validatingAirline undefined when not provided', () => {
    const fi = flightInfoToFareItinerary(makeFlight());
    expect(fi.validatingAirline).toBeUndefined();
  });

  it('maps multi-segment flights using FlightSegmentInfo[]', () => {
    const fi = flightInfoToFareItinerary(
      makeFlight({
        segments: [
          {
            origin_code: 'AMS',
            origin_city: 'Amsterdam',
            destination_code: 'CDG',
            destination_city: 'Paris',
            departure_time: '10:00',
            departure_date: '2026-06-01',
            arrival_time: '11:30',
            arrival_date: '2026-06-01',
            duration: '1h 30m',
            duration_minutes: 90,
            airline: 'Air France',
            airline_code: 'AF',
            logo_url: 'https://cdn/af.png',
            flight_number: 'AF1241',
            cabin_class: 'Economy',
          },
          {
            origin_code: 'CDG',
            origin_city: 'Paris',
            destination_code: 'BCN',
            destination_city: 'Barcelona',
            departure_time: '13:00',
            departure_date: '2026-06-01',
            arrival_time: '14:30',
            arrival_date: '2026-06-01',
            duration: '1h 30m',
            duration_minutes: 90,
            airline: 'Vueling',
            airline_code: 'VY',
            logo_url: 'https://cdn/vy.png',
            flight_number: 'VY8001',
          },
        ],
        stops: 1,
      })
    );
    const segs = fi.flightLegs[0]!.flightSegments;
    expect(segs).toHaveLength(2);
    expect(segs[0]!.departureAirport!.iataCode).toBe('AMS');
    expect(segs[0]!.arrivalAirport!.iataCode).toBe('CDG');
    expect(segs[0]!.marketingAirline?.iataCode).toBe('AF');
    expect(segs[0]!.marketingAirline?.airlineName).toBe('Air France');
    expect(segs[0]!.flightDuration?.totalMinutes).toBe(90);
    expect(segs[0]!.marketingFlightNumber?.formattedNumber).toBe('AF1241');
    expect(segs[1]!.departureAirport!.iataCode).toBe('CDG');
    expect(segs[1]!.arrivalAirport!.iataCode).toBe('BCN');
    expect(segs[1]!.marketingAirline?.iataCode).toBe('VY');
    expect(fi.flightLegs[0]!.totalStops).toBe(1);
  });

  it('falls back to departure_code/city aliases in segments when origin_code is absent', () => {
    const fi = flightInfoToFareItinerary(
      makeFlight({
        segments: [
          {
            departure_code: 'AMS',
            departure_city: 'Amsterdam',
            destination_code: 'BCN',
            destination_city: 'Barcelona',
            departure_time: '10:00',
            departure_date: '2026-06-01',
            arrival_time: '13:30',
            arrival_date: '2026-06-01',
            duration: '3h 30m',
          },
        ],
      })
    );
    const seg = fi.flightLegs[0]!.flightSegments[0]!;
    expect(seg.departureAirport!.iataCode).toBe('AMS');
    expect(seg.departureAirport!.cityName).toBe('Amsterdam');
  });

  it('leaves segment marketingAirline undefined when airline_code is absent', () => {
    const fi = flightInfoToFareItinerary(
      makeFlight({
        segments: [
          {
            origin_code: 'AMS',
            destination_code: 'BCN',
            departure_time: '10:00',
            departure_date: '2026-06-01',
            arrival_time: '13:30',
            arrival_date: '2026-06-01',
            duration: '3h 30m',
          },
        ],
      })
    );
    expect(fi.flightLegs[0]!.flightSegments[0]!.marketingAirline).toBeUndefined();
  });

  it('reconstructs separate outbound/return legs for round-trip with leg_index segments', () => {
    const fi = flightInfoToFareItinerary(
      makeFlight({
        is_round_trip: true,
        segments: [
          {
            origin_code: 'AMS',
            origin_city: 'Amsterdam',
            destination_code: 'BCN',
            destination_city: 'Barcelona',
            departure_time: '10:00',
            departure_date: '2026-06-01',
            arrival_time: '13:30',
            arrival_date: '2026-06-01',
            duration: '3h 30m',
            duration_minutes: 210,
            leg_index: 0,
          },
          {
            origin_code: 'BCN',
            origin_city: 'Barcelona',
            destination_code: 'AMS',
            destination_city: 'Amsterdam',
            departure_time: '15:00',
            departure_date: '2026-06-08',
            arrival_time: '18:30',
            arrival_date: '2026-06-08',
            duration: '3h 30m',
            duration_minutes: 210,
            leg_index: 1,
          },
        ],
      })
    );
    expect(fi.flightLegs).toHaveLength(2);
    expect(fi.flightLegs[0]!.flightSegments[0]!.departureAirport!.iataCode).toBe('AMS');
    expect(fi.flightLegs[1]!.flightSegments[0]!.departureAirport!.iataCode).toBe('BCN');
    expect(fi.flightLegs[0]!.totalStops).toBe(0);
    expect(fi.flightLegs[1]!.totalStops).toBe(0);
    expect(fi.journeyType).toBe('Return');
    expect(fi.pricing!.fareSourceCode).toBe('fare-1');
  });

  it('keeps all segments in a single leg when round-trip segments have no leg_index', () => {
    const fi = flightInfoToFareItinerary(
      makeFlight({
        is_round_trip: true,
        segments: [
          {
            origin_code: 'AMS',
            destination_code: 'BCN',
            departure_time: '10:00',
            departure_date: '2026-06-01',
            arrival_time: '13:30',
            arrival_date: '2026-06-01',
            duration: '3h 30m',
          },
          {
            origin_code: 'BCN',
            destination_code: 'AMS',
            departure_time: '15:00',
            departure_date: '2026-06-08',
            arrival_time: '18:30',
            arrival_date: '2026-06-08',
            duration: '3h 30m',
          },
        ],
        stops: 1,
      })
    );
    expect(fi.flightLegs).toHaveLength(1);
    expect(fi.flightLegs[0]!.flightSegments).toHaveLength(2);
    expect(fi.journeyType).toBe('Return');
  });

  it('emits empty fareSourceCode and warns when flight.id is missing', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const fi = flightInfoToFareItinerary(makeFlight({ id: '' }));
    expect(fi.pricing!.fareSourceCode).toBe('');
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });
});

describe('searchParamsToFormParams', () => {
  it('maps OneWay to one-way tripType', () => {
    expect(searchParamsToFormParams(makeSearchParams({ journey_type: 'OneWay' })).tripType).toBe('one-way');
  });

  it('maps Return / RoundTrip / Circle to round-trip tripType', () => {
    expect(searchParamsToFormParams(makeSearchParams({ journey_type: 'Return' })).tripType).toBe('round-trip');
    expect(searchParamsToFormParams(makeSearchParams({ journey_type: 'RoundTrip' })).tripType).toBe('round-trip');
    expect(searchParamsToFormParams(makeSearchParams({ journey_type: 'Circle' })).tripType).toBe('round-trip');
  });

  it('prefers origin_city / destination_city for from/to labels', () => {
    const form = searchParamsToFormParams(makeSearchParams());
    expect(form.from).toBe('Amsterdam');
    expect(form.to).toBe('Barcelona');
  });

  it('falls back to origin/destination IATA when city fields are absent', () => {
    const form = searchParamsToFormParams(
      makeSearchParams({ origin_city: null, destination_city: null })
    );
    expect(form.from).toBe('AMS');
    expect(form.to).toBe('BCN');
  });

  it('builds fromAirport / toAirport when IATA is present', () => {
    const form = searchParamsToFormParams(makeSearchParams());
    expect(form.fromAirport).toMatchObject({ iata: 'AMS', city: 'Amsterdam' });
    expect(form.toAirport).toMatchObject({ iata: 'BCN', city: 'Barcelona' });
  });

  it('leaves fromAirport / toAirport undefined when IATA is missing', () => {
    const form = searchParamsToFormParams(
      makeSearchParams({ origin_iata: undefined, destination_iata: undefined })
    );
    expect(form.fromAirport).toBeUndefined();
    expect(form.toAirport).toBeUndefined();
  });

  it('passes through passengers and cabin class', () => {
    const form = searchParamsToFormParams(
      makeSearchParams({ passengers: { adults: 2, children: 1, infants: 0 }, cabin_class: 'Business' })
    );
    expect(form.travellers.adults).toBe(2);
    expect(form.travellers.children).toBe(1);
    expect(form.travellers.infants).toBe(0);
    expect(form.travellers.cabinClass).toBe('Business');
  });

  it('defaults passengers to 1/0/0 when missing', () => {
    const form = searchParamsToFormParams(
      makeSearchParams({ passengers: undefined as unknown as FlightSearchParams['passengers'] })
    );
    expect(form.travellers.adults).toBe(1);
    expect(form.travellers.children).toBe(0);
    expect(form.travellers.infants).toBe(0);
  });

  it('propagates originIsCity / destinationIsCity flags', () => {
    const form = searchParamsToFormParams(
      makeSearchParams({ origin_is_city: true, destination_is_city: false })
    );
    expect(form.originIsCity).toBe(true);
    expect(form.destinationIsCity).toBe(false);
  });

  it('sets date and returnDate from departure_date / return_date', () => {
    const form = searchParamsToFormParams(
      makeSearchParams({ departure_date: '2026-06-01', return_date: '2026-06-08' })
    );
    expect(form.date).toBe('2026-06-01');
    expect(form.returnDate).toBe('2026-06-08');
  });
});

describe('extractedToSearchResponse', () => {
  it('wires sessionId, fareItineraries and form params together', () => {
    const { data, params } = extractedToSearchResponse({
      session_id: 'sid-42',
      flights: [makeFlight(), makeFlight({ id: 'fare-2', price: 200 })],
      data: {
        search_params: makeSearchParams(),
        summary: { total_flights: 2, direct_count: 2, price_range: { min: 149.5, max: 200 } },
      },
    });
    expect(data.sessionId).toBe('sid-42');
    expect(data.fareItineraries).toHaveLength(2);
    expect(data.fareItineraries[0]!.pricing!.fareSourceCode).toBe('fare-1');
    expect(data.fareItineraries[1]!.pricing!.fareSourceCode).toBe('fare-2');
    expect(params.tripType).toBe('one-way');
    expect(params.from).toBe('Amsterdam');
  });

  it('defaults sessionId to empty string when missing', () => {
    const { data } = extractedToSearchResponse({
      session_id: '',
      flights: [],
      data: {
        search_params: makeSearchParams(),
        summary: { total_flights: 0, direct_count: 0, price_range: { min: 0, max: 0 } },
      },
    });
    expect(data.sessionId).toBe('');
  });
});

describe('multicityToSearchResponse', () => {
  it('flattens legs into multicityLegs and uses first leg for top-level fareItineraries', () => {
    const emptySummary = { total_flights: 0, direct_count: 0, price_range: { min: 0, max: 0 } };
    const emptyCategories = {
      cheapest: { label: 'Cheapest', flights: [] },
      fastest: { label: 'Fastest', flights: [] },
      best_value: { label: 'Best Value', flights: [] },
    };
    const { data, params } = multicityToSearchResponse({
      searchParams: makeSearchParams(),
      legs: [
        {
          legIndex: 0,
          origin: 'AMS',
          destination: 'BCN',
          departureDate: '2026-06-01',
          sessionId: 'leg-0-sid',
          summary: emptySummary,
          categories: emptyCategories,
          flights: [makeFlight({ id: 'leg0-fare1' })],
        },
        {
          legIndex: 1,
          origin: 'BCN',
          destination: 'MAD',
          departureDate: '2026-06-05',
          sessionId: 'leg-1-sid',
          summary: emptySummary,
          categories: emptyCategories,
          flights: [makeFlight({ id: 'leg1-fare1', origin_code: 'BCN', destination_code: 'MAD' })],
        },
      ],
    });
    expect(params.tripType).toBe('multi-city');
    expect(params.segments).toHaveLength(2);
    expect(params.segments![0]).toMatchObject({ from: 'AMS', to: 'BCN', date: '2026-06-01' });
    expect(params.segments![1]).toMatchObject({ from: 'BCN', to: 'MAD', date: '2026-06-05' });
    expect(data.sessionId).toBe('leg-0-sid');
    expect(data.fareItineraries).toHaveLength(1);
    expect(data.fareItineraries[0]!.pricing!.fareSourceCode).toBe('leg0-fare1');
    expect(data.multicityLegs).toHaveLength(2);
    expect(data.multicityLegs![0]!.fareItineraries[0]!.pricing!.fareSourceCode).toBe('leg0-fare1');
    expect(data.multicityLegs![1]!.fareItineraries[0]!.pricing!.fareSourceCode).toBe('leg1-fare1');
  });
});
