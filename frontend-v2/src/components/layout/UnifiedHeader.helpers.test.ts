import { describe, it, expect } from 'vitest';
import { resolveSection, resolveCenterVariant } from './UnifiedHeader';

describe('resolveSection', () => {
  it('returns flights for /flights paths', () => {
    expect(resolveSection('/flights')).toBe('flights');
    expect(resolveSection('/flights/recommendations')).toBe('flights');
    expect(resolveSection('/flights/search')).toBe('flights');
  });

  it('returns hotels for /hotels paths', () => {
    expect(resolveSection('/hotels')).toBe('hotels');
    expect(resolveSection('/hotels/search')).toBe('hotels');
  });

  it('returns itinerary for /itinerary paths', () => {
    expect(resolveSection('/itinerary')).toBe('itinerary');
    expect(resolveSection('/itinerary/abc123')).toBe('itinerary');
  });

  it('returns itinerary for /itineraries (prefix overlap)', () => {
    expect(resolveSection('/itineraries')).toBe('itinerary');
    expect(resolveSection('/itineraries/abc123')).toBe('itinerary');
  });

  it('returns null for chat and root paths', () => {
    expect(resolveSection('/')).toBeNull();
    expect(resolveSection('/chat')).toBeNull();
    expect(resolveSection('/profile')).toBeNull();
  });

  it('strips /public/chat prefix before resolving', () => {
    expect(resolveSection('/public/chat/flights/recommendations')).toBe('flights');
    expect(resolveSection('/public/chat/hotels/search')).toBe('hotels');
    expect(resolveSection('/public/chat/itinerary')).toBe('itinerary');
    expect(resolveSection('/public/chat')).toBeNull();
  });
});

describe('resolveCenterVariant', () => {
  it('returns flights for /flights paths', () => {
    expect(resolveCenterVariant('/flights')).toBe('flights');
    expect(resolveCenterVariant('/flights/search')).toBe('flights');
  });

  it('returns hotels for /hotels paths', () => {
    expect(resolveCenterVariant('/hotels')).toBe('hotels');
    expect(resolveCenterVariant('/hotels/search')).toBe('hotels');
  });

  it('returns chat for all other paths', () => {
    expect(resolveCenterVariant('/')).toBe('chat');
    expect(resolveCenterVariant('/chat')).toBe('chat');
    expect(resolveCenterVariant('/itinerary')).toBe('chat');
    expect(resolveCenterVariant('/profile')).toBe('chat');
  });

  it('strips /public/chat prefix before resolving', () => {
    expect(resolveCenterVariant('/public/chat/flights/recommendations')).toBe('flights');
    expect(resolveCenterVariant('/public/chat/hotels')).toBe('hotels');
    expect(resolveCenterVariant('/public/chat')).toBe('chat');
    expect(resolveCenterVariant('/public/chat/itinerary')).toBe('chat');
  });
});
