import { describe, it, expect, vi } from 'vitest';
import type { FlightInfo } from '@/types/api.helpers';
import type { ChatResponse } from '@/types/chat';
import {
  lastRichNavigationPayload,
  navigateAuthenticatedChatRichResultIfApplicable,
} from './navigateAuthenticatedChatRichResult';
import { ROUTES } from '@/features/routing';
import { store } from '@/store';

const minimalFlight = (id: string): FlightInfo =>
  ({
    id,
    departure_time: '10:00',
    departure_date: '2026-04-01',
    arrival_time: '12:00',
    arrival_date: '2026-04-01',
    origin_code: 'LHR',
    destination_code: 'JFK',
    duration: '2h',
    duration_minutes: 120,
    stops: 0,
    price: 100,
    currency: 'USD',
    airline: 'BA',
    airline_code: 'BA',
  }) as FlightInfo;

const flightResponse: ChatResponse = {
  message: 'Here are flights',
  chat_id: 'c1',
  intent_name: 'search',
  confidence: 1,
  type: 'flight_search_results',
  data: {
    data: {
      search_params: {
        origin: 'LHR',
        destination: 'JFK',
        departure_date: '2026-06-01',
        return_date: null,
        journey_type: 'OneWay',
        passengers: { adults: 1, children: 0, infants: 0 },
      },
      summary: {
        total_flights: 3,
        direct_count: 1,
        price_range: { min: 100, max: 500, currency: 'USD' },
      },
      categories: {
        cheapest: { label: 'Cheapest', flights: [minimalFlight('c')] },
        fastest: { label: 'Fastest', flights: [minimalFlight('f')] },
        best_value: { label: 'Best Value', flights: [minimalFlight('b')] },
      },
    },
    session_id: 'sess',
  },
};

const hotelResponse: ChatResponse = {
  message: 'Here are hotels',
  chat_id: 'c1',
  intent_name: 'search',
  confidence: 1,
  type: 'hotel_search_results',
  data: {
    data: {
      search_params: {
        city: 'Paris',
        check_in: '2026-06-01',
        check_out: '2026-06-05',
        rooms: [{ adults: 2, children: 0, children_ages: [] }],
      },
      summary: { total_hotels: 2, price_range: { min: 80, max: 300, currency: 'EUR' } },
      categories: {
        cheapest: { label: 'Cheapest', hotels: [{ hotel_code: 'h1', hotel_name: 'Budget', star_rating: 3, price: 80, currency: 'EUR' }] },
      },
    },
    session_id: 'sess-h',
  },
};

const itineraryResponse: ChatResponse = {
  message: 'Here is your itinerary',
  chat_id: 'c1',
  intent_name: 'itinerary',
  confidence: 1,
  type: 'itinerary_results',
  data: {
    destination: 'Rome',
    structured_itinerary: { itineraryItems: [{ day: 1, title: 'Arrival' }] },
  },
};

describe('lastRichNavigationPayload', () => {
  it('returns root type when no multi-item chain', () => {
    const response: ChatResponse = {
      message: 'm',
      chat_id: 'c1',
      intent_name: 'x',
      confidence: 1,
      type: 'hotel_search_results',
      data: { data: { search_params: {} } },
    };
    const rich = lastRichNavigationPayload(response);
    expect(rich?.type).toBe('hotel_search_results');
  });

  it('returns last rich type in chain', () => {
    const response: ChatResponse = {
      message: 'm',
      chat_id: 'c1',
      intent_name: 'x',
      confidence: 1,
      type: 'message',
      data: {
        chain_responses: [
          { type: 'hand_back', message: 'x' },
          { type: 'flight_search_results', message: 'a', session_id: 's1' },
          { type: 'hotel_search_results', message: 'b', data: { search_params: {} } },
        ],
      },
    };
    const rich = lastRichNavigationPayload(response);
    expect(rich?.type).toBe('hotel_search_results');
  });

  it('returns null for plain message type', () => {
    const response: ChatResponse = {
      message: 'hello',
      chat_id: 'c1',
      intent_name: 'x',
      confidence: 1,
      type: 'message',
      data: {},
    };
    expect(lastRichNavigationPayload(response)).toBeNull();
  });
});

describe('navigateAuthenticatedChatRichResultIfApplicable', () => {
  it('no-ops when pathname is not /chat or /public/chat', () => {
    const navigate = vi.fn();
    navigateAuthenticatedChatRichResultIfApplicable(
      store.dispatch,
      navigate,
      ROUTES.HOME,
      true,
      flightResponse
    );
    expect(navigate).not.toHaveBeenCalled();
  });

  it('no-ops on /public/chat when authenticated (handled by PublicRoute redirect)', () => {
    const navigate = vi.fn();
    navigateAuthenticatedChatRichResultIfApplicable(
      store.dispatch,
      navigate,
      ROUTES.PUBLIC_CHAT,
      true,
      flightResponse
    );
    expect(navigate).not.toHaveBeenCalled();
  });

  it('no-ops on /chat when unauthenticated', () => {
    const navigate = vi.fn();
    navigateAuthenticatedChatRichResultIfApplicable(
      store.dispatch,
      navigate,
      ROUTES.CHAT,
      false,
      flightResponse
    );
    expect(navigate).not.toHaveBeenCalled();
  });

  it('no-ops on content sub-routes (avoids re-navigation)', () => {
    const navigate = vi.fn();
    navigateAuthenticatedChatRichResultIfApplicable(
      store.dispatch,
      navigate,
      '/public/chat/flights/search',
      false,
      flightResponse
    );
    expect(navigate).not.toHaveBeenCalled();
  });

  it('navigates to /flights/search on /chat (authenticated, flight_search_results)', () => {
    const navigate = vi.fn();
    navigateAuthenticatedChatRichResultIfApplicable(
      store.dispatch,
      navigate,
      ROUTES.CHAT,
      true,
      flightResponse
    );
    expect(navigate).toHaveBeenCalledWith(
      ROUTES.FLIGHTS_SEARCH,
      expect.objectContaining({ state: expect.objectContaining({ fromChat: true }) })
    );
  });

  it('navigates to /public/chat/flights/search on /public/chat (guest, flight_search_results)', () => {
    const navigate = vi.fn();
    navigateAuthenticatedChatRichResultIfApplicable(
      store.dispatch,
      navigate,
      ROUTES.PUBLIC_CHAT,
      false,
      flightResponse
    );
    expect(navigate).toHaveBeenCalledWith(
      ROUTES.PUBLIC_CHAT_FLIGHTS_SEARCH,
      expect.objectContaining({ state: expect.objectContaining({ fromChat: true }) })
    );
  });

  it('navigates to /public/chat/hotels/search on /public/chat (guest, hotel_search_results)', () => {
    const navigate = vi.fn();
    navigateAuthenticatedChatRichResultIfApplicable(
      store.dispatch,
      navigate,
      ROUTES.PUBLIC_CHAT,
      false,
      hotelResponse
    );
    expect(navigate).toHaveBeenCalledWith(
      ROUTES.PUBLIC_CHAT_HOTELS_SEARCH,
      expect.objectContaining({ state: expect.objectContaining({ fromChat: true }) })
    );
  });

  it('navigates to /hotels/search on /chat (authenticated, hotel_search_results)', () => {
    const navigate = vi.fn();
    navigateAuthenticatedChatRichResultIfApplicable(
      store.dispatch,
      navigate,
      ROUTES.CHAT,
      true,
      hotelResponse
    );
    expect(navigate).toHaveBeenCalledWith(
      ROUTES.HOTELS_SEARCH,
      expect.objectContaining({ state: expect.objectContaining({ fromChat: true }) })
    );
  });

  it('navigates to /public/chat/itinerary on /public/chat (guest, itinerary_results)', () => {
    const navigate = vi.fn();
    navigateAuthenticatedChatRichResultIfApplicable(
      store.dispatch,
      navigate,
      ROUTES.PUBLIC_CHAT,
      false,
      itineraryResponse
    );
    expect(navigate).toHaveBeenCalled();
    const [path] = navigate.mock.calls[0]!;
    expect(path).toContain('/public/chat/itinerary');
  });

  it('navigates to /itinerary on /chat (authenticated, itinerary_results)', () => {
    const navigate = vi.fn();
    navigateAuthenticatedChatRichResultIfApplicable(
      store.dispatch,
      navigate,
      ROUTES.CHAT,
      true,
      itineraryResponse
    );
    expect(navigate).toHaveBeenCalled();
    const [path] = navigate.mock.calls[0]!;
    expect(path).toContain('/itinerary');
    expect(path).not.toContain('/public');
  });

  it('no-ops for non-rich response type', () => {
    const navigate = vi.fn();
    const plainResponse: ChatResponse = {
      message: 'hello',
      chat_id: 'c1',
      intent_name: 'x',
      confidence: 1,
      type: 'message',
      data: {},
    };
    navigateAuthenticatedChatRichResultIfApplicable(
      store.dispatch,
      navigate,
      ROUTES.CHAT,
      true,
      plainResponse
    );
    expect(navigate).not.toHaveBeenCalled();
  });
});
