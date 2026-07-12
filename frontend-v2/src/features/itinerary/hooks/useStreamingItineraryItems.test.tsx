/**
 * Tests for ``useStreamingItineraryItems`` — issue #1117 piece 4d.
 *
 * Verifies the partial-snapshot reshaping from Redux into the
 * ``ItineraryItem[]`` shape consumed by the existing itinerary
 * components, including defensive handling of camelCase/snake_case key
 * variations and missing fields during early partials.
 */

import { describe, expect, it, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { Provider } from 'react-redux';
import type { ReactNode } from 'react';

import { makeTestStore } from '@/store';
import {
  clearStreamingItinerary,
  setStreamingItinerary,
} from '@/store/slices/chatSlice';

import { useStreamingItineraryItems } from './useStreamingItineraryItems';

let store: ReturnType<typeof makeTestStore>;

function wrap({ children }: { children: ReactNode }) {
  return <Provider store={store}>{children}</Provider>;
}

beforeEach(() => {
  store = makeTestStore();
});

describe('useStreamingItineraryItems', () => {
  it('returns inactive + null items when streaming has not started', () => {
    const { result } = renderHook(() => useStreamingItineraryItems(), {
      wrapper: wrap,
    });
    expect(result.current).toEqual({ items: null, active: false });
  });

  it('reports active=true with no items when streaming started but no partial yet', () => {
    // setStreamingItinerary always sets active=true; an empty-ish partial
    // simulates "stream started but parser hasn't emitted anything useful".
    store.dispatch(setStreamingItinerary({}));
    const { result } = renderHook(() => useStreamingItineraryItems(), {
      wrapper: wrap,
    });
    expect(result.current.active).toBe(true);
    expect(result.current.items).toBeNull();
  });

  it('shapes camelCase itineraryItems into ItineraryItem[]', () => {
    store.dispatch(
      setStreamingItinerary({
        itineraryItems: [
          { day: 1, title: 'Arrival' },
          {
            day: 2,
            title: 'Vatican',
            description: 'See the highlights.',
            imageUrl: 'https://example.com/vatican.jpg',
          },
        ],
      }),
    );
    const { result } = renderHook(() => useStreamingItineraryItems(), {
      wrapper: wrap,
    });
    expect(result.current.active).toBe(true);
    expect(result.current.items).toEqual([
      {
        day: 1,
        title: 'Arrival',
        description: '',
        imageUrl: '',
        expandedContent: null,
      },
      {
        day: 2,
        title: 'Vatican',
        description: 'See the highlights.',
        imageUrl: 'https://example.com/vatican.jpg',
        expandedContent: null,
      },
    ]);
  });

  it('accepts snake_case keys (some Gemini parser shapes)', () => {
    store.dispatch(
      setStreamingItinerary({
        itinerary_items: [
          {
            day: 1,
            title: 'Arrival',
            image_url: 'https://example.com/x.jpg',
            expanded_content: { activities: [{ location: 'Hotel' }] },
          },
        ],
      }),
    );
    const { result } = renderHook(() => useStreamingItineraryItems(), {
      wrapper: wrap,
    });
    expect(result.current.items?.[0]).toMatchObject({
      day: 1,
      title: 'Arrival',
      imageUrl: 'https://example.com/x.jpg',
    });
    // expandedContent passes through (cast as opaque — actual shape
    // matches ExpandedDayContent in production where the parser emits it).
    expect(result.current.items?.[0]?.expandedContent).toEqual({
      activities: [{ location: 'Hotel' }],
    });
  });

  it('drops malformed day entries (missing day number or title)', () => {
    store.dispatch(
      setStreamingItinerary({
        itineraryItems: [
          { day: 1, title: 'Good day' },
          { title: 'Day number missing — should be dropped' },
          { day: 2 }, // title missing — dropped
          'not even an object', // dropped
        ],
      }),
    );
    const { result } = renderHook(() => useStreamingItineraryItems(), {
      wrapper: wrap,
    });
    expect(result.current.items).toHaveLength(1);
    expect(result.current.items?.[0]?.day).toBe(1);
  });

  it('returns inactive after clearStreamingItinerary fires', () => {
    store.dispatch(
      setStreamingItinerary({
        itineraryItems: [{ day: 1, title: 'Arrival' }],
      }),
    );
    store.dispatch(clearStreamingItinerary());
    const { result } = renderHook(() => useStreamingItineraryItems(), {
      wrapper: wrap,
    });
    expect(result.current).toEqual({ items: null, active: false });
  });
});
