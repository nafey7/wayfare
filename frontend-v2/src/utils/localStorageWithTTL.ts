export const TTL_24H_MS = 24 * 60 * 60 * 1000;

interface StoredEntry<T> {
  value: T;
  expiresAt: number;
}

export function readWithTTL<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== 'object' || parsed === null) return null;
    const obj = parsed as Record<string, unknown>;
    // Legacy entries stored before the TTL wrapper was introduced have no expiresAt key.
    // Return them as-is so the search form doesn't reset on first load after a deploy.
    // The next write will replace them with the TTL-wrapped format.
    if (!('expiresAt' in obj)) {
      return obj as unknown as T;
    }
    if (typeof obj.expiresAt !== 'number' || Date.now() > obj.expiresAt) {
      localStorage.removeItem(key);
      return null;
    }
    return obj.value as T;
  } catch {
    return null;
  }
}

export function writeWithTTL<T>(key: string, value: T, ttlMs: number): void {
  try {
    const entry: StoredEntry<T> = { value, expiresAt: Date.now() + ttlMs };
    localStorage.setItem(key, JSON.stringify(entry));
  } catch {
    // quota / private mode
  }
}

export function removeWithTTL(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // ignore
  }
}
