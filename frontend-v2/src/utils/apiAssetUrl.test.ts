import { describe, it, expect } from 'vitest';
import { resolveBackendAssetUrl, resolveBackendAssetUrlOptional } from './apiAssetUrl';

describe('apiAssetUrl', () => {
  it('resolveBackendAssetUrl returns http URLs unchanged', () => {
    expect(resolveBackendAssetUrl('https://cdn.example.com/img.jpg')).toBe(
      'https://cdn.example.com/img.jpg',
    );
  });

  it('resolveBackendAssetUrlOptional returns null for empty input', () => {
    expect(resolveBackendAssetUrlOptional(null)).toBeNull();
    expect(resolveBackendAssetUrlOptional(undefined)).toBeNull();
    expect(resolveBackendAssetUrlOptional('')).toBeNull();
    expect(resolveBackendAssetUrlOptional('   ')).toBeNull();
  });

  it('resolveBackendAssetUrl keeps path in output for API paths', () => {
    const out = resolveBackendAssetUrl('/api/places/photos/x');
    expect(out).toContain('/api/places/photos/x');
  });
});
