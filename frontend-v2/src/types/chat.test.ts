import { describe, it, expect } from 'vitest';
import {
  isItinerarySearchResults,
  isFlightSearchResults,
  isHotelSearchResults,
  type ChatMessage,
} from './chat';

function makeMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    _id: 'msg-1',
    content: { messages: [{ text: 'test' }] },
    from: 'bot',
    type: 'message',
    contentType: 'message',
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

describe('isItinerarySearchResults', () => {
  it('returns true when type is itinerary_results and extraData is present', () => {
    const msg = makeMessage({
      type: 'itinerary_results',
      extraData: { structured_itinerary: {}, session_id: 's1' },
    });
    expect(isItinerarySearchResults(msg)).toBe(true);
  });

  it('returns false when type is itinerary_results but extraData is undefined', () => {
    const msg = makeMessage({ type: 'itinerary_results' });
    expect(isItinerarySearchResults(msg)).toBe(false);
  });

  it('returns false when type is message', () => {
    const msg = makeMessage({ type: 'message', extraData: {} });
    expect(isItinerarySearchResults(msg)).toBe(false);
  });

  it('returns false when type is flight_search_results', () => {
    const msg = makeMessage({
      type: 'flight_search_results',
      extraData: { data: {}, session_id: 's1' },
    });
    expect(isItinerarySearchResults(msg)).toBe(false);
    expect(isFlightSearchResults(msg)).toBe(true);
  });

  it('returns false when type is hotel_search_results', () => {
    const msg = makeMessage({
      type: 'hotel_search_results',
      extraData: { data: {}, session_id: 's1' },
    });
    expect(isItinerarySearchResults(msg)).toBe(false);
    expect(isHotelSearchResults(msg)).toBe(true);
  });
});
