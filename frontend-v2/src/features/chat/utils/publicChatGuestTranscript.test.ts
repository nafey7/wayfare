import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { ChatMessage } from '@/types/chat';

import {
  saveGuestChatTranscript,
  peekGuestChatTranscript,
  clearGuestChatTranscriptForSession,
  clearGuestChatTranscript,
} from './publicChatGuestTranscript';

describe('publicChatGuestTranscript', () => {
  let store: Record<string, string>;

  beforeEach(() => {
    store = {};
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => {
        store[k] = v;
      },
      removeItem: (k: string) => {
        delete store[k];
      },
      clear: () => {
        store = {};
      },
      length: 0,
      key: () => null,
    });
  });

  const sampleMessages: ChatMessage[] = [
    {
      _id: 'u1',
      from: 'user',
      type: 'message',
      contentType: 'message',
      content: { messages: [{ text: 'hello' }] },
      timestamp: new Date().toISOString(),
    },
  ];

  it('peek does not remove stored transcript', () => {
    saveGuestChatTranscript(sampleMessages, 'sess-a');
    expect(peekGuestChatTranscript('sess-a')).toEqual(sampleMessages);
    expect(peekGuestChatTranscript('sess-a')).toEqual(sampleMessages);
  });

  it('clearGuestChatTranscriptForSession removes one session', () => {
    saveGuestChatTranscript(sampleMessages, 'sess-a');
    saveGuestChatTranscript(sampleMessages, 'sess-b');
    clearGuestChatTranscriptForSession('sess-a');
    expect(peekGuestChatTranscript('sess-a')).toBeNull();
    expect(peekGuestChatTranscript('sess-b')).toEqual(sampleMessages);
  });

  it('saveGuestChatTranscript persists at most the last 30 messages', () => {
    const many: ChatMessage[] = Array.from({ length: 31 }, (_, i) => ({
      _id: `id-${i}`,
      from: 'user' as const,
      type: 'message' as const,
      contentType: 'message' as const,
      content: { messages: [{ text: `t${i}` }] },
      timestamp: new Date().toISOString(),
    }));
    saveGuestChatTranscript(many, 'sess-cap');
    const raw = store['voya_public_chat_guest_transcript_v1:sess-cap'];
    const parsed = JSON.parse(raw!) as ChatMessage[];
    expect(parsed).toHaveLength(30);
    expect(parsed[0]!._id).toBe('id-1');
    expect(parsed[29]!._id).toBe('id-30');
  });

  it('clearGuestChatTranscript clears current session from publicChatSession', async () => {
    const { getPublicChatSessionId, setPublicChatSessionId } = await import('./publicChatSession');
    setPublicChatSessionId('sess-clear');
    saveGuestChatTranscript(sampleMessages, 'sess-clear');
    clearGuestChatTranscript();
    expect(peekGuestChatTranscript('sess-clear')).toBeNull();
    expect(getPublicChatSessionId()).toBe('sess-clear');
  });
});
