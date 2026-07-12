import type { FetchBaseQueryError } from '@reduxjs/toolkit/query/react';

/** Guards guest Places session-token refresh after repeated 401/403 (see ChatContext). */

export const MAX_PLACES_SESSION_FORBIDDEN_REFRESH_ATTEMPTS = 5;

const BASE_BACKOFF_MS = 400;
/** Upper bound for exponential backoff. With the default attempt cap (5), the series tops out at 6400ms before the last slot; this mainly protects hypothetical callers that raise the attempt limit. */
const MAX_BACKOFF_MS = 10_000;

/** Backoff when the refresh request fails without a client HTTP response (network, 5xx, etc.) so we do not burn a cap slot. */
export const TRANSIENT_PLACES_SESSION_REFRESH_BACKOFF_MS = 2_000;

function isFetchBaseQueryErrorLike(error: unknown): error is FetchBaseQueryError {
  return typeof error === 'object' && error !== null && 'status' in error;
}

/**
 * Whether a failed refresh should consume one of the per-session cap attempts.
 * Transient conditions (no HTTP 4xx from the client’s perspective) do not count so 5xx / network blips cannot exhaust the budget before a later success.
 */
export function shouldCountPlacesSessionRefreshFailureTowardCap(error: unknown): boolean {
  if (!isFetchBaseQueryErrorLike(error)) {
    return false;
  }
  const { status } = error;
  return typeof status === 'number' && status >= 400 && status < 500;
}

/**
 * Delay before the next refresh attempt after a completed run (`count` = completed
 * refreshes so far this public-chat session). Caps tight loops even when mint returns 200.
 */
export function computePlacesSessionForbiddenBackoffMs(completedRefreshCount: number): number {
  if (completedRefreshCount <= 0) {
    return 0;
  }
  return Math.min(MAX_BACKOFF_MS, BASE_BACKOFF_MS * 2 ** (completedRefreshCount - 1));
}
