import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  addGuestItinerary,
  getGuestItineraries,
  removeGuestItinerary,
  clearGuestItineraries,
} from './guestItineraries';

const KEY = 'voya_guest_itineraries';
const ITINERARY = { itineraryItems: [{ day: 1, activities: ['Tour'] }] };
const ITINERARY_B = { itineraryItems: [{ day: 2, activities: ['Museum'] }] };

beforeEach(() => {
  localStorage.removeItem(KEY);
});

describe('getGuestItineraries', () => {
  it('returns [] when nothing is stored', () => {
    expect(getGuestItineraries()).toEqual([]);
  });

  it('returns [] for malformed JSON', () => {
    localStorage.setItem(KEY, 'not-json');
    expect(getGuestItineraries()).toEqual([]);
  });

  it('returns [] when envelope lacks entries array', () => {
    localStorage.setItem(KEY, JSON.stringify({ entries: 'bad' }));
    expect(getGuestItineraries()).toEqual([]);
  });

  it('filters out entries older than 30 days (TTL eviction)', () => {
    const old = Date.now() - 31 * 24 * 60 * 60 * 1000;
    localStorage.setItem(
      KEY,
      JSON.stringify({
        entries: [{ structuredItinerary: ITINERARY, createdAt: old }],
      }),
    );
    expect(getGuestItineraries()).toEqual([]);
  });

  it('keeps entries within 30 days', () => {
    const recent = Date.now() - 1000;
    localStorage.setItem(
      KEY,
      JSON.stringify({
        entries: [{ structuredItinerary: ITINERARY, createdAt: recent }],
      }),
    );
    expect(getGuestItineraries()).toHaveLength(1);
  });
});

describe('addGuestItinerary', () => {
  it('stores a new entry', () => {
    addGuestItinerary({ structuredItinerary: ITINERARY });
    expect(getGuestItineraries()).toHaveLength(1);
    expect(getGuestItineraries()[0]?.structuredItinerary).toEqual(ITINERARY);
  });

  it('dedupes by savedItineraryId — replaces existing entry', () => {
    addGuestItinerary({ structuredItinerary: ITINERARY, savedItineraryId: 'abc' });
    addGuestItinerary({ structuredItinerary: ITINERARY_B, savedItineraryId: 'abc' });
    const entries = getGuestItineraries();
    expect(entries).toHaveLength(1);
    expect(entries[0]?.structuredItinerary).toEqual(ITINERARY_B);
  });

  it('does not dedupe by savedItineraryId when ids differ', () => {
    addGuestItinerary({ structuredItinerary: ITINERARY, savedItineraryId: 'a1' });
    addGuestItinerary({ structuredItinerary: ITINERARY_B, savedItineraryId: 'a2' });
    expect(getGuestItineraries()).toHaveLength(2);
  });

  it('content-equality dedupe against most recent entry (rapid-fire guard)', () => {
    addGuestItinerary({ structuredItinerary: ITINERARY });
    addGuestItinerary({ structuredItinerary: ITINERARY });
    expect(getGuestItineraries()).toHaveLength(1);
  });

  it('does NOT dedupe when content differs (different itinerary)', () => {
    addGuestItinerary({ structuredItinerary: ITINERARY });
    addGuestItinerary({ structuredItinerary: ITINERARY_B });
    expect(getGuestItineraries()).toHaveLength(2);
  });

  it('caps at MAX_ENTRIES (20) dropping oldest', () => {
    for (let i = 0; i < 21; i++) {
      addGuestItinerary({ structuredItinerary: { itineraryItems: [{ day: i }] } });
    }
    expect(getGuestItineraries()).toHaveLength(20);
  });

  it('ignores entries without structuredItinerary', () => {
    // @ts-expect-error — deliberately passing invalid entry
    addGuestItinerary({ structuredItinerary: null });
    expect(getGuestItineraries()).toHaveLength(0);
  });

  it('tolerates localStorage.setItem errors gracefully', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded');
    });
    expect(() => addGuestItinerary({ structuredItinerary: ITINERARY })).not.toThrow();
    spy.mockRestore();
  });
});

describe('removeGuestItinerary', () => {
  it('removes entry matching savedItineraryId', () => {
    addGuestItinerary({ structuredItinerary: ITINERARY, savedItineraryId: 'keep' });
    addGuestItinerary({ structuredItinerary: ITINERARY_B, savedItineraryId: 'remove' });
    const toRemove = getGuestItineraries().find((e) => e.savedItineraryId === 'remove')!;
    removeGuestItinerary(toRemove);
    const remaining = getGuestItineraries();
    expect(remaining).toHaveLength(1);
    expect(remaining[0]?.savedItineraryId).toBe('keep');
  });

  it('removes entry by createdAt when no savedItineraryId', () => {
    // Pre-populate with distinct createdAt values to avoid same-millisecond collision
    localStorage.setItem(
      KEY,
      JSON.stringify({
        entries: [
          { structuredItinerary: ITINERARY_B, createdAt: Date.now() },
          { structuredItinerary: ITINERARY, createdAt: Date.now() - 1000 },
        ],
      }),
    );
    const all = getGuestItineraries();
    expect(all).toHaveLength(2);
    removeGuestItinerary(all[0]!);
    expect(getGuestItineraries()).toHaveLength(1);
  });
});

describe('clearGuestItineraries', () => {
  it('removes all entries', () => {
    addGuestItinerary({ structuredItinerary: ITINERARY });
    addGuestItinerary({ structuredItinerary: ITINERARY_B });
    clearGuestItineraries();
    expect(getGuestItineraries()).toEqual([]);
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('is a no-op when nothing is stored', () => {
    expect(() => clearGuestItineraries()).not.toThrow();
  });
});
