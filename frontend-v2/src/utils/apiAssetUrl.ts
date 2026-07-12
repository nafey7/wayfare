/**
 * Backend origin and absolute URL resolution for API assets (images, proxies).
 * Used when the page origin differs from the API (e.g. Vite dev server).
 */

const API_BASE = import.meta.env.VITE_API_URL ?? '/api';

/** Origin derived from VITE_API_URL, or empty for same-origin relative paths. */
export function getBackendOriginFromApiBase(): string {
  const trimmed = String(API_BASE).trim();
  if (!trimmed || trimmed.startsWith('/')) {
    return '';
  }
  try {
    return new URL(trimmed).origin;
  } catch {
    return import.meta.env.DEV ? 'http://localhost:8000' : '';
  }
}

/**
 * Resolves a path or URL to an absolute URL for fetch or img src
 * (matches prior getFetchUrl / getFullUrl behavior in hotel image components).
 */
export function resolveBackendAssetUrl(url: string): string {
  const u = url.trim();
  if (u.startsWith('http')) return u;
  const origin = getBackendOriginFromApiBase();
  return origin ? `${origin}${u.startsWith('/') ? '' : '/'}${u}` : u;
}

/** Same as resolveBackendAssetUrl but returns null for empty/missing input. */
export function resolveBackendAssetUrlOptional(
  url: string | null | undefined,
): string | null {
  if (url == null || typeof url !== 'string') return null;
  const trimmed = url.trim();
  if (!trimmed) return null;
  return resolveBackendAssetUrl(trimmed);
}

// Third-party airline logo CDN (undocumented; GIF per IATA/ICAO code).
// Used as a fallback when the backend does not supply logo_url.
const AIRLINE_LOGO_CDN = 'https://travelnext.works/api/airlines';

/**
 * Returns the fallback CDN URL for an airline logo, or null if the code is
 * absent / fails the basic IATA/ICAO format check.
 */
export function airlineLogoFallbackUrl(code: string | null | undefined): string | null {
  if (!code) return null;
  const safe = code.trim().toUpperCase();
  return /^[A-Z0-9]{2,3}$/.test(safe) ? `${AIRLINE_LOGO_CDN}/${safe}.gif` : null;
}
