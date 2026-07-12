/**
 * Static mock data for flight search, results, and filter Storybook stories.
 * Shape-matched to live types — import from @/types, never redefine inline.
 * Re-export overlapping fixtures from mockFlightData.ts rather than duplicating.
 */
import type { FlightLeg } from '@/types/flight';
import type { FilterableFlight, FlightFilterState } from '../utils/flightFilters';
import { defaultFlightFilterState } from '../utils/flightFilters';
import type { AirportOption, TravellersData } from '@/types/flights';

export { defaultFlightFilterState };

// ---------------------------------------------------------------------------
// FlightLeg fixtures — shape matches FlightLeg from @/types/flight
// FlightCard reads: leg.departure.{city, airport, date, time},
//                   leg.arrival.{city, airport, date, time},
//                   leg.duration, leg.stops, leg.stopsText, leg.airlinesInfo
// ---------------------------------------------------------------------------

export const mockFlightLegAMS_BCN: FlightLeg = {
  departure: { city: 'Amsterdam', airport: 'AMS', date: '10 Jun 2026', time: '06:20' },
  arrival: { city: 'Barcelona', airport: 'BCN', date: '10 Jun 2026', time: '08:40' },
  duration: '2h 20m',
  stops: 0,
  stopsText: 'Non Stop',
  legLabel: 'OUTBOUND',
  airlinesInfo: [{ name: 'Vueling', code: 'VY', flights: ['VY8373'] }],
};

export const mockFlightLegBCN_AMS: FlightLeg = {
  departure: { city: 'Barcelona', airport: 'BCN', date: '17 Jun 2026', time: '11:00' },
  arrival: { city: 'Amsterdam', airport: 'AMS', date: '17 Jun 2026', time: '13:20' },
  duration: '2h 20m',
  stops: 0,
  stopsText: 'Non Stop',
  legLabel: 'RETURN',
  airlinesInfo: [{ name: 'Vueling', code: 'VY', flights: ['VY8374'] }],
};

export const mockFlightLegOneStop: FlightLeg = {
  departure: { city: 'Amsterdam', airport: 'AMS', date: '10 Jun 2026', time: '09:00' },
  arrival: { city: 'Barcelona', airport: 'BCN', date: '10 Jun 2026', time: '13:30' },
  duration: '4h 30m',
  stops: 1,
  stopsText: '1 stop via MAD',
  legLabel: 'OUTBOUND',
  airlinesInfo: [{ name: 'Iberia', code: 'IB', flights: ['IB3169'] }],
};

// ---------------------------------------------------------------------------
// FlightCard flight fixtures — exact shape for FlightCardProps['flight']
// ---------------------------------------------------------------------------

export const mockFlightCardOneWay = {
  id: 'story-ow-1',
  aircraftName: 'Airbus A320',
  flightNumber: 'VY8373',
  journeyType: 'OneWay',
  tags: [] as string[],
  passengers: 1,
  passengerCounts: { adults: 1, children: 0, infants: 0 },
  legs: [mockFlightLegAMS_BCN],
  price: 92,
};

export const mockFlightCardRoundTrip = {
  id: 'story-rt-1',
  aircraftName: 'Airbus A320',
  flightNumber: 'VY8373',
  journeyType: 'Return',
  tags: [] as string[],
  passengers: 2,
  passengerCounts: { adults: 2, children: 0, infants: 0 },
  legs: [mockFlightLegAMS_BCN, mockFlightLegBCN_AMS],
  price: 184,
};

export const mockFlightCardMultiStop = {
  id: 'story-ms-1',
  aircraftName: 'Boeing 737',
  flightNumber: 'IB3169',
  journeyType: 'OneWay',
  tags: [] as string[],
  passengers: 1,
  passengerCounts: { adults: 1, children: 0, infants: 0 },
  legs: [mockFlightLegOneStop],
  price: 65,
};

export const mockFlightCardBestValue = {
  id: 'story-bv-1',
  aircraftName: 'Airbus A320',
  flightNumber: 'HV6153',
  journeyType: 'Return',
  tags: ['Best Value'] as string[],
  passengers: 1,
  passengerCounts: { adults: 1, children: 0, infants: 0 },
  legs: [
    {
      departure: { city: 'Amsterdam', airport: 'AMS', date: '10 Jun 2026', time: '07:45' },
      arrival: { city: 'Barcelona', airport: 'BCN', date: '10 Jun 2026', time: '10:00' },
      duration: '2h 15m',
      stops: 0,
      stopsText: 'Non Stop',
      legLabel: 'OUTBOUND',
      airlinesInfo: [{ name: 'Transavia', code: 'HV', flights: ['HV6153'] }],
    },
    {
      departure: { city: 'Barcelona', airport: 'BCN', date: '17 Jun 2026', time: '12:00' },
      arrival: { city: 'Amsterdam', airport: 'AMS', date: '17 Jun 2026', time: '14:15' },
      duration: '2h 15m',
      stops: 0,
      stopsText: 'Non Stop',
      legLabel: 'RETURN',
      airlinesInfo: [{ name: 'Transavia', code: 'HV', flights: ['HV6154'] }],
    },
  ],
  price: 124,
};

// ---------------------------------------------------------------------------
// FilterableFlight fixtures — used by FlightFiltersDialog stories
// FilterableFlight.legs only needs: stops, departure.time, arrival.time,
// duration?, airlinesInfo?[].{code, name}
// ---------------------------------------------------------------------------

export const mockFilterableFlights: FilterableFlight[] = [
  {
    id: 'filter-1',
    price: 92,
    legs: [
      {
        stops: 0,
        departure: { time: '06:20' },
        arrival: { time: '08:40' },
        duration: '2h 20m',
        airlinesInfo: [{ code: 'VY', name: 'Vueling' }],
      },
      {
        stops: 0,
        departure: { time: '11:00' },
        arrival: { time: '13:20' },
        duration: '2h 20m',
        airlinesInfo: [{ code: 'VY', name: 'Vueling' }],
      },
    ],
  },
  {
    id: 'filter-2',
    price: 148,
    legs: [
      {
        stops: 0,
        departure: { time: '10:15' },
        arrival: { time: '12:25' },
        duration: '2h 10m',
        airlinesInfo: [{ code: 'KL', name: 'KLM' }],
      },
      {
        stops: 0,
        departure: { time: '13:30' },
        arrival: { time: '15:40' },
        duration: '2h 10m',
        airlinesInfo: [{ code: 'KL', name: 'KLM' }],
      },
    ],
  },
  {
    id: 'filter-3',
    price: 65,
    legs: [
      {
        stops: 1,
        departure: { time: '09:00' },
        arrival: { time: '13:30' },
        duration: '4h 30m',
        airlinesInfo: [{ code: 'IB', name: 'Iberia' }],
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// FlightFilterState — active filter preset (directOnly + price range)
// ---------------------------------------------------------------------------

export const mockFilterStateActive: FlightFilterState = {
  ...defaultFlightFilterState,
  priceMin: 80,
  priceMax: 150,
  directOnly: true,
};

// ---------------------------------------------------------------------------
// FareRules mock data — matches FareRulesProps['fareRules']
// ---------------------------------------------------------------------------

export const mockFareRulesData = {
  fare_rules: [
    {
      rule_description:
        'CANCELLATIONS\n' +
        'Ticket is non-refundable.\n' +
        'No-show: Ticket is non-refundable.\n\n' +
        'CHANGES\n' +
        'Before departure: Changes are permitted with a fee of USD 100 per person.\n' +
        'After departure: Ticket is non-changeable.',
    },
  ],
  baggage_information: [] as unknown[],
};

export const mockFareRulesRestrictive = {
  fare_rules: [
    {
      rule_description:
        'CANCELLATIONS\n' +
        'No refunds are permitted under any circumstances.\n\n' +
        'CHANGES\n' +
        'No changes are permitted after ticket issuance.\n\n' +
        'NAME CHANGES\n' +
        'Name changes are not permitted.',
    },
  ],
  baggage_information: [] as unknown[],
};

// ---------------------------------------------------------------------------
// AirportOption fixtures — for AirportAutocomplete stories
// ---------------------------------------------------------------------------

export const mockAirportOptionAMS: AirportOption = {
  iata: 'AMS',
  name: 'Amsterdam Airport Schiphol',
  city: 'Amsterdam',
  country: 'Netherlands',
  isCityOption: false,
};

export const mockAirportOptionBCN: AirportOption = {
  iata: 'BCN',
  name: 'Barcelona El Prat Airport',
  city: 'Barcelona',
  country: 'Spain',
  isCityOption: false,
};

// ---------------------------------------------------------------------------
// TravellersData fixtures — for TravellersSelector stories
// ---------------------------------------------------------------------------

export const mockTravellersDefault: TravellersData = {
  adults: 1,
  children: 0,
  infants: 0,
  cabinClass: 'Economy',
};

export const mockTravellersWithChildren: TravellersData = {
  adults: 2,
  children: 2,
  infants: 0,
  cabinClass: 'Economy',
};

export const mockTravellersMax: TravellersData = {
  adults: 9,
  children: 8,
  infants: 2,
  cabinClass: 'Business',
};
