/**
 * Strapi REST base URL and request helpers (separate from Voya backend {@link baseApi}).
 */
export function getStrapiBaseUrl(): string | undefined {
  const raw = import.meta.env.VITE_STRAPI_URL as string | undefined;
  if (!raw?.trim()) return undefined;
  return raw.replace(/\/?$/, '');
}

export function strapiApiUrl(path: string): string | undefined {
  const base = getStrapiBaseUrl();
  if (!base) return undefined;
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${base}${p}`;
}

export function strapiRequestHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  const token = import.meta.env.VITE_STRAPI_API_TOKEN as string | undefined;
  if (token?.trim()) {
    headers.Authorization = `Bearer ${token.trim()}`;
  }
  return headers;
}
