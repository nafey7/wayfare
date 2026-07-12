import { describe, it, expect } from 'vitest';
import { isSafeCssBackgroundUrl } from './secureCssUrl';

describe('isSafeCssBackgroundUrl', () => {
  it('allows http(s) and same-origin paths', () => {
    expect(isSafeCssBackgroundUrl('https://cdn.example.com/a.jpg')).toBe(true);
    expect(isSafeCssBackgroundUrl('http://localhost/uploads/x.png')).toBe(true);
    expect(isSafeCssBackgroundUrl('/uploads/hero.jpg')).toBe(true);
  });

  it('rejects protocol-relative, data URLs, and breakout characters', () => {
    expect(isSafeCssBackgroundUrl('//evil.com/x.jpg')).toBe(false);
    expect(isSafeCssBackgroundUrl('data:image/svg+xml,<svg/>')).toBe(false);
    expect(isSafeCssBackgroundUrl('https://x.com/a)url(evil)')).toBe(false);
    expect(isSafeCssBackgroundUrl('https://x.com/a\\')).toBe(false);
    expect(isSafeCssBackgroundUrl('https://x.com/a"')).toBe(false);
    expect(isSafeCssBackgroundUrl('https://x.com/a\'')).toBe(false);
  });
});
