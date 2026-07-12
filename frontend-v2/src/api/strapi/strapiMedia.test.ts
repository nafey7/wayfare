import { describe, it, expect } from 'vitest';
import { absoluteMediaUrl, pickMediaUrl } from './strapiMedia';

describe('absoluteMediaUrl', () => {
  it('returns absolute URLs unchanged', () => {
    expect(absoluteMediaUrl('https://cdn.example.com/a.jpg', 'http://localhost:1337')).toBe(
      'https://cdn.example.com/a.jpg',
    );
  });

  it('prefixes relative uploads with Strapi base', () => {
    expect(absoluteMediaUrl('/uploads/foo.webp', 'http://localhost:1337')).toBe(
      'http://localhost:1337/uploads/foo.webp',
    );
  });
});

describe('pickMediaUrl', () => {
  const base = 'http://localhost:1337';

  it('reads Strapi v4 media shape', () => {
    const media = {
      data: {
        id: 1,
        attributes: {
          url: '/uploads/hero.jpg',
        },
      },
    };
    expect(pickMediaUrl(media, base)).toBe('http://localhost:1337/uploads/hero.jpg');
  });

  it('returns undefined for empty data', () => {
    expect(pickMediaUrl({ data: null }, base)).toBeUndefined();
  });
});
