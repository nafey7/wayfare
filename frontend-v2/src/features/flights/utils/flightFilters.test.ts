import { describe, it, expect } from 'vitest';
import {
  defaultFlightFilterState,
  filterFlights,
  minutesToTime,
  extractAirlinesFromFlights,
  extractCabinClassesFromFlights,
  extractDepartureAirportsFromFlights,
  extractArrivalAirportsFromFlights,
  type FlightFilterState,
  type FilterableFlight,
} from './flightFilters';

function makeFlight(overrides: Partial<FilterableFlight> & { price: number; legs: FilterableFlight['legs'] }): FilterableFlight {
  return {
    id: 'f1',
    ...overrides,
    _originalItinerary:
      overrides._originalItinerary ??
      (overrides.legs
        ? {
            flight_legs: overrides.legs.map((leg) => ({
              flight_segments:
                (leg.segments ?? []).length
                  ? [{ departure_airport: { iata_code: 'LHR' }, arrival_airport: { iata_code: 'JFK' }, cabin_class: 'Economy' }]
                  : [],
            })),
          }
        : undefined),
  } as FilterableFlight;
}

describe('flightFilters', () => {
  describe('defaultFlightFilterState', () => {
    it('has priceMin and priceMax null', () => {
      expect(defaultFlightFilterState.priceMin).toBeNull();
      expect(defaultFlightFilterState.priceMax).toBeNull();
    });
    it('has directOnly and stops flags false by default', () => {
      expect(defaultFlightFilterState.directOnly).toBe(false);
      expect(defaultFlightFilterState.stops1).toBe(false);
      expect(defaultFlightFilterState.stops2Plus).toBe(false);
    });
  });

  describe('filterFlights', () => {
    const baseLeg = {
      stops: 0,
      departure: { time: '10:00' },
      arrival: { time: '12:00' },
      duration: '2h',
      totalTimeDisplay: '2h',
      airlinesInfo: [{ code: 'BA', name: 'British Airways' }],
    };

    it('returns all flights when state is default (no filters applied)', () => {
      const flights: FilterableFlight[] = [
        makeFlight({ price: 100, legs: [{ ...baseLeg }] }),
        makeFlight({ price: 200, legs: [{ ...baseLeg }] }),
      ];
      const result = filterFlights(flights, defaultFlightFilterState);
      expect(result).toHaveLength(2);
    });

    it('filters by priceMin', () => {
      const state: FlightFilterState = { ...defaultFlightFilterState, priceMin: 150 };
      const flights: FilterableFlight[] = [
        makeFlight({ price: 100, legs: [{ ...baseLeg }] }),
        makeFlight({ price: 200, legs: [{ ...baseLeg }] }),
      ];
      const result = filterFlights(flights, state);
      expect(result).toHaveLength(1);
      expect(result[0]!.price).toBe(200);
    });

    it('filters by priceMax', () => {
      const state: FlightFilterState = { ...defaultFlightFilterState, priceMax: 150 };
      const flights: FilterableFlight[] = [
        makeFlight({ price: 100, legs: [{ ...baseLeg }] }),
        makeFlight({ price: 200, legs: [{ ...baseLeg }] }),
      ];
      const result = filterFlights(flights, state);
      expect(result).toHaveLength(1);
      expect(result[0]!.price).toBe(100);
    });

    it('filters by directOnly (stops === 0)', () => {
      const state: FlightFilterState = { ...defaultFlightFilterState, directOnly: true };
      const direct = makeFlight({ price: 100, legs: [{ ...baseLeg, stops: 0 }] });
      const oneStop = makeFlight({ price: 100, legs: [{ ...baseLeg, stops: 1 }] });
      const result = filterFlights([direct, oneStop], state);
      expect(result).toHaveLength(1);
      expect(result[0]!.legs[0]!.stops).toBe(0);
    });

    it('filters by stops1', () => {
      const state: FlightFilterState = { ...defaultFlightFilterState, stops1: true };
      const direct = makeFlight({ price: 100, legs: [{ ...baseLeg, stops: 0 }] });
      const oneStop = makeFlight({ price: 100, legs: [{ ...baseLeg, stops: 1 }] });
      const result = filterFlights([direct, oneStop], state);
      expect(result).toHaveLength(1);
      expect(result[0]!.legs[0]!.stops).toBe(1);
    });

    it('filters by airline when airlines selected', () => {
      const state: FlightFilterState = { ...defaultFlightFilterState, airlines: ['BA'] };
      const withBA = makeFlight({ price: 100, legs: [{ ...baseLeg, airlinesInfo: [{ code: 'BA', name: 'British Airways' }] }] });
      const withAA = makeFlight({ price: 100, legs: [{ ...baseLeg, airlinesInfo: [{ code: 'AA', name: 'American' }] }] });
      const result = filterFlights([withBA, withAA], state);
      expect(result).toHaveLength(1);
      expect(result[0]!.legs[0]!.airlinesInfo![0]!.code).toBe('BA');
    });

    it('preserves generic type (extra fields)', () => {
      type Extended = FilterableFlight & { label: string };
      const flights: Extended[] = [
        { ...makeFlight({ price: 100, legs: [{ ...baseLeg }] }), label: 'A' } as Extended,
      ];
      const result = filterFlights(flights, defaultFlightFilterState);
      expect((result[0] as Extended).label).toBe('A');
    });
  });

  describe('minutesToTime', () => {
    it('formats minutes to HH:MM', () => {
      expect(minutesToTime(0)).toBe('00:00');
      expect(minutesToTime(60)).toBe('01:00');
      expect(minutesToTime(90)).toBe('01:30');
      expect(minutesToTime(600)).toBe('10:00');
    });
    it('wraps hours with % 24', () => {
      expect(minutesToTime(24 * 60)).toBe('00:00');
    });
  });

  describe('extractAirlinesFromFlights', () => {
    it('returns unique airlines sorted by name', () => {
      const flights: FilterableFlight[] = [
        makeFlight({ price: 100, legs: [{ stops: 0, departure: { time: '10:00' }, arrival: { time: '12:00' }, airlinesInfo: [{ code: 'BA', name: 'British Airways' }] }] }),
        makeFlight({ price: 100, legs: [{ stops: 0, departure: { time: '14:00' }, arrival: { time: '16:00' }, airlinesInfo: [{ code: 'AA', name: 'American' }, { code: 'BA', name: 'British Airways' }] }] }),
      ];
      const airlines = extractAirlinesFromFlights(flights);
      expect(airlines).toHaveLength(2);
      expect(airlines.map((a) => a.code).sort()).toEqual(['AA', 'BA']);
      expect(airlines.find((a) => a.code === 'AA')!.name).toBe('American');
    });
  });

  describe('extractCabinClassesFromFlights', () => {
    it('returns unique cabin classes from _originalItinerary', () => {
      const flights: FilterableFlight[] = [
        makeFlight({
          price: 100,
          legs: [],
          _originalItinerary: {
            flightLegs: [
              { flightSegments: [{ cabinClass: 'Economy' }, { cabinClass: 'Business' }] },
            ],
          },
        }) as FilterableFlight,
      ];
      const cabins = extractCabinClassesFromFlights(flights);
      expect(cabins.sort()).toEqual(['Business', 'Economy']);
    });
  });

  describe('extractDepartureAirportsFromFlights', () => {
    it('returns unique departure airports with code and name (first leg)', () => {
      const flights: FilterableFlight[] = [
        makeFlight({
          price: 100,
          legs: [],
          _originalItinerary: {
            flightLegs: [{ flightSegments: [{ departureAirport: { iataCode: 'LHR', cityName: 'London Heathrow' } }] }],
          },
        }) as FilterableFlight,
        makeFlight({
          price: 100,
          legs: [],
          _originalItinerary: {
            flightLegs: [{ flightSegments: [{ departureAirport: { iataCode: 'CDG', cityName: 'Paris Charles de Gaulle' } }] }],
          },
        }) as FilterableFlight,
      ];
      const airports = extractDepartureAirportsFromFlights(flights);
      expect(airports.map((a) => a.code).sort()).toEqual(['CDG', 'LHR']);
      expect(airports.find((a) => a.code === 'LHR')?.name).toBe('London Heathrow');
    });
  });

  describe('extractArrivalAirportsFromFlights', () => {
    it('returns unique arrival airports (last segment of first leg)', () => {
      const flights: FilterableFlight[] = [
        makeFlight({
          price: 100,
          legs: [],
          _originalItinerary: {
            flightLegs: [
              {
                flightSegments: [
                  { departureAirport: { iataCode: 'LHR' }, arrivalAirport: { iataCode: 'JFK', cityName: 'New York JFK' } },
                ],
              },
            ],
          },
        }) as FilterableFlight,
      ];
      const airports = extractArrivalAirportsFromFlights(flights);
      expect(airports.map((a) => a.code)).toEqual(['JFK']);
      expect(airports[0]!.name).toBe('New York JFK');
    });
  });

  describe('return airport filters', () => {
    it('filters by returnDepartureAirports when round trip', () => {
      const state: FlightFilterState = { ...defaultFlightFilterState, returnDepartureAirports: ['JFK'] };
      const roundTripWithJFK = makeFlight({
        price: 100,
        legs: [{ stops: 0, departure: { time: '10:00' }, arrival: { time: '18:00' } }, { stops: 0, departure: { time: '20:00' }, arrival: { time: '08:00' } }],
        _originalItinerary: {
          flightLegs: [
            { flightSegments: [{ departureAirport: { iataCode: 'LHR' }, arrivalAirport: { iataCode: 'JFK' } }] },
            { flightSegments: [{ departureAirport: { iataCode: 'JFK' }, arrivalAirport: { iataCode: 'LHR' } }] },
          ],
        },
      }) as FilterableFlight;
      const roundTripWithEWR = makeFlight({
        price: 100,
        legs: [{ stops: 0, departure: { time: '10:00' }, arrival: { time: '18:00' } }, { stops: 0, departure: { time: '20:00' }, arrival: { time: '08:00' } }],
        _originalItinerary: {
          flightLegs: [
            { flightSegments: [{ departureAirport: { iataCode: 'LHR' }, arrivalAirport: { iataCode: 'EWR' } }] },
            { flightSegments: [{ departureAirport: { iataCode: 'EWR' }, arrivalAirport: { iataCode: 'LHR' } }] },
          ],
        },
      }) as FilterableFlight;
      const result = filterFlights([roundTripWithJFK, roundTripWithEWR], state);
      expect(result).toHaveLength(1);
      expect(result[0]!.legs[1]).toBeDefined();
    });

    it('filters by returnArrivalAirports when round trip', () => {
      const state: FlightFilterState = { ...defaultFlightFilterState, returnArrivalAirports: ['LHR'] };
      const roundTrip = makeFlight({
        price: 100,
        legs: [{ stops: 0, departure: { time: '10:00' }, arrival: { time: '18:00' } }, { stops: 0, departure: { time: '20:00' }, arrival: { time: '08:00' } }],
        _originalItinerary: {
          flightLegs: [
            { flightSegments: [{ departureAirport: { iataCode: 'LHR' }, arrivalAirport: { iataCode: 'JFK' } }] },
            { flightSegments: [{ departureAirport: { iataCode: 'JFK' }, arrivalAirport: { iataCode: 'LHR' } }] },
          ],
        },
      }) as FilterableFlight;
      const result = filterFlights([roundTrip], state);
      expect(result).toHaveLength(1);
    });
  });
});
