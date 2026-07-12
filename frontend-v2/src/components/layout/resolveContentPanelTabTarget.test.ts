import { describe, it, expect } from 'vitest';
import { resolveTarget } from './resolveContentPanelTabTarget';

const PUBLIC_PREFIX = '/public/chat';

describe('resolveTarget', () => {
  it('returns fallback when stored path is null or undefined', () => {
    expect(resolveTarget(null, `${PUBLIC_PREFIX}/itinerary`, PUBLIC_PREFIX)).toBe(
      `${PUBLIC_PREFIX}/itinerary`
    );
    expect(resolveTarget(undefined, `${PUBLIC_PREFIX}/itinerary`, PUBLIC_PREFIX)).toBe(
      `${PUBLIC_PREFIX}/itinerary`
    );
  });

  it('auth context (prefix empty): uses fallback when stored path is public-prefixed', () => {
    expect(resolveTarget(`${PUBLIC_PREFIX}/itinerary`, '/itinerary', '')).toBe('/itinerary');
    expect(
      resolveTarget(`${PUBLIC_PREFIX}/flights/search?q=x`, '/flights/search', '')
    ).toBe('/flights/search');
  });

  it('auth context (prefix empty): keeps auth-scoped stored path', () => {
    expect(resolveTarget('/flights/search?q=foo', '/flights/search', '')).toBe(
      '/flights/search?q=foo'
    );
    expect(resolveTarget('/itinerary', '/itinerary', '')).toBe('/itinerary');
  });

  it('public context: prefixes auth-scoped stored path and preserves query', () => {
    expect(
      resolveTarget('/flights/search?q=X', `${PUBLIC_PREFIX}/flights/search`, PUBLIC_PREFIX)
    ).toBe(`${PUBLIC_PREFIX}/flights/search?q=X`);
    expect(
      resolveTarget('/itinerary', `${PUBLIC_PREFIX}/itinerary`, PUBLIC_PREFIX)
    ).toBe(`${PUBLIC_PREFIX}/itinerary`);
  });

  it('public context: keeps already-prefixed stored path', () => {
    expect(
      resolveTarget(
        `${PUBLIC_PREFIX}/flights/search?q=Y`,
        `${PUBLIC_PREFIX}/flights/search`,
        PUBLIC_PREFIX
      )
    ).toBe(`${PUBLIC_PREFIX}/flights/search?q=Y`);
  });

  it('public context: returns fallback when stored path is not a known content path', () => {
    expect(resolveTarget('/other', `${PUBLIC_PREFIX}/flights/search`, PUBLIC_PREFIX)).toBe(
      `${PUBLIC_PREFIX}/flights/search`
    );
  });
});
