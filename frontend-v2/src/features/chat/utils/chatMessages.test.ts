import { describe, it, expect } from 'vitest';
import { rebuildHistoryMessages, type RawHistoryMessage } from './chatMessages';

describe('rebuildHistoryMessages', () => {
  it('returns an empty array for empty input', () => {
    expect(rebuildHistoryMessages([])).toEqual([]);
  });

  it('marks bot rich-result messages with _isFromHistory: true', () => {
    const raw: RawHistoryMessage[] = [
      {
        sender: 'assistant',
        message: 'Flights LHR–JFK',
        timestamp: '2026-01-01T00:00:00Z',
        type: 'flight_search_results',
        extra_data: {
          data: { search_params: { origin: 'LHR', destination: 'JFK' } },
          session_id: 'sess-1',
        },
      },
    ];
    const result = rebuildHistoryMessages(raw);
    expect(result).toHaveLength(1);
    expect(result[0]!.from).toBe('bot');
    expect(result[0]!.type).toBe('flight_search_results');
    expect(result[0]!.extraData?._isFromHistory).toBe(true);
    // Original extra_data fields preserved
    expect(result[0]!.extraData?.session_id).toBe('sess-1');
  });

  it('preserves existing extra_data fields without mutating the source object', () => {
    const original: Record<string, unknown> = {
      data: { foo: 'bar' },
      session_id: 'sess-2',
    };
    const raw: RawHistoryMessage[] = [
      {
        sender: 'bot',
        message: 'Hotels Paris',
        type: 'hotel_search_results',
        extra_data: original,
      },
    ];
    const result = rebuildHistoryMessages(raw);
    // Source extra_data should NOT gain the flag (immutability)
    expect(original).not.toHaveProperty('_isFromHistory');
    expect(result[0]!.extraData?._isFromHistory).toBe(true);
    expect(result[0]!.extraData?.data).toEqual({ foo: 'bar' });
  });

  it('leaves extraData undefined when no extra_data was present', () => {
    const raw: RawHistoryMessage[] = [
      {
        sender: 'bot',
        message: 'Hi there',
        type: 'message',
      },
    ];
    const result = rebuildHistoryMessages(raw);
    expect(result[0]!.extraData).toBeUndefined();
  });

  it('routes "user" sender to a user message (no _isFromHistory flag added)', () => {
    const raw: RawHistoryMessage[] = [
      {
        sender: 'user',
        message: 'find flights to JFK',
        timestamp: '2026-01-01T00:00:00Z',
      },
    ];
    const result = rebuildHistoryMessages(raw);
    expect(result[0]!.from).toBe('user');
    // createUserMessage does not accept extraData; flag is irrelevant for user messages
    expect(result[0]!.extraData).toBeUndefined();
  });

  it('preserves the original timestamp from the backend payload', () => {
    const raw: RawHistoryMessage[] = [
      {
        sender: 'bot',
        message: 'reply',
        timestamp: '2025-12-25T12:34:56.789Z',
        type: 'message',
      },
    ];
    const result = rebuildHistoryMessages(raw);
    expect(result[0]!.timestamp).toBe('2025-12-25T12:34:56.789Z');
  });

  it('handles unknown bot type by falling back to "message"', () => {
    const raw: RawHistoryMessage[] = [
      {
        sender: 'bot',
        message: 'reply',
        type: 'mystery_type',
      },
    ];
    const result = rebuildHistoryMessages(raw);
    expect(result[0]!.type).toBe('message');
  });

  it('rebuilds a mixed user/bot transcript preserving order', () => {
    const raw: RawHistoryMessage[] = [
      { sender: 'user', message: 'flights LHR-JFK' },
      {
        sender: 'bot',
        message: 'I found 3 flights',
        type: 'flight_search_results',
        extra_data: { data: {}, session_id: 'sess' },
      },
      { sender: 'user', message: 'book option 1' },
    ];
    const result = rebuildHistoryMessages(raw);
    expect(result.map((m) => m.from)).toEqual(['user', 'bot', 'user']);
    expect(result[1]!.extraData?._isFromHistory).toBe(true);
  });
});
