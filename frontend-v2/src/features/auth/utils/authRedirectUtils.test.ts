import { describe, it, expect } from 'vitest';
import {
  checkRedirectToChatAfterAuth,
  getRedirectToChatAfterAuth,
  setRedirectToChatAfterSearch,
} from './authRedirectUtils';
import { isPublicRoute, PUBLIC_ROUTES } from '../constants';

describe('authRedirectUtils', () => {
  it('checkRedirectToChatAfterAuth returns fallback', () => {
    expect(checkRedirectToChatAfterAuth()).toEqual({ redirect: 'fallback' });
  });

  it('getRedirectToChatAfterAuth returns fallback', () => {
    expect(getRedirectToChatAfterAuth()).toEqual({ redirect: 'fallback' });
  });

  it('setRedirectToChatAfterSearch is a no-op', () => {
    expect(() => setRedirectToChatAfterSearch('anything')).not.toThrow();
  });
});

describe('auth constants', () => {
  describe('isPublicRoute', () => {
    it('returns true for all PUBLIC_ROUTES', () => {
      for (const route of PUBLIC_ROUTES) {
        expect(isPublicRoute(route)).toBe(true);
      }
    });

    it('returns false for protected routes', () => {
      expect(isPublicRoute('/home')).toBe(false);
      expect(isPublicRoute('/chat')).toBe(false);
      expect(isPublicRoute('/profile')).toBe(false);
    });

    it('returns true for parameterized subpaths of public routes', () => {
      expect(isPublicRoute('/reset-password/token123')).toBe(true);
      expect(isPublicRoute('/complete-registration/xyz')).toBe(true);
      expect(isPublicRoute('/forgot-password/extra')).toBe(true);
      expect(isPublicRoute('/public/chat')).toBe(true);
    });

    it('does not match / as prefix for other paths', () => {
      expect(isPublicRoute('/home')).toBe(false);
      expect(isPublicRoute('/chat')).toBe(false);
    });
  });
});
