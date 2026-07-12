// Static mock chat data for Storybook stories — shape-matched to live contracts.
import type { ChatMessage } from '@/types/chat';
import type { FlightSegmentInfo } from '@/types/api.helpers';
import { mockExtractedHotelSearchData } from '@/features/hotels/__fixtures__/mockHotelDetailData';

const STATIC_TS = '2026-04-23T10:00:00.000Z';

const DEPART = '2026-05-12';
const RETURN = '2026-05-19';

// Flight segments (outbound + inbound) so the inline FlightSearchResultsPanel
// renders real airport codes / durations on mobile instead of N/A — same class
// of fixture-shape regression PR #852 caught for desktop. flightMapper reads
// `segments[]`, not the top-level shorthand fields.
const segOutbound = (departureTime: string, arrivalTime: string, duration: string): FlightSegmentInfo => ({
  departure_code: 'AMS',
  departure_city: 'Amsterdam',
  departure_airport: 'Amsterdam Airport Schiphol',
  destination_code: 'BCN',
  destination_city: 'Barcelona',
  destination_airport: 'Barcelona El Prat Airport',
  departure_time: departureTime,
  departure_date: DEPART,
  arrival_time: arrivalTime,
  arrival_date: DEPART,
  duration,
});

const segInbound: FlightSegmentInfo = {
  departure_code: 'BCN',
  departure_city: 'Barcelona',
  departure_airport: 'Barcelona El Prat Airport',
  destination_code: 'AMS',
  destination_city: 'Amsterdam',
  destination_airport: 'Amsterdam Airport Schiphol',
  departure_time: '11:00',
  departure_date: RETURN,
  arrival_time: '13:20',
  arrival_date: RETURN,
  duration: '2h 20m',
};

export const mockUserMessage: ChatMessage = {
  _id: 'msg-user-1',
  content: {
    messages: [{ text: 'I want to fly from Amsterdam to Barcelona next month.' }],
  },
  from: 'user',
  type: 'message',
  contentType: 'message',
  timestamp: STATIC_TS,
};

export const mockBotTextMessage: ChatMessage = {
  _id: 'msg-bot-1',
  content: {
    messages: [
      {
        text: "Welcome to Voya! 👋 Where would you like to travel?",
      },
    ],
  },
  from: 'bot',
  type: 'message',
  contentType: 'message',
  timestamp: STATIC_TS,
};

export const mockBotMarkdownMessage: ChatMessage = {
  _id: 'msg-bot-md-1',
  content: {
    messages: [
      {
        text:
          "Here are a few things I can help with:\n\n" +
          "- **Find flights** between two cities\n" +
          "- **Book hotels** with flexible dates\n" +
          "- **Plan an itinerary** for a multi-day trip\n\n" +
          "Just tell me what you're planning!",
      },
    ],
  },
  from: 'bot',
  type: 'message',
  contentType: 'message',
  timestamp: STATIC_TS,
};

export const mockTypingMessage: ChatMessage = {
  _id: 'msg-typing-1',
  content: {
    messages: [{ text: '' }],
  },
  from: 'bot',
  type: 'typing',
  contentType: 'message',
  timestamp: STATIC_TS,
  status: 10,
};

export const mockFlightResultsMessage: ChatMessage = {
  _id: 'msg-flights-1',
  content: {
    messages: [
      {
        text:
          'I found great flights from Amsterdam (AMS) to Barcelona (BCN).\n\n' +
          'Tap **View flights** to see cheapest, fastest, and best-value options.',
      },
    ],
  },
  from: 'bot',
  type: 'flight_search_results',
  contentType: 'message',
  timestamp: STATIC_TS,
  messageId: 'mid-flights-1',
  extraData: {
    session_id: 'sess-flights-1',
    data: {
      search_params: {
        origin: 'AMS',
        destination: 'BCN',
        departure_date: DEPART,
        return_date: RETURN,
        journey_type: 'Return',
        passengers: { adults: 1, children: 0, infants: 0 },
      },
      summary: {
        total_flights: 24,
        direct_count: 8,
        price_range: { min: 92, max: 480, currency: 'EUR' },
      },
      categories: {
        cheapest: {
          label: 'Cheapest',
          flights: [
            {
              id: 'flt-cheap-1',
              departure_time: '06:20',
              departure_date: DEPART,
              arrival_time: '08:40',
              arrival_date: DEPART,
              origin_code: 'AMS',
              destination_code: 'BCN',
              duration: '2h 20m',
              duration_minutes: 140,
              stops: 0,
              price: 92,
              currency: 'EUR',
              airline: 'Vueling',
              airline_code: 'VY',
              segments: [segOutbound('06:20', '08:40', '2h 20m'), segInbound],
            },
          ],
        },
        fastest: {
          label: 'Fastest',
          flights: [
            {
              id: 'flt-fast-1',
              departure_time: '10:15',
              departure_date: DEPART,
              arrival_time: '12:25',
              arrival_date: DEPART,
              origin_code: 'AMS',
              destination_code: 'BCN',
              duration: '2h 10m',
              duration_minutes: 130,
              stops: 0,
              price: 148,
              currency: 'EUR',
              airline: 'KLM',
              airline_code: 'KL',
              segments: [segOutbound('10:15', '12:25', '2h 10m'), segInbound],
            },
          ],
        },
        best_value: {
          label: 'Best Value',
          flights: [
            {
              id: 'flt-best-1',
              departure_time: '07:45',
              departure_date: DEPART,
              arrival_time: '10:00',
              arrival_date: DEPART,
              origin_code: 'AMS',
              destination_code: 'BCN',
              duration: '2h 15m',
              duration_minutes: 135,
              stops: 0,
              price: 124,
              currency: 'EUR',
              airline: 'Transavia',
              airline_code: 'HV',
              segments: [segOutbound('07:45', '10:00', '2h 15m'), segInbound],
            },
          ],
        },
      },
    },
  },
};

export const mockHotelResultsMessage: ChatMessage = {
  _id: 'msg-hotels-1',
  content: {
    messages: [
      {
        text:
          'I found hotels in Barcelona for your dates.\n\n' +
          'Tap **View hotels** to compare best-value, cheapest, and highest-rated options.',
      },
    ],
  },
  from: 'bot',
  type: 'hotel_search_results',
  contentType: 'message',
  timestamp: STATIC_TS,
  messageId: 'mid-hotels-1',
  // Reuse the populated hotel fixture so the inline HotelSearchResultsPanel
  // renders real hotel cards on mobile (instead of an empty-state) — same
  // fixture-shape rule as the flight fixture above.
  extraData: {
    session_id: 'sess-hotels-1',
    data: mockExtractedHotelSearchData.data,
  },
};

export const mockItineraryResultsMessage: ChatMessage = {
  _id: 'msg-itin-1',
  content: {
    messages: [
      { text: "Here's your 5-day itinerary for Barcelona! Tap **View itinerary** for the full plan." },
    ],
  },
  from: 'bot',
  type: 'itinerary_results',
  contentType: 'message',
  timestamp: STATIC_TS,
  messageId: 'mid-itin-1',
  extraData: {
    session_id: 'sess-itin-1',
    destination: 'Barcelona',
    departure_date: '2026-05-12',
    return_date: '2026-05-17',
    adults: 2,
    structured_itinerary: {
      itineraryItems: [
        { day: 1, title: 'Arrival & Gothic Quarter' },
        { day: 2, title: 'Sagrada Família & Gaudí highlights' },
        { day: 3, title: 'Beach day at Barceloneta' },
      ],
    },
  },
};

// Representative conversation for the ChatPanel story — order is the visible transcript.
export const mockConversation: ChatMessage[] = [
  mockBotTextMessage,
  mockUserMessage,
  {
    ...mockBotTextMessage,
    _id: 'msg-bot-2',
    content: {
      messages: [
        { text: 'Let me search flights from Amsterdam to Barcelona for you…' },
      ],
    },
  },
  mockFlightResultsMessage,
  {
    ...mockUserMessage,
    _id: 'msg-user-2',
    content: { messages: [{ text: 'Great, now find me a hotel for those dates.' }] },
  },
  mockHotelResultsMessage,
  {
    ...mockUserMessage,
    _id: 'msg-user-3',
    content: { messages: [{ text: 'Can you plan a full 5-day itinerary?' }] },
  },
  mockItineraryResultsMessage,
];
