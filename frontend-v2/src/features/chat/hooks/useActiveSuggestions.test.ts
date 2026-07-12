import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import type { ChatMessage, ChatMessageType } from '@/types/chat';
import { useActiveSuggestions } from './useActiveSuggestions';

function userMsg(id: string): ChatMessage {
  return {
    _id: id,
    from: 'user',
    type: 'message',
    contentType: 'message',
    content: { messages: [{ text: 'hello' }] },
    timestamp: new Date(),
  };
}

function botMsg(
  id: string,
  options?: {
    suggestions?: Array<{ title: string; command: string }>;
    type?: ChatMessageType;
  },
): ChatMessage {
  const { suggestions, type = 'message' } = options ?? {};
  return {
    _id: id,
    from: 'bot',
    type,
    contentType: 'message',
    content: {
      messages: [{ text: 'reply' }],
      ...(suggestions ? { suggestions } : {}),
    },
    timestamp: new Date(),
  };
}

function typingMsg(id: string): ChatMessage {
  return {
    _id: id,
    from: 'bot',
    type: 'typing',
    contentType: 'message',
    content: { messages: [{ text: '' }] },
    timestamp: new Date(),
  };
}

describe('useActiveSuggestions', () => {
  it('returns suggestions from the latest bot message', () => {
    const s1 = { title: 'First', command: '/first' };
    const s2 = { title: 'Second', command: '/second' };
    const messages: ChatMessage[] = [
      botMsg('b1', { suggestions: [s1] }),
      botMsg('b2', { suggestions: [s2] }),
    ];
    const { result } = renderHook(() => useActiveSuggestions(messages));
    expect(result.current.activeSuggestions).toEqual([s2]);
  });

  it('returns empty when the last message is from the user (waiting for reply)', () => {
    const s = { title: 'Book', command: '/book' };
    const messages: ChatMessage[] = [
      botMsg('b1', { suggestions: [s] }),
      userMsg('u1'),
    ];
    const { result } = renderHook(() => useActiveSuggestions(messages));
    expect(result.current.activeSuggestions).toEqual([]);
  });

  it('returns empty when the last message is typing', () => {
    const s = { title: 'Book', command: '/book' };
    const messages: ChatMessage[] = [botMsg('b1', { suggestions: [s] }), typingMsg('t1')];
    const { result } = renderHook(() => useActiveSuggestions(messages));
    expect(result.current.activeSuggestions).toEqual([]);
  });

  it('returns empty after dismiss() for the current bot message', () => {
    const s = { title: 'Book', command: '/book' };
    const messages: ChatMessage[] = [botMsg('b1', { suggestions: [s] })];
    const { result } = renderHook(() => useActiveSuggestions(messages));
    expect(result.current.activeSuggestions).toEqual([s]);

    act(() => {
      result.current.dismiss();
    });
    expect(result.current.activeSuggestions).toEqual([]);
  });

  it('shows suggestions again when a new bot message with a different _id arrives after dismiss', () => {
    const s1 = { title: 'A', command: '/a' };
    const s2 = { title: 'B', command: '/b' };
    const messagesRef: { current: ChatMessage[] } = {
      current: [botMsg('b1', { suggestions: [s1] })],
    };
    const { result, rerender } = renderHook(() => useActiveSuggestions(messagesRef.current));

    act(() => {
      result.current.dismiss();
    });
    expect(result.current.activeSuggestions).toEqual([]);

    messagesRef.current = [botMsg('b1', { suggestions: [s1] }), botMsg('b2', { suggestions: [s2] })];
    rerender();
    expect(result.current.activeSuggestions).toEqual([s2]);
  });

  it('returns empty when the latest bot message has no suggestions (e.g. flight results)', () => {
    const messages: ChatMessage[] = [
      botMsg('b1', { type: 'flight_search_results', suggestions: undefined }),
    ];
    const { result } = renderHook(() => useActiveSuggestions(messages));
    expect(result.current.activeSuggestions).toEqual([]);
  });
});
