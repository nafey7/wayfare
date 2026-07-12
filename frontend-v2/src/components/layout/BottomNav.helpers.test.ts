import { describe, it, expect } from 'vitest';
import { resolveActiveTab, shouldShowChatTab } from './BottomNav';

describe('resolveActiveTab', () => {
  it('returns account for /profile paths', () => {
    expect(resolveActiveTab('/profile')).toBe('account');
    expect(resolveActiveTab('/profile/settings')).toBe('account');
  });

  it('returns trips for /itinerary paths', () => {
    expect(resolveActiveTab('/itinerary')).toBe('trips');
    expect(resolveActiveTab('/itinerary/abc123')).toBe('trips');
  });

  it('returns trips for /itineraries (prefix overlap with /itinerary)', () => {
    expect(resolveActiveTab('/itineraries')).toBe('trips');
    expect(resolveActiveTab('/itineraries/abc123')).toBe('trips');
  });

  it('returns explore for /chat paths (chat tab removed)', () => {
    expect(resolveActiveTab('/chat')).toBe('explore');
  });

  it('returns explore for /public/chat paths (chat tab removed)', () => {
    expect(resolveActiveTab('/public/chat')).toBe('explore');
    expect(resolveActiveTab('/public/chat/flights/recommendations')).toBe('explore');
  });

  it('returns explore for all other paths', () => {
    expect(resolveActiveTab('/')).toBe('explore');
    expect(resolveActiveTab('/flights')).toBe('explore');
    expect(resolveActiveTab('/hotels')).toBe('explore');
    expect(resolveActiveTab('/home')).toBe('explore');
  });
});

describe('shouldShowChatTab', () => {
  it('returns true for /home and /home/* sub-paths', () => {
    expect(shouldShowChatTab('/home')).toBe(true);
    expect(shouldShowChatTab('/home/anything')).toBe(true);
  });

  it('returns true for /profile and sub-paths', () => {
    expect(shouldShowChatTab('/profile')).toBe(true);
    expect(shouldShowChatTab('/profile/settings')).toBe(true);
  });

  it('returns true for /itineraries and sub-paths', () => {
    expect(shouldShowChatTab('/itineraries')).toBe(true);
    expect(shouldShowChatTab('/itineraries/abc123')).toBe(true);
  });

  it('returns false for flights, hotels, chat, and itinerary (with-chat) routes', () => {
    expect(shouldShowChatTab('/chat')).toBe(false);
    expect(shouldShowChatTab('/flights')).toBe(false);
    expect(shouldShowChatTab('/flights/search')).toBe(false);
    expect(shouldShowChatTab('/hotels')).toBe(false);
    expect(shouldShowChatTab('/itinerary')).toBe(false);
    expect(shouldShowChatTab('/itinerary/abc123')).toBe(false);
  });

  it('returns true for / (public landing page)', () => {
    expect(shouldShowChatTab('/')).toBe(true);
  });

  it('returns false for /public/chat and other non-nav routes', () => {
    expect(shouldShowChatTab('/public/chat')).toBe(false);
  });

  it('returns false for public content routes (ChatSheet handles mobile chat there)', () => {
    expect(shouldShowChatTab('/public/chat/flights/search')).toBe(false);
    expect(shouldShowChatTab('/public/chat/hotels/search')).toBe(false);
    expect(shouldShowChatTab('/public/chat/itinerary')).toBe(false);
  });
});
