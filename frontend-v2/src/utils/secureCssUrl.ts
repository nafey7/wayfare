/**
 * Validates a URL for safe use inside a CSS `url(...)` value.
 * Rejects `data:`, protocol-relative `//`, breakout characters, and control bytes.
 */
const CSS_URL_SPECIAL = new Set(['\\', '"', "'", '(', ')', '<', '>', ';', '`']);

function hasUnsafeCssUrlChars(value: string): boolean {
  for (const ch of value) {
    if (CSS_URL_SPECIAL.has(ch)) return true;
    const c = ch.charCodeAt(0);
    if (c < 32) return true;
  }
  return false;
}

export function isSafeCssBackgroundUrl(value: string): boolean {
  if (!value || value.length > 8192) return false;
  const v = value.trim();
  if (v.startsWith('https://') || v.startsWith('http://')) {
    return !hasUnsafeCssUrlChars(v);
  }
  if (v.startsWith('/') && !v.startsWith('//')) {
    return !hasUnsafeCssUrlChars(v);
  }
  return false;
}
