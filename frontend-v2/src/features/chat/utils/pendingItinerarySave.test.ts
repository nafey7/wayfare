import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  stashPendingItinerarySave,
  consumePendingItinerarySave,
  clearPendingItinerarySave,
} from './pendingItinerarySave';

const KEY = 'voya_pending_itinerary_save';

describe('pendingItinerarySave', () => {
  beforeEach(() => {
    localStorage.removeItem(KEY);
  });

  it('round-trips stash → consume', () => {
    const payload = {
      structured_itinerary: { itineraryItems: [{ day: 1 }] },
      trip_meta: { destination: 'Paris' },
    };
    stashPendingItinerarySave(payload);
    const result = consumePendingItinerarySave();
    expect(result).toEqual(payload);
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('returns null when nothing is stashed', () => {
    expect(consumePendingItinerarySave()).toBeNull();
  });

  it('returns null and removes key when data is older than 24 hours', () => {
    const old = {
      data: {
        structured_itinerary: { itineraryItems: [] },
      },
      timestamp: Date.now() - 25 * 60 * 60 * 1000,
    };
    localStorage.setItem(KEY, JSON.stringify(old));
    expect(consumePendingItinerarySave()).toBeNull();
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('returns data when within 24 hours', () => {
    const recent = {
      data: {
        structured_itinerary: { itineraryItems: [{ day: 1 }] },
      },
      timestamp: Date.now() - 1000,
    };
    localStorage.setItem(KEY, JSON.stringify(recent));
    const result = consumePendingItinerarySave();
    expect(result).toEqual(recent.data);
  });

  it('clearPendingItinerarySave removes the key', () => {
    stashPendingItinerarySave({
      structured_itinerary: { itineraryItems: [] },
    });
    expect(localStorage.getItem(KEY)).not.toBeNull();
    clearPendingItinerarySave();
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('handles malformed JSON gracefully', () => {
    localStorage.setItem(KEY, 'not-json');
    expect(consumePendingItinerarySave()).toBeNull();
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('handles missing structured_itinerary', () => {
    const envelope = {
      data: { trip_meta: { destination: 'Rome' } },
      timestamp: Date.now(),
    };
    localStorage.setItem(KEY, JSON.stringify(envelope));
    expect(consumePendingItinerarySave()).toBeNull();
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('tolerates localStorage errors on stash', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded');
    });
    expect(() =>
      stashPendingItinerarySave({ structured_itinerary: {} })
    ).not.toThrow();
    spy.mockRestore();
  });
});
