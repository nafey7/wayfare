import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readWithTTL, writeWithTTL, removeWithTTL, TTL_24H_MS } from './localStorageWithTTL';

const NOW = 1_000_000_000_000; // fixed timestamp

beforeEach(() => {
  localStorage.clear();
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('writeWithTTL / readWithTTL', () => {
  it('stores and retrieves a value before expiry', () => {
    writeWithTTL('key', { foo: 'bar' }, TTL_24H_MS);
    expect(readWithTTL('key')).toEqual({ foo: 'bar' });
  });

  it('returns null and removes key after expiry', () => {
    writeWithTTL('key', { foo: 'bar' }, TTL_24H_MS);
    vi.setSystemTime(NOW + TTL_24H_MS + 1);
    expect(readWithTTL('key')).toBeNull();
    expect(localStorage.getItem('key')).toBeNull();
  });

  it('returns null for a missing key', () => {
    expect(readWithTTL('nonexistent')).toBeNull();
  });

  it('returns legacy value for entries without expiresAt key (deploy-migration compatibility)', () => {
    const legacy = { from: 'LAX', to: 'NYC' };
    localStorage.setItem('key', JSON.stringify(legacy));
    expect(readWithTTL('key')).toEqual(legacy);
    // Legacy entry is NOT evicted — next write will replace it with the TTL format
    expect(localStorage.getItem('key')).not.toBeNull();
  });

  it('returns null and evicts data with expiresAt: null', () => {
    localStorage.setItem('key', JSON.stringify({ value: { x: 1 }, expiresAt: null }));
    expect(readWithTTL('key')).toBeNull();
    expect(localStorage.getItem('key')).toBeNull();
  });

  it('returns null and evicts data with expiresAt: "string"', () => {
    localStorage.setItem('key', JSON.stringify({ value: { x: 1 }, expiresAt: 'tomorrow' }));
    expect(readWithTTL('key')).toBeNull();
    expect(localStorage.getItem('key')).toBeNull();
  });

  it('returns null gracefully for invalid JSON', () => {
    localStorage.setItem('key', 'not-json');
    expect(readWithTTL('key')).toBeNull();
  });
});

describe('removeWithTTL', () => {
  it('removes a stored key', () => {
    writeWithTTL('key', 42, TTL_24H_MS);
    removeWithTTL('key');
    expect(readWithTTL('key')).toBeNull();
  });

  it('does not throw for a missing key', () => {
    expect(() => removeWithTTL('nonexistent')).not.toThrow();
  });
});
