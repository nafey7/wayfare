import { describe, it, expect, beforeEach, vi } from 'vitest';

// vi.resetModules() clears the module registry so _cachedOrigin resets between tests.
describe('appendOriginToPrompt', () => {
  beforeEach(() => {
    vi.resetModules();
    sessionStorage.clear();
  });

  it('appends the stored session origin to the prompt', async () => {
    sessionStorage.setItem('voya_chat_origin', 'London');
    const { appendOriginToPrompt } = await import('./inspirationTripChat');
    expect(appendOriginToPrompt('See Kyoto')).toBe('See Kyoto. My origin is London');
  });

  it('returns the same origin on repeated calls within a session', async () => {
    sessionStorage.setItem('voya_chat_origin', 'Paris');
    const { appendOriginToPrompt } = await import('./inspirationTripChat');
    const origin = (p: string) => p.split('My origin is ')[1];
    expect(origin(appendOriginToPrompt('trip A'))).toBe(origin(appendOriginToPrompt('trip B')));
  });

  it('picks a different city when destination matches the cached origin', async () => {
    sessionStorage.setItem('voya_chat_origin', 'Tokyo');
    const { appendOriginToPrompt } = await import('./inspirationTripChat');
    const result = appendOriginToPrompt('See Tokyo temples', 'Tokyo');
    expect(result).not.toMatch(/My origin is Tokyo$/);
    expect(result).toMatch(/My origin is London$/);
  });

  it('uses the explicit origin (e.g. detected location) when provided', async () => {
    sessionStorage.setItem('voya_chat_origin', 'London');
    const { appendOriginToPrompt } = await import('./inspirationTripChat');
    expect(appendOriginToPrompt('See Kyoto', 'Tokyo', 'Berlin')).toBe(
      'See Kyoto. My origin is Berlin',
    );
  });

  it('substitutes when explicit origin matches the destination', async () => {
    const { appendOriginToPrompt } = await import('./inspirationTripChat');
    const result = appendOriginToPrompt('See Berlin nightlife', 'Berlin', 'Berlin');
    expect(result).not.toMatch(/My origin is Berlin$/);
  });
});
