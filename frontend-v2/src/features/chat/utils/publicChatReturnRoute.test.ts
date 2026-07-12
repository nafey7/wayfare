import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  stashPublicChatReturnTo,
  peekPublicChatReturnTo,
  consumePublicChatReturnTo,
  clearPublicChatReturnTo,
} from './publicChatReturnRoute';

const KEY = 'voya_public_chat_return_to';

describe('publicChatReturnRoute', () => {
  beforeEach(() => {
    localStorage.removeItem(KEY);
  });

  it('stash → consume returns correct path', () => {
    stashPublicChatReturnTo('/flights/recommendations');
    expect(consumePublicChatReturnTo()).toBe('/flights/recommendations');
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('stash with search → consume returns path + search', () => {
    stashPublicChatReturnTo('/hotels/search', '?q=paris');
    expect(consumePublicChatReturnTo()).toBe('/hotels/search?q=paris');
  });

  it('returns null when data is older than 24 hours', () => {
    const old = {
      path: '/flights/recommendations',
      timestamp: Date.now() - 25 * 60 * 60 * 1000,
    };
    localStorage.setItem(KEY, JSON.stringify(old));
    expect(consumePublicChatReturnTo()).toBeNull();
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('returns data when within 24 hours', () => {
    const recent = {
      path: '/itinerary',
      timestamp: Date.now() - 1000,
    };
    localStorage.setItem(KEY, JSON.stringify(recent));
    expect(consumePublicChatReturnTo()).toBe('/itinerary');
  });

  it('stash is no-op for invalid path and consume returns null', () => {
    stashPublicChatReturnTo('/admin/bookings');
    expect(localStorage.getItem(KEY)).toBeNull();
    expect(consumePublicChatReturnTo()).toBeNull();
  });

  it('consume clears the key', () => {
    stashPublicChatReturnTo('/flights/search');
    consumePublicChatReturnTo();
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('peek returns path and does not remove valid data', () => {
    stashPublicChatReturnTo('/hotels/search');
    expect(peekPublicChatReturnTo()).toBe('/hotels/search');
    expect(localStorage.getItem(KEY)).not.toBeNull();
    expect(consumePublicChatReturnTo()).toBe('/hotels/search');
  });

  it('tolerates localStorage errors on stash', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded');
    });
    expect(() => stashPublicChatReturnTo('/flights/search')).not.toThrow();
    spy.mockRestore();
  });

  it('clearPublicChatReturnTo removes the key', () => {
    stashPublicChatReturnTo('/itinerary');
    clearPublicChatReturnTo();
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('handles malformed JSON on consume', () => {
    localStorage.setItem(KEY, 'not-json');
    expect(consumePublicChatReturnTo()).toBeNull();
    expect(localStorage.getItem(KEY)).toBeNull();
  });
});
