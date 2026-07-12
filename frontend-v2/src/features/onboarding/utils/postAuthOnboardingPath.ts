/**
 * When a guest opens the auth modal from onboarding, we stash the route they should
 * land on after a successful sign-in (e.g. trip step). Consumed in AuthModal after login.
 */

const SESSION_KEY = 'voya_post_auth_onboarding_path';

const ALLOWED_PATHS = new Set<string>([
  '/onboarding',
  '/onboarding/welcome',
  '/onboarding/location',
  '/onboarding/trip',
]);

function isAllowedPath(path: string): boolean {
  return ALLOWED_PATHS.has(path);
}

export function stashPostAuthOnboardingPath(path: string): void {
  if (!isAllowedPath(path)) return;
  try {
    sessionStorage.setItem(SESSION_KEY, path);
  } catch {
    /* quota / private mode */
  }
}

/**
 * Returns the stashed path once, then removes it. Returns null if missing or invalid.
 */
export function consumePostAuthOnboardingPath(): string | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(SESSION_KEY);
    return isAllowedPath(raw) ? raw : null;
  } catch {
    return null;
  }
}

export function clearPostAuthOnboardingPath(): void {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* ignore */
  }
}
