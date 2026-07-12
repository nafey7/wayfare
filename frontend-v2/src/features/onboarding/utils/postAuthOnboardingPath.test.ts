import { describe, it, expect, beforeEach } from 'vitest';
import {
  clearPostAuthOnboardingPath,
  consumePostAuthOnboardingPath,
  stashPostAuthOnboardingPath,
} from './postAuthOnboardingPath';
import { ROUTES } from '@/features/routing/constants';

describe('postAuthOnboardingPath', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('stashes and consumes an allowed path', () => {
    stashPostAuthOnboardingPath(ROUTES.ONBOARDING_TRIP);
    expect(consumePostAuthOnboardingPath()).toBe(ROUTES.ONBOARDING_TRIP);
    expect(consumePostAuthOnboardingPath()).toBeNull();
  });

  it('ignores stashing disallowed paths', () => {
    stashPostAuthOnboardingPath('/evil-redirect');
    expect(sessionStorage.length).toBe(0);
  });

  it('returns null for tampered session value on consume', () => {
    sessionStorage.setItem('voya_post_auth_onboarding_path', '/not-onboarding');
    expect(consumePostAuthOnboardingPath()).toBeNull();
  });

  it('clears the stash', () => {
    stashPostAuthOnboardingPath(ROUTES.ONBOARDING_LOCATION);
    clearPostAuthOnboardingPath();
    expect(consumePostAuthOnboardingPath()).toBeNull();
  });
});
