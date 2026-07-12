import { describe, expect, it } from 'vitest';
import {
  FLIGHT_DETAILS_MULTICITY_SEGMENT,
  ROUTES,
  flightDetailsPath,
  toRelativePath,
  isPublicChatContentRoute,
  publicToAuthRoute,
  authToPublicRoute,
  getContentDomain,
  getContentRoutePrefix,
} from './constants';

describe('toRelativePath', () => {
  it('strips a single leading slash for React Router path props', () => {
    expect(toRelativePath(ROUTES.HOME)).toBe('home');
    expect(toRelativePath(ROUTES.PUBLIC_CHAT)).toBe('public/chat');
  });

  it('returns paths without a leading slash unchanged', () => {
    expect(toRelativePath('already-relative')).toBe('already-relative');
  });
});

describe('flightDetailsPath', () => {
  it('builds multi-city trip details URL with reserved segment', () => {
    expect(flightDetailsPath(FLIGHT_DETAILS_MULTICITY_SEGMENT)).toBe(
      `${ROUTES.FLIGHTS}/details/multicity`
    );
  });

  it('encodes fare tokens for single-leg details', () => {
    expect(flightDetailsPath('abc::token')).toBe(`${ROUTES.FLIGHTS}/details/abc%3A%3Atoken`);
  });
});

describe('isPublicChatContentRoute', () => {
  it('returns true for public chat content sub-routes', () => {
    expect(isPublicChatContentRoute('/public/chat/itinerary')).toBe(true);
    expect(isPublicChatContentRoute('/public/chat/flights/recommendations')).toBe(true);
    expect(isPublicChatContentRoute('/public/chat/hotels/search')).toBe(true);
  });

  it('returns false for the public chat root', () => {
    expect(isPublicChatContentRoute('/public/chat')).toBe(false);
  });

  it('returns false for non-public-chat routes', () => {
    expect(isPublicChatContentRoute('/flights/recommendations')).toBe(false);
    expect(isPublicChatContentRoute('/chat')).toBe(false);
  });
});

describe('publicToAuthRoute', () => {
  it('strips /public/chat prefix', () => {
    expect(publicToAuthRoute('/public/chat/flights/recommendations')).toBe('/flights/recommendations');
    expect(publicToAuthRoute('/public/chat/itinerary')).toBe('/itinerary');
  });

  it('returns /chat for /public/chat itself (authenticated shell for the same surface)', () => {
    expect(publicToAuthRoute('/public/chat')).toBe(ROUTES.CHAT);
  });

  it('passes through non-public paths', () => {
    expect(publicToAuthRoute('/flights/search')).toBe('/flights/search');
  });
});

describe('authToPublicRoute', () => {
  it('adds /public/chat prefix', () => {
    expect(authToPublicRoute('/flights/recommendations')).toBe('/public/chat/flights/recommendations');
    expect(authToPublicRoute('/itinerary')).toBe('/public/chat/itinerary');
  });
});

describe('getContentDomain', () => {
  it('detects flights from both prefixes', () => {
    expect(getContentDomain('/flights/search')).toBe('flights');
    expect(getContentDomain('/public/chat/flights/recommendations')).toBe('flights');
  });

  it('detects hotels from both prefixes', () => {
    expect(getContentDomain('/hotels/search')).toBe('hotels');
    expect(getContentDomain('/public/chat/hotels/search')).toBe('hotels');
  });

  it('detects itinerary from both prefixes', () => {
    expect(getContentDomain('/itinerary')).toBe('itinerary');
    expect(getContentDomain('/public/chat/itinerary/abc')).toBe('itinerary');
  });

  it('returns null for unrelated paths', () => {
    expect(getContentDomain('/chat')).toBeNull();
    expect(getContentDomain('/profile')).toBeNull();
  });
});

describe('getContentRoutePrefix', () => {
  it('returns /public/chat on public chat routes', () => {
    expect(getContentRoutePrefix('/public/chat')).toBe('/public/chat');
    expect(getContentRoutePrefix('/public/chat/flights/recommendations')).toBe('/public/chat');
  });

  it('returns empty string on authenticated routes', () => {
    expect(getContentRoutePrefix('/flights/search')).toBe('');
    expect(getContentRoutePrefix('/chat')).toBe('');
  });
});
