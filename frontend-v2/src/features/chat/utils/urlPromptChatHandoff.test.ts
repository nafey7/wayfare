import { describe, it, expect } from 'vitest';

import { shouldSkipRedundantUrlPromptSend } from './urlPromptChatHandoff';
import type { ChatMessage } from '@/types/chat';

function userMessage(text: string): ChatMessage {
  return {
    _id: '1',
    content: { messages: [{ text }] },
    from: 'user',
    type: 'message',
    contentType: 'message',
    timestamp: new Date().toISOString(),
  };
}

describe('shouldSkipRedundantUrlPromptSend', () => {
  it('returns false when public chat is disabled', () => {
    expect(
      shouldSkipRedundantUrlPromptSend(false, [userMessage('hi')], 'hi')
    ).toBe(false);
  });

  it('returns false when public chat is on but no matching user message', () => {
    expect(shouldSkipRedundantUrlPromptSend(true, [], 'hello')).toBe(false);
    expect(
      shouldSkipRedundantUrlPromptSend(true, [userMessage('other')], 'hello')
    ).toBe(false);
  });

  it('returns true when public chat is on and a user message matches the prompt', () => {
    expect(
      shouldSkipRedundantUrlPromptSend(true, [userMessage('Paris trip')], 'Paris trip')
    ).toBe(true);
  });

  it('matches after trim', () => {
    expect(
      shouldSkipRedundantUrlPromptSend(true, [userMessage('  x  ')], 'x')
    ).toBe(true);
  });
});
