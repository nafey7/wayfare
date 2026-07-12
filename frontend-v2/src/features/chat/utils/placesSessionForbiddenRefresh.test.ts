import { describe, expect, it } from 'vitest';

import {
  computePlacesSessionForbiddenBackoffMs,
  MAX_PLACES_SESSION_FORBIDDEN_REFRESH_ATTEMPTS,
  shouldCountPlacesSessionRefreshFailureTowardCap,
  TRANSIENT_PLACES_SESSION_REFRESH_BACKOFF_MS,
} from './placesSessionForbiddenRefresh';

describe('computePlacesSessionForbiddenBackoffMs', () => {
  it('returns 0 for non-positive completed counts', () => {
    expect(computePlacesSessionForbiddenBackoffMs(0)).toBe(0);
    expect(computePlacesSessionForbiddenBackoffMs(-1)).toBe(0);
  });

  it('doubles backoff with a cap', () => {
    expect(computePlacesSessionForbiddenBackoffMs(1)).toBe(400);
    expect(computePlacesSessionForbiddenBackoffMs(2)).toBe(800);
    expect(computePlacesSessionForbiddenBackoffMs(3)).toBe(1600);
    expect(computePlacesSessionForbiddenBackoffMs(10)).toBe(10_000);
  });
});

describe('MAX_PLACES_SESSION_FORBIDDEN_REFRESH_ATTEMPTS', () => {
  it('is 5 — maximum completed refresh runs per public-chat session', () => {
    expect(MAX_PLACES_SESSION_FORBIDDEN_REFRESH_ATTEMPTS).toBe(5);
  });
});

describe('TRANSIENT_PLACES_SESSION_REFRESH_BACKOFF_MS', () => {
  it('is 2000ms — backoff after 5xx / network refresh failures without consuming a cap slot', () => {
    expect(TRANSIENT_PLACES_SESSION_REFRESH_BACKOFF_MS).toBe(2_000);
  });
});

describe('shouldCountPlacesSessionRefreshFailureTowardCap', () => {
  it('counts 401 toward cap (e.g. refresh fails when the session header is invalid)', () => {
    expect(
      shouldCountPlacesSessionRefreshFailureTowardCap({ status: 401, data: {} })
    ).toBe(true);
  });

  it('counts other client 4xx from RTK (429 rate limit, 404, etc.)', () => {
    expect(
      shouldCountPlacesSessionRefreshFailureTowardCap({ status: 429, data: {} })
    ).toBe(true);
    expect(
      shouldCountPlacesSessionRefreshFailureTowardCap({ status: 404, data: {} })
    ).toBe(true);
  });

  it('does not count 5xx, FETCH_ERROR, or non-errors', () => {
    expect(
      shouldCountPlacesSessionRefreshFailureTowardCap({ status: 503, data: {} })
    ).toBe(false);
    expect(
      shouldCountPlacesSessionRefreshFailureTowardCap({ status: 'FETCH_ERROR', error: 'Failed' })
    ).toBe(false);
    expect(shouldCountPlacesSessionRefreshFailureTowardCap(new Error('network'))).toBe(false);
  });
});
