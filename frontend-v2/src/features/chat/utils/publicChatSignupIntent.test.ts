import { describe, it, expect, beforeEach, afterEach } from 'vitest';

import type { ChatMessage } from '@/types/chat';

import {
  clearPublicChatPendingCompleteRegistration,
  hasCompleteRegistrationPublicChatHandoffSignals,
  isPublicChatPendingCompleteRegistration,
  setPublicChatPendingCompleteRegistration,
} from './publicChatSignupIntent';

/** Shape must satisfy {@link peekGuestChatTranscript} validation in publicChatGuestTranscript. */
const minimalGuestTranscriptMessage: ChatMessage = {
  _id: '1',
  from: 'user',
  type: 'message',
  contentType: 'message',
  content: { messages: [{ text: 'hello' }] },
  timestamp: new Date().toISOString(),
};

describe('publicChatSignupIntent', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('sets and reads pending complete-registration intent', () => {
    expect(isPublicChatPendingCompleteRegistration()).toBe(false);
    setPublicChatPendingCompleteRegistration();
    expect(isPublicChatPendingCompleteRegistration()).toBe(true);
    clearPublicChatPendingCompleteRegistration();
    expect(isPublicChatPendingCompleteRegistration()).toBe(false);
  });

  it('hasCompleteRegistrationPublicChatHandoffSignals is true when intent is set', () => {
    setPublicChatPendingCompleteRegistration();
    expect(hasCompleteRegistrationPublicChatHandoffSignals()).toBe(true);
  });

  it('hasCompleteRegistrationPublicChatHandoffSignals is true when /public/chat message flag is set', () => {
    localStorage.setItem('voya_public_chat_route_user_messaged_v1', '1');
    expect(hasCompleteRegistrationPublicChatHandoffSignals()).toBe(true);
  });

  it('hasCompleteRegistrationPublicChatHandoffSignals is true when guest transcript exists', () => {
    const sid = '00000000-0000-4000-8000-000000000001';
    localStorage.setItem('voya_public_chat_session_id', sid);
    localStorage.setItem(
      `voya_public_chat_guest_transcript_v1:${sid}`,
      JSON.stringify([minimalGuestTranscriptMessage])
    );
    expect(hasCompleteRegistrationPublicChatHandoffSignals()).toBe(true);
  });

  it('hasCompleteRegistrationPublicChatHandoffSignals is false without intent or transcript', () => {
    expect(hasCompleteRegistrationPublicChatHandoffSignals()).toBe(false);
  });
});
