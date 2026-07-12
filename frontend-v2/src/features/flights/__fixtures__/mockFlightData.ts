/**
 * Static mock flight data for Storybook stories.
 *
 * Shaped to match the live backend contracts so stories render the same as
 * production. No API calls, no randomness. Import types from @/types — never
 * redefine shapes inline.
 *
 * Where fields overlap with chat fixtures in mockChatData.ts the underlying
 * FlightInfo records are compatible; we build on top of the same structure.
 */
import type {
  ExtractedFlightSearchData,
  FlightInfo,
  FlightSearchParams,
  ExtractedDateRangeFlightData,
  FlightSegmentInfo,
} from '@/types/api.helpers';
import type { MulticityChatPayloadNormalized } from '@/features/chat/utils/extractMulticityFlightSearchResults';
import type { MulticityLegTabRow } from '@/features/flights/components/MulticityLegPillTabs';
import type {
  MulticityLegSearchResultCamel,
  FlightRevalidateResponseCamel,
  ProcessedLeg,
} from '@/types/flightBackend';
import type { MulticityLegSelection } from '@/store/slices/flightBookingSlice';

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

const DEPART_DATE = '2026-06-10';
const RETURN_DATE = '2026-06-17';

// ---------------------------------------------------------------------------
// Common FlightInfo entries (reused across categories / legs)
// ---------------------------------------------------------------------------

const segmentAMS_BCN: FlightSegmentInfo = {
  departure_code: 'AMS',
  departure_city: 'Amsterdam',
  departure_airport: 'Amsterdam Airport Schiphol',
  destination_code: 'BCN',
  destination_city: 'Barcelona',
  destination_airport: 'Barcelona El Prat Airport',
  departure_time: '06:20',
  departure_date: DEPART_DATE,
  arrival_time: '08:40',
  arrival_date: DEPART_DATE,
  duration: '2h 20m',
};

const segmentBCN_AMS: FlightSegmentInfo = {
  departure_code: 'BCN',
  departure_city: 'Barcelona',
  departure_airport: 'Barcelona El Prat Airport',
  destination_code: 'AMS',
  destination_city: 'Amsterdam',
  destination_airport: 'Amsterdam Airport Schiphol',
  departure_time: '11:00',
  departure_date: RETURN_DATE,
  arrival_time: '13:20',
  arrival_date: RETURN_DATE,
  duration: '2h 20m',
};

export const mockFlightInfoCheapest: FlightInfo = {
  id: 'flt-cheap-1',
  departure_time: '06:20',
  departure_date: DEPART_DATE,
  arrival_time: '08:40',
  arrival_date: DEPART_DATE,
  origin_code: 'AMS',
  origin_city: 'Amsterdam',
  origin_airport: 'Amsterdam Airport Schiphol',
  destination_code: 'BCN',
  destination_city: 'Barcelona',
  destination_airport: 'Barcelona El Prat Airport',
  duration: '2h 20m',
  duration_minutes: 140,
  stops: 0,
  price: 92,
  currency: 'EUR',
  airline: 'Vueling',
  airline_code: 'VY',
  flight_number: 'VY8373',
  segments: [segmentAMS_BCN, segmentBCN_AMS],
};

export const mockFlightInfoFastest: FlightInfo = {
  id: 'flt-fast-1',
  departure_time: '10:15',
  departure_date: DEPART_DATE,
  arrival_time: '12:25',
  arrival_date: DEPART_DATE,
  origin_code: 'AMS',
  origin_city: 'Amsterdam',
  origin_airport: 'Amsterdam Airport Schiphol',
  destination_code: 'BCN',
  destination_city: 'Barcelona',
  destination_airport: 'Barcelona El Prat Airport',
  duration: '2h 10m',
  duration_minutes: 130,
  stops: 0,
  price: 148,
  currency: 'EUR',
  airline: 'KLM',
  airline_code: 'KL',
  flight_number: 'KL1673',
  segments: [
    {
      ...segmentAMS_BCN,
      departure_time: '10:15',
      arrival_time: '12:25',
      duration: '2h 10m',
    },
    {
      ...segmentBCN_AMS,
      departure_time: '13:30',
      arrival_time: '15:40',
      duration: '2h 10m',
    },
  ],
};

export const mockFlightInfoBestValue: FlightInfo = {
  id: 'flt-best-1',
  departure_time: '07:45',
  departure_date: DEPART_DATE,
  arrival_time: '10:00',
  arrival_date: DEPART_DATE,
  origin_code: 'AMS',
  origin_city: 'Amsterdam',
  origin_airport: 'Amsterdam Airport Schiphol',
  destination_code: 'BCN',
  destination_city: 'Barcelona',
  destination_airport: 'Barcelona El Prat Airport',
  duration: '2h 15m',
  duration_minutes: 135,
  stops: 0,
  price: 124,
  currency: 'EUR',
  airline: 'Transavia',
  airline_code: 'HV',
  flight_number: 'HV6153',
  segments: [
    {
      ...segmentAMS_BCN,
      departure_time: '07:45',
      arrival_time: '10:00',
      duration: '2h 15m',
    },
    {
      ...segmentBCN_AMS,
      departure_time: '12:00',
      arrival_time: '14:15',
      duration: '2h 15m',
    },
  ],
};

// ---------------------------------------------------------------------------
// Shared search params
// ---------------------------------------------------------------------------

export const mockSearchParams: FlightSearchParams = {
  origin: 'AMS',
  destination: 'BCN',
  departure_date: DEPART_DATE,
  return_date: RETURN_DATE,
  journey_type: 'Return',
  passengers: { adults: 2, children: 0, infants: 0 },
  origin_city: 'Amsterdam',
  destination_city: 'Barcelona',
  cabin_class: 'Economy',
};

// ---------------------------------------------------------------------------
// ExtractedFlightSearchData — single search (used by FlightSearchResultsPanel)
// ---------------------------------------------------------------------------

export const mockExtractedFlightSearchData: ExtractedFlightSearchData = {
  session_id: 'sess-flights-story-1',
  flights: [mockFlightInfoCheapest, mockFlightInfoFastest, mockFlightInfoBestValue],
  origin_location: { latitude: 52.3086, longitude: 4.7639 },
  destination_location: { latitude: 41.2971, longitude: 2.0785 },
  data: {
    search_params: mockSearchParams,
    summary: {
      total_flights: 24,
      direct_count: 8,
      price_range: { min: 92, max: 480, currency: 'EUR' },
    },
    categories: {
      cheapest: {
        label: 'Cheapest',
        flights: [mockFlightInfoCheapest],
      },
      fastest: {
        label: 'Fastest',
        flights: [mockFlightInfoFastest],
      },
      best_value: {
        label: 'Best Value',
        flights: [mockFlightInfoBestValue],
      },
    },
  },
};

// ---------------------------------------------------------------------------
// ExtractedDateRangeFlightData — multi-date variant
// ---------------------------------------------------------------------------

export const mockExtractedDateRangeData: ExtractedDateRangeFlightData = {
  searched_from: '2026-06-08',
  searched_to: '2026-06-14',
  has_more: false,
  overall_best: mockFlightInfoBestValue,
  overall: {
    cheapest: mockFlightInfoCheapest,
    fastest: mockFlightInfoFastest,
    best_value: mockFlightInfoBestValue,
  },
  dates: [
    {
      date: '2026-06-08',
      day_name: 'Mon',
      available: true,
      session_id: 'sess-dr-0',
      summary: {
        total_flights: 12,
        direct_count: 4,
        price_range: { min: 105, max: 350, currency: 'EUR' },
      },
      categories: {
        cheapest: {
          label: 'Cheapest',
          flights: [{ ...mockFlightInfoCheapest, id: 'flt-dr-cheap-0', departure_date: '2026-06-08', price: 105 }],
        },
        fastest: {
          label: 'Fastest',
          flights: [{ ...mockFlightInfoFastest, id: 'flt-dr-fast-0', departure_date: '2026-06-08', price: 162 }],
        },
        best_value: {
          label: 'Best Value',
          flights: [{ ...mockFlightInfoBestValue, id: 'flt-dr-best-0', departure_date: '2026-06-08', price: 138 }],
        },
      },
    },
    {
      date: '2026-06-10',
      day_name: 'Wed',
      available: true,
      session_id: 'sess-dr-1',
      summary: {
        total_flights: 24,
        direct_count: 8,
        price_range: { min: 92, max: 480, currency: 'EUR' },
      },
      categories: {
        cheapest: { label: 'Cheapest', flights: [mockFlightInfoCheapest] },
        fastest: { label: 'Fastest', flights: [mockFlightInfoFastest] },
        best_value: { label: 'Best Value', flights: [mockFlightInfoBestValue] },
      },
    },
    {
      date: '2026-06-12',
      day_name: 'Fri',
      available: true,
      session_id: 'sess-dr-2',
      summary: {
        total_flights: 18,
        direct_count: 6,
        price_range: { min: 99, max: 420, currency: 'EUR' },
      },
      categories: {
        cheapest: {
          label: 'Cheapest',
          flights: [{ ...mockFlightInfoCheapest, id: 'flt-dr-cheap-2', departure_date: '2026-06-12', price: 99 }],
        },
        fastest: {
          label: 'Fastest',
          flights: [{ ...mockFlightInfoFastest, id: 'flt-dr-fast-2', departure_date: '2026-06-12', price: 155 }],
        },
        best_value: {
          label: 'Best Value',
          flights: [{ ...mockFlightInfoBestValue, id: 'flt-dr-best-2', departure_date: '2026-06-12', price: 129 }],
        },
      },
    },
  ],
};

// ---------------------------------------------------------------------------
// MulticityChatPayloadNormalized — Circle / multicity search
// (MulticityRecommendationsPanel)
// ---------------------------------------------------------------------------

const multicitySearchParams: FlightSearchParams = {
  origin: 'LHR',
  destination: 'JFK',
  departure_date: '2026-07-01',
  return_date: null,
  journey_type: 'Circle',
  passengers: { adults: 1, children: 0, infants: 0 },
  cabin_class: 'Economy',
};

const mockLegFlightLHR_JFK: FlightInfo = {
  id: 'flt-mc-0-1',
  departure_time: '08:00',
  departure_date: '2026-07-01',
  arrival_time: '10:30',
  arrival_date: '2026-07-01',
  origin_code: 'LHR',
  origin_city: 'London',
  origin_airport: 'London Heathrow Airport',
  destination_code: 'JFK',
  destination_city: 'New York',
  destination_airport: 'John F. Kennedy International Airport',
  duration: '7h 30m',
  duration_minutes: 450,
  stops: 0,
  price: 320,
  currency: 'USD',
  airline: 'British Airways',
  airline_code: 'BA',
  flight_number: 'BA177',
  segments: [
    {
      departure_code: 'LHR',
      departure_city: 'London',
      departure_airport: 'London Heathrow Airport',
      destination_code: 'JFK',
      destination_city: 'New York',
      destination_airport: 'John F. Kennedy International Airport',
      departure_time: '08:00',
      departure_date: '2026-07-01',
      arrival_time: '10:30',
      arrival_date: '2026-07-01',
      duration: '7h 30m',
    },
  ],
};

const mockLegFlightJFK_CDG: FlightInfo = {
  id: 'flt-mc-1-1',
  departure_time: '14:00',
  departure_date: '2026-07-08',
  arrival_time: '04:00',
  arrival_date: '2026-07-09',
  origin_code: 'JFK',
  origin_city: 'New York',
  origin_airport: 'John F. Kennedy International Airport',
  destination_code: 'CDG',
  destination_city: 'Paris',
  destination_airport: 'Paris Charles de Gaulle Airport',
  duration: '7h 00m',
  duration_minutes: 420,
  stops: 0,
  price: 290,
  currency: 'USD',
  airline: 'Air France',
  airline_code: 'AF',
  flight_number: 'AF007',
  segments: [
    {
      departure_code: 'JFK',
      departure_city: 'New York',
      departure_airport: 'John F. Kennedy International Airport',
      destination_code: 'CDG',
      destination_city: 'Paris',
      destination_airport: 'Paris Charles de Gaulle Airport',
      departure_time: '14:00',
      departure_date: '2026-07-08',
      arrival_time: '04:00',
      arrival_date: '2026-07-09',
      duration: '7h 00m',
    },
  ],
};

const mockLegFlightCDG_LHR: FlightInfo = {
  id: 'flt-mc-2-1',
  departure_time: '11:00',
  departure_date: '2026-07-14',
  arrival_time: '11:25',
  arrival_date: '2026-07-14',
  origin_code: 'CDG',
  origin_city: 'Paris',
  origin_airport: 'Paris Charles de Gaulle Airport',
  destination_code: 'LHR',
  destination_city: 'London',
  destination_airport: 'London Heathrow Airport',
  duration: '1h 25m',
  duration_minutes: 85,
  stops: 0,
  price: 110,
  currency: 'USD',
  airline: 'British Airways',
  airline_code: 'BA',
  flight_number: 'BA308',
  segments: [
    {
      departure_code: 'CDG',
      departure_city: 'Paris',
      departure_airport: 'Paris Charles de Gaulle Airport',
      destination_code: 'LHR',
      destination_city: 'London',
      destination_airport: 'London Heathrow Airport',
      departure_time: '11:00',
      departure_date: '2026-07-14',
      arrival_time: '11:25',
      arrival_date: '2026-07-14',
      duration: '1h 25m',
    },
  ],
};

function makeLegCategories(flight: FlightInfo) {
  const bestValue = { ...flight, id: `${flight.id}-bv`, price: flight.price + 15 };
  const fastest = { ...flight, id: `${flight.id}-fa`, duration: '6h 45m', duration_minutes: 405, price: flight.price + 30 };
  return {
    cheapest: { label: 'Cheapest', flights: [flight] },
    fastest: { label: 'Fastest', flights: [fastest] },
    best_value: { label: 'Best Value', flights: [bestValue] },
  };
}

export const mockMulticityPayload: MulticityChatPayloadNormalized = {
  searchParams: multicitySearchParams,
  multicityParallel: true,
  legs: [
    {
      legIndex: 0,
      origin: 'LHR',
      destination: 'JFK',
      departureDate: '2026-07-01',
      sessionId: 'sess-mc-0',
      summary: { total_flights: 10, direct_count: 4, price_range: { min: 320, max: 650, currency: 'USD' } },
      categories: makeLegCategories(mockLegFlightLHR_JFK),
      flights: [mockLegFlightLHR_JFK],
      originLocation: { latitude: 51.477, longitude: -0.461 },
      destinationLocation: { latitude: 40.6413, longitude: -73.7781 },
    },
    {
      legIndex: 1,
      origin: 'JFK',
      destination: 'CDG',
      departureDate: '2026-07-08',
      sessionId: 'sess-mc-1',
      summary: { total_flights: 8, direct_count: 3, price_range: { min: 290, max: 580, currency: 'USD' } },
      categories: makeLegCategories(mockLegFlightJFK_CDG),
      flights: [mockLegFlightJFK_CDG],
      originLocation: { latitude: 40.6413, longitude: -73.7781 },
      destinationLocation: { latitude: 49.0097, longitude: 2.5479 },
    },
    {
      legIndex: 2,
      origin: 'CDG',
      destination: 'LHR',
      departureDate: '2026-07-14',
      sessionId: 'sess-mc-2',
      summary: { total_flights: 15, direct_count: 10, price_range: { min: 110, max: 280, currency: 'USD' } },
      categories: makeLegCategories(mockLegFlightCDG_LHR),
      flights: [mockLegFlightCDG_LHR],
      originLocation: { latitude: 49.0097, longitude: 2.5479 },
      destinationLocation: { latitude: 51.477, longitude: -0.461 },
    },
  ],
};

// ---------------------------------------------------------------------------
// MulticityLegTabRow[] — pill tabs only (no flight data needed)
// ---------------------------------------------------------------------------

export const mockLegTabRows: MulticityLegTabRow[] = [
  { legIndex: 0, origin: 'LHR', destination: 'JFK', departureDate: '2026-07-01' },
  { legIndex: 1, origin: 'JFK', destination: 'CDG', departureDate: '2026-07-08' },
  { legIndex: 2, origin: 'CDG', destination: 'LHR', departureDate: '2026-07-14' },
];

export const mockLegTabRowsMany: MulticityLegTabRow[] = [
  { legIndex: 0, origin: 'LHR', destination: 'JFK', departureDate: '2026-07-01' },
  { legIndex: 1, origin: 'JFK', destination: 'CDG', departureDate: '2026-07-08' },
  { legIndex: 2, origin: 'CDG', destination: 'DXB', departureDate: '2026-07-14' },
  { legIndex: 3, origin: 'DXB', destination: 'SIN', departureDate: '2026-07-20' },
  { legIndex: 4, origin: 'SIN', destination: 'LHR', departureDate: '2026-07-26' },
];

// ---------------------------------------------------------------------------
// MulticityLegSearchResultCamel[] — used by MulticitySelectionBottomBar
// ---------------------------------------------------------------------------

export const mockAllLegs: MulticityLegSearchResultCamel[] = [
  {
    legIndex: 0,
    origin: 'LHR',
    destination: 'JFK',
    departureDate: '2026-07-01',
    sessionId: 'sess-mc-0',
    supplier: 'TBO',
    fareItineraries: [],
  },
  {
    legIndex: 1,
    origin: 'JFK',
    destination: 'CDG',
    departureDate: '2026-07-08',
    sessionId: 'sess-mc-1',
    supplier: 'TBO',
    fareItineraries: [],
  },
  {
    legIndex: 2,
    origin: 'CDG',
    destination: 'LHR',
    departureDate: '2026-07-14',
    sessionId: 'sess-mc-2',
    supplier: 'TBO',
    fareItineraries: [],
  },
];

// Minimal revalidate response — only the fields parseFareFromRevalidateResponse reads.
function makeRevalidateResponse(amount: number, currency: string): FlightRevalidateResponseCamel {
  return {
    sessionId: `sess-reval-${amount}`,
    fareSourceCode: `fsrc-${amount}`,
    isFareAvailable: true,
    validatedFareItineraries: [
      {
        flightLegs: [],
        updatedPricing: {
          validatedFareTotals: {
            totalFare: { amount, currency },
          },
        },
      },
    ],
    errors: null,
  };
}

function makeSelectedFlightData(id: string, price: number) {
  return {
    id,
    aircraftName: 'Boeing 737',
    flightNumber: 'BA177',
    tags: [] as string[],
    passengers: 1,
    passengerCounts: { adults: 1, children: 0, infants: 0 },
    legs: [] as ProcessedLeg[],
    price,
  };
}

/** One leg selected — partially completed multicity */
export const mockSelectedLegsPartial: Record<number, MulticityLegSelection> = {
  0: {
    legIndex: 0,
    sessionId: 'sess-mc-0',
    fareSourceCode: 'fsrc-leg-0',
    selectedFlightData: makeSelectedFlightData('flt-mc-0-1', 320),
    revalidateResponse: makeRevalidateResponse(320, 'USD'),
  },
};

/** All three legs selected — ready to review & book */
export const mockSelectedLegsComplete: Record<number, MulticityLegSelection> = {
  0: {
    legIndex: 0,
    sessionId: 'sess-mc-0',
    fareSourceCode: 'fsrc-leg-0',
    selectedFlightData: makeSelectedFlightData('flt-mc-0-1', 320),
    revalidateResponse: makeRevalidateResponse(320, 'USD'),
  },
  1: {
    legIndex: 1,
    sessionId: 'sess-mc-1',
    fareSourceCode: 'fsrc-leg-1',
    selectedFlightData: makeSelectedFlightData('flt-mc-1-1', 290),
    revalidateResponse: makeRevalidateResponse(290, 'USD'),
  },
  2: {
    legIndex: 2,
    sessionId: 'sess-mc-2',
    fareSourceCode: 'fsrc-leg-2',
    selectedFlightData: makeSelectedFlightData('flt-mc-2-1', 110),
    revalidateResponse: makeRevalidateResponse(110, 'USD'),
  },
};
