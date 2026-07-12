import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { FlightInfo } from '@/types/api.helpers';
import type { ChatMessage, ChatResponse } from '@/types/chat';
import { store } from '@/store';
import { setChatOpen, setPlacesSessionToken } from '@/store/slices/uiSlice';
import { ROUTES } from '@/features/routing';
import * as gtm from '@/utils/gtm';
import { applySuccessfulChatResponse, type CreateBotMessageFn } from './applySuccessfulChatResponse';

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

const categoriesWithOneEach = {
  cheapest: { label: 'Cheapest', flights: [minimalFlight('c')] },
  fastest: { label: 'Fastest', flights: [minimalFlight('f')] },
  best_value: { label: 'Best Value', flights: [minimalFlight('b')] },
};

const flightSearchPayload = {
  data: {
    search_params: {
      origin: 'LHR',
      destination: 'JFK',
      departure_date: '2026-06-01',
      return_date: null,
      journey_type: 'OneWay' as const,
      passengers: { adults: 1, children: 0, infants: 0 },
    },
    summary: {
      total_flights: 3,
      direct_count: 1,
      price_range: { min: 100, max: 500, currency: 'USD' },
    },
    categories: categoriesWithOneEach,
  },
  session_id: 'sess-flight-1',
};

const createBotMessage: CreateBotMessageFn = (text, messageId, type, extraData) => ({
  _id: `bot-${messageId ?? 'm'}`,
  content: { messages: [{ text }] },
  from: 'bot',
  type: (type as ChatMessage['type']) || 'message',
  contentType: 'message',
  timestamp: new Date().toISOString(),
  messageId,
  extraData,
});

describe('applySuccessfulChatResponse', () => {
  beforeEach(() => {
    store.dispatch(setChatOpen(true));
  });

  it('navigates to flight search on /chat when authenticated (flight_search_results)', () => {
    const navigate = vi.fn();
    const dispatch = vi.fn();

    const response: ChatResponse = {
      message: 'Here are flights',
      chat_id: 'chat-1',
      intent_name: 'search',
      confidence: 1,
      type: 'flight_search_results',
      data: flightSearchPayload,
    };

    applySuccessfulChatResponse(
      {
        dispatch: dispatch as unknown as import('@/store').AppDispatch,
        navigate,
        pathname: ROUTES.CHAT,
        chatId: null,
        isAuthenticated: true,
        getChatPanelOpen: () => true,
        getMessages: () => [],
        playSound: vi.fn(),
        setIsTyping: vi.fn(),
        createBotMessage,
        allowRichResultAutoNavigation: true,
      },
      response,
      'user text',
      { persistGuestChatId: false }
    );

    expect(navigate).toHaveBeenCalled();
    const [path] = navigate.mock.calls[0]!;
    expect(path).toContain('/flights/search');
    expect(dispatch).toHaveBeenCalled();
  });

  it('auto-navigates to public flight search on /public/chat (guest)', () => {
    const navigate = vi.fn();
    const dispatch = vi.fn();

    const response: ChatResponse = {
      message: 'Here are flights',
      chat_id: 'chat-1',
      intent_name: 'search',
      confidence: 1,
      type: 'flight_search_results',
      data: flightSearchPayload,
    };

    applySuccessfulChatResponse(
      {
        dispatch: dispatch as unknown as import('@/store').AppDispatch,
        navigate,
        pathname: ROUTES.PUBLIC_CHAT,
        chatId: null,
        isAuthenticated: false,
        getChatPanelOpen: () => true,
        getMessages: () => [],
        playSound: vi.fn(),
        setIsTyping: vi.fn(),
        createBotMessage,
        allowRichResultAutoNavigation: true,
      },
      response,
      'user text',
      { persistGuestChatId: true }
    );

    expect(navigate).toHaveBeenCalled();
    const [path] = navigate.mock.calls[0]!;
    expect(path).toBe(ROUTES.PUBLIC_CHAT_FLIGHTS_SEARCH);
  });

  describe('when allowRichResultAutoNavigation is false', () => {
    it('does not auto-navigate for flight_search_results', () => {
      const navigate = vi.fn();
      const dispatch = vi.fn();

      const response: ChatResponse = {
        message: 'Here are flights',
        chat_id: 'chat-1',
        intent_name: 'search',
        confidence: 1,
        type: 'flight_search_results',
        data: flightSearchPayload,
      };

      applySuccessfulChatResponse(
        {
          dispatch: dispatch as unknown as import('@/store').AppDispatch,
          navigate,
          pathname: ROUTES.CHAT,
          chatId: null,
          isAuthenticated: true,
          getChatPanelOpen: () => true,
          getMessages: () => [],
          playSound: vi.fn(),
          setIsTyping: vi.fn(),
          createBotMessage,
          allowRichResultAutoNavigation: false,
        },
        response,
        'user text',
        { persistGuestChatId: false }
      );

      expect(navigate).not.toHaveBeenCalled();
    });

    it('does not auto-navigate for hotel_search_results', () => {
      const navigate = vi.fn();
      const dispatch = vi.fn();

      const hotelPayload = {
        data: {
          search_params: {
            destination_city: 'Paris',
            check_in_date: '2026-07-01',
            check_out_date: '2026-07-07',
            rooms: 1,
            adults: 2,
            children: 0,
          },
          summary: { total_found: 5 },
          categories: {
            best_value: { hotels: [] },
            cheapest: { hotels: [] },
            highest_rated: { hotels: [] },
          },
        },
        session_id: 'sess-hotel-1',
      };

      const response: ChatResponse = {
        message: 'Here are hotels',
        chat_id: 'chat-1',
        intent_name: 'search',
        confidence: 1,
        type: 'hotel_search_results',
        data: hotelPayload,
      };

      applySuccessfulChatResponse(
        {
          dispatch: dispatch as unknown as import('@/store').AppDispatch,
          navigate,
          pathname: ROUTES.CHAT,
          chatId: null,
          isAuthenticated: true,
          getChatPanelOpen: () => true,
          getMessages: () => [],
          playSound: vi.fn(),
          setIsTyping: vi.fn(),
          createBotMessage,
          allowRichResultAutoNavigation: false,
        },
        response,
        'user text',
        { persistGuestChatId: false }
      );

      expect(navigate).not.toHaveBeenCalled();
    });

    it('does not auto-navigate for itinerary_results', () => {
      const navigate = vi.fn();
      const dispatch = vi.fn();

      const response: ChatResponse = {
        message: "Here's your itinerary",
        chat_id: 'chat-1',
        intent_name: 'itinerary',
        confidence: 1,
        type: 'itinerary_results',
        data: { destination: 'Rome', structured_itinerary: {} },
      };

      applySuccessfulChatResponse(
        {
          dispatch: dispatch as unknown as import('@/store').AppDispatch,
          navigate,
          pathname: ROUTES.CHAT,
          chatId: null,
          isAuthenticated: true,
          getChatPanelOpen: () => true,
          getMessages: () => [],
          playSound: vi.fn(),
          setIsTyping: vi.fn(),
          createBotMessage,
          allowRichResultAutoNavigation: false,
        },
        response,
        'user text',
        { persistGuestChatId: false }
      );

      expect(navigate).not.toHaveBeenCalled();
    });
  });

  it('dispatches setPlacesSessionToken when places_session_token is present', () => {
    const navigate = vi.fn();
    const dispatch = vi.fn();

    const response: ChatResponse = {
      message: 'ok',
      chat_id: 'chat-1',
      intent_name: 'itinerary',
      confidence: 1,
      type: 'message',
      places_session_token: 'guest-places-jwt',
    };

    applySuccessfulChatResponse(
      {
        dispatch: dispatch as unknown as import('@/store').AppDispatch,
        navigate,
        pathname: ROUTES.PUBLIC_CHAT,
        chatId: null,
        isAuthenticated: false,
        getChatPanelOpen: () => true,
        getMessages: () => [],
        playSound: vi.fn(),
        setIsTyping: vi.fn(),
        createBotMessage,
      },
      response,
      'user text',
      { persistGuestChatId: false }
    );

    expect(dispatch).toHaveBeenCalledWith(setPlacesSessionToken('guest-places-jwt'));
  });

  describe('user_message_index in chat_message_sent event', () => {
    it('reports 1-based count of user messages from getMessages', () => {
      const trackEventSpy = vi.spyOn(gtm, 'trackEvent');
      const navigate = vi.fn();
      const dispatch = vi.fn();

      const makeMessage = (id: string, from: 'user' | 'bot'): ChatMessage => ({
        _id: id,
        content: { messages: [{ text: 'hi' }] },
        from,
        type: 'message',
        contentType: 'message',
        timestamp: new Date().toISOString(),
      });

      // Simulate 3 messages in store: user, bot, user — index should be 2
      const messages: ChatMessage[] = [
        makeMessage('u1', 'user'),
        makeMessage('b1', 'bot'),
        makeMessage('u2', 'user'),
      ];

      const response: ChatResponse = {
        message: 'Hello',
        chat_id: 'chat-1',
        intent_name: 'greeting',
        confidence: 1,
        type: 'message',
      };

      applySuccessfulChatResponse(
        {
          dispatch: dispatch as unknown as import('@/store').AppDispatch,
          navigate,
          pathname: ROUTES.CHAT,
          chatId: 'chat-1',
          isAuthenticated: true,
          getChatPanelOpen: () => true,
          getMessages: () => messages,
          playSound: vi.fn(),
          setIsTyping: vi.fn(),
          createBotMessage,
        },
        response,
        'hello',
        { persistGuestChatId: false }
      );

      const call = trackEventSpy.mock.calls.find(([name]) => name === 'chat_message_sent');
      expect(call).toBeDefined();
      expect(call![1]).toMatchObject({ user_message_index: 2 });

      trackEventSpy.mockRestore();
    });

    it('reports user_message_index of 1 for the first message', () => {
      const trackEventSpy = vi.spyOn(gtm, 'trackEvent');
      const navigate = vi.fn();
      const dispatch = vi.fn();

      const makeMessage = (id: string, from: 'user' | 'bot'): ChatMessage => ({
        _id: id,
        content: { messages: [{ text: 'hi' }] },
        from,
        type: 'message',
        contentType: 'message',
        timestamp: new Date().toISOString(),
      });

      const response: ChatResponse = {
        message: 'Welcome!',
        chat_id: 'new-chat',
        intent_name: 'greeting',
        confidence: 1,
        type: 'message',
      };

      applySuccessfulChatResponse(
        {
          dispatch: dispatch as unknown as import('@/store').AppDispatch,
          navigate,
          pathname: ROUTES.CHAT,
          chatId: null,
          isAuthenticated: false,
          getChatPanelOpen: () => true,
          getMessages: () => [makeMessage('u1', 'user')],
          playSound: vi.fn(),
          setIsTyping: vi.fn(),
          createBotMessage,
        },
        response,
        'hi',
        { persistGuestChatId: true }
      );

      const call = trackEventSpy.mock.calls.find(([name]) => name === 'chat_message_sent');
      expect(call).toBeDefined();
      expect(call![1]).toMatchObject({ user_message_index: 1 });

      trackEventSpy.mockRestore();
    });
  });
});
